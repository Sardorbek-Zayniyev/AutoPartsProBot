from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.state import StateFilter
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Product, Cart, CartItem, SavedItemList, SavedItem
from telegram_bot.app.user.product import format_product_info, product_keyboard
from telegram_bot.app.user.main_controls import CART_CONTROLS_KEYBOARD

cart_router = Router()



class CartFSM(StatesGroup):
    waiting_viewing_cart = State()
    waiting_viewing_saved_items = State()



@cart_router.message(F.text.in_(("👁️ Savatni ko'rish", "♥️ Saqlangan mahsulotlar")))
async def cart_controls_handler(message: Message, state: FSMContext):
    """
    Handle cart control actions (view cart, clear cart)
    """

    actions = {
        "👁️ Savatni ko'rish": (CartFSM.waiting_viewing_cart, show_cart),
        "♥️ Saqlangan mahsulotlar": (CartFSM.waiting_viewing_saved_items, show_saved_items_list),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)




# Cart list
@sync_to_async
def get_total_price(cart):
    return cart.total_price()

@sync_to_async
def get_quantity(cart_item):
    return cart_item.get_quantity()

# Main Cart
@cart_router.message(StateFilter(CartFSM.waiting_viewing_cart))
async def show_cart(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    if not user:
        await message.answer("Iltimos, avval ro'yxatdan o'ting.")
        return

    cart, _ = await sync_to_async(Cart.objects.get_or_create)(user=user, is_active=True)
    cart_items = await sync_to_async(list)(cart.items.all())

    if not cart_items:
        await message.answer("Savatingiz bo'sh.")
        return

    await update_cart_message(message, user)

async def update_cart_message(message: Message, user):
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()
    cart_items = await sync_to_async(list)(cart.items.all())

    if not cart_items:
        await message.edit_text("Savatingiz bo'sh.")
        return

    cart_text = "<b> Sizning savatingiz:</b>\n\n"
    total_price = 0

    for index, item in enumerate(cart_items, start=1):
        product = await sync_to_async(lambda: item.product)()
        subtotal = await sync_to_async(item.subtotal)()
        total_price += subtotal
        cart_text += (f"<b>{index}</b>. <b>{product.name}:</b> {product.price} x {item.quantity} = {subtotal} <b>so'm</b>\n")

    cart_text += f"\n<b>Jami:</b> {total_price} <b>so'm</b>"

    try:
        await message.edit_text(cart_text, parse_mode='HTMl', reply_markup=(await cart_keyboard(cart)))
    except TelegramBadRequest:
        await message.answer(cart_text, parse_mode='HTMl', reply_markup=(await cart_keyboard(cart)))

@cart_router.callback_query(F.data_in(('increase_cart_item_quantity:', 'decrease_cart_item_quantity:', 'remove_item_from_cart')))
async def update_cart_item_quantity(callback_query: CallbackQuery):
    action = callback_query.data.split(':')[0]
    item_id = int(callback_query.data.split(':')[1])
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()
    item = await sync_to_async(CartItem.objects.filter(id=item_id, cart=cart).first)()
    product = await sync_to_async(item.get_product)()

    if not item:
        await callback_query.answer("Mahsulot mavjud emas")
        return

    if action == 'increase_cart_item_quantity':
        item.quantity += 1
        product.reserved_stock += 1
        await sync_to_async(product.save)()
        await sync_to_async(item.save)()
        await callback_query.answer(f"Mahsulot savatga qo'shildi")
    elif action == 'decrease_cart_item_quantity':
        if item.quantity > 1:
            item.quantity -= 1
            await sync_to_async(item.save)()
            await callback_query.answer("Mahsulot kamaytirildi")
        else:
            await sync_to_async(item.delete)()
            await callback_query.answer("Mahsulot savatdan o'chirildi")
        product.reserved_stock -= 1
        await sync_to_async(product.save)()
    elif action == 'remove_item_from_cart':
        product.reserved_stock -= item.quantity 
        await sync_to_async(product.save)()
        await sync_to_async(item.delete)()
        await callback_query.answer("Mahsulot savatdan olib tashlandi")

    await update_cart_message(callback_query.message, user)

async def cart_keyboard(cart):
    cart_items = await sync_to_async(list)(cart.items.all())
    if cart_items:
        cart_keyboards = [
            [
                InlineKeyboardButton(text=f"{await sync_to_async(item.get_product)()}", callback_data="noop"),
                InlineKeyboardButton(
                    text=f"➖", callback_data=f"decrease_cart_item_quantity:{item.id}"),
                InlineKeyboardButton(
                    text=f"🛒 {item.quantity}", callback_data=f"item:{item.id}"),
                InlineKeyboardButton(
                    text=f"➕", callback_data=f"increase_cart_item_quantity:{item.id}"),
                InlineKeyboardButton(
                    text="❌", callback_data=f"remove_item_from_cart:{item.id}"),
            ] for item in cart_items
            ] + [[InlineKeyboardButton(text="🗑️ Savatni tozalash", callback_data="clear_cart")]
            ] + [[InlineKeyboardButton(text="✅ Buyurtmaga o'tish", callback_data=f"proceed_to_order:{cart.id}")]]
        return InlineKeyboardMarkup(inline_keyboard=cart_keyboards)
    else:
        return None

@cart_router.callback_query(F.data == "clear_cart")
async def clear_cart(callback_query: CallbackQuery):
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()
    if cart:
        await sync_to_async(cart.items.all().delete)()
        await callback_query.answer("Savat tozalandi")

        try:
            # Try to edit the message
            await callback_query.message.edit_text("Savatingiz bo'sh.")
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest as e:
            # If the message is not modified, answer the callback with an appropriate message
            await callback_query.answer("Savat allaqachon bo'sh.")

# Cart for each product
@cart_router.callback_query(F.data == "view_cart")
async def view_cart_callback(callback_query: CallbackQuery, state: FSMContext):
    user = await get_user_from_db(callback_query.from_user.id)
    await update_cart_message(callback_query.message, user)

@cart_router.callback_query(F.data.startswith(('increase_product_quantity:', 'decrease_product_quantity:', 'delete_product:')))
async def update_product_quantity(callback_query: CallbackQuery):
    action, product_id = callback_query.data.split(':')
    product_id = int(product_id)

    # Lock product row for update
    product = await sync_to_async(Product.objects.select_for_update().get)(id=product_id)

    user = await get_user_from_db(callback_query.from_user.id)
    
    # Ensure user has a cart
    cart = await sync_to_async(Cart.objects.filter(user=user).first)() or await sync_to_async(Cart.objects.create)(user=user)
    
    # Get cart item if it exists
    cart_item, created = await sync_to_async(CartItem.objects.get_or_create)(cart=cart, product=product, defaults={'quantity': 0})
    quantity = cart_item.quantity if cart_item else 0

    if action == 'increase_product_quantity':
        if product.available_stock > 0:
            if product.reserved_stock <= product.stock:
                if not created:
                    cart_item.quantity += 1
                else:
                    cart_item.quantity = 1
                product.reserved_stock += 1 
                await sync_to_async(product.save)()
                await sync_to_async(cart_item.save)()
                await callback_query.answer(f"Mahsulot savatga qo'shildi.")   
            else:
                await callback_query.answer(f"Kechirasiz, {product.name} mahsulotidan faqat {product.available_stock} ta mavjud.")
        else:
            await callback_query.answer(f"Kechirasiz, {product.name} mahsuloti tugagan.")
    elif action == 'decrease_product_quantity':
        if cart_item:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                
                await sync_to_async(cart_item.save)()
                await callback_query.answer(f"Mahsulot kamaytirildi.")
            else:
                await sync_to_async(cart_item.delete)()
                cart_item = None
                await callback_query.answer("Mahsulot savatdan o'chirildi")
            product.reserved_stock -= 1 
            await sync_to_async(product.save)()
        else:
            await callback_query.answer("Mahsulot savatda yo'q.")
            return
    elif action == 'delete_product':
        if cart_item:
            product.reserved_stock -= quantity  
            await sync_to_async(product.save)()
            await sync_to_async(cart_item.delete)()
            cart_item = None
            await callback_query.answer("Mahsulot savatdan o'chirildi.")
        else:
            await callback_query.answer("Mahsulot savatda yo'q.")
    else:
        return await callback_query.answer("Noto'g'ri amal.")
    
    product_info = await format_product_info(product)
    new_markup = await product_keyboard(product_id, cart_item, user)
    
    try:
        new_markup = await product_keyboard(product_id, cart_item, user)
        if callback_query.message.reply_markup != new_markup:
            await callback_query.message.edit_caption(parse_mode='HTML', caption=product_info, reply_markup=new_markup)
            if action == 'increase_product_quantity':
                await callback_query.answer("Mahsulot savatga qo'shildi")
            elif action == 'decrease_product_quantity':
                await callback_query.answer("Mahsulot savatdan o'chirildi")
            elif action == 'delete_product':
                await callback_query.answer("Mahsulot savatdan olib tashlandi.")
        else:
            await callback_query.answer("Savat yangilandi, ammo hech narsa o'zgarmadi.")
    except TelegramBadRequest as e:
        await callback_query.answer("Savatda o'zgarish yo'q.")

# Saved Items start
@cart_router.message(StateFilter(CartFSM.waiting_viewing_saved_items))
async def show_saved_items_list(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user, name="Wishlist").first)()

    saved_items = await sync_to_async(list)(SavedItem.objects.filter(saved_item_list=saved_item_list))

    if not saved_items:
        await message.answer("Saqlanganlar ro'yxati bo'sh.")
        return

    list_text = "Saqlangan mahsulotlar:\n\n"

    for index, item in enumerate(saved_items, start=1):
        product = await sync_to_async(lambda: item.product)()
        list_text += (f"{index}. {await sync_to_async(lambda: product.car_model)()} — {product.name}: {product.price}so'm\n")

    await message.answer(list_text, reply_markup=(await saved_items_list_keyboard(saved_items)))

async def saved_items_list_keyboard(saved_items=None):
    if saved_items:
        buttons = [
            [
                InlineKeyboardButton(text=f"{await sync_to_async(lambda: item.product)()}", callback_data=f"noop"),
                InlineKeyboardButton(text="💔", callback_data=f"remove_saved_item_from_list:{await sync_to_async(lambda: item.product.id)()}"),
            ] for item in saved_items
        ] + [[InlineKeyboardButton(text="🗑️ Saqlanganlarni tozalash", callback_data="clear_saved_items_list:None")]]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    else:
        return None

@cart_router.callback_query(F.data.startswith('remove_saved_item_from_list:', 'clear_saved_items_list:'))
async def manage_saved_items_in_cart(callback_query: CallbackQuery):
    action, product_id = callback_query.data.split(':')
    user = await get_user_from_db(callback_query.from_user.id)

    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user, name="Wishlist").first)()
    if action =='remove_saved_item_from_list':
        product = await sync_to_async(Product.objects.get)(id=product_id)
        if saved_item_list:
            saved_item = await sync_to_async(SavedItem.objects.filter(saved_item_list=saved_item_list, product=product).first)()
            if saved_item:
                await sync_to_async(saved_item.delete)()
                success_message = "Mahsulot saqlanganlar ro'yxatidan olib tashlandi! 💔"
            else:
                success_message = "Mahsulot saqlanganlar ro'yxatida topilmadi."
                await callback_query.answer(success_message)
                return

            saved_items = await sync_to_async(list)(SavedItem.objects.filter(saved_item_list=saved_item_list))

            if not saved_items:
                await callback_query.message.edit_text("Saqlanganlar ro'yxati bo'sh.")
            updated_markup = await saved_items_list_keyboard(saved_items)
            try:
                await callback_query.message.edit_reply_markup(reply_markup=updated_markup)
            except TelegramBadRequest:
                await callback_query.answer(success_message)
        else:
            await callback_query.answer("Saqlanganlar ro'yxati bo'sh.")
    elif action == 'clear_saved_items_list':
        if saved_item_list:
            # QuerySet `.delete()` instead of converting to a list
            deleted_count, _ = await sync_to_async(SavedItem.objects.filter(saved_item_list=saved_item_list).delete)()

            if deleted_count > 0:
                await callback_query.answer("Saqlangan ro'yxati tozalandi")
                try:
                    await callback_query.message.edit_text("Saqlanganlar ro'yxati bo'sh.")
                    await callback_query.message.edit_reply_markup(reply_markup=None)
                except TelegramBadRequest:
                    await callback_query.answer("Saqlanganlar ro'yxati allaqachon bo'sh.")
            else:
                await callback_query.answer("Saqlanganlar ro'yxati allaqachon bo'sh.")
        else:
            await callback_query.answer("Saqlanganlar ro'yxati bo'sh.")

@cart_router.callback_query(F.data.startswith('save_item:', 'remove_saved_item:'))
async def manage_saved_item_in_product(callback_query: CallbackQuery):
    action = callback_query.data.split(':')[0]
    product_id = int(callback_query.data.split(':')[1])
    user = await get_user_from_db(callback_query.from_user.id)
    product = await sync_to_async(Product.objects.get)(id=product_id)

    if action == 'save_item':
        saved_item_list, created = await sync_to_async(SavedItemList.objects.get_or_create)(user=user, name="Wishlist")
        await sync_to_async(SavedItem.objects.create)(saved_item_list=saved_item_list, product=product)
        success_message = "Mahsulot saqlanganlar ro'yxatiga saqlandi! ❤️"
    elif action == 'remove_saved_item':
        saved_item = await sync_to_async(SavedItem.objects.filter(saved_item_list__user=user, product=product).first)()
        if saved_item:
            await sync_to_async(saved_item.delete)()
            success_message = "Mahsulot saqlanganlar ro'yxatidan olib tashlandi! 💔"
        else:
            await callback_query.answer("Saqlanganlar ro'yxatida o'zgarish yo'q.")
            return  # Exit early if item not found

    cart_item = await sync_to_async(CartItem.objects.filter(cart__user=user, product=product).first)()
    updated_markup = await product_keyboard(product_id, cart_item, user)

    try:
        await callback_query.message.edit_reply_markup(reply_markup=updated_markup)
    except TelegramBadRequest as e:
        # Error handling is already done for 'remove' action when item not found
        if action == 'save_item':
            await callback_query.answer("Saqlanganlar ro'yxatida o'zgarish yo'q.")
    else:
        await callback_query.answer(success_message)
# Saved Items end
