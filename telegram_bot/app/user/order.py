from aiogram import Router, F
from django.utils import timezone
from asgiref.sync import sync_to_async
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telegram_bot.app.utils import get_user_from_db, IsUserFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram_bot.app.user.utils import user_keyboard_back_to_order
from aiogram.types import InlineKeyboardMarkup, CallbackQuery, Message
from telegram_app.models import Cart, Order, OrderItem, CartItem, RewardHistory

user_order_router = Router()

class UserOrderFSM(StatesGroup):
    user_waiting_get_current_orders = State()
    user_waiting_view_order_history = State()
    user_waiting_start_order_cancellation = State()
    user_waiting_order_history_paginated = State()
    user_waiting_search_orders = State()

#Utils
STATUS_CHOICES = {
        'Pending': 'Yig\'ilmoqda ⏳', 'Shipped': 'Jo‘natildi 🚚',
        'Delivered': 'Yetkazilgan ✅', 'Cancelled': 'Bekor qilingan 🚫'
    }

async def user_format_order_info(order, user):
    order_items = order.items.all()
    items_text = "\n".join([f"{index + 1}. {item.product.name} - {item.quantity} ta - {item.price} so'm" for index, item in enumerate(order_items)])
    PAYMENT_METHOD_CHOICES = {'Cash': 'Naqd 💵', 'Card': 'Karta 💳', 'Payme': 'Payme 📲', 'Click': 'Click 📱'}
    PAYMENT_STATUS_CHOICES = {'Unpaid': 'To\'lanmagan ⚠️', 'Paid': 'To\'langan ✅'}
    return (
        f"<b>🆔 Buyurtma raqami:</b> #{order.order_id}\n"
        f"<b>📌 Yetkazish holati:</b> {STATUS_CHOICES[order.status]}\n"
        f"<b>💳 To'lov usuli:</b> {PAYMENT_METHOD_CHOICES[order.payment_method]}\n"
        f"<b>🔄 To'lov holati:</b> {PAYMENT_STATUS_CHOICES[order.payment_status]}\n"
        f"<b>📅 Sana:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"<b>📍 Manzil:</b> {user.region}, {user.city}, {user.street_address}\n\n"
        f"<b>🛍 Mahsulotlar:</b>\n{items_text}\n\n" +
       (f"<b>💰 Jami summa:</b> <del>{order.total_price}</del> so‘m\n"
        f"<b>🏷️ Chegirma bilan summa:</b> {order.discounted_price} so‘m" if order.discounted_price else
        f"<b>💰 Jami summa:</b> {order.total_price} so‘m")
    )

def user_order_keyboard(order):
    builder = InlineKeyboardBuilder()
    builder.button(text="📜 Buyurtmalar bo'limi", callback_data="user_orders_section"),
    if order.status in ['Pending', 'Shipped']:
        builder.button(text="🚫 Bekor qilish", callback_data=f"user_cancel_order:{order.id}")
    builder.button(text="❌", callback_data="user_delete_message")
    builder.adjust(2, 1)
    return builder.as_markup()

async def user_handle_order_search_results(message: Message, orders, state: FSMContext):
    if not orders:
        await message.answer("❌ Hech qanday buyurtma topilmadi.")
        return
    
    await state.update_data(user_search_results=orders)
    
    orders_with_numbers = [(index + 1, order) for index, order in enumerate(orders)]
    total_pages = ((len(orders_with_numbers) + 9) // 10)
    await user_display_fetched_orders_page(1, message, orders_with_numbers, total_pages, 10, "user_search_orders", state)

async def user_handle_order_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    
    page_num = int(data_parts[1])
    state_data = await state.get_data()
    orders = state_data.get("user_search_results", [])
   
    orders_with_numbers = [(index + 1, order) for index, order in enumerate(orders)]
    orders_per_page = 10
    total_pages = (len(orders_with_numbers) + orders_per_page - 1) // orders_per_page
    
    await user_display_fetched_orders_page(page_num, callback_query, orders_with_numbers, total_pages, orders_per_page, callback_prefix, state)
    await callback_query.answer()

async def user_display_fetched_orders_page(page_num, message_or_callback, orders_with_numbers, total_pages, per_page, callback_prefix, state):
    start_idx = (page_num - 1) * per_page
    end_idx = min(start_idx + per_page, len(orders_with_numbers))
    page_orders = orders_with_numbers[start_idx:end_idx]
    current_state = await state.get_state()

    if current_state.startswith('UserOrderFSM:user_waiting_view_order_history'):
        message_text = f"📜 Buyurtmalar tarixi bo'limi:\n\n"
    elif current_state.startswith('UserOrderFSM:user_waiting_start_order_cancellation'):
        message_text = f"🚫 Buyurtmani bekor qilish bo'limi:\n\n"
    else:
        message_text = f"⏳ Joriy buyurtmalar bo'limi:\n\n" 

    message_text += (
        f"🔍 Umumiy natija: {len(orders_with_numbers)} ta buyurtma topildi.\n"
        f"📜 Sahifa natijasi: {start_idx + 1}-{end_idx}:\n\n")
    
    for number, order in page_orders:
        space_prefix = "    " if number < 10 else "      " 
        message_text += (
            f"{number}. 🆔 <b>Buyurtma IDsi:</b> #{order.order_id}\n"
            f"{space_prefix}📅 <b>Sana:</b> {order.created_at.strftime('%Y-%m-%d')}\n"
            f"{space_prefix}📌 <b>Yetkazish holati:</b> {STATUS_CHOICES[order.status]}\n" +
           (f"{space_prefix}💰 <b>Jami summa:</b> <del>{order.total_price}</del> so‘m\n"
            f"{space_prefix}🏷️ <b>Chegirma bilan summa:</b> {order.discounted_price} so‘m\n" if order.discounted_price else 
            f"{space_prefix}💰 <b>Jami summa:</b>{order.total_price} so‘m\n") +
            f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
        )
        
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()

    for number, order in page_orders:
        builder.button(text=str(number), callback_data=f"user_selected_order:{order.order_id}")

    builder.adjust(5)

    if total_pages > 1:
        pagination_buttons = []
        if page_num > 1:
            pagination_buttons.append({"text": "⬅️", "callback_data": f"{callback_prefix}_other_pages:{page_num - 1}"})

        pagination_buttons.append({"text": "❌", "callback_data": "user_delete_message"})

        if page_num < total_pages:
            pagination_buttons.append({"text": "➡️", "callback_data": f"{callback_prefix}_other_pages:{page_num + 1}"})

        for btn in pagination_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(pagination_buttons)) 
    
    else:
        pagination.button(text="❌", callback_data="user_delete_message")
        pagination.adjust(5, 5, 1)  

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=builder.export() + pagination.export() + user_keyboard_back_to_order().inline_keyboard
    )

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text=message_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        new_message = await message_or_callback.answer(text=message_text, reply_markup=keyboard, parse_mode="HTML")
        await state.update_data(message_ids=[new_message.message_id])

# Get all orders
async def user_get_all_orders(message: Message, state: FSMContext, current_orders=None):
    user = await get_user_from_db(message.from_user.id)
    if current_orders:
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user, status__in=['Pending', 'Shipped']).order_by('-created_at').only('order_id', 'created_at', 'total_price', 'discounted_price', 'status')))()
    else:
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user).order_by('-created_at').only('order_id', 'created_at', 'total_price', 'discounted_price', 'status')))()
    await user_handle_order_search_results(message, orders, state)

@user_order_router.callback_query(IsUserFilter(), F.data.startswith('user_search_orders_other_pages:'))
async def user_get_all_orders_other_pages_callback(callback_query: CallbackQuery, state: FSMContext):
    await user_handle_order_other_pages(callback_query, state, callback_prefix="user_search_orders")

# Get single order
@user_order_router.callback_query(IsUserFilter(), F.data.startswith("user_selected_order:"))
async def user_selected_order(callback_query: CallbackQuery, state: FSMContext):
    order_id = callback_query.data.split(":")[1]
    user = await get_user_from_db(callback_query.from_user.id)
    order = await sync_to_async(lambda: Order.objects.filter(order_id=order_id, user=user).prefetch_related('items__product').first())()
    if not order:
        await callback_query.message.edit_text("❌ Buyurtma topilmadi.")
        return
    order_info = await user_format_order_info(order, user)
    await callback_query.message.answer(order_info,  parse_mode='HTML', reply_markup=user_order_keyboard(order))
    await callback_query.answer()

# Cencellation process
@user_order_router.callback_query(IsUserFilter(), F.data.startswith("user_cancel_order:"))
async def user_confirm_order_cancellation(callback_query: CallbackQuery, state: FSMContext):
    id = callback_query.data.split(":")[1]
    user = await get_user_from_db(callback_query.from_user.id)
    order = await sync_to_async(lambda: Order.objects.filter(id=id, user=user).prefetch_related('items__product').first())()
    if not order:
        await callback_query.message.answer("❌ Buyurtma topilmadi")
        return

    builder = InlineKeyboardBuilder()
 
    builder.button(text="✅ Ha", callback_data=f"user_confirm_cancel:{order.id}"), 
    builder.button(text="❌ Yo'q", callback_data=f"user_cancel_cancelation:{order.id}"), 
    builder.adjust(2)

    await callback_query.message.edit_text(f"Buyurtma #{order.order_id} ni bekor qilishni tasdiqlaysizmi?\n\n{await user_format_order_info(order, user)}", parse_mode='HTML', reply_markup=builder.as_markup())

# Confirm cancellation
@user_order_router.callback_query(IsUserFilter(), F.data.startswith("user_confirm_cancel:"))
async def user_confirm_order_cancellation(callback_query: CallbackQuery, state: FSMContext):
    id = callback_query.data.split(":")[1]
    user = await get_user_from_db(callback_query.from_user.id)
    order = await sync_to_async(lambda: Order.objects.select_related('cart').filter(id=id, user=user).first())()
    
    if order and order.status in ['Pending', 'Shipped']:
        order.status = "Cancelled"
        order.updated_at = timezone.now()
        await sync_to_async(order.save)()

        # ✅ **Mahsulotlarni zaxiraga qaytarish**
        order_items = await sync_to_async(list)(order.items.select_related('product').all())
        for item in order_items:
            product = item.product
            product.stock += item.quantity  
            product.stock = max(product.stock, 0)
            product.available = product.stock > 0  # **Mavjudligini tekshirish**
            await sync_to_async(product.save)()

        cart = order.cart

        # ✅ **Promokodlarni tiklash**
        promocodes = await sync_to_async(list)(cart.promocodes.all())
        for promo in promocodes:
            promo.used_count = max(promo.used_count - 1, 0)  # `used_count` kamaytirish
            if promo.used_count < promo.usage_limit:
                promo.is_active = True  # **Agar limitdan past bo‘lsa, faollashtirish**
            await sync_to_async(promo.save)()

            # ✅ **Agar bu promokod reward orqali ishlatilgan bo‘lsa, uni `RewardHistory`ga qaytarish**
            reward_history = await sync_to_async(lambda: RewardHistory.objects.filter(
                user=user, reward__promocode=promo, is_used=True
            ).first())()
            if reward_history:
                reward_history.is_used = False
                await sync_to_async(reward_history.save)()

        # ✅ **Sovg‘alarni qaytarish**
        rewards = await sync_to_async(list)(cart.rewards.all())
        for reward in rewards:
            reward_history = await sync_to_async(lambda: RewardHistory.objects.filter(
                user=user, reward=reward, is_used=True
            ).first())()
            if reward_history:
                reward_history.is_used = False 
                await sync_to_async(reward_history.save)()

        await callback_query.message.edit_text(f"✅ Buyurtma #{order.order_id} muvaffaqiyatli bekor qilindi!")
    
    else:
        await callback_query.message.edit_text("❌ Buyurtma topilmadi yoki bekor qilib bo‘lmaydi.")
         
    await callback_query.answer()
    await state.clear()

# Cancel cancellation
@user_order_router.callback_query(IsUserFilter(), F.data.startswith("user_cancel_cancelation:"))
async def user_cancel_cancellation(callback_query: CallbackQuery, state: FSMContext):
    id = callback_query.data.split(":")[1]
    user = await get_user_from_db(callback_query.from_user.id)
    order = await sync_to_async(lambda: Order.objects.filter(id=id, user=user).prefetch_related('items__product').first())()
    await callback_query.answer("Buyurtma bekor qilish rad etildi. ✅")
    await callback_query.message.edit_text(f"{await user_format_order_info(order, user)}", parse_mode='HTML', reply_markup=user_order_keyboard(order))
    await state.clear()

# Proceed to order
@user_order_router.callback_query(IsUserFilter(), F.data.startswith('user_proceed_to_order:'))
async def user_proceed_to_order(callback_query: CallbackQuery, state: FSMContext):
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Naqd pul", callback_data="payment_select:Cash")
    builder.button(text="💳 UzCard/Humo", callback_data="payment_select:Card")
    builder.button(text="📲 Payme", callback_data="payment_select:Payme")
    builder.button(text="📱 Click", callback_data="payment_select:Click")
    builder.adjust(2)

    await callback_query.message.edit_text(f"💳 <b>To‘lov usulini tanlang:</b>", parse_mode="HTML", reply_markup=builder.as_markup())
    await callback_query.answer()

@user_order_router.callback_query(IsUserFilter(), F.data.startswith('payment_select:'))
async def process_payment_selection(callback_query: CallbackQuery, state: FSMContext):
    """To‘lov usuli tanlanganda order yaratish"""
    
    payment_method = callback_query.data.split(":")[1]
    
    user = await get_user_from_db(callback_query.from_user.id)

    if not user:
        await callback_query.answer("Iltimos, avval ro‘yxatdan o‘ting.")
        return
    
    if not user.region or not user.city or not user.street_address:
        await callback_query.answer("⚠️ Buyurtma yaratish uchun avval manzilingizni to'liq to‘ldiring!", show_alert=True)
        return
    
    cart = await sync_to_async(Cart.objects.filter(user=user, is_active=True).first)()
    if not cart:
        await callback_query.answer("Savatingiz bo‘sh yoki faol emas.")
        return  
    
    total_price = await sync_to_async(cart.total_price)()
    discounted_price = await sync_to_async(cart.discounted_price)()
    cart_items = await sync_to_async(list)(CartItem.objects.filter(cart=cart).select_related('product'))
    if not cart_items:
        await callback_query.answer("Savatingiz bo‘sh.")
        return

    for item in cart_items:
        product = item.product
        available_stock = await sync_to_async(lambda: product.available_stock)()
        if available_stock < item.quantity:
            await callback_query.answer(f"{product.name} uchun yetarli zaxira yo‘q!")
            return
        # Reservdan chiqarish (kamaytirish)
        product.reserved_stock -= item.quantity
        product.reserved_stock = max(product.reserved_stock, 0) 
        # Umumiy zaxirani kamaytirish
        product.stock -= item.quantity
        product.stock = max(product.stock, 0)  
        product.available = product.stock > 0
        await sync_to_async(product.save)()

    # ✅ **Order yaratish**
    order = await sync_to_async(Order.objects.create)(
        cart=cart,
        user=user,
        region=user.region,
        city=user.city,
        street_address=user.street_address,
        total_price=total_price,
        discounted_price=discounted_price,
        status="Pending",
        payment_method=payment_method, 
        payment_status="Unpaid",
        created_at=timezone.now(),
        updated_at=timezone.now()
    )

    # ✅ **OrderItem yaratish**
    try:
        order_items = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=await sync_to_async(lambda: item.product.discounted_price)()
            )
            for item in cart_items
        ]
        await sync_to_async(OrderItem.objects.bulk_create)(order_items)
    except Exception as e:
        print(f"Exception: {e}")
        await callback_query.answer("❌ Buyurtma yaratishda xatolik yuz berdi. Iltimos, qayta urinib ko‘ring.")
        return
    
    # ✅ **Savatchani o‘chirish (deaktivatsiya qilish)**
    cart.is_active = False
    cart.reserved_until = None
    cart.warning_sent = False
    await sync_to_async(cart.save)()

    PAYMENT_METHOD_CHOICES = dict([
        ('Cash', '💵 Naqd'),
        ('Card', '💳 Karta'),
        ('Payme', 'Payme'),
        ('Click', 'Click'),])
    
    await callback_query.message.edit_text(
        f"✅ <b>Buyurtma yaratildi!</b>\n\n"
        f"🆔 Buyurtma raqami: #{order.order_id}\n"
        + (f"💰 Jami summa: <del>{total_price}</del> so‘m\n"
           f"🏷️ Chegirma bilan: {discounted_price} so‘m\n" if discounted_price else f"💰 Jami summa: {total_price} so‘m\n"),
        f"💳 To‘lov usuli: {PAYMENT_METHOD_CHOICES[payment_method]}\n"
        f"📜 Buyurtmalar bo‘limida statusni kuzatib borishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=user_keyboard_back_to_order()
    )
    await state.clear()






