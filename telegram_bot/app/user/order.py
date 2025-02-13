from aiogram import Router, F
import asyncio
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Cart, Order, OrderItem
from telegram_bot.app.user.main_controls import ORDERS_CONTROLS_KEYBOARD

order_router = Router()


# Order functionlity
@order_router.callback_query(F.data.startswith('proceed_to_order:'))
async def proceed_to_order(callback_query: CallbackQuery):
    user = await get_user_from_db(callback_query.from_user.id)
    cart_id = int(callback_query.data.split(':')[1])

    if not user:
        await callback_query.answer("Iltimos, avval ro'yxatdan o'ting.")
        return
    
    cart = await sync_to_async(Cart.objects.filter(id=cart_id, is_active=True).first)() 
    if not cart:
        await callback_query.answer("Savatingiz bo'sh yoki faol emas.")
        return

    cart_items = await sync_to_async(list)(cart.items.all())

    if not cart_items:  
        await callback_query.answer("Savatingiz bo'sh.")
        return

    total_price = sum(await asyncio.gather(*(sync_to_async(item.subtotal)() for item in cart_items)))

    # Create the order
    order = await sync_to_async(Order.objects.create)(
        cart=cart,
        user=user,
        total_price=total_price,
        status="Pending",
        payment_status="Unpaid"  # Set initial payment status
    )
    
    # Create OrderItems
    order_items = [
        OrderItem(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )
        for item in cart_items
    ]
    # Save all OrderItems in bulk to improve performance
    await sync_to_async(OrderItem.objects.bulk_create)(order_items)
    
    # Set cart as inactive
    cart.is_active = False
    await sync_to_async(cart.save)()

    # Prepare the payment options keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Naqd pul", callback_data=f"payment:{order.order_id}:cod"),
            InlineKeyboardButton(text="UzCard/Humo", callback_data=f"payment:{order.order_id}:uzcard_humo"),
        ],
        [
            InlineKeyboardButton(text="Payme", callback_data=f"payment:{order.order_id}:payme"),
            InlineKeyboardButton(text="Click", callback_data=f"payment:{order.order_id}:click")
        ]
    ])
    
    # await update_cart_message(callback_query.message, user)
    await callback_query.answer("Buyurtmangiz qabul qilindi!")
    await callback_query.message.answer(f"Buyurtma muvaffaqiyatli yaratildi! ✅\nBuyurtma raqami: {order.order_id}\nJami summa: {total_price}\n\nTo'lov turini tanlang: 👇", reply_markup=keyboard)


