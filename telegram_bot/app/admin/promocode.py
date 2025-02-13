from aiogram import Router, F
import asyncio
from django.utils import timezone
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Promocode 
from telegram_bot.app.admin.utils import skip_inline_button, single_item_buttons, confirmation_keyboard, ACTIVITY_KEYBOARD
from telegram_bot.app.admin.main_controls import PROMOCODE_CONTROLS_KEYBOARD

# Create a router for admin handlers
promocode_router = Router()





#Promocode part start
class PromocodeFSM(StatesGroup):
    waiting_promocode_add = State()
    waiting_promocode_discount_percentage = State()
    waiting_promocode_start_date = State()
    waiting_promocode_end_date = State()
    waiting_promocode_usage_limit = State()
    waiting_promocode_activity = State()
    #Edit
    waiting_get_all_promocode = State ()
    waiting_edit_promocode = State()
    waiting_edit_promocode_by_code = State()
    waiting_edit_promocode_field = State()
    waiting_edit_promocode_discount_percentage = State()
    waiting_edit_promocode_start_date = State()
    waiting_edit_promocode_end_date = State()
    waiting_edit_promocode_usage_limit = State()
    waiting_edit_promocode_activity = State()
    waiting_edit_promocode_deletion = State()
    

# Main control handlers
@promocode_router.message(F.text.in_(("➕ Promocode qo'shish", "✒️ Promocodeni tahrirlash", "✨ Barcha promocodelarni ko'rish")))
async def promocode_controls_handler(message: Message, state: FSMContext):
    actions = {
        "➕ Promocode qo'shish": (PromocodeFSM.waiting_promocode_add, add_promocode),
        "✒️ Promocodeni tahrirlash": (PromocodeFSM.waiting_edit_promocode, edit_promocode),
        "✨ Barcha promocodelarni ko'rish": (PromocodeFSM.waiting_get_all_promocode, get_all_promocodes),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

# Adding promocode
@promocode_router.message(PromocodeFSM.waiting_promocode_add)
async def add_promocode(message: Message, state: FSMContext):
    promocode_template = (
        "📝 *Promokod yaratish quyidagi tartibda bo'ladi: 👇*\n\n"
        "📉 *Chegirma foizi:* \n"
        "📅🕙 *Boshlanish sanasi va soati:* \n"
        "📅🕛 *Tugash sanasi va soati:* \n"
        f"🔢 *Foydalanish chegarasi:* \n"
        f"🔢 *Foydalanilgan soni:* \n"
        "✅ *Faollik:* \n\n"
        "Promokod yaratish uchun kerakli ma'lumotlarni kiriting!"
    )
    await message.answer(text=promocode_template, parse_mode="Markdown")

    await message.answer("Promocode uchun chegirma foizini kiriting (masalan, 10 yoki 15.5):")
    await state.set_state(PromocodeFSM.waiting_promocode_discount_percentage)

@promocode_router.message(PromocodeFSM.waiting_promocode_discount_percentage)
async def set_promocode_discount_percentage(message: Message, state: FSMContext):
    try:
        discount_percentage = float(message.text.strip())
        if not (0 < discount_percentage <= 100):
            await message.answer("❌ Chegirma foizi 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        await state.update_data(discount_percentage=discount_percentage)
        await message.answer("Promocode boshlanish sanasini kiriting (masalan, 2025-05-15 10:00):")
        await state.set_state(PromocodeFSM.waiting_promocode_start_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")

@promocode_router.message(PromocodeFSM.waiting_promocode_start_date)
async def set_promocode_start_date(message: Message, state: FSMContext):
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        await state.update_data(start_date=start_date)
        await message.answer("Promocode tugash sanasini kiriting (masalan, 2025-05-25 23:59):")
        await state.set_state(PromocodeFSM.waiting_promocode_end_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")

@promocode_router.message(PromocodeFSM.waiting_promocode_end_date)
async def set_promocode_end_date(message: Message, state: FSMContext):
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)
        await state.update_data(end_date=end_date)
        await message.answer("Promocode foydalanish chegarasini kiriting (masalan, 100):")
        await state.set_state(PromocodeFSM.waiting_promocode_usage_limit)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")

@promocode_router.message(PromocodeFSM.waiting_promocode_usage_limit)
async def set_promocode_usage_limit(message: Message, state: FSMContext):
    try:
        usage_limit = int(message.text.strip())
        if usage_limit <= 0:
            await message.answer("❌ Foydalanish chegarasi 0 dan katta bo'lishi kerak.")
            return
        await state.update_data(usage_limit=usage_limit)
        await message.answer("Promocode faolligini tanlang (Faol/Nofaol):", reply_markup=ACTIVITY_KEYBOARD)
        await state.set_state(PromocodeFSM.waiting_promocode_activity)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 100).")

@promocode_router.message(PromocodeFSM.waiting_promocode_activity)
async def set_promocode_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        is_active = activity == "✅ Faol"
        await state.update_data(is_active=is_active)
        await save_promocode(message, state)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")

async def save_promocode(message, state):
    user = await get_user_from_db(message.from_user.id)

    data = await state.get_data()
    discount_percentage = data.get("discount_percentage")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    usage_limit = data.get("usage_limit")
    is_active = data.get("is_active")

    promocode = await sync_to_async(Promocode.objects.create)(
        owner = user,
        updated_by = user,
        discount_percentage=discount_percentage,
        valid_from=start_date,
        valid_until=end_date,
        usage_limit=usage_limit,
        is_active=is_active,
    )

    await message.answer(f"✅ Promocode '{promocode.code}' muvaffaqiyatli yaratildi.", reply_markup=PROMOCODE_CONTROLS_KEYBOARD)
    await state.clear()

#search
async def format_promocode_info(promocode):
    promocode_info = (
        f"📝 Promocode: *{promocode.code}*\n"
        f"📉 Chegirma foizi: *{int(promocode.discount_percentage) if promocode.discount_percentage % 1 == 0 else promocode.discount_percentage} %* \n"
        f"📅🕙 Boshlanish sanasi: *{promocode.valid_from.strftime('%Y-%m-%d %H:%M')}*\n"
        f"📅🕛 Tugash sanasi: *{promocode.valid_until.strftime('%Y-%m-%d %H:%M')}*\n"
        f"✅ Faollik: *{'Faol ✅' if promocode.is_active else 'Nofaol ❌'}*\n"
        f"🔢 Foydalanish chegarasi: *{promocode.usage_limit}*\n"
        f"🔢 Foydalanilgan soni: *{promocode.used_count}*\n"
    )
    return promocode_info

async def promocode_edit_keyboard(promocode_id):
    fields = ['Chegirma foizi', 'Boshlanish sanasi','Foydalanish chegarasi', 'Tugash sanasi',  'Faollik']
    keyboard = []
    for i in range(0, len(fields), 2):
        row = [
            InlineKeyboardButton(text=fields[i], callback_data=f"promo_field_{fields[i]}:{promocode_id}")
        ]
        if i + 1 < len(fields):
            row.append(InlineKeyboardButton(text=fields[i + 1], callback_data=f"promo_field_{fields[i+1]}:{promocode_id}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🗑 Promokodni o'chirish", callback_data=f"promocode_delete:{promocode_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Bosh menu", callback_data="◀️ Bosh menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def handle_promocode_search_results(message: Message, promocodes, state: FSMContext):
    if not promocodes:
        await message.answer("❌ Hech qanday promocode topilmadi.")
        return
    
    # Store the search results in the state
    await state.update_data(search_results=promocodes)
    
    promocodes_with_numbers = [(index + 1, promocode) for index, promocode in enumerate(promocodes)]
    total_pages = ((len(promocodes_with_numbers) + 9) // 10)
    await display_promocodes_page(1, message, promocodes_with_numbers, total_pages, 10, "search_promocode", state)

async def handle_promocode_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')

    page_num = int(data_parts[1])
    state_data = await state.get_data()
    promocodes = state_data.get("search_results", [])
   
    promocodes_with_numbers = [(index + 1, promocode) for index, promocode in enumerate(promocodes)]
    promocodes_per_page = 10
    total_pages = (len(promocodes_with_numbers) + promocodes_per_page - 1) // promocodes_per_page
    
    await display_promocodes_page(page_num, callback_query, promocodes_with_numbers, total_pages, promocodes_per_page, callback_prefix, state)
    await callback_query.answer()

async def display_promocodes_page(page_num, callback_query_or_message, promocodes_with_numbers, total_pages, promocodes_per_page, callback_prefix, state):
    start_index = (page_num - 1) * promocodes_per_page
    end_index = min(start_index + promocodes_per_page, len(promocodes_with_numbers))
    page_promocodes = promocodes_with_numbers[start_index:end_index]

    getting_process = await state.get_state() == PromocodeFSM.waiting_get_all_promocode
    
    message_text = (
        f"{ '✨ Promokodni ko\'rish bo\'limi:\n\n' if getting_process else '✒️ Promokodni tahrirlash bo\'limi: \n\n'} 🔍 Umumiy natija: {len(promocodes_with_numbers)} ta promokodlar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, promocode in page_promocodes:
        message_text += f"{number}. {promocode.code}\n"

    promocode_buttons = []
    row = []
    for number, promocode in page_promocodes:
        if getting_process:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"promocode:{promocode.id}:get"))
        else:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"promocode:{promocode.id}:none"))
        if len(row) == 5:
            promocode_buttons.append(row)
            row = []

    if row:
        promocode_buttons.append(row)

    pagination_buttons = []

    if total_pages > 1:
        if page_num > 1:
            pagination_buttons.append(InlineKeyboardButton(
                text="⬅️", callback_data=f"{callback_prefix}_other_pages:{page_num - 1}"))

        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))

        if page_num < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="➡️", callback_data=f"{callback_prefix}_other_pages:{page_num + 1}"))
    else:
        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=promocode_buttons + [pagination_buttons])
    
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )

async def update_and_clean_messages_promocode(message: Message, chat_id: int, message_id: int, text: str, promocode_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=(await promocode_edit_keyboard(promocode_id))
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)


@promocode_router.message(PromocodeFSM.waiting_get_all_promocode)
async def get_all_promocodes(message: Message, state: FSMContext):
    promocodes = await sync_to_async(list)(Promocode.objects.all())
    await handle_promocode_search_results(message, promocodes, state)

@promocode_router.callback_query(F.data.startswith('search_promocode_other_pages:'))
async def get_search_promocode_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_promocode_other_pages(callback_query, state, callback_prefix="search_promocode")

@promocode_router.callback_query(F.data.startswith('promocode:'))
async def get_single_promocode(callback_query: CallbackQuery):
    promocode_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    promocode = await sync_to_async(Promocode.objects.filter(id=promocode_id).first)()
    
    if not promocode:
        await callback_query.message.answer("❌ Promocode topilmadi.")
        await callback_query.answer()
        return
    
    promocode_info = await format_promocode_info(promocode)


    try:
        if action == "get":
            await callback_query.message.answer(text=promocode_info, parse_mode='Markdown', reply_markup=await single_item_buttons())
        else:
            await callback_query.message.answer(text=promocode_info, parse_mode='Markdown', reply_markup=await promocode_edit_keyboard(promocode_id))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Promokodni yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    await callback_query.answer()

#edit
@promocode_router.message(PromocodeFSM.waiting_edit_promocode)
async def edit_promocode(message: Message, state: FSMContext):
    await message.answer("Tahrirlash uchun promocode kodini kiriting: 👇")
    await state.set_state(PromocodeFSM.waiting_edit_promocode_by_code)

@promocode_router.message(PromocodeFSM.waiting_edit_promocode_by_code)
async def search_promocode_by_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    promocodes = await sync_to_async(list)(Promocode.objects.filter(code__icontains=code))
    await handle_promocode_search_results(message, promocodes, state)

@promocode_router.callback_query(F.data.startswith('promo_field_'))
async def promocode_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[2]
    promocode_id = int(callback_query.data.split(":")[1])

    user = await get_user_from_db(callback_query.from_user.id)
    promocode = await sync_to_async(Promocode.objects.filter(id=promocode_id).first)()

    if not promocode:
        await callback_query.answer("❌ Xatolik: Promokod topilmadi.")
        return
    
    field_actions = {
        "Chegirma foizi":       (PromocodeFSM.waiting_edit_promocode_discount_percentage),
        "Boshlanish sanasi":    (PromocodeFSM.waiting_edit_promocode_start_date),
        "Tugash sanasi":        (PromocodeFSM.waiting_edit_promocode_end_date),
        "Faollik":             (PromocodeFSM.waiting_edit_promocode_activity), 
        "Foydalanish chegarasi":(PromocodeFSM.waiting_edit_promocode_usage_limit),
        "deletepromocode":      (PromocodeFSM.waiting_edit_promocode_deletion),
    }   
        
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, promokodni asosiy bo‘limidan qaytadan tanlang.")
        return
    
    await state.update_data(message_id=message_id, chat_id=chat_id, promocode=promocode, user=user)

    next_state = field_actions[field]
    await state.set_state(next_state)



    if field == "deletepromocode":
        await callback_query.message.answer(f"Ushbu chegirmani o‘chirmoqchimisiz? 🗑", reply_markup=await confirmation_keyboard(promocode, promocode_id))
    elif field == "Faollik":
        await callback_query.message.answer(f"'{promocode}' chegirmasining yangi {field.lower()}ni tanlang:", reply_markup=ACTIVITY_KEYBOARD)
    else:
        await callback_query.message.answer(f"'{promocode}' chegirmasining yangi {field.lower()}ni kiriting:", reply_markup=ReplyKeyboardRemove())

    await callback_query.answer()

@promocode_router.message(PromocodeFSM.waiting_edit_promocode_discount_percentage)
async def edit_promocode_discount_percentage(message: Message, state: FSMContext):
    try:
        discount_percentage = float(message.text.strip())
        if not (0 < discount_percentage <= 100):
            await message.answer("❌ Chegirma foizi 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        data = await state.get_data()
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        promocode = data.get("promocode")

        if promocode.discount_percentage == discount_percentage:
            await message.answer(f"❌ Chegirma foizi allaqachon '{discount_percentage}'% da turibdi. Boshqa son kiriting: ")
            return
        
        if promocode:
            promocode.discount_percentage = discount_percentage
            promocode.updated_by = user

            await sync_to_async(promocode.save)()
            await message.answer(f"✅ Promokod chegirma foizi '{discount_percentage}'% ga yangilandi👆")
            text = await format_promocode_info(promocode)
            await update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
        else:
            await message.answer("❌ Promokod topilmadi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")

@promocode_router.message(PromocodeFSM.waiting_edit_promocode_start_date)
async def edit_promocode_start_date(message: Message, state: FSMContext):
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        
        data = await state.get_data()
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        promocode = data.get("promocode")

        if promocode.valid_from == start_date:
            await message.answer(f"❌ Promokod boshlanish sanasi allaqachon '{start_date.strftime('%Y-%m-%d %H:%M')}'da turibdi. Boshqa sana kiriting: ")
            return
        
        if promocode:
            promocode.valid_from = start_date
            promocode.updated_by = user
            await sync_to_async(promocode.save)()
            await message.answer(f"✅ Promokod boshlanish sanasi '{start_date.strftime('%Y-%m-%d %H:%M')}'ga yangilandi👆")
            text = await format_promocode_info(promocode)
            await update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
        else:
            await message.answer("❌ Promokod topilmadi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")

@promocode_router.message(PromocodeFSM.waiting_edit_promocode_end_date)
async def edit_promocode_end_date(message: Message, state: FSMContext):
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)
        
        data = await state.get_data()
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        promocode = data.get("promocode")

        if promocode.valid_until == end_date:
            await message.answer(f"❌ Promokod tugash sanasi  allaqachon '{end_date.strftime('%Y-%m-%d %H:%M')}'da turibdi. Boshqa sana kiriting: ")
            return
        
        if promocode:
            promocode.valid_until = end_date
            promocode.updated_by = user
            await sync_to_async(promocode.save)()
            await message.answer(f"✅ Promokod tugash sanasi '{end_date.strftime('%Y-%m-%d %H:%M')}' ga yangilandi👆")
            text = await format_promocode_info(promocode)
            await update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
        else:
            await message.answer("❌ Promokod topilmadi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")

@promocode_router.message(PromocodeFSM.waiting_edit_promocode_usage_limit)
async def edit_promocode_usage_limit(message: Message, state: FSMContext):  
    try:
        usage_limit = int(message.text.strip())
        if usage_limit <= 0:
            await message.answer("❌ Foydalanish chegarasi 0 dan katta bo'lishi kerak.")
            return
        
        data = await state.get_data()
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        promocode = data.get("promocode")
        promocode.updated_by = user


        if promocode.usage_limit == usage_limit:
            await message.answer(f"❌ Promokod foydalanish chegarasi allaqachon '{usage_limit}' ta turibdi. Boshqa son kiriting: ")
            return
        

        if promocode:
            promocode.usage_limit = usage_limit
            await sync_to_async(promocode.save)()
            await message.answer(f"✅ Promokod foydalanish chegarasi {usage_limit} ta ga yangilandi👆")
            text = await format_promocode_info(promocode)
            await update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
        else:
            await message.answer("❌ Promokod topilmadi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 100). ")

@promocode_router.message(PromocodeFSM.waiting_edit_promocode_activity)
async def edit_promocode_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        is_active = activity == "✅ Faol"
        
        data = await state.get_data()
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        promocode = data.get("promocode")
        
        if promocode.is_active == is_active:
            await message.answer(f"❌ Promokod faolligi allaqachon '{activity}'da turibdi. Boshqa holat kiriting: ")
            return
        
        if promocode:
            promocode.is_active = is_active
            promocode.updated_by = user
            await sync_to_async(promocode.save)()
            await message.answer(f"✅ Promokod faolligi {"'faol'" if is_active else "'nofaol'"} holatga yangilandi👆")
            text = await format_promocode_info(promocode)
            await update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
        else:
            await message.answer("❌ Promokod topilmadi.")
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")

#deletion
@promocode_router.callback_query(F.data.startswith("promocode_delete"))
async def promocode_delete_callback(callback_query: CallbackQuery, state: FSMContext):
 
    promocode_id = int(callback_query.data.split(":")[1])
    promocode = await sync_to_async(Promocode.objects.filter(id=promocode_id).first)()

    await state.update_data(category_id=promocode_id)
    await callback_query.message.edit_text(f"'{promocode.code}' promokodini o‘chirmoqchimisiz?", reply_markup=await confirmation_keyboard("promocode",promocode_id))
    
@promocode_router.callback_query(F.data.startswith("promocode_confirm_delete:"))
async def promocode_confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id, message_id = data.get("chat_id"), data.get("message_id")

    promocode_id = int(callback_query.data.split(":")[1])
    promocode = await sync_to_async(Promocode.objects.filter(id=promocode_id).first)()

    if not promocode:
        await callback_query.answer(f"⚠️ Promokod topilmadi. Admin qaytadan urinib ko'ring.")
        return
    
    try:
        await sync_to_async(promocode.delete)()  
        await callback_query.answer(f"✅ '{promocode.code}' promokodi o‘chirildi.")

        if message_id and chat_id:
            await callback_query.bot.delete_message(chat_id=chat_id, message_id=callback_query.message.message_id)
            for msg_id in range(callback_query.message.message_id, message_id + 1, -1):
                await callback_query.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            # await callback_query.message.answer("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))
        # else:
            # await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))
        await state.clear()
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Promokodni o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@promocode_router.callback_query(F.data.startswith("promocode_cancel_delete:"))
async def promocode_cancel_delete(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id, message_id = data.get("chat_id"), data.get("message_id")
    promocode_id = int(callback_query.data.split(":")[1])
    promocode = await sync_to_async(Promocode.objects.filter(id=promocode_id).first)()
    text = await format_promocode_info(promocode)
    if not promocode:
        await callback_query.answer(f"⚠️ Promokod topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(text=text, parse_mode='Markdown', reply_markup=await promocode_edit_keyboard(promocode_id))

    if message_id and chat_id:
        text = f"Tanlangan promokod: {promocode.name}\nMaydonni tanlang:👇"
        await update_and_clean_messages_promocode(callback_query.message, chat_id, message_id, text, promocode_id )
#Promocode part end

