import os
from aiogram import Router, F
from django.db.models import Count, Q
from asgiref.sync import sync_to_async
from telegram_app.models import Question
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile, CallbackQuery
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_bot.app.admin.utils import admin_keyboard_back_to_appeals_section
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

admin_help_router = Router()

class AdminHelpFSM(StatesGroup):
    admin_waiting_help_start = State()
    admin_waiting_category_selection = State()
    admin_waiting_view_questions = State()
    admin_waiting_question_action = State()
    admin_waiting_answer_text = State()
    

# Category Mapping
CATEGORY_MAPPING = {
    "🔧 Texnik yordam": "technical",
    "📦 Buyurtmalar": "orders",
    "💬 Umumiy savollar": "general",
}

# Utils
async def admin_show_statistics(message: Message):
    stats = await sync_to_async(lambda: Question.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status="pending")),
        claimed=Count('id', filter=Q(status="claimed")),
        answered=Count('id', filter=Q(status="answered"))
    ))()

    stats_message = (
        "📊 <b>Savollar bo‘yicha statistika:</b>\n\n"
        f"🔢 <b>Kelib tushgan savollar soni:</b> {stats['total']} ta\n"
        f"⏳ <b>Javob berilishi kutilayotgan:</b> {stats['pending']} ta\n"
        f"👨‍💼 <b>Ko'rib chiqilmoqda:</b> {stats['claimed']} ta\n"
        f"✅ <b>Javob berilgan:</b> {stats['answered']} ta"
    )

    await message.answer(stats_message, parse_mode="HTML", reply_markup=admin_help_menu_keyboard())

def admin_help_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    for display_name in CATEGORY_MAPPING.keys():
        builder.button(text=display_name)
    builder.button(text="📊 Savollar statistikasi")
    builder.button(text="◀️ Bosh menu")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def admin_format_question_info(question):
    """Format a question's information for display to admins."""
    status_display = question.get_status_display()
    category_display = question.get_category_display()
    user_name = question.user.full_name if question.user else "Anonim"
    claimed_by = question.claimed_by.full_name if question.claimed_by else "Hech kim"
    return (
        f"📌 <b>Savol IDsi:</b> {question.id}\n"
        f"👤 <b>Kimdan:</b> {user_name}\n"
        f"📂 <b>Savol turi:</b> {category_display}\n"
        f"📜 <b>Matni:</b> {question.text or '—'}\n"
        f"📢 <b>Holati:</b> {status_display}\n"
        f"👨‍💼 <b>Qabul qilgan:</b> {claimed_by}\n"
        + (f"💬 <b>Javob:</b> {question.answer}\n" if question.answer else "")
    )

async def admin_send_answer_to_user(bot, question, answer_text):
    """Send the admin's answer to the user who asked the question."""
    user = question.user
    if not user or not user.telegram_id:
        return

    answer_message = (
        f"<b>Assalamu Aleykum ismim {question.claimed_by}</b> 😊\n\n"
        f"📩 <b>Savolingizga javob:</b>\n"
        f"📜 <b>Savolingiz:</b> {question.text}\n"
        f"💬 <b>Javob:</b> {answer_text}"
    )
    
    if question.photo and os.path.exists(question.photo.path):
        try:
            photo_file = FSInputFile(question.photo.path, filename=os.path.basename(question.photo.path))
            await bot.send_photo(
                chat_id=user.telegram_id,
                photo=photo_file,
                caption=answer_message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending photo: {e}")
            await bot.send_message(
                chat_id=user.telegram_id,
                text=f"⚠️ Rasmni yuklashda xatolik yuz berdi.\n\n{answer_message}",
                parse_mode="HTML"
            )
    else:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=answer_message,
            parse_mode="HTML"
        )

async def admin_display_questions_list(page_num, callback_query_or_message, questions, total_pages, questions_per_page, state, category_name):
    """Display a paginated list of questions for admins."""
    start_index = (page_num - 1) * questions_per_page
    end_index = min(start_index + questions_per_page, len(questions))
    page_questions = questions[start_index:end_index]

    message_text = (
        f"📋 <b>{category_name} bo‘yicha savollar:</b>\n\n"
        f"🔍 <b>Umumiy natija:</b> {len(questions)} ta savol topildi.\n"
        f"📜 <b>Sahifa natijasi:</b> {start_index + 1}-{end_index}:\n\n"
    )
    for idx, question in enumerate(page_questions, start=start_index + 1):
        claimed_by = question.claimed_by.full_name if question.claimed_by else "Yo‘q"
        message_text += f"{idx}. {question.text[:18]}... — {question.get_status_display()}\n"

    builder = InlineKeyboardBuilder()
    for idx, question in enumerate(page_questions, start=start_index + 1):
        builder.button(text=str(idx), callback_data=f"admin_select_question:{question.id}")
    builder.adjust(5)

    pagination = InlineKeyboardBuilder()
    if total_pages > 1:
        navigation_buttons = []
        if page_num > 1:
            navigation_buttons.append({"text": "⬅️", "callback_data": f"admin_view_questions_other_pages:{page_num - 1}"})
        navigation_buttons.append({"text": "❌", "callback_data": "admin_delete_message"})
        if page_num < total_pages:
            navigation_buttons.append({"text": "➡️", "callback_data": f"admin_view_questions_other_pages:{page_num + 1}"})
        
        for btn in navigation_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(len(navigation_buttons))
    else:
        pagination.button(text="❌", callback_data="admin_delete_message")
        pagination.adjust(1)

    keyboard = builder.as_markup()
    keyboard.inline_keyboard.extend(pagination.as_markup().inline_keyboard)
    keyboard.inline_keyboard.extend(admin_keyboard_back_to_appeals_section().inline_keyboard)

    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        new_message = await callback_query_or_message.answer(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
        await state.update_data(message_ids=[new_message.message_id])

# Handlers
@admin_help_router.message(AdminHelpFSM.admin_waiting_help_start)
async def admin_help_start(message: Message, state: FSMContext):
    await message.answer("Admin qaysi turdagi murojaatlarga javob bermoqchisiz? Tanlang 👇", reply_markup=admin_help_menu_keyboard())
    await state.set_state(AdminHelpFSM.admin_waiting_category_selection)

@admin_help_router.message(AdminHelpFSM.admin_waiting_category_selection)
async def admin_select_category(message: Message, state: FSMContext):
    category_display = message.text
    category_value = CATEGORY_MAPPING[category_display]
    questions = await sync_to_async(list)(
        Question.objects.filter(
            category=category_value,
            status__in=["pending", "claimed"]
        ).select_related('claimed_by').order_by("-created_at")
    )
    
    if not questions:
        await message.answer(f"❌ {category_display} bo‘yicha ko‘rib chiqilishi kerak bo‘lgan savollar yo‘q.")
        return

    await state.update_data(questions=questions, selected_category=category_display)
    total_pages = (len(questions) + 9) // 10 
    await admin_display_questions_list(1, message, questions, total_pages, 10, state, category_display)
    await state.set_state(AdminHelpFSM.admin_waiting_view_questions)

@admin_help_router.callback_query(IsAdminFilter(), F.data.startswith("admin_view_questions_other_pages:"))
async def admin_view_questions_other_pages(callback_query: CallbackQuery, state: FSMContext):
    page_num = int(callback_query.data.split(":")[1])
    data = await state.get_data()
    questions = data.get("questions", [])
    category_display = data.get("selected_category", "Savollar")
    if not questions:
        await callback_query.answer("❌ Savollar topilmadi. Sahifani qayta yuklang.")
        return

    total_pages = (len(questions) + 9) // 10
    await admin_display_questions_list(page_num, callback_query, questions, total_pages, 10, state, category_display)
    await callback_query.answer()

@admin_help_router.callback_query(IsAdminFilter(), F.data.startswith("admin_select_question:"))
async def admin_select_question(callback_query: CallbackQuery, state: FSMContext):
    question_id = int(callback_query.data.split(":")[1])
    question = await sync_to_async(Question.objects.filter(id=question_id).select_related('user', 'claimed_by').first)()
    if not question:
        await callback_query.message.answer("❌ Savol topilmadi.")
        return

    admin = await get_user_from_db(callback_query.from_user.id)
    await state.update_data(selected_question_id=question_id)
    question_info = await admin_format_question_info(question)
    
    builder = InlineKeyboardBuilder()
    if question.status == "pending":
        builder.button(text="✅ Qabul qilish", callback_data=f"admin_claim_question:{question_id}")
    elif question.status == "claimed":
        if question.claimed_by != admin:
            await callback_query.answer("⚠️ Bu savol boshqa admin tomondan qabul qilgan, agar javob berishni xohlasangiz ❗️Qabul qilish tugmasini bosing.", show_alert=True)
            builder.button(text="❗ Qabul qilish", callback_data=f"admin_claim_question:{question_id}")
        else:
            builder.button(text="✍️ Javob berish", callback_data=f"admin_answer_question:{question_id}")
    builder.button(text="❌", callback_data="admin_delete_message")
    keyboard = builder.as_markup()

    if question.photo and os.path.exists(question.photo.path):
        try:
            input_file = FSInputFile(question.photo.path, filename=os.path.basename(question.photo.path))
            await callback_query.message.answer_photo(input_file, parse_mode='HTML', caption=question_info, reply_markup=keyboard)
        except Exception as e:
            await callback_query.message.answer(f"Rasmni yuklashda xatolik yuz berdi.\n\n{question_info}", parse_mode='HTML', reply_markup=keyboard)
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(
            parse_mode='HTML', text=question_info, reply_markup=keyboard
        )
    await callback_query.answer()
    await state.set_state(AdminHelpFSM.admin_waiting_question_action)

@admin_help_router.callback_query(IsAdminFilter(), F.data.startswith("admin_claim_question:"))
async def admin_claim_question(callback_query: CallbackQuery, state: FSMContext):
    question_id = int(callback_query.data.split(":")[1])
    question = await sync_to_async(Question.objects.filter(id=question_id).select_related('claimed_by', 'user').first)()
    if not question:
        await callback_query.answer("❌ Savol topilmadi.")
        return

    admin = await get_user_from_db(callback_query.from_user.id)
    if admin.role not in ["Admin", "Superadmin"]:
        await callback_query.answer("❌ Sizda bu savolni qabul qilish huquqi yo‘q.")
        return

    # Agar savol pending yoki claimed bo'lsa, claimed_by ni yangi admin bilan yangilaymiz
    if question.status in ["pending", "claimed"]:
        if question.claimed_by != admin:
            previous_admin = question.claimed_by.full_name if question.claimed_by else "Hech kim"
            question.status = Question.STATUS_CLAIMED
            question.claimed_by = admin
            await sync_to_async(question.save)()
            await callback_query.answer(f"✅ Savol {previous_admin} dan sizga o‘tkazildi.")
        else:
            previous_admin = question.claimed_by.full_name if question.claimed_by else "Hech kim"
            question.status = Question.STATUS_CLAIMED
            question.claimed_by = admin
            await sync_to_async(question.save)()
            await callback_query.answer("✅ Bu savol allaqachon siz tomondan qabul qilingan edi.")
    else:
        await callback_query.answer("❌ Bu savolga allaqachon javob berilgan.")
        return

    question_info = await admin_format_question_info(question)
    await state.update_data(selected_question_id=question_id)
    
    # Xabar rasmli yoki matnli ekanligini tekshirish
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Javob berish", callback_data=f"admin_answer_question:{question_id}")
    builder.button(text="❌", callback_data="admin_delete_message")
    keyboard = builder.as_markup()

    if callback_query.message.photo:  # Agar xabar rasmli bo'lsa
        await callback_query.message.edit_caption(
            caption=question_info,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:  # Agar xabar oddiy matn bo'lsa
        await callback_query.message.edit_text(
            text=question_info,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await callback_query.answer()

@admin_help_router.callback_query(IsAdminFilter(), F.data.startswith("admin_answer_question:"))
async def admin_prompt_answer_question(callback_query: CallbackQuery, state: FSMContext):
    question_id = int(callback_query.data.split(":")[1])
    question = await sync_to_async(Question.objects.filter(id=question_id).select_related('claimed_by').first)()
    
    if not question:
        await callback_query.answer("❌ Savol topilmadi.")
        return
    
    if question.status != "claimed":
        await callback_query.answer("❌ Savol qabul qilinmagan.")
        return

    admin = await get_user_from_db(callback_query.from_user.id)
    if question.claimed_by != admin:
        await callback_query.answer("❌ Bu savol siz tomonidan qabul qilinmagan.")
        return

    await state.update_data(selected_question_id=question_id)
    await callback_query.message.answer("Savolga javobingizni yozing:")
    await state.set_state(AdminHelpFSM.admin_waiting_answer_text)
    await callback_query.answer()

@admin_help_router.message(AdminHelpFSM.admin_waiting_answer_text)
async def admin_submit_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    question_id = data.get("selected_question_id")
    if not question_id:
        await message.answer("❌ Savol tanlanmadi. Qaytadan urinib ko'ring.")
        return

    question = await sync_to_async(Question.objects.filter(id=question_id).select_related('claimed_by', 'user').first)()
    if not question:
        await message.answer("❌ Savol topilmadi.")
        return

    admin = await get_user_from_db(message.from_user.id)
    if question.claimed_by != admin:
        await message.answer("❌ Bu savol siz tomonidan qabul qilinmagan.")
        return

    answer_text = message.text.strip()
    question.answer = answer_text
    question.status = Question.STATUS_ANSWERED
    await sync_to_async(question.save)()

    await admin_send_answer_to_user(message.bot, question, answer_text)
    await message.answer("✅ Javob muvaffaqiyatli yuborildi!")
    await state.clear()
