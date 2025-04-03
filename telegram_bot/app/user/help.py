import os
import asyncio
from aiogram import Router, F
from django.conf import settings
from django.core.files import File
from asgiref.sync import sync_to_async
from telegram_app.models import Question
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile, CallbackQuery
from telegram_bot.app.utils import get_user_from_db, get_admins, IsUserFilter
from telegram_bot.app.user.utils import user_escape_markdown
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from telegram_bot.app.user.utils import user_keyboard_back_to_help_section

user_help_router = Router()

class UserHelpFSM(StatesGroup):
    user_waiting_help_start = State()
    user_waiting_for_category_of_question = State()
    user_waiting_for_question = State()
    user_waiting_for_text_after_photo = State()
    user_waiting_for_my_questions = State()
    

# Utils 
CATEGORY_MAPPING = {
    "🔧 Texnik yordam": "technical",
    "📦 Buyurtmalar": "orders",
    "💬 Umumiy savollar": "general",
}

async def send_question_to_admins(message: Message, question, user):
    admins = await get_admins()
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Qabul qilish", callback_data=f"admin_claim_question:{question.id}")
    builder.button(text="❌", callback_data="user_delete_message")
    user_name = user_escape_markdown(user.full_name)

    question_text = (
        f"❗️<b>Diqqat yangi murojaat</b>❗️\n"
        f"📌 <b>Savol IDsi</b>: {question.id}\n"
        f"👤 <b>Kimdan</b>: <a href='tg://user?id={user.telegram_id}'>{user_name}</a> \n"
        f"📂 <b>Savol turi</b>: {question.get_category_display()} bo'yicha\n"
        f"📜 <b>Savol matni</b>: {question.text}\n\n"
        f" <i>Ushbu savolga murojaatlar bo'limidan kirib javob berishingiz mumkin.</i>"

    )
    tasks = []
    for admin in admins:
        if question.photo and os.path.exists(question.photo.path):
            try:
                photo_file = FSInputFile(question.photo.path, filename=os.path.basename(question.photo.path))
                tasks.append(
                    message.bot.send_photo(
                        chat_id=admin.telegram_id,
                        photo=photo_file,
                        caption=question_text,
                        parse_mode="HTML"
                    )
                )
            except Exception as e:
                print(f"Error loading photo: {e}")
                tasks.append(
                    message.bot.send_message(
                        chat_id=admin.telegram_id,
                        text=f"⚠️ Rasmni yuklashda xatolik yuz berdi.\n\n{question_text}",
                        parse_mode="HTML"
                    )
                )
        else:
            tasks.append(
                message.bot.send_message(
                    chat_id=admin.telegram_id,
                    text=question_text,
                    parse_mode="HTML"
                )
            )
    await asyncio.gather(*tasks, return_exceptions=True)

async def user_format_question_info(question):
    """Format a question's information for display."""
    status_display = question.get_status_display()
    category_display = question.get_category_display()
    return (
        f"📂 <b>Savol turi:</b> {category_display}\n"
        f"📜 <b>Savol:</b> {question.text or '—'}\n"
        + (f"📢 <b>Holati:</b> {status_display}\n" if status_display != 'Javob berilgan'  else "")
        + (f"👤 <b>Javob bergan shaxs:</b> {question.claimed_by}\n" if status_display == 'Javob berilgan' else "")
        + (f"💬 <b>Javob:</b> {question.answer}\n" if status_display == 'Javob berilgan' else "")
    )

def user_help_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Mening murojaatlarim")
    builder.button(text="🔧 Texnik yordam")
    builder.button(text="📦 Buyurtmalar")
    builder.button(text="💬 Umumiy savollar")
    builder.button(text="⬅️ Bosh menu")
    builder.adjust(1, 2) 
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def user_handle_search_questions_result(message: Message, questions, state: FSMContext, previous_message_id=None):
    """Handle the result of fetching questions and initiate pagination."""
    if not questions:
        if isinstance(message, CallbackQuery):
            await message.message.answer("❌ Savollar topilmadi.")
        else:
            await message.answer("❌ Savollar topilmadi.")
        return
    await state.update_data(search_results=questions)
    
    questions_with_numbers = [(index + 1, question) for index, question in enumerate(questions)]
    total_pages = ((len(questions_with_numbers) + 9) // 10)  # 10 questions per page
    if previous_message_id:
        await user_display_fetched_questions_list(1, message, questions_with_numbers, total_pages, 10, "user_search_question", state, previous_message_id)
    else:
        await user_display_fetched_questions_list(1, message, questions_with_numbers, total_pages, 10, "user_search_question", state)

async def user_handle_get_all_questions_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    """Handle pagination for subsequent pages of questions."""
    data_parts = callback_query.data.split(':')
    if len(data_parts) != 2:
        await callback_query.answer("❌ Xatolik qaytadan urinib ko'ring.")
        return
    
    page_num = int(data_parts[1])
    data = await state.get_data()
    questions = data.get("search_results", [])
    if not questions:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, sahifani qaytadan yuklang.", show_alert=True)
        return
    
    questions_with_numbers = [(index + 1, question) for index, question in enumerate(questions)]
    total_pages = (len(questions_with_numbers) + 9) // 10
    await user_display_fetched_questions_list(page_num, callback_query, questions_with_numbers, total_pages, 10, callback_prefix, state)
    await callback_query.answer()

async def user_display_fetched_questions_list(page_num, callback_query_or_message, questions_with_numbers, total_pages, questions_per_page, callback_prefix, state, previous_message_id=None):
    """Display a paginated list of questions."""
    start_index = (page_num - 1) * questions_per_page
    end_index = min(start_index + questions_per_page, len(questions_with_numbers))
    page_questions = questions_with_numbers[start_index:end_index]

    message_text = (
        f"📋 <b>Sizning savollaringiz:</b>\n\n"
        f"🔍 <b>Umumiy natija:</b> {len(questions_with_numbers)} ta savol topildi.\n"
        f"📜 <b>Sahifa natijasi:</b> {start_index + 1}-{end_index}:\n\n"
    )
    for number, question in page_questions:
        message_text += f"{number}. {question.text[:18]}... — {question.get_category_display()} ({question.get_status_display()})\n"

    # Build pagination buttons
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()
    for number, question in page_questions:
        builder.button(text=str(number), callback_data=f"user_selected_question:{question.id}")

    builder.adjust(5)

    if total_pages > 1:
        navigation_buttons = []
        if page_num > 1:
            navigation_buttons.append({"text": "⬅️", "callback_data": f"{callback_prefix}_other_pages:{page_num - 1}"})
        navigation_buttons.append({"text": "❌", "callback_data": "user_delete_message"})
        if page_num < total_pages:
            navigation_buttons.append({"text": "➡️", "callback_data": f"{callback_prefix}_other_pages:{page_num + 1}"})
        
        for btn in navigation_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(len(navigation_buttons))
    else:
        pagination.button(text="❌", callback_data="user_delete_message")
        pagination.adjust(1)

    question_keyboard = builder.as_markup()
    question_keyboard.inline_keyboard.extend(pagination.as_markup().inline_keyboard)
    question_keyboard.inline_keyboard.extend(user_keyboard_back_to_help_section().inline_keyboard)

    # Send or edit the message
    if isinstance(callback_query_or_message, CallbackQuery):
        new_message = await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=question_keyboard, parse_mode="HTML"
        )
    elif previous_message_id:
        new_message = await callback_query_or_message.bot.edit_message_text(
            text=message_text,
            chat_id=callback_query_or_message.chat.id,
            message_id=previous_message_id,
            reply_markup=question_keyboard,
            parse_mode="HTML"
        )
    else:
        new_message = await callback_query_or_message.answer(
            text=message_text, reply_markup=question_keyboard, parse_mode="HTML"
        )
        await state.update_data(search_result_message_id=new_message.message_id)
    
    await state.update_data(message_ids=[new_message.message_id])

@user_help_router.message(UserHelpFSM.user_waiting_help_start)
async def user_help_start(message: Message, state: FSMContext):
    await message.answer("Savolingiz qaysi bo'limga tegishli?", reply_markup=user_help_menu_keyboard())

@user_help_router.message(UserHelpFSM.user_waiting_for_category_of_question)
async def user_select_category_of_question(message: Message, state: FSMContext):
    await state.update_data(category=CATEGORY_MAPPING[message.text])
    await message.answer("Bizga 3 xil usulda savol yo'llashingiz mumkin! 😊"
                         "\n✍️ Savolingizni faqat matn ko'rinishida yuboring."
                         "\n📸 Rasm yuborib keyin matnli xabar yuboring."
                         "\n🖼 Savolingizni rasmning izohiga matn sifatida yozib yuboring."
                         f"\n\nSizni {message.text.lower()} bo'yicha nima savol qiziqtiryapti?")
    await state.set_state(UserHelpFSM.user_waiting_for_question)

@user_help_router.message(UserHelpFSM.user_waiting_for_question)
async def user_get_question_from_users_and_send(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    data = await state.get_data() or {}
    category = data.get("category")

    if message.text and not message.photo:
        question_text = message.text.strip()
        question = await sync_to_async(Question.objects.create)(
            user=user, text=question_text, category=category
        )
        await send_question_to_admins(message, question, user)
        await message.answer("✅ Savolingiz tegishli bo'limga yuborildi! Tez orada javob berishadi 😊")
        await state.clear()
    elif message.photo and message.caption:
        caption = message.caption.strip()
        photo_file_id = message.photo[-1].file_id
        file = await message.bot.get_file(photo_file_id)
        file_path = os.path.join(settings.MEDIA_ROOT, 'question_photos', f"{file.file_id}.jpg")
        try:
            await message.bot.download_file(file.file_path, file_path)
            with open(file_path, 'rb') as f:
                question = await sync_to_async(Question.objects.create)(
                    user=user,
                    category=category,
                    text=caption,
                    photo=File(f, name=os.path.basename(file_path)),
                )
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
        await send_question_to_admins(message, question, user)
        await message.answer("✅ Savolingiz tegishli bo'limga yuborildi! Tez orada javob berishadi 😊")
        await state.clear()
    elif message.photo and not message.caption:
        photo_file_id = message.photo[-1].file_id
        await state.update_data(photo=photo_file_id)
        await message.answer("Rasm qabul qilindi. Endi savolingizni yozing!")
        await state.set_state(UserHelpFSM.user_waiting_for_text_after_photo)
    else:
        await message.answer(f"Hurmatli {user.full_name}, savolni faqat matni yoki rasm ko'rinishida yuboring!")

@user_help_router.message(UserHelpFSM.user_waiting_for_text_after_photo)
async def user_add_text_after_photo(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    data = await state.get_data() or {}
    photo_file_id = data.get("photo")
    category = data.get("category")

    if not photo_file_id or not category:
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        return
    
    if message.text:
        file = await message.bot.get_file(photo_file_id)
        file_path = os.path.join(settings.MEDIA_ROOT, 'question_photos', f"{file.file_id}.jpg")
        try:
            await message.bot.download_file(file.file_path, file_path)
            with open(file_path, 'rb') as f:
                question = await sync_to_async(Question.objects.create)(
                    user=user,
                    category=category,
                    text=message.text.strip(),
                    photo=File(f, name=os.path.basename(file_path)),
                )
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
        await send_question_to_admins(message, question, user)
        await message.answer("✅ Savolingiz tegishli bo'limga yuborildi! Tez orada javob berishadi 😊")
        await state.clear()
    else:
        await message.answer(f"Hurmatli {user.full_name}, faqat matni yoki rasm ko'rinishida yuboring!")

# Updated handler for viewing questions with pagination
@user_help_router.message(UserHelpFSM.user_waiting_for_my_questions)
async def user_view_my_questions(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    questions = await sync_to_async(list)(Question.objects.filter(user=user).order_by("-created_at"))
    await user_handle_search_questions_result(message, questions, state)

# Callback handler for pagination
@user_help_router.callback_query(IsUserFilter(), F.data.startswith('user_search_question_other_pages:'))
async def user_get_all_questions_other_pages_callback(callback_query: CallbackQuery, state: FSMContext):
    await user_handle_get_all_questions_other_pages(callback_query, state, callback_prefix="user_search_question")

# Callback handler for selecting a question
@user_help_router.callback_query(IsUserFilter(), F.data.startswith('user_selected_question:'))
async def user_get_selected_question_callback(callback_query: CallbackQuery, state: FSMContext):
    question_id = int(callback_query.data.split(':')[1])
    await callback_query.answer()

    question = await sync_to_async(Question.objects.filter(id=question_id).select_related('claimed_by').first)()
    
    if not question:
        await callback_query.message.answer("❌ Savol topilmadi.")
        return

    question_info = await user_format_question_info(question)
    builder = InlineKeyboardBuilder()
    builder.button(text="❌", callback_data="user_delete_message")
    keyboard = builder.as_markup()

    if question.photo and os.path.exists(question.photo.path):
        try:
            input_file = FSInputFile(
                question.photo.path, filename=os.path.basename(question.photo.path))
            await callback_query.message.answer_photo(
                input_file, parse_mode='HTML', caption=question_info, reply_markup=keyboard
            )
        except Exception as e:
            await callback_query.message.answer(
                f"Rasmni yuklashda xatolik yuz berdi.\n\n{question_info}",
                parse_mode='HTML', reply_markup=keyboard
            )
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(
            parse_mode='HTML', text=question_info, reply_markup=keyboard
        )













        