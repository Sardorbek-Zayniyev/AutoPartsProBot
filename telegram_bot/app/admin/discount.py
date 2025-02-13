from aiogram import Router, F
import asyncio
from django.utils import timezone
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Discount
from telegram_bot.app.admin.utils import skip_inline_button, single_item_buttons, confirmation_keyboard, ACTIVITY_KEYBOARD, CONFIRM_KEYBOARD
from telegram_bot.app.admin.main_controls import DISCOUNT_CONTROLS_KEYBOARD
# Create a router for admin handlers
discount_router = Router()


class DiscountFSM(StatesGroup):
    #add
    waiting_discount_add = State()
    waiting_discount_percentage = State()
    waiting_discount_start_date = State()
    waiting_discount_end_date = State()
    waiting_discount_name = State()
    waiting_discount_name_input = State()
    waiting_discount_activity = State()
    #edit
    waiting_get_all_discounts = State ()
    waiting_edit_discounts_by_name = State()
    waiting_edit_discounts_by_name_search = State()
    waiting_discount_edit_percentage = State()
    waiting_discount_edit_start_date = State()
    waiting_discount_edit_end_date = State()
    waiting_discount_edit_name = State()
    waiting_discount_edit_activity = State()
    waiting_discount_delete = State()



#Discount part started
@discount_router.message(F.text.in_(("➕ Chegirma qo'shish", "✒️ Chegirmalarni tahrirlash", "✨ Barcha chegirmalarni ko'rish")))
async def discount_controls_handler(message: Message, state: FSMContext):
    """
    Handle discount management actions (add, edit).
    """
    actions = {
        "➕ Chegirma qo'shish": (DiscountFSM.waiting_discount_add, add_discount),
        "✒️ Chegirmalarni tahrirlash": (DiscountFSM.waiting_edit_discounts_by_name, get_all_discounts_by_name),
        "✨ Barcha chegirmalarni ko'rish": (DiscountFSM.waiting_get_all_discounts, get_all_discounts),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#adding part
@discount_router.message(DiscountFSM.waiting_discount_add)
async def add_discount(message: Message, state: FSMContext):
    """
    Chegirma yaratishni boshlash.
    """
    discount_template = (
        "📝 *Chegirma yaratish quyidagi tartibda bo'ladi: 👇*\n\n"
        "📉 *Chegirma foizi:* \n"
        "📅🕙 *Boshlanish sanasi va soati:* \n"
        "📅🕛 *Tugash sanasi va soati:* \n"
        "📝 *Chegirma nomi:*\n"
        "✅ *Faollik:* \n\n"
        "Chegirma yaratish uchun kerakli ma'lumotlarni kiriting!"
    )

    await message.answer(text=discount_template, parse_mode='Markdown')

    try:
        await message.answer("Chegirma miqdorini kiriting (masalan, 10 yoki 15.5):")
        await state.set_state(DiscountFSM.waiting_discount_percentage)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma qo'shishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@discount_router.message(DiscountFSM.waiting_discount_percentage)
async def set_discount_percentage(message: Message, state: FSMContext):
    """
    Chegirma miqdorini qabul qilish va saqlash.
    """
    try:
        percentage = float(message.text.strip())
        if not (0 < percentage <= 100):
            await message.answer("❌ Chegirma miqdori 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        
        await state.update_data(percentage=percentage)

        await message.answer("Chegirma boshlanish sanasini kiriting (masalan, 2025-05-15 10:00):")
        await state.set_state(DiscountFSM.waiting_discount_start_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")

@discount_router.message(DiscountFSM.waiting_discount_start_date)
async def set_discount_start_date(message: Message, state: FSMContext):
    """
    Chegirma boshlanish sanasini qabul qilish va saqlash.
    """
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)  

        await state.update_data(start_date=start_date)

        await message.answer("Chegirma tugash sanasini kiriting (masalan, 2025-05-25 23:59):")
        await state.set_state(DiscountFSM.waiting_discount_end_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")

@discount_router.message(DiscountFSM.waiting_discount_end_date)
async def set_discount_end_date(message: Message, state: FSMContext):
    """
    Chegirma tugash sanasini qabul qilish.
    """
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)  

        await state.update_data(end_date=end_date)
        await message.answer("Chegirma faolligini tanlang. (Faol/Nofaol) 👇", reply_markup=ACTIVITY_KEYBOARD)
        await state.set_state(DiscountFSM.waiting_discount_activity)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")

@discount_router.message(DiscountFSM.waiting_discount_activity)
async def set_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        isactive = activity == "✅ Faol"
        await state.update_data(isactive=isactive)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Nom kiritish", callback_data="enter_name")],
            [InlineKeyboardButton(text="O'tkazib yuborish", callback_data="skip_name")]
        ])

        await message.answer("Chegirma nomini kiriting yoki o'tkazib yuboring:", reply_markup=keyboard)
        await state.set_state(DiscountFSM.waiting_discount_name)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")
 
@discount_router.callback_query(DiscountFSM.waiting_discount_name)
async def process_discount_name(callback_query: CallbackQuery, state: FSMContext):
    """
    Chegirma nomini qabul qilish yoki o'tkazib yuborish.
    """
    action = callback_query.data

    if action == "enter_name":
        await callback_query.message.answer("Chegirma nomini kiriting:")
        await callback_query.answer()
        await state.set_state(DiscountFSM.waiting_discount_name_input)
    elif action == "skip_name":
        await state.update_data(name=None)
        await callback_query.answer()
        await save_discount(callback_query, state)

@discount_router.message(DiscountFSM.waiting_discount_name_input)
async def set_discount_name(message: Message, state: FSMContext):
    """
    Chegirma nomini qabul qilish va saqlash.
    """
    name = message.text.strip()
    await state.update_data(name=name)

    await save_discount(message, state)

async def save_discount(message, state):
    """
    Chegirma ma'lumotlarini saqlash.
    """
    user = await get_user_from_db(message.from_user.id)

    data = await state.get_data()
    percentage = data.get("percentage")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    isactive = data.get("isactive")
    name = data.get("name")
   
    discount = await sync_to_async(Discount.objects.create)(
        owner=user,
        updated_by=user,
        percentage=percentage,
        start_date=start_date,
        end_date=end_date,
        is_active=isactive,
        name=name,
    )
    text = f"✅ '{discount.name or discount}' Chegirmasi muvaffaqiyatli yaratildi.\n "

    if isinstance(message, CallbackQuery):
        await message.message.answer(text=text, reply_markup=DISCOUNT_CONTROLS_KEYBOARD)
    else:  
        await message.answer(text=text, reply_markup=DISCOUNT_CONTROLS_KEYBOARD)

    await state.update_data(discount_id=discount.id)
# --------------------------------------------------
#Utils
async def format_discount_info(discount):
    return (
        f"📝 Chegirma nomi: *{discount.name}*\n"
        f"📉 Chegirma foizi: *{int(discount.percentage) if discount.percentage % 1 == 0 else discount.percentage} %* \n"
        f"📅🕙 Boshlanish sanasi va soati: *{discount.start_date_normalize}* \n"
        f"📅🕛Tugash sanasi va soati: *{discount.end_date_normalize}* \n"
        f"✨ Faollik: *{'Faol ✅' if discount.is_active else 'Muddati oʻtgan ❌'}* \n\n"
    )

async def discount_edit_keyboard(discount_id):

    fields = ['Miqdori', 'Boshlanish sanasi', 'Nomi', 'Tugash sanasi','Faolligi']

    keyboard = [[InlineKeyboardButton(text="Tahrirlash uchun tanlang 👇", callback_data="noop")]]
    for i in range(0, len(fields), 2):
        row = [
            InlineKeyboardButton(text=fields[i], callback_data=f"dicount_field_{fields[i]}:{discount_id}")
        ]
        if i + 1 < len(fields): 
            row.append(InlineKeyboardButton(text=fields[i + 1], callback_data=f"dicount_field_{fields[i+1]}:{discount_id}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🗑 Chegirmani o'chirish", callback_data=f"dicount_field_deletediscount:{discount_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Bosh menu", callback_data="◀️ Bosh menu"), InlineKeyboardButton(text="❌ Ushbu xabarni o'chirish", callback_data="delete_message")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def handle_discount_search_results(message: Message, discounts, state: FSMContext):
    if not discounts:
        await message.answer("❌ Chegirma topilmadi.")
        return
    
    await state.update_data(search_results=discounts)
    
    discounts_with_numbers = [(index + 1, discount) for index, discount in enumerate(discounts)]
    total_pages = ((len(discounts_with_numbers) + 9) // 10)
    await display_discount_page(1, message, discounts_with_numbers, total_pages, 10, "search_discount", state)

async def handle_discount_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    
    page_num = int(data_parts[1])
    state_data = await state.get_data()
    discounts = state_data.get("search_results", [])
   
    discounts_with_numbers = [(index + 1, discount) for index, discount in enumerate(discounts)]
    discounts_per_page = 10
    total_pages = (len(discounts_with_numbers) + discounts_per_page - 1) // discounts_per_page
    
    await display_discount_page(page_num, callback_query, discounts_with_numbers, total_pages, discounts_per_page, callback_prefix, state)
    await callback_query.answer()

async def display_discount_page(page_num, callback_query_or_message, discounts_with_numbers, total_pages, discounts_per_page, callback_prefix, state):
    start_index = (page_num - 1) * discounts_per_page
    end_index = min(start_index + discounts_per_page, len(discounts_with_numbers))
    page_discounts = discounts_with_numbers[start_index:end_index]

    getting_process = await state.get_state() == DiscountFSM.waiting_get_all_discounts
    
    message_text = (
        f"{ '✨ Chegirmani ko\'rish bo\'limi:\n\n' if getting_process else '✒️ Chegirmani tahrirlash bo\'limi: \n\n'} 🔍 Umumiy natija: {len(discounts_with_numbers)} ta chegirmalar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, discount in page_discounts:
        message_text += f"{number}. {discount.name}\n"

    discount_buttons = []
    row = []
    for number, discount in page_discounts:
        if getting_process:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"discount:{discount.id}:get"))
        else:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"discount:{discount.id}:none"))
        if len(row) == 5:
            discount_buttons.append(row)
            row = []

    if row:
        discount_buttons.append(row)

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
    
    

    keyboard = InlineKeyboardMarkup(inline_keyboard=discount_buttons + [pagination_buttons])
    
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
        
async def update_and_clean_messages_discount(message: Message, chat_id: int, message_id: int, text: str, discount_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=await discount_edit_keyboard(discount_id)
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

# --------------------------------------------------
#search all discounts
@discount_router.message(DiscountFSM.waiting_get_all_discounts)
async def get_all_discounts(message: Message, state: FSMContext):
    discounts = await sync_to_async(list)(Discount.objects.all())
    await handle_discount_search_results(message, discounts, state)

#search discount by name
@discount_router.message(DiscountFSM.waiting_edit_discounts_by_name)
async def get_all_discounts_by_name(message: Message, state: FSMContext):
    await message.answer("Chegirmaning nomini kiriting: 👇")
    await state.set_state(DiscountFSM.waiting_edit_discounts_by_name_search)

@discount_router.message(DiscountFSM.waiting_edit_discounts_by_name_search)
async def search_discount_by_name(message: Message, state: FSMContext):
    name = message.text.strip().title()
    discounts = await sync_to_async(list)(Discount.objects.filter(name__icontains=name))
    await handle_discount_search_results(message, discounts, state)

@discount_router.callback_query(F.data.startswith('search_discount_other_pages:'))
async def get_search_discount_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_discount_other_pages(callback_query, state, callback_prefix="search_discount")


#show single discount
@discount_router.callback_query(F.data.startswith('discount:'))
async def get_single_discount(callback_query: CallbackQuery):
    discount_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    discount = await sync_to_async(Discount.objects.filter(id=discount_id).first)()

    if not discount:
        await callback_query.message.answer("❌ Xatolik: Chegirma topilmadi.")
        await callback_query.answer()
        return
    
    discount_info = await format_discount_info(discount)

    try:
        if action == "get":
            await callback_query.message.answer(text=discount_info, parse_mode='Markdown', reply_markup=await single_item_buttons())
        else:
            await callback_query.message.answer(text=discount_info, parse_mode='Markdown', reply_markup=await discount_edit_keyboard(discount_id))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Discountni yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    await callback_query.answer()

#...
@discount_router.callback_query(F.data.startswith('dicount_field_'))
async def discount_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[2]
    discount_id = int(callback_query.data.split(":")[1])

    user = await get_user_from_db(callback_query.from_user.id)
    discount = await sync_to_async(Discount.objects.filter(id=discount_id).first)()
    if not discount:
        await callback_query.answer("❌ Xatolik: Chegirma topilmadi.")
        return
    
    field_actions = {
        "Miqdori":              (DiscountFSM.waiting_discount_edit_percentage),
        "Boshlanish sanasi":    (DiscountFSM.waiting_discount_edit_start_date),
        "Nomi":                 (DiscountFSM.waiting_discount_edit_name),
        "Tugash sanasi":        (DiscountFSM.waiting_discount_edit_end_date),
        "Faolligi":             (DiscountFSM.waiting_discount_edit_activity), 
        "deletediscount":       (DiscountFSM.waiting_discount_delete),
    }   
        
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, chegirmani asosiy bo‘limidan qaytadan tanlang.")
        return
    
    await state.update_data(message_id=message_id, chat_id=chat_id, discount=discount, user=user)

    next_state = field_actions[field]
    await state.set_state(next_state)



    if field == "deletediscount":
        await callback_query.message.answer(f"Ushbu chegirmani o‘chirmoqchimisiz? 🗑", reply_markup=CONFIRM_KEYBOARD)
    elif field == "Faolligi":
        await callback_query.message.answer(f"{discount} chegirmasining yangi {field.lower()}ni tanlang:", reply_markup=ACTIVITY_KEYBOARD)
    else:
        await callback_query.message.answer(f"{discount} chegirmasining yangi {field.lower()}ni kiriting:", reply_markup=ReplyKeyboardRemove())

    await callback_query.answer()

@discount_router.message(DiscountFSM.waiting_discount_edit_percentage)
async def edit_discount_percentage(message: Message, state: FSMContext):
    """
    Chegirma miqdorini tahrirlash.
    """
    try:
        percentage = float(message.text.strip())
        if not (0 < percentage <= 100):
            await message.answer("❌ Chegirma miqdori 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return

        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')

        if discount:
            discount.percentage = percentage
            discount.updated_by = user
            await sync_to_async(discount.save)()

            await message.answer(f"✅ Chegirma miqdori {percentage}% ga yangilandi. 👆")
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma miqdorini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@discount_router.message(DiscountFSM.waiting_discount_edit_start_date)
async def edit_discount_start_date(message: Message, state: FSMContext):
    """
    Chegirma boshlanish sanasini tahrirlash.
    """
    try:
        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        if discount:
            discount.start_date = start_date
            discount.updated_by = user
            await sync_to_async(discount.save)()

            await message.answer(f"✅ Chegirma boshlanish sanasi {start_date.strftime('%Y-%m-%d %H:%M')} ga yangilandi. 👆")
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma boshlanish sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@discount_router.message(DiscountFSM.waiting_discount_edit_end_date)
async def edit_discount_end_date(message: Message, state: FSMContext):
    """
    Chegirma tugash sanasini tahrirlash.
    """
    try:
        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)

        if discount:
            discount.end_date = end_date
            discount.updated_by = user
            await sync_to_async(discount.save)()

            await message.answer(f"✅ Chegirma tugash sanasi {end_date.strftime('%Y-%m-%d %H:%M')} ga yangilandi. 👆")
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma tugash sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@discount_router.message(DiscountFSM.waiting_discount_edit_activity)
async def edit_discount_activity(message: Message, state: FSMContext):
    try:
        activity = message.text.strip()
        if activity in ["✅ Faol", "❌ Nofaol"]:
            isactive = activity == "✅ Faol"

            data = await state.get_data()
            discount = data.get("discount")
            chat_id = data.get("chat_id")
            message_id = data.get("message_id")
            user = data.get('user')

            if discount.is_active == isactive:
                await message.answer(f"❌ Chegirma faolligi o'zi {"nofaol" if activity=='ha' else "faol"} turibdi. 👆")
                return
            
            if discount:
                discount.is_active = isactive
                discount.updated_by = user
                await sync_to_async(discount.save)()
                await message.answer(f"✅ Chegirma {"nofaol" if activity=='ha' else "faol"} bo'ldi. 👆")
                text = await format_discount_info(discount)
                await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
            else:
                await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
        else:
            await message.answer("Admin, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma faolligini  yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@discount_router.message(DiscountFSM.waiting_discount_edit_name)
async def edit_discount_name(message: Message, state: FSMContext):
    """
    Chegirma nomini tahrirlash.
    """
    try:
        name = message.text.strip()
        if name.isdigit():
            await message.answer("❌ Noto'g'ri format. Admin chegirma nomi faqat raqamdan iborat bo'lishi mumkin emas!")
            return
        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        
        if discount:
            discount.name = name
            discount.updated_by = user
            await sync_to_async(discount.save)()
            await message.answer(f"✅ Chegirma nomi '{name}' ga yangilandi. 👆")
            
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma tugash sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@discount_router.message(DiscountFSM.waiting_discount_delete)
async def discount_delete(message: Message, state: FSMContext):

    confirm_text = message.text.strip().lower()
    data = await state.get_data()

    discount = data.get('discount')
    message_id = data.get('message_id')
    chat_id = data.get('chat_id')

    if not discount:
        await message.answer("❌ Bunday chegirma topilmadi. Admin, qayta urinib ko'ring.")
        await state.clear()
        return

    if confirm_text not in ["ha", "yo'q"]:
        await message.answer("Admin, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
        return
    
    try:
        if confirm_text == "ha":
            await sync_to_async(discount.delete)()

            delete_tasks = [
                message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                for msg_id in range(message.message_id, message_id - 1, -1)
            ]
            await asyncio.gather(*delete_tasks, return_exceptions=True)

            await message.answer(f"✅ Chegirma '{discount.name}' muvaffaqiyatli o'chirildi!", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer(f"❌ Chegirmaning o'chirilishi bekor qilindi.", reply_markup=ReplyKeyboardRemove())

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirmani o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    finally:
        await state.clear()

#Discount part end