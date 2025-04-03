from aiogram import Router, F
import asyncio
from django.utils import timezone
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_app.models import Order
from telegram_bot.app.admin.utils import (
    admin_keyboard_back_to_order,
    admin_escape_markdown,
    admin_check_state_data,
    admin_get_cancel_reply_keyboard,
)

admin_order_router = Router()

class AdminOrderFSM(StatesGroup):
    # Filter by status
    admin_waiting_filter_by_status = State()
    admin_waiting_search_order_by_delivery_status = State()

    # Filter by payment status
    admin_waiting_filter_by_payment_status = State()
    admin_waiting_search_order_by_payment_status = State()

    # Filter by payment method
    admin_waiting_filter_by_payment_method = State()
    admin_waiting_search_order_by_payment_method = State()

    # Filter by user
    admin_waiting_filter_by_user = State()
    admin_waiting_input_user_id = State()

    # Filter by date
    admin_waiting_filter_by_date = State()
    admin_waiting_input_date = State()

    # Edit
    admin_waiting_edit_order_field = State()
    admin_waiting_edit_order_delivery_status = State()
    admin_waiting_edit_order_payment_status = State()
    admin_waiting_edit_order_payment_method = State()
    admin_waiting_edit_order_delivery_address = State()

    # Deleting
    admin_waiting_order_deletion = State()

DELIVERY_STATUS_CHOICES = {'Pending': 'Yig‘ilmoqda ⏳', 'Shipped':'Jo‘natildi 🚚', 'Delivered':'Yetkazilgan ✅', 'Cancelled' : 'Bekor qilingan 🚫'}
PAYMENT_STATUS_CHOICES = {'Unpaid': 'To\'lanmagan ⚠️', 'Paid': 'To\'langan ✅'}
PAYMENT_METHOD_CHOICES = {'Cash': 'Naqd 💵', 'Card': 'Karta 💳', 'Payme': 'Payme 📲', 'Click': 'Click 📱'}
ORDER_ADDRESS_FIELDS = {
          'region':'Viloyat',
          'city' : 'Shahar',
          'street_address' : 'Ko\'cha'
    }
# Utils

async def admin_send_order_updation_to_user(bot, order, answer_text):
    """Send the admin's answer to the user who asked the question."""
    user = order.user
    if not user or not user.telegram_id:
        return
    answer_message = await admin_format_order_info(order)
    await bot.send_message(chat_id=user.telegram_id, text=answer_message + answer_text, parse_mode="HTML")

async def admin_get_order_by_id(id):
    return await sync_to_async(lambda: Order.objects.select_related('user').filter(id=id).prefetch_related('items__product').first())()

async def admin_format_order_info(order):
    order_items = order.items.all()
    items_text = "\n".join([f"{index + 1}. {item.product.name} - {item.quantity} ta - {item.price} so'm" for index, item in enumerate(order_items)])
    user_name = admin_escape_markdown(order.user.full_name)
    return (
            f"🆔 <b>Buyurtma ID:</b> #{order.order_id}\n"
            f"👤 <b>Foydalanuvchi:</b> <a href='tg://user?id={order.user.telegram_id}'>{user_name}</a>\n"
            f"📌 <b>Yetkazish holati:</b> {DELIVERY_STATUS_CHOICES[order.status]}\n"
            f"💸 <b>To‘lov usuli:</b> {PAYMENT_METHOD_CHOICES[order.payment_method]}\n"
            f"🔄 <b>To‘lov holati:</b> {PAYMENT_STATUS_CHOICES[order.payment_status]}\n"
            f"📅 <b>Sana:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"📍 <b>Manzil:</b> {order.region}, {order.city}, {order.street_address}\n\n"
            f"<b>🛍 Mahsulotlar:</b>\n{items_text}\n\n" +
           (f"<b>💰 Jami summa:</b> <del>{order.total_price}</del> so‘m\n"
            f"<b>🏷️ Chegirma bilan summa:</b> {order.discounted_price} so‘m" if order.discounted_price else 
            f"<b>💰 Jami summa:</b> {order.total_price} so‘m")
        )

def admin_order_delivery_status_keyboard():
    builder = ReplyKeyboardBuilder()
    for status_key, status_label in DELIVERY_STATUS_CHOICES.items():
        builder.button(text=status_label)
    builder.button(text="📜 Buyurtmalar bo'limi")
    builder.button(text="◀️ Bosh menu")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def admin_order_payment_status_keyboard():
    builder = ReplyKeyboardBuilder()
    for status_key, status_label in PAYMENT_STATUS_CHOICES.items():
        builder.button(text=status_label)
    builder.button(text="📜 Buyurtmalar bo'limi")
    builder.button(text="◀️ Bosh menu")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_order_payment_method_keyboard():
    builder = ReplyKeyboardBuilder()
    for status_key, status_label in PAYMENT_METHOD_CHOICES.items():
        builder.button(text=status_label)
    builder.button(text="📜 Buyurtmalar bo'limi")
    builder.button(text="◀️ Bosh menu")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_order_edit_keyboard(order_id):
    fields = ['Yetkazish holati', 'Yetkazib berish manzili', 'To‘lov holati', 'To‘lov usuli']
    builder = InlineKeyboardBuilder()
    for i in range(0, len(fields), 2):
        row = [
            InlineKeyboardButton(text=fields[i], callback_data=f"admin_order_field_{fields[i]}:{order_id}")
        ]
        if i + 1 < len(fields):
            row.append(InlineKeyboardButton(text=fields[i + 1], callback_data=f"admin_order_field_{fields[i+1]}:{order_id}"))
        builder.row(*row)
    builder.button(text="❌", callback_data=f"admin_delete_message")
    # builder.button(text="🗑 Buyurtmani o'chirish", callback_data=f"admin_order_field_delete_order:{order_id}")
    builder.adjust(2, 2, 1)
    return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_keyboard_back_to_order().inline_keyboard)

def admin_back_to_single_order_keyboard(order_id):

    back_to_order = InlineKeyboardBuilder()
    back_to_order.row(
        InlineKeyboardButton(text="❌", callback_data='admin_delete_message'),
        InlineKeyboardButton(text="↩️ Orqaga", callback_data=f'admin_selected_order:{order_id}')
    )
    return InlineKeyboardMarkup(inline_keyboard=back_to_order.export() + admin_keyboard_back_to_order().inline_keyboard)

async def admin_handle_order_search_results(message: Message, orders, state: FSMContext, prefix: str = "admin_search_order"):
    if not orders:
        await message.answer("❌ Hech qanday buyurtma topilmadi.")
        return
    await state.update_data(search_results=orders)
    orders_with_numbers = [(index + 1, order) for index, order in enumerate(orders)]
    total_pages = ((len(orders_with_numbers) + 9) // 10)
    await admin_display_orders_page(1, message, orders_with_numbers, total_pages, 10, prefix, state)

async def admin_handle_order_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    page_num = int(data_parts[1])
    if not (data := await admin_check_state_data(state, callback_query)):
        return
    orders = data.get("search_results", [])
    orders_with_numbers = [(index + 1, order) for index, order in enumerate(orders)]
    orders_per_page = 10
    total_pages = (len(orders_with_numbers) + orders_per_page - 1) // orders_per_page
    await admin_display_orders_page(page_num, callback_query, orders_with_numbers, total_pages, orders_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_display_orders_page(page_num, callback_query_or_message, orders_with_numbers, total_pages, orders_per_page, callback_prefix, state):
    start_index = (page_num - 1) * orders_per_page
    end_index = min(start_index + orders_per_page, len(orders_with_numbers))
    page_orders = orders_with_numbers[start_index:end_index]
   
    message_text = (
        f"🔍 Umumiy natija: {len(orders_with_numbers)} ta buyurtma topildi.\n"
        f"📜 Sahifa natijasi: {start_index + 1}-{end_index}:\n\n")
    
    for number, order in page_orders:
        space_prefix = "    " if number < 10 else "      " 
        message_text += (
            f"{number}. 🆔 <b>Buyurtma IDsi:</b> #{order.order_id}\n"
            f"{space_prefix}📅 <b>Sana:</b> {order.created_at.strftime('%Y-%m-%d')}\n"
            f"{space_prefix}📌 <b>Yetkazish holati:</b> {DELIVERY_STATUS_CHOICES[order.status]}\n"+
           (f"{space_prefix}💰 <b>Jami summa:</b> <del>{order.total_price}</del> so‘m\n" +
            f"{space_prefix}🏷️ <b>Chegirma bilan summa:</b> {order.discounted_price} so‘m\n" if order.discounted_price else 
            f"{space_prefix}💰 <b>Jami summa:</b>{order.total_price} so‘m\n") +
            f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
        )


    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()

    for number, order in page_orders:
        builder.button(text=str(number), callback_data=f"admin_selected_order:{order.id}")


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
    additional_buttons = admin_keyboard_back_to_order().inline_keyboard

    final_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + pagination.export() + additional_buttons)

    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")
    else:
        await callback_query_or_message.reply(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")

async def admin_update_and_clean_messages_order(message: Message, chat_id: int, message_id: int, text: str, order_id: int):
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=admin_order_edit_keyboard(order_id)
    )
    delete_tasks = [message.bot.delete_message(chat_id, msg_id) for msg_id in range(message.message_id, message_id, -1)]
    await asyncio.gather(*delete_tasks, return_exceptions=True)

# Get single order
@admin_order_router.callback_query(IsAdminFilter(), F.data.startswith('admin_selected_order:'))
async def admin_get_single_order(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    id = int(callback_query.data.split(':')[1])
    order = await admin_get_order_by_id(id)
    if not order:
        await callback_query.message.answer("❌ Buyurtma topilmadi.")
        await callback_query.answer()
        return
    order_info = await admin_format_order_info(order)
    current_state = await state.get_state()
    try:
        try:
            if current_state.startswith('AdminOrderFSM:admin_waiting_edit_order'):
                await callback_query.message.edit_text(text=order_info, parse_mode='HTML', reply_markup=admin_order_edit_keyboard(id))
        except: 
            await callback_query.message.answer(text=order_info, parse_mode='HTML', reply_markup=admin_order_edit_keyboard(id))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Buyurtmani yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

# Filter by status
@admin_order_router.message(AdminOrderFSM.admin_waiting_filter_by_status)
async def admin_filter_by_delivery_status(message: Message, state: FSMContext):
    await message.answer("Buyurtma holatini tanlang:", reply_markup=admin_order_delivery_status_keyboard())
    await state.set_state(AdminOrderFSM.admin_waiting_search_order_by_delivery_status)

@admin_order_router.message(AdminOrderFSM.admin_waiting_search_order_by_delivery_status)
async def admin_search_order_by_delivery_status(message: Message, state: FSMContext):
    selected_status = message.text.strip()
    status_key = None
    for key, label in DELIVERY_STATUS_CHOICES.items():
        if label == selected_status:
            status_key = key
            break
    if status_key is None:
        await message.answer(
            f"❌ Noto‘g‘ri holat tanlandi. Quyidagilardan birini tanlang:\n{', '.join(DELIVERY_STATUS_CHOICES.values())}", reply_markup=admin_order_delivery_status_keyboard())
        return
    
    orders = await sync_to_async(lambda: list(Order.objects.filter(status=status_key).select_related('user').order_by('-created_at')))()
    await admin_handle_order_search_results(message, orders, state)
    await state.clear()

# Filter by payment status
@admin_order_router.message(AdminOrderFSM.admin_waiting_filter_by_payment_status)
async def admin_filter_by_payment_status(message: Message, state: FSMContext):
    await message.answer(f"To‘lov holatini tanlang:\n", reply_markup=admin_order_payment_status_keyboard())
    await state.set_state(AdminOrderFSM.admin_waiting_search_order_by_payment_status)

@admin_order_router.message(AdminOrderFSM.admin_waiting_search_order_by_payment_status)
async def admin_search_order_by_payment_status(message: Message, state: FSMContext):
    payment_status = message.text.strip()
    status_key = None
    for key, label in PAYMENT_STATUS_CHOICES.items():
        if label == payment_status:
            status_key = key
            break
    orders = await sync_to_async(lambda: list(Order.objects.filter(payment_status=status_key).select_related('user').order_by('-created_at')))()
    await admin_handle_order_search_results(message, orders, state)

# Filter by payment method
@admin_order_router.message(AdminOrderFSM.admin_waiting_filter_by_payment_method)
async def admin_filter_by_payment_method(message: Message, state: FSMContext):
    await message.answer(f"To‘lov usulini tanlang:\n", reply_markup=admin_order_payment_method_keyboard())
    await state.set_state(AdminOrderFSM.admin_waiting_search_order_by_payment_method)

@admin_order_router.message(AdminOrderFSM.admin_waiting_search_order_by_payment_method)
async def admin_search_order_by_payment_method(message: Message, state: FSMContext):
    payment_method = message.text.strip()
    status_key = None
    for key, label in PAYMENT_STATUS_CHOICES.items():
        if label == payment_method:
            status_key = key
            break
    orders = await sync_to_async(lambda: list(Order.objects.filter(payment_method=status_key).select_related('user').order_by('-created_at')))()
    await admin_handle_order_search_results(message, orders, state)

# Filter by user
@admin_order_router.message(AdminOrderFSM.admin_waiting_filter_by_user)
async def admin_filter_by_user(message: Message, state: FSMContext):
    await message.answer("Foydalanuvchi Telegram ID sini kiriting (masalan, 123456789):", reply_markup=admin_get_cancel_reply_keyboard().as_markup(resize_keyboard=True))
    await state.set_state(AdminOrderFSM.admin_waiting_input_user_id)

@admin_order_router.message(AdminOrderFSM.admin_waiting_input_user_id)
async def admin_search_order_by_user_id(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
        orders = await sync_to_async(lambda: list(Order.objects.filter(user__telegram_id=telegram_id).select_related('user').order_by('-created_at')))()
        if not orders:
            await message.answer("❌ Bu foydalanuvchiga tegishli buyurtma topilmadi.")
            return
        await admin_handle_order_search_results(message, orders, state)
    except ValueError:
        await message.answer("❌ Noto‘g‘ri format. Iltimos, Telegram ID raqamini kiriting (masalan, 123456789).")

# Filter by date
@admin_order_router.message(AdminOrderFSM.admin_waiting_filter_by_date)
async def admin_filter_by_date(message: Message, state: FSMContext):
    await message.answer("Sanani kiriting (masalan, 2025-03-25):", reply_markup=admin_get_cancel_reply_keyboard().as_markup(resize_keyboard=True))
    await state.set_state(AdminOrderFSM.admin_waiting_input_date)

@admin_order_router.message(AdminOrderFSM.admin_waiting_input_date)
async def admin_input_date(message: Message, state: FSMContext):
    try:
        date_input = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d")
        date_start = timezone.make_aware(date_input.replace(hour=0, minute=0, second=0))
        date_end = timezone.make_aware(date_input.replace(hour=23, minute=59, second=59))
        orders = await sync_to_async(lambda: list(Order.objects.filter(created_at__range=(date_start, date_end)).select_related('user').order_by('-created_at')))()
        if not orders:
            await message.answer(f"❌ {message.text} sanasida buyurtma topilmadi.")
            return
        await admin_handle_order_search_results(message, orders, state)
    except ValueError:
        await message.answer("❌ Noto‘g‘ri format. Iltimos, sanani to‘g‘ri kiriting (masalan, 2025-03-25).")

# Editing part
@admin_order_router.callback_query(IsAdminFilter(), F.data.startswith('admin_order_field_'))
async def admin_order_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[3]
    order_id = int(callback_query.data.split(":")[1])
    user = await get_user_from_db(callback_query.from_user.id)
    order = await admin_get_order_by_id(order_id)
    if not order:
        await callback_query.answer("❌ Xatolik: Buyurtma topilmadi.")
        return

    field_actions = {
        "Yetkazish holati": (AdminOrderFSM.admin_waiting_edit_order_delivery_status, "status", DELIVERY_STATUS_CHOICES),
        "Yetkazib berish manzili": (AdminOrderFSM.admin_waiting_edit_order_delivery_address, None, ORDER_ADDRESS_FIELDS),
        "To‘lov holati": (AdminOrderFSM.admin_waiting_edit_order_payment_status, "payment_status", PAYMENT_STATUS_CHOICES),
        "To‘lov usuli": (AdminOrderFSM.admin_waiting_edit_order_payment_method, "payment_method", PAYMENT_METHOD_CHOICES),
        # "delete_order": (AdminOrderFSM.admin_waiting_order_deletion, None, None),
    }

    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, buyurtmani asosiy bo‘limidan qaytadan tanlang.")
        return

    await state.update_data(message_id=message_id, chat_id=chat_id, order=order, user=user)
    next_state = field_actions[field][0]
    await state.set_state(next_state)

    # if field == "delete_order":
    #     await callback_query.message.answer(f"Ushbu buyurtmani o‘chirmoqchimisiz? 🗑", reply_markup=admin_delete_confirmation_keyboard("admin_order", order_id))
    # else:
    builder = InlineKeyboardBuilder()
    choices = field_actions[field][2]  
    field_key = field_actions[field][1]  
    if choices and field_key: 
        current_value = getattr(order, field_key)
        for key, value in choices.items():
            if key == current_value:  
                continue
            builder.button(text=value, callback_data=f"admin_edit_{field_key}:{key}")
        builder.adjust(2)
        keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_back_to_single_order_keyboard(order.id).inline_keyboard)
        await callback_query.message.edit_text(f"🆔 ~ #{order.order_id} \n Buyurtmaning yangi {field.lower()}ni tanlang:", reply_markup=keyboard)
    else:
        for key, value in choices.items():
            builder.button(text=value, callback_data=f"admin_edit_address:{key}")
        builder.adjust(3)
        keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_back_to_single_order_keyboard(order.id).inline_keyboard)
        await callback_query.message.edit_text("📍 Manzilning qaysi maydonini o'zgartirmoqchisiz?", parse_mode='HTML', reply_markup=keyboard)
    await callback_query.answer()

@admin_order_router.callback_query(IsAdminFilter(), F.data.startswith(('admin_edit_status:', 'admin_edit_payment_status:', 'admin_edit_payment_method:', 'admin_edit_address:')))
async def admin_edit_order_field(callback_query: CallbackQuery, state: FSMContext):
    if not (data := await admin_check_state_data(state, callback_query)):
        return
    order, chat_id, message_id, user = (data.get(k) for k in ("order", "chat_id", "message_id", "user"))

    field_part = callback_query.data.split(":")[0]
    field_type = "_".join(field_part.split("_")[2:])
    new_value = callback_query.data.split(":")[1]

    field_configs = {
        "status": ("status", DELIVERY_STATUS_CHOICES, "Yetkazish holati"),
        "payment_status": ("payment_status", PAYMENT_STATUS_CHOICES, "To‘lov holati"),
        "payment_method": ("payment_method", PAYMENT_METHOD_CHOICES, "To‘lov usuli"),
        "address": (None, ORDER_ADDRESS_FIELDS, "Yetkazib berish manzili"),
    }

    if field_type == "address":
        field_key = new_value  
        display_name = ORDER_ADDRESS_FIELDS[field_key]

        
        await callback_query.message.edit_text(f"🆔 ~ #{order.order_id} \n Yangi {display_name.lower()}ni kiriting:", parse_mode='HTML',
                                               reply_markup=admin_back_to_single_order_keyboard(order.id))
            
        await state.update_data(address_field_to_edit=field_key)
    else:
        try:
            field_key, choices, field_name = field_configs[field_type]
        except KeyError:
            await callback_query.answer("❌ Xatolik: Noto‘g‘ri maydon turi.")
            return

        setattr(order, field_key, new_value)
        await sync_to_async(order.save)(update_fields=[field_key])

        await callback_query.answer(f"✅ {field_name} '{choices[new_value]}' ga yangilandi.")
        order_info = await admin_format_order_info(order)
        await admin_update_and_clean_messages_order(callback_query.message, chat_id, message_id, order_info, order.id)

        answer_text = f'\n\nBuyurtmangizning {field_name.lower()} "{choices[new_value]}" ga yangilandi😊'
        await admin_send_order_updation_to_user(callback_query.bot, order, answer_text)

@admin_order_router.message(AdminOrderFSM.admin_waiting_edit_order_delivery_address)
async def admin_edit_order_delivery_address(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return
    
    order, chat_id, message_id, user = (data.get(k) for k in ("order", "chat_id", "message_id", "user"))
    field_key = data.get("address_field_to_edit")
    new_value = message.text.strip()

    if field_key not in ['region', 'city', 'street_address']:
        await message.answer("❌ Xatolik: Yuqoridagi tugmalardan birini tanlang 👆")
        return

    setattr(order, field_key, new_value)
    await sync_to_async(order.save)(update_fields=[field_key])

    await message.answer(f"✅ {ORDER_ADDRESS_FIELDS[field_key]} yangilandi.")
    order_info = await admin_format_order_info(order)
    await admin_update_and_clean_messages_order(message, chat_id, message_id, order_info, order.id)

    answer_text = f'\n\nBuyurtmangizning manzili "{new_value}" ga yangilandi😊'
    await admin_send_order_updation_to_user(message.bot, order, answer_text)
    await state.clear()






