from aiogram import Router, F
import asyncio
from django.utils import timezone
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_app.models import Discount, Product
from telegram_bot.app.admin.utils import (
    admin_skip_inline_button, 
    admin_single_item_buttons, 
    admin_keyboard_back_to_discount,
    admin_delete_confirmation_keyboard, 
    admin_escape_markdown, 
    admin_check_state_data,
    admin_get_cancel_reply_keyboard,
    admin_keyboard_remove_products_from_discount,
    ADMIN_ACTIVITY_KEYBOARD,
    )

admin_discount_router = Router()

class AdminDiscountFSM(StatesGroup):
    # Get
    admin_waiting_get_all_discounts = State()

    # Add
    admin_waiting_discount_add = State()
    admin_waiting_discount_percentage = State()
    admin_waiting_discount_start_date = State()
    admin_waiting_discount_end_date = State()
    admin_waiting_discount_name = State()
    admin_waiting_discount_activity = State()

    # Edit
    admin_waiting_edit_discount = State()
    admin_waiting_edit_discount_by_name = State()
    admin_waiting_discount_edit_percentage = State()
    admin_waiting_discount_edit_start_date = State()
    admin_waiting_discount_edit_end_date = State()
    admin_waiting_discount_edit_name = State()
    admin_waiting_discount_edit_activity = State()

    #Add product to discount
    admin_waiting_add_product_to_discount = State()
    admin_waiting_remove_product_from_discount = State()

    # Deleting
    admin_waiting_discount_delete = State()

# Utils
async def admin_get_discount_by_id(discount_id):
    return await sync_to_async(lambda: Discount.objects.select_related('owner', 'updated_by').filter(id=discount_id).first())()

def admin_remove_product_keyboard(discount_id, products):
    builder = InlineKeyboardBuilder()
    for i, product in enumerate(products):
        builder.button(
            text=f"{i+1}. {product.name}",
            callback_data=f"admin_remove_product_from_discount:{discount_id}:{product.id}"
        )
    builder.button(text="◀️ Orqaga", callback_data=f"admin_discount:{discount_id}:get")
    builder.adjust(1) 
    return builder.as_markup()

async def admin_format_discount_info(discount):
    owner_name = admin_escape_markdown(discount.owner.full_name)
    updated_by_name = admin_escape_markdown(discount.updated_by.full_name)
    return (
        f"📝 Chegirma nomi: *{discount.name}*\n"
        f"📉 Chegirma foizi: *{int(discount.percentage) if discount.percentage % 1 == 0 else discount.percentage} %*\n"
        f"📅🕙 Boshlanish sanasi va soati: *{discount.start_date_normalize}*\n"
        f"📅🕛 Tugash sanasi va soati: *{discount.end_date_normalize}*\n"
        f"✨ Faollik: *{'Faol ✅' if discount.is_active else 'Muddati oʻtgan ❌'}*\n"
        f"👤 Yaratgan: [{owner_name}](tg://user?id={discount.owner.telegram_id})\n"
        f"✏️ Oxirgi tahrir: [{updated_by_name}](tg://user?id={discount.updated_by.telegram_id})\n"
    )

def admin_discount_edit_keyboard(discount_id):
    fields = ['Miqdori', 'Boshlanish sanasi', 'Nomi', 'Tugash sanasi', 'Faolligi']
    builder = InlineKeyboardBuilder()
    builder.button(text="Tahrirlash uchun tanlang 👇", callback_data="noop")
    for i in range(0, len(fields), 2):
        builder.button(text=fields[i], callback_data=f"admin_discount_field_{fields[i]}:{discount_id}")
        if i + 1 < len(fields):
            builder.button(text=fields[i + 1], callback_data=f"admin_discount_field_{fields[i+1]}:{discount_id}")
    builder.button(text="🗑 Chegirmani o'chirish", callback_data=f"admin_discount_delete:{discount_id}")
    builder.adjust(1, 2, 2, 1, 1)
    return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_single_item_buttons().inline_keyboard)

async def admin_handle_search_discounted_products_result(callback_query_or_message, products, state: FSMContext):
    if not products:
        text = "❌ Chegirmali mahsulotlar topilmadi."
        if isinstance(callback_query_or_message, CallbackQuery):
            await callback_query_or_message.message.answer(text)
        else:    
            await callback_query_or_message.answer(text)
        return
    await state.update_data(discounted_products=products)
    
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    
    total_pages = ((len(products_with_numbers) + 9) // 10)
    await admin_display_discounted_products_page(1, callback_query_or_message, products_with_numbers, total_pages, 10, "admin_search_discounted_products_page", state)

async def admin_handle_discounted_products_result_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    page_num = int(data_parts[1])
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    products = data.get("discounted_products", [])
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    await admin_display_discounted_products_page(page_num, callback_query, products_with_numbers, total_pages, products_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_display_discounted_products_page(page_num, callback_query_or_message, products_with_numbers, total_pages, products_per_page, callback_prefix, state):
    start_index = (page_num - 1) * products_per_page
    end_index = min(start_index + products_per_page, len(products_with_numbers))
    page_products = products_with_numbers[start_index:end_index]

    message_text = (
    f"✨ Chegirmadan mahsulotlarni olib tashlash bo\'limi:\n\n"
    f"🔍 Umumiy natija: {len(products_with_numbers)} ta chegirmalar topildi.\n\n"
    f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, product in page_products:
        message_text += f"{number}. {product.car_brand}|{product.car_model} — {product.name[:15]}\n"

    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()

    for number, product in page_products:
        callback_data = f"admin_remove_discounted_products:{product.id}"
        builder.button(text=str(number), callback_data=callback_data)

    builder.adjust(5)
    if total_pages > 1:
        pagination_buttons = []
        if page_num > 1:
            pagination_buttons.append({"text": "⬅️", "callback_data": f"{callback_prefix}_other_pages:{page_num - 1}"})
        pagination_buttons.append({"text": "❌", "callback_data": "admin_delete_message"})
        if page_num < total_pages:
            pagination_buttons.append({"text": "➡️", "callback_data": f"{callback_prefix}_other_pages:{page_num + 1}"})
        for btn in pagination_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(pagination_buttons))
    else:
        pagination.button(text="❌", callback_data="admin_delete_message")
        pagination.adjust(5, 5, 1)
    additional_buttons = admin_keyboard_remove_products_from_discount().inline_keyboard

    final_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + pagination.export() + additional_buttons)
    if isinstance(callback_query_or_message, CallbackQuery):
        new_message = await callback_query_or_message.message.edit_text(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")
    else:
        new_message = await callback_query_or_message.answer(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")
    await state.update_data(message_ids=[new_message.message_id])

async def admin_handle_discount_search_results(message, discounts, state: FSMContext):
    if not discounts:
        await message.answer("❌ Chegirma topilmadi.")
        return
    await state.update_data(search_results=discounts)
    discounts_with_numbers = [(index + 1, discount) for index, discount in enumerate(discounts)]
    total_pages = ((len(discounts_with_numbers) + 9) // 10)
    await admin_display_discount_page(1, message, discounts_with_numbers, total_pages, 10, "admin_search_discount", state)

async def admin_handle_discount_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    page_num = int(data_parts[1])
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    discounts = data.get("search_results", [])
    discounts_with_numbers = [(index + 1, discount) for index, discount in enumerate(discounts)]
    discounts_per_page = 10
    total_pages = (len(discounts_with_numbers) + discounts_per_page - 1) // discounts_per_page
    await admin_display_discount_page(page_num, callback_query, discounts_with_numbers, total_pages, discounts_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_display_discount_page(page_num, callback_query_or_message, discounts_with_numbers, total_pages, discounts_per_page, callback_prefix, state):
    start_index = (page_num - 1) * discounts_per_page
    end_index = min(start_index + discounts_per_page, len(discounts_with_numbers))
    page_discounts = discounts_with_numbers[start_index:end_index]

    getting_process = await state.get_state() == AdminDiscountFSM.admin_waiting_get_all_discounts
    setting_product_process = await state.get_state() == AdminDiscountFSM.admin_waiting_add_product_to_discount
    removing_product_process = await state.get_state() == AdminDiscountFSM.admin_waiting_remove_product_from_discount

    message_text = (
    f"{'✨ Chegirmani ko\'rish bo\'limi:\n\n' if getting_process else ('✨ Chegirmaga mahsulotlarni qo\'shish bo\'limi:\n\n' if setting_product_process else ('✨ Chegirmadan mahsulotlarni olib tashlash bo\'limi:\n\n' if removing_product_process else '✒️ Chegirmani tahrirlash bo\'limi:\n\n'))}"
    f"🔍 Umumiy natija: {len(discounts_with_numbers)} ta chegirmalar topildi.\n\n"
    f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, discount in page_discounts:
        message_text += f"{number}. {discount.name}\n"
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()

    for number, discount in page_discounts:
        if setting_product_process:
            callback_data = f"admin_select_discount_for_product:{discount.id}"
        else:
            if removing_product_process:
                callback_data = f"admin_discount:{discount.id}:remove_product"
            else:
                callback_data = f"admin_discount:{discount.id}:get" if getting_process else f"admin_discount:{discount.id}:none"
        builder.button(text=str(number), callback_data=callback_data)

    builder.adjust(5)
    if total_pages > 1:
        pagination_buttons = []
        if page_num > 1:
            pagination_buttons.append({"text": "⬅️", "callback_data": f"{callback_prefix}_other_pages:{page_num - 1}"})
        pagination_buttons.append({"text": "❌", "callback_data": "admin_delete_message"})
        if page_num < total_pages:
            pagination_buttons.append({"text": "➡️", "callback_data": f"{callback_prefix}_other_pages:{page_num + 1}"})
        for btn in pagination_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(pagination_buttons))
    else:
        pagination.button(text="❌", callback_data="admin_delete_message")
        pagination.adjust(5, 5, 1)
    additional_buttons = admin_keyboard_back_to_discount().inline_keyboard
    final_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + pagination.export() + additional_buttons)
    if isinstance(callback_query_or_message, CallbackQuery):
        new_message = await callback_query_or_message.message.edit_text(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")
    else:
        new_message = await callback_query_or_message.answer(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")
    await state.update_data(message_ids=[new_message.message_id])
    
async def admin_update_and_clean_message_discount(message: Message, chat_id: int, message_id: int, text: str, discount_id: int):
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=admin_discount_edit_keyboard(discount_id)
    )
    delete_tasks = [message.bot.delete_message(chat_id, msg_id) for msg_id in range(message.message_id, message_id, -1)]
    await asyncio.gather(*delete_tasks, return_exceptions=True)

# Get all discounts
@admin_discount_router.message(AdminDiscountFSM.admin_waiting_get_all_discounts, AdminDiscountFSM.admin_waiting_add_product_to_discount, AdminDiscountFSM.admin_waiting_remove_product_from_discount)
async def admin_get_all_discounts(message: Message, state: FSMContext):
    discounts = await sync_to_async(lambda: list(Discount.objects.select_related('owner', 'updated_by').all()))()
    await admin_handle_discount_search_results(message, discounts, state)

@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_discount_other_pages:'))
async def admin_get_all_discounts_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_discount_other_pages(callback_query, state, callback_prefix="admin_search_discount")

@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_discounted_products_page_other_pages:'))
async def admin_get_all_discounted_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_discounted_products_result_other_pages(callback_query, state, callback_prefix="admin_search_discounted_products_page")

# Get single discount
@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith('admin_discount:'))
async def admin_get_single_discount(callback_query: CallbackQuery, state: FSMContext):    
    discount_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]

    discount = await admin_get_discount_by_id(discount_id)
    if not discount:
        await callback_query.message.answer("❌ Xatolik: Chegirma topilmadi.")
        await callback_query.answer()
        return
    
    discount_info = await admin_format_discount_info(discount)

    try:
        if action == "get":
            await callback_query.message.edit_text(
                text=discount_info,
                parse_mode='Markdown',
                reply_markup=admin_discount_edit_keyboard(discount_id)
            )
        elif action == 'remove_product':
            await state.update_data(discount_id=discount_id)
            products = await sync_to_async(list)(discount.products.select_related("car_brand", "car_model").only("name", "price", "car_brand__name", "car_model__name").all())
            await admin_handle_search_discounted_products_result(callback_query, products, state)
        else:
            await callback_query.message.edit_text(
                text=discount_info,
                parse_mode='Markdown',
                reply_markup=admin_discount_edit_keyboard(discount_id)
            )
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.edit_text("❌ Discountni yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")
    await callback_query.answer()

# Adding part
@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_add)
async def admin_add_discount(message: Message, state: FSMContext):
    discount_template = (
        "📝 *Chegirma yaratish quyidagi tartibda bo'ladi: 👇*\n\n"
        "📉 *Chegirma foizi:*\n"
        "📅🕙 *Boshlanish sanasi va soati:*\n"
        "📅🕛 *Tugash sanasi va soati:*\n"
        "📝 *Chegirma nomi:*\n"
        "✅ *Faollik:*\n\n"
        "Chegirma yaratish uchun kerakli ma'lumotlarni kiriting!"
    )
    await message.answer(text=discount_template, parse_mode='Markdown')
    try:
        await message.answer("Chegirma miqdorini kiriting (masalan, 10 yoki 15.5):", reply_markup=admin_get_cancel_reply_keyboard().as_markup(resize_keyboard=True))
        await state.set_state(AdminDiscountFSM.admin_waiting_discount_percentage)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma qo'shishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_percentage)
async def admin_set_discount_percentage(message: Message, state: FSMContext):
    try:
        percentage = float(message.text.strip())
        if not (0 < percentage <= 100):
            await message.answer("❌ Chegirma miqdori 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        await state.update_data(percentage=percentage)
        await message.answer("Chegirma boshlanish sanasini kiriting (masalan, 2025-05-15 10:00):")
        await state.set_state(AdminDiscountFSM.admin_waiting_discount_start_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_start_date)
async def admin_set_discount_start_date(message: Message, state: FSMContext):
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        await state.update_data(start_date=start_date)
        await message.answer("Chegirma tugash sanasini kiriting (masalan, 2025-05-25 23:59):")
        await state.set_state(AdminDiscountFSM.admin_waiting_discount_end_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_end_date)
async def admin_set_discount_end_date(message: Message, state: FSMContext):
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)
        await state.update_data(end_date=end_date)
        await message.answer("Chegirma nomini kiriting:", reply_markup=admin_skip_inline_button("admin_skip_discount_name"))
        await state.set_state(AdminDiscountFSM.admin_waiting_discount_name)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_name)
async def admin_set_discount_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer("Chegirma faolligini tanlang. (Faol/Nofaol) 👇", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    await state.set_state(AdminDiscountFSM.admin_waiting_discount_activity)

@admin_discount_router.callback_query(IsAdminFilter(), F.data == "admin_skip_discount_name_skip_step")
async def admin_skip_name(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("✅ O‘tkazib yuborildi. Davom etamiz...")
    await state.update_data(name=None)
    await callback_query.message.answer("Chegirma faolligini tanlang. (Faol/Nofaol) 👇", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    await state.set_state(AdminDiscountFSM.admin_waiting_discount_activity)

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_activity)
async def admin_set_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        isactive = activity == "✅ Faol"
        await state.update_data(isactive=isactive)
        await state.set_state(AdminDiscountFSM.admin_waiting_discount_name)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")
    await admin_save_discount(message, state)

async def admin_save_discount(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
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
    from telegram_bot.app.admin.main_controls import ADMIN_DISCOUNT_CONTROLS_KEYBOARD
    if isinstance(message, CallbackQuery):
        await message.message.answer(text=text, reply_markup=ADMIN_DISCOUNT_CONTROLS_KEYBOARD)
    else:
        await message.answer(text=text, reply_markup=ADMIN_DISCOUNT_CONTROLS_KEYBOARD)
    await state.update_data(discount_id=discount.id)

# Editing part
@admin_discount_router.message(AdminDiscountFSM.admin_waiting_edit_discount)
async def admin_edit_discount(message: Message, state: FSMContext):
    await message.answer("Chegirmaning nomini kiriting: 👇")
    await state.set_state(AdminDiscountFSM.admin_waiting_edit_discount_by_name)

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_edit_discount_by_name)
async def admin_search_discount_by_name(message: Message, state: FSMContext):
    name = message.text.strip().title()
    discounts = await sync_to_async(lambda: list(Discount.objects.select_related('owner', 'updated_by').filter(name__icontains=name)))()
    await admin_handle_discount_search_results(message, discounts, state)

@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith('admin_discount_field_'))
async def admin_discount_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[3]
    discount_id = int(callback_query.data.split(":")[1])
    user = await get_user_from_db(callback_query.from_user.id)
    discount = await admin_get_discount_by_id(discount_id)
    if not discount:
        await callback_query.answer("❌ Xatolik: Chegirma topilmadi.")
        return
    field_actions = {
        "Miqdori": (AdminDiscountFSM.admin_waiting_discount_edit_percentage),
        "Boshlanish sanasi": (AdminDiscountFSM.admin_waiting_discount_edit_start_date),
        "Nomi": (AdminDiscountFSM.admin_waiting_discount_edit_name),
        "Tugash sanasi": (AdminDiscountFSM.admin_waiting_discount_edit_end_date),
        "Faolligi": (AdminDiscountFSM.admin_waiting_discount_edit_activity),
        "discount_delete": (AdminDiscountFSM.admin_waiting_discount_delete),
    }
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, chegirmani asosiy bo‘limidan qaytadan tanlang.")
        return
    await state.update_data(message_id=message_id, chat_id=chat_id, discount=discount, user=user)
    next_state = field_actions[field]
    await state.set_state(next_state)
    if field == "discount_delete":
        await callback_query.message.answer(f"Ushbu chegirmani o‘chirmoqchimisiz? 🗑", reply_markup=admin_delete_confirmation_keyboard("admin_discount", discount_id))
    elif field == "Faolligi":
        await callback_query.message.answer(f"{discount} chegirmasining yangi {field.lower()}ni tanlang:", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    else:
        await callback_query.message.answer(f"{discount} chegirmasining yangi {field.lower()}ni kiriting:", reply_markup=ReplyKeyboardRemove())
    await callback_query.answer()

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_edit_percentage)
async def admin_edit_discount_percentage(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    discount, chat_id, message_id, user = (data.get(k) for k in ("discount", "chat_id", "message_id", "user"))
    if not discount:
        await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
        return
    try:
        percentage = float(message.text.strip())
        if not (0 < percentage <= 100):
            await message.answer("❌ Chegirma miqdori 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        discount.percentage = percentage
        discount.updated_by = user
        await sync_to_async(discount.save)()
        await message.answer(f"✅ Chegirma miqdori {percentage}% ga yangilandi. 👆")
        text = await admin_format_discount_info(discount)
        await admin_update_and_clean_message_discount(message, chat_id, message_id, text, discount.id)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma miqdorini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_edit_start_date)
async def admin_edit_discount_start_date(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    discount, chat_id, message_id, user = (data.get(k) for k in ("discount", "chat_id", "message_id", "user"))
    if not discount:
        await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
        return
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        discount.start_date = start_date
        discount.updated_by = user
        await sync_to_async(discount.save)()
        await message.answer(f"✅ Chegirma boshlanish sanasi {start_date.strftime('%Y-%m-%d %H:%M')} ga yangilandi. 👆")
        text = await admin_format_discount_info(discount)
        await admin_update_and_clean_message_discount(message, chat_id, message_id, text, discount.id)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma boshlanish sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_edit_end_date)
async def admin_edit_discount_end_date(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    discount, chat_id, message_id, user = (data.get(k) for k in ("discount", "chat_id", "message_id", "user"))
    if not discount:
        await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
        return
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)
        discount.end_date = end_date
        discount.updated_by = user
        await sync_to_async(discount.save)()
        await message.answer(f"✅ Chegirma tugash sanasi {end_date.strftime('%Y-%m-%d %H:%M')} ga yangilandi. 👆")
        text = await admin_format_discount_info(discount)
        await admin_update_and_clean_message_discount(message, chat_id, message_id, text, discount.id)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma tugash sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_edit_activity)
async def admin_edit_discount_activity(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    discount, chat_id, message_id, user = (data.get(k) for k in ("discount", "chat_id", "message_id", "user"))
    if not discount:
        await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
        return
    try:
        activity = message.text.strip()
        if activity in ["✅ Faol", "❌ Nofaol"]:
            isactive = activity == "✅ Faol"
            if isactive and discount.end_date < timezone.now():
                await message.answer("❌ Chegirma muddati tugagan. Faollashtirish uchun tugash sanasini o'zgartiring.")
                return
            if discount.is_active == isactive:
                await message.answer(f"❌ Chegirma faolligi allaqachon {activity} da turibdi. 👆", 
                                     reply_markup=ADMIN_ACTIVITY_KEYBOARD)
                return
            discount.is_active = isactive
            discount.updated_by = user
            await sync_to_async(discount.save)()
            await message.answer(f"✅ Chegirma {'nofaol' if activity=='ha' else 'faol'} bo'ldi. 👆")
            text = await admin_format_discount_info(discount)
            await admin_update_and_clean_message_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma faolligini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_discount_router.message(AdminDiscountFSM.admin_waiting_discount_edit_name)
async def admin_edit_discount_name(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    discount, chat_id, message_id, user = (data.get(k) for k in ("discount", "chat_id", "message_id", "user"))
    if not discount:
        await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
        return
    try:
        name = message.text.strip()
        if name.isdigit():
            await message.answer("❌ Noto'g'ri format. Admin chegirma nomi faqat raqamdan iborat bo'lishi mumkin emas!")
            return
        discount.name = name
        discount.updated_by = user
        await sync_to_async(discount.save)()
        await message.answer(f"✅ Chegirma nomi '{name}' ga yangilandi. 👆")
        text = await admin_format_discount_info(discount)
        await admin_update_and_clean_message_discount(message, chat_id, message_id, text, discount.id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma nomini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

# Deleting part
@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith("admin_discount_delete"))
async def admin_discount_delete_callback(callback_query: CallbackQuery, state: FSMContext):
    discount_id = int(callback_query.data.split(":")[1])
    discount = await admin_get_discount_by_id(discount_id)
    await state.update_data(discount_id=discount_id)
    await callback_query.message.edit_text(f"'{discount.name}' chegirmani o‘chirmoqchimisiz?", reply_markup=admin_delete_confirmation_keyboard("admin_discount", discount_id))

@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith("admin_discount_confirm_delete:"))
async def admin_discount_confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    discount_id = int(callback_query.data.split(":")[1])
    discount = await admin_get_discount_by_id(discount_id)
    if not discount:
        await callback_query.answer(f"⚠️ Chegirma topilmadi. Admin qaytadan urinib ko'ring.")
        return
    try:
        await sync_to_async(discount.delete)()
        await callback_query.answer(f"✅ '{discount.name}' chegirma o‘chirildi.")
        await callback_query.bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Chegirmani o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith("admin_discount_cancel_delete:"))
async def admin_discount_cancel_delete(callback_query: CallbackQuery, state: FSMContext):
    discount_id = int(callback_query.data.split(":")[1])
    discount = await admin_get_discount_by_id(discount_id)
    text = await admin_format_discount_info(discount)
    if not discount:
        await callback_query.answer(f"⚠️ Chegirma topilmadi. Admin qaytadan urinib ko'ring")
        return
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(text=text, parse_mode='Markdown', reply_markup=admin_discount_edit_keyboard(discount_id))


#Add discount to product
@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith("admin_select_discount_for_product:"))
async def admin_select_discount_for_product(callback_query: CallbackQuery, state: FSMContext):
    discount_id = int(callback_query.data.split(":")[1])
    discount = await admin_get_discount_by_id(discount_id)

    await state.update_data(discount_id=discount_id)
    await callback_query.message.edit_text(f"'{discount.name}' chegirmasi tanlandi ✅\nMahsulotni tanlash uchun uning nomini kiriting 👇")
    
@admin_discount_router.message(AdminDiscountFSM.admin_waiting_add_product_to_discount)
async def admin_select_discount_for_product(message: Message, state: FSMContext):
    from telegram_bot.app.admin.product import admin_fetch_all_products_page_by_retrieved_name
    await admin_fetch_all_products_page_by_retrieved_name(message, state)

@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith("admin_add_product_to_discount:"))
async def admin_add_product_to_discount(callback_query: CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split(":")[1])
    data = await state.get_data() or {}
    discount_id = data.get("discount_id")
    selected_products = data.get("selected_products", [])

    if not discount_id:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
        return
   
    product = await Product.objects.filter(id=product_id).only('name').afirst()
    discount = await admin_get_discount_by_id(discount_id)

    is_already_added = await sync_to_async(discount.products.filter(id=product_id).exists)()
    if is_already_added:
        await callback_query.answer(f"⚠️ '{product.name}' bu chegirmaga allaqachon qo‘shilgan.", show_alert=True)
        return
    
    if product_id in selected_products:
        await callback_query.answer(f"⚠️'{product.name}' allaqachon tanlangan.")
    elif product_id not in selected_products:
        selected_products.append(product_id)
        await state.update_data(selected_products=selected_products)
        await callback_query.answer(f"✅ '{product.name}' tanlandi.")

@admin_discount_router.callback_query(IsAdminFilter(), F.data == "admin_confirm_products_to_discount")
async def admin_confirm_products_to_discount(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    discount_id = data.get("discount_id")
    selected_products = data.get("selected_products", [])

    if not discount_id:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
        return
    
    if not selected_products:
        await callback_query.answer("❌ Hech qanday mahsulot tanlanmadi. Tasdiqlash uchun oldin mahsulot tanlashingiz kerak!", show_alert=True)
        return
    
    
    discount = await admin_get_discount_by_id(discount_id)
    products = await sync_to_async(list)(Product.objects.filter(id__in=selected_products))
    
    # Mahsulotlarni chegirmaga qo‘shish
    try:
        await callback_query.message.edit_text(f"⏳ Mahsulotlar qo'shilmoqda...")
        await sync_to_async(discount.products.add)(*products)
    except Exception as e:
        await callback_query.message.answer(f"Mahsulotni chegirmaga qo'shishda xatolik yuz berdi.\nXatolik sababi {e}")

    from telegram_bot.app.admin.main_controls import ADMIN_DISCOUNT_CONTROLS_KEYBOARD
    await callback_query.message.edit_text(f"✅ '{discount.name}' chegirmasiga {len(products)} ta mahsulot muvaffaqqiyatli qo‘shildi!")
    await callback_query.message.answer(text="Chegirmalarni boshqaruvi uchun tugmalar:", reply_markup=ADMIN_DISCOUNT_CONTROLS_KEYBOARD)
    
    await state.clear()
    await callback_query.answer()

#Remove product from discount
@admin_discount_router.callback_query(IsAdminFilter(), F.data.startswith("admin_remove_discounted_products:"))
async def admin_remove_product_from_discount(callback_query: CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split(":")[1])
    data = await state.get_data() or {}
    discount_id = data.get("discount_id")

    if not discount_id:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
        return
    
    selected_products_for_removing = data.get("selected_products_for_removing", [])

    discount = await admin_get_discount_by_id(discount_id)
    product = await discount.products.filter(id=product_id).only("name").afirst()

    if product_id in selected_products_for_removing:
        await callback_query.answer(f"⚠️'{product.name}' allaqachon tanlangan.")
    elif product_id not in selected_products_for_removing:
        selected_products_for_removing.append(product_id)
        await state.update_data(selected_products_for_removing=selected_products_for_removing)
        await callback_query.answer(f"✅ '{product.name}' tanlandi.")

@admin_discount_router.callback_query(IsAdminFilter(), F.data == "admin_confirm_remove_discounted_products")
async def admin_confirm_remove_product_from_discount(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    discount_id = data.get("discount_id")
    selected_products_for_removing = data.get("selected_products_for_removing", [])

    if not discount_id:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
        return
    
    if not selected_products_for_removing:
        await callback_query.answer("❌ Hech qanday mahsulot tanlanmadi. Tasdiqlash uchun oldin mahsulot tanlashingiz kerak!", show_alert=True)
        return
    
    
    discount = await admin_get_discount_by_id(discount_id)
    products = await sync_to_async(list)(Product.objects.filter(id__in=selected_products_for_removing))
    
    # Mahsulotlarni chegirmaga qo‘shish
    try:
        await callback_query.message.edit_text(f"⏳ Mahsulotlar olib tashlanmoqda...")
        await sync_to_async(discount.products.remove)(*products)
    except Exception as e:
        await callback_query.message.answer(f"Mahsulotni chegirmadab olib tashlashda xatolik yuz berdi.\nXatolik sababi {e}")

    from telegram_bot.app.admin.main_controls import ADMIN_DISCOUNT_CONTROLS_KEYBOARD
    await callback_query.message.edit_text(f"✅ '{discount.name}' chegirmasidan {len(products)} ta mahsulot muvaffaqqiyatli olib tashlandi!")
    await callback_query.message.answer(text="Chegirmalarni boshqaruvi uchun tugmalar:", reply_markup=ADMIN_DISCOUNT_CONTROLS_KEYBOARD)
    
    await state.clear()
    await callback_query.answer()



















