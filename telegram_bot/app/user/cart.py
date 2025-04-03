import os
import asyncio
from aiogram import Router, F
from datetime import timedelta
from django.utils import timezone
from aiogram.types import FSInputFile
from asgiref.sync import sync_to_async
from django.db.models import F as F_model
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from telegram_bot.app.utils import get_user_from_db, IsUserFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from telegram_bot.app.user.product import user_format_product_info, user_product_keyboard
from telegram_app.models import Product, Cart, CartItem, SavedItemList, SavedItem, Promocode, RewardHistory
from telegram_bot.app.user.utils import user_invalid_command_message, user_keyboard_back_to_main_menu, user_keyboard_back_to_cart

user_cart_router = Router()


class UserCartFSM(StatesGroup):
    user_waiting_get_cart = State()
    user_waiting_get_saved_items = State()
    user_waiting_add_rewards_to_cart = State()
    user_waiting_add_promocode_to_cart = State()

# Utils


async def user_get_total_price(cart):
    return await sync_to_async(cart.total_price)()

async def user_get_quantity(cart_item):
    return await sync_to_async(cart_item.get_quantity)()

async def user_update_cart_message(message: Message, user):
    REWARD_TYPES = {
        "free_shipping": "🚚 Bepul yetkazib berish",
        "gift": "🎁 Sovg'a",
        "promocode": "🎟 Promokod",
    }

    cart = await sync_to_async(Cart.objects.filter(user=user, is_active=True)
                               .prefetch_related('promocodes', 'rewards', 'items__product')
                               .first)()

    if not cart or not cart.items.exists():
        try:
            await message.edit_text("Savatingiz bo'sh.")
        except TelegramBadRequest:
            await message.answer("Savatingiz bo'sh.")
        return

    cart_text = "<b> Sizning savatingiz:</b>\n\n"
    total_price = await sync_to_async(cart.total_price)()
    discounted_price = await sync_to_async(cart.discounted_price)()

    cart_items = await sync_to_async(list)(
        cart.items.select_related("product").values("id", "quantity", "product__name", "product__price")
    )

    for index, item in enumerate(cart_items, start=1):
        subtotal = item["product__price"] * item["quantity"]
        cart_text += (
            f"<b>{index}</b>. <b>{item['product__name']}:</b> "
            f"{item['product__price']} x {item['quantity']} = {subtotal} <b>so'm</b>\n"
        )

    promocodes = await sync_to_async(list)(cart.promocodes.all())
    if promocodes:
        promo_texts = [f"{i}. 🎟 {promo.code} ({promo.discount_percentage}% chegirma)" for i, promo in enumerate(promocodes, start=1)]
        cart_text += f"\n\n<b>Qo‘shilgan promokodlar:</b>\n" + "\n".join(promo_texts)

    rewards = await sync_to_async(list)(cart.rewards.all())
    if rewards:
        reward_texts = [f"{i}. 🎁 {reward.name}  ({REWARD_TYPES[reward.reward_type]})" for i, reward in enumerate(rewards, start=1)]
        cart_text += f"\n\n<b>Qo‘shilgan sovg‘alar:</b>\n" + "\n".join(reward_texts)

    cart_text += f"\n\n<b>Jami:</b> <b>{f'<del>{total_price}</del>' if promocodes else total_price} so'm</b>"
    if promocodes:
        cart_text += f"\n<b>Chegirma bilan:</b> {discounted_price} <b>so'm</b>"

    keyboard = await user_cart_keyboard(cart)

    try:
        await message.edit_text(cart_text, parse_mode="HTML", reply_markup=keyboard)
    except TelegramBadRequest:
        await message.answer(cart_text, parse_mode="HTML", reply_markup=keyboard)

async def user_cart_keyboard(cart):
    cart_items = await sync_to_async(list)(CartItem.objects.filter(cart=cart).values('id', 'quantity', 'product__name'))
    if not cart_items:
        return None

    builder = InlineKeyboardBuilder()
    for index, item in enumerate(cart_items, start=1):
        product_name = item['product__name']
        builder.row(
            InlineKeyboardButton(
                text=f"{index}. {product_name}", callback_data=f"user_item:{item['id']}:cart_item"),
            InlineKeyboardButton(
                text="➖", callback_data=f"user_decrease_cart_item_quantity:{item['id']}"),
            InlineKeyboardButton(
                text=f"🛒 {item['quantity']}", callback_data="user_noop"),
            InlineKeyboardButton(
                text="➕", callback_data=f"user_increase_cart_item_quantity:{item['id']}"),
            InlineKeyboardButton(
                text="❌", callback_data=f"user_remove_cart_item_from_cart:{item['id']}"),
        )
    builder.row(InlineKeyboardButton(text="🗑️ Savatni tozalash", callback_data="user_clear_cart"), InlineKeyboardButton(
        text="🎟 Promokod qo'shish", callback_data=f"user_add_promocode_or_reward_to_cart"))
    builder.row(InlineKeyboardButton(text="✅ Buyurtmaga o'tish",
                callback_data=f"user_proceed_to_order:{cart.id}"))
    builder.row(InlineKeyboardButton(
        text="❌", callback_data="user_delete_message"))
    return builder.as_markup()

async def user_saved_items_list_keyboard(saved_items=None):
    if not saved_items:
        return None

    builder = InlineKeyboardBuilder()
    for index, item in enumerate(saved_items, start=1):
        product_name = item['product__name']
        builder.row(
            InlineKeyboardButton(
                text=f"{index}. {product_name}", callback_data=f"user_item:{item['id']}:saved_item"),
            InlineKeyboardButton(
                text="💔", callback_data=f"user_remove_saved_item_from_list:{item['id']}"),
        )

    builder.row(InlineKeyboardButton(text="🗑️ Saqlanganlarni tozalash",
                callback_data="user_clear_saved_items_list:None"))
    builder.attach(InlineKeyboardBuilder.from_markup(
        user_keyboard_back_to_main_menu()))

    return builder.as_markup()

# Cart part start


@user_cart_router.message(UserCartFSM.user_waiting_get_cart)
async def user_get_cart(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    if not user:
        await message.reply("Iltimos, avval ro'yxatdan o'ting.")
        await state.clear()
        return
    cart = await sync_to_async(Cart.objects.filter(user=user, is_active=True).order_by('-created_at').first)()
    if not cart:
        cart = await sync_to_async(Cart.objects.create)(user=user, is_active=True)

    cart_items = await sync_to_async(list)(CartItem.objects.filter(cart=cart).values('id'))
    if not cart_items:
        await message.answer("Savatingiz bo'sh.")
        return
    await user_update_cart_message(message, user)


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith(('user_increase_cart_item_quantity:', 'user_decrease_cart_item_quantity:', 'user_remove_cart_item_from_cart:')))
async def user_manage_cart_item_quantity(callback_query: CallbackQuery):
    action, item_id = callback_query.data.split(':')
    item_id = int(item_id)

    user = await get_user_from_db(callback_query.from_user.id)
    cart, _ = await sync_to_async(Cart.objects.get_or_create)(user=user, is_active=True)

    cart_item = await sync_to_async(CartItem.objects.select_related(
        'product',
        'product__category',
        'product__car_brand',
        'product__car_model',
        'product__owner',
        'product__updated_by'
    ).filter(id=item_id, cart=cart).first)()
    if not cart_item:
        await callback_query.answer("Mahsulot savatda topilmadi.")
        return

    product = await sync_to_async(lambda: cart_item.product)()
    quantity = cart_item.quantity

    if action == 'user_increase_cart_item_quantity':
        if product.available_stock > 0 and product.reserved_stock < product.stock:
            cart_item.quantity += 1
            product.reserved_stock += 1
            cart.reserved_until = timezone.now() + timedelta(minutes=15)
            cart.warning_sent = False
            await sync_to_async(product.save)()
            await sync_to_async(cart_item.save)()
            await sync_to_async(cart.save)()
            await callback_query.answer(f"Mahsulot savatga qo'shildi.")
        else:
            await callback_query.answer(f"Kechirasiz, {product.name} mahsuloti tugadi.")
    elif action == 'user_decrease_cart_item_quantity':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            product.reserved_stock -= 1
            product.reserved_stock = max(0, product.reserved_stock)
            await sync_to_async(cart_item.save)()
            await sync_to_async(product.save)()
            await sync_to_async(cart.save)()
            await callback_query.answer(f"Mahsulot kamaytirildi.")
        else:
            product.reserved_stock -= 1
            product.reserved_stock = max(0, product.reserved_stock)
            await sync_to_async(cart_item.delete)()
            cart_item = None
            await sync_to_async(product.save)()
            await sync_to_async(cart.save)()
            await callback_query.answer("Mahsulot savatdan o'chirildi")
    elif action == 'user_remove_cart_item_from_cart':
        product.reserved_stock -= quantity
        product.reserved_stock = max(0, product.reserved_stock)
        await sync_to_async(cart_item.delete)()
        cart_item = None
        cart.reserved_until = timezone.now() + timedelta(minutes=15)
        cart.warning_sent = False
        await sync_to_async(product.save)()
        await sync_to_async(cart.save)()
        await callback_query.answer("Mahsulot savatdan o'chirildi.")
    else:
        return await callback_query.answer("Noto'g'ri amal.")

    await user_update_cart_message(callback_query.message, user)


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith('user_extend_cart_time:'))
async def user_extend_cart_time(callback_query: CallbackQuery):
    _, cart_id = callback_query.data.split(':')
    cart_id = int(cart_id)

    cart = await sync_to_async(Cart.objects.get)(id=cart_id)
    cart.reserved_until = timezone.now() + timedelta(minutes=15)
    cart.warning_sent = False
    await sync_to_async(cart.save)()
    await callback_query.message.edit_text("Savatingizning vaqti 15 daqiqaga uzaytirildi!")
    await asyncio.sleep(3)
    try:
        await callback_query.message.bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id
        )
    except Exception as e:
        print(f"Xabarni o‘chirishda xatolik: {e}")
    await callback_query.answer()


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith("user_item:"))
async def user_get_single_product(callback_query: CallbackQuery, state: FSMContext):
    item_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()
    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user).first)()

    if action == "cart_item":
        item = await sync_to_async(CartItem.objects.select_related('product__car_brand', 'product__car_model', 'product__category', 'product__owner', 'product__updated_by').filter(id=item_id, cart=cart).first)()
    elif action == "saved_item":
        item = await sync_to_async(SavedItem.objects.select_related('product__car_brand', 'product__car_model', 'product__category', 'product__owner', 'product__updated_by').filter(id=item_id, saved_item_list=saved_item_list).first)()

    product = await sync_to_async(lambda: item.product)()
    product_id = product.id

    product_info = await user_format_product_info(product)

    cart_item = await sync_to_async(CartItem.objects.filter(cart=cart, product=product).first)()

    keyboard = await user_product_keyboard(product_id, cart_item, user)

    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(
                product.photo.path, filename=os.path.basename(product.photo.path))
            await callback_query.message.answer_photo(input_file, parse_mode='HTML', caption=product_info, reply_markup=keyboard)
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(f"Mahsulot rasmi mavjud emas.\n\n{product_info}", parse_mode='HTML', reply_markup=keyboard)

    await callback_query.answer()


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith("user_clear_cart"))
async def user_clear_cart(callback_query: CallbackQuery):
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.select_related('user').filter(user=user).first)()
    if cart:
        await sync_to_async(cart.items.all().delete)()
        await callback_query.answer("Savat tozalandi")

        try:
            await callback_query.message.edit_text("Savatingiz bo'sh.")
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest as e:
            await callback_query.answer("Savat allaqachon bo'sh.")

# Add reward or promocode to cart
@user_cart_router.callback_query(IsUserFilter(), F.data.startswith('user_add_promocode_or_reward_to_cart'))
async def user_select_reward_or_promocode(callback_query: CallbackQuery, state: FSMContext):
    user = await get_user_from_db(callback_query.from_user.id)

    has_rewards = await sync_to_async(lambda: RewardHistory.objects.filter(user=user, is_successful=True, is_used=False).exists())()
    builder = InlineKeyboardBuilder()
    if has_rewards:
        builder.button(text=f"🎁 Mening sovg'alarim ichidan", callback_data=f"user_add_my_rewards_to_my_cart")
    builder.button(text=f"🎫 Boshqa promokod", callback_data=f"user_add_promocode_to_my_cart")
    keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + user_keyboard_back_to_cart().inline_keyboard)
    try:
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    except:
        await callback_query.message.answer(reply_markup=keyboard)
    await callback_query.answer()

# Add promocode to cart
@user_cart_router.callback_query(IsUserFilter(), F.data.startswith("user_add_promocode_to_my_cart"))
async def user_request_promocode(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(UserCartFSM.user_waiting_add_promocode_to_cart)
    await callback_query.message.answer("🎫 Promokodni kiriting:")
    await callback_query.answer()

@user_cart_router.message(UserCartFSM.user_waiting_add_promocode_to_cart)
async def user_add_promocode_to_cart(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    promocode_text = message.text.strip().upper()

    if not promocode_text:
        await message.answer("⚠️ Promokod bo‘sh bo‘lishi mumkin emas. Qayta kiriting:")
        return

    promocode = await sync_to_async(lambda: Promocode.objects.filter(
        code=promocode_text, is_active=True, valid_from__lte=timezone.now(), valid_until__gte=timezone.now()
    ).first())()

    if not promocode:
        await message.answer("❌ Bunday promokod topilmadi yoki muddati o‘tgan!", reply_markup=user_keyboard_back_to_cart())
        return

    try:
        cart = await sync_to_async(Cart.objects.filter(user=user, is_active=True).order_by('-created_at').first)()
        if not cart:
            cart = await sync_to_async(Cart.objects.create)(user=user, is_active=True)
   
        if promocode.used_count < promocode.usage_limit:
            await sync_to_async(cart.promocodes.add)(promocode)

            promocode.used_count += 1  
            if promocode.used_count >= promocode.usage_limit:
                promocode.is_active = False 

            await sync_to_async(promocode.save)()  

        else:
            await message.answer("❌ Bu promokod ishlatilgan yoki muddati tugagan!", reply_markup=user_keyboard_back_to_cart())
            return
        await sync_to_async(cart.promocodes.add)(promocode)
        sent_message = await message.answer(f"✅ Promokod {promocode.code} ({promocode.discount_percentage}% chegirma) savatga qo‘shildi!")
        await user_update_cart_message(message, user)

        await asyncio.sleep(3)  
        try:
            await sent_message.delete()
        except:
            pass
    
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")

    await state.clear()

# Add reward to cart
@user_cart_router.callback_query(IsUserFilter(), F.data.startswith('user_add_my_rewards_to_my_cart'))
async def user_add_my_rewards_to_my_cart(callback_query: CallbackQuery, state: FSMContext):
    from telegram_bot.app.user.reward import user_handle_reward_search_results
    await state.set_state(UserCartFSM.user_waiting_add_rewards_to_cart)
    user = await get_user_from_db(callback_query.from_user.id)
    rewards = await sync_to_async(list)(RewardHistory.objects.filter(user=user, is_used=False, is_successful=True).order_by('is_used').values(reward_fk=F_model('reward__id'), name=F_model('reward__name',), reward_type=F_model('reward__reward_type')))
    await callback_query.answer()
    await user_handle_reward_search_results(callback_query, rewards, state)

@user_cart_router.callback_query(IsUserFilter(), F.data.startswith("user_add_single_reward_to_cart:"))
async def user_add_single_reward_to_cart(callback_query: CallbackQuery, state: FSMContext):
    """
    Foydalanuvchi tanlagan sovg‘asini savatga qo‘shish.
    """
    reward_id = int(callback_query.data.split(":")[1])

    user = await get_user_from_db(callback_query.from_user.id)
    if not user:
        await callback_query.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    reward_history = await sync_to_async(lambda: RewardHistory.objects.filter(
        user=user, reward_id=reward_id, is_successful=True, is_used=False
    ).select_related('reward__promocode').first())()

    if not reward_history:
        await callback_query.answer("Sizda bunday sovg‘a mavjud emas yoki allaqachon ishlatilgan!", show_alert=True)
        return

    reward = reward_history.reward

    try:
        cart = await sync_to_async(Cart.objects.filter(user=user, is_active=True).order_by('-created_at').first)()
        if not cart:
            cart = await sync_to_async(Cart.objects.create)(user=user, is_active=True)

        if reward.reward_type == "promocode" and reward.promocode:
            promocode = reward.promocode

            if promocode.used_count < promocode.usage_limit:
                await sync_to_async(cart.promocodes.add)(promocode)

                promocode.used_count += 1  
                if promocode.used_count >= promocode.usage_limit:
                    promocode.is_active = False 

                await sync_to_async(promocode.save)() 
            else:
                await callback_query.answer("❌ Bu promokod ishlatilgan yoki muddati tugagan!", show_alert=True)
                return

        else:
            await sync_to_async(cart.rewards.add)(reward)

        reward_history.is_used = True
        await sync_to_async(reward_history.save)()

        await callback_query.answer("🎁 Sovg‘a savatga qo‘shildi!", show_alert=True)
        await user_update_cart_message(callback_query.message, user)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")

# Manage cart_items through product keyboard


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith("user_get_cart_through_product"))
async def user_get_cart_through_product(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user = await get_user_from_db(callback_query.from_user.id)
    await user_update_cart_message(callback_query.message, user)


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith(('user_increase_product_quantity:', 'user_decrease_product_quantity:', 'user_remove_product:')))
async def user_manage_product_quantity(callback_query: CallbackQuery):
    action, product_id = callback_query.data.split(':')
    product_id = int(product_id)

    product = await sync_to_async(lambda: Product.objects.select_related("category", "car_brand", "car_model", "owner", "updated_by").filter(id=product_id).first())()
    user = await get_user_from_db(callback_query.from_user.id)

    cart = await sync_to_async(Cart.objects.filter(user=user, is_active=True).first)() or await sync_to_async(Cart.objects.create)(user=user)

    cart_item, created = await sync_to_async(CartItem.objects.get_or_create)(cart=cart, product=product, defaults={'quantity': 0})
    quantity = cart_item.quantity if cart_item else 0

    if action == 'user_increase_product_quantity':
        if product.available_stock > 0:
            if product.reserved_stock <= product.stock:
                if not created:
                    cart_item.quantity += 1
                else:
                    cart_item.quantity = 1
                product.reserved_stock += 1
                cart.reserved_until = timezone.now() + timedelta(minutes=15)
                cart.warning_sent = False
                await sync_to_async(product.save)()
                await sync_to_async(cart_item.save)()
                await sync_to_async(cart.save)()
                await callback_query.answer(f"Mahsulot savatga qo'shildi.")
            else:
                await callback_query.answer(f"Kechirasiz, {product.name} mahsulotidan faqat {product.available_stock} ta mavjud.")
        else:
            await callback_query.answer(f"Kechirasiz, {product.name} mahsuloti tugagan.")
    elif action == 'user_decrease_product_quantity':
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
            product.reserved_stock = max(0, product.reserved_stock)
            cart.reserved_until = timezone.now() + timedelta(minutes=15)
            cart.warning_sent = False
            await sync_to_async(product.save)()
            await sync_to_async(cart.save)()
        else:
            await callback_query.answer("Mahsulot savatda yo'q.")
            return
    elif action == 'user_remove_product':
        if cart_item:
            product.reserved_stock -= quantity
            product.reserved_stock = max(0, product.reserved_stock)
            await sync_to_async(cart_item.delete)()
            cart_item = None
            cart.reserved_until = timezone.now() + timedelta(minutes=15)
            cart.warning_sent = False
            await sync_to_async(product.save)()
            await sync_to_async(cart.save)()
            await callback_query.answer("Mahsulot savatdan o'chirildi.")
        else:
            await callback_query.answer("Mahsulot savatda yo'q.")
    else:
        return await callback_query.answer("Noto'g'ri amal.")

    product_info = await user_format_product_info(product)
    new_markup = await user_product_keyboard(product_id, cart_item, user)

    try:
        new_markup = await user_product_keyboard(product_id, cart_item, user)
        if callback_query.message.reply_markup != new_markup:
            await callback_query.message.edit_caption(parse_mode='HTML', caption=product_info, reply_markup=new_markup)
            if action == 'user_increase_product_quantity':
                await callback_query.answer("Mahsulot savatga qo'shildi")
            elif action == 'user_decrease_product_quantity':
                await callback_query.answer("Mahsulot savatdan o'chirildi")
            elif action == 'user_remove_product':
                await callback_query.answer("Mahsulot savatdan olib tashlandi.")
        else:
            await callback_query.answer("Savat yangilandi, ammo hech narsa o'zgarmadi.")
    except TelegramBadRequest as e:
        await callback_query.answer("Savatda o'zgarish yo'q.")

# Saved Items part start


@user_cart_router.message(UserCartFSM.user_waiting_get_saved_items)
async def user_get_saved_items_list(message: Message, state: FSMContext):
    if message.text == "♥️ Saqlangan mahsulotlar":
        user = await get_user_from_db(message.from_user.id)

        saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user, name="Wishlist").first)()
        saved_items = await sync_to_async(list)(
            SavedItem.objects.select_related('product__car_model')
            .filter(saved_item_list=saved_item_list)
            .values('id', 'product__name', 'product__price', 'product__car_model__name')
        )

        if not saved_items:
            await message.answer("Saqlanganlar ro'yxati bo'sh.")
            return

        list_text = "Saqlangan mahsulotlar:\n\n"

        for index, item in enumerate(saved_items, start=1):
            list_text += (
                f"{index}. {item['product__car_model__name']} — "
                f"{item['product__name']}: {item['product__price']}so'm\n"
            )

        await message.answer(list_text, reply_markup=(await user_saved_items_list_keyboard(saved_items)))

    else:
        await message.reply(text=user_invalid_command_message, reply_markup=user_keyboard_back_to_main_menu())


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith(('user_save_item:', 'user_remove_saved_item:')))
async def user_manage_saved_item_in_product_keyboard(callback_query: CallbackQuery):
    action = callback_query.data.split(':')[0]
    product_id = int(callback_query.data.split(':')[1])
    user = await get_user_from_db(callback_query.from_user.id)
    product = await sync_to_async(Product.objects.get)(id=product_id)

    if action == 'user_save_item':
        saved_item_list, created = await sync_to_async(SavedItemList.objects.get_or_create)(user=user, name="Wishlist")
        await sync_to_async(SavedItem.objects.create)(saved_item_list=saved_item_list, product=product)
        success_message = "Mahsulot saqlanganlar ro'yxatiga saqlandi! ❤️"
    elif action == 'user_remove_saved_item':
        saved_item = await sync_to_async(SavedItem.objects.filter(saved_item_list__user=user, product=product).first)()
        if saved_item:
            await sync_to_async(saved_item.delete)()
            success_message = "Mahsulot saqlanganlar ro'yxatidan olib tashlandi! 💔"
        else:
            await callback_query.answer("Saqlanganlar ro'yxatida o'zgarish yo'q.")
            return

    cart_item = await sync_to_async(CartItem.objects.filter(cart__user=user, product=product).first)()
    updated_markup = await user_product_keyboard(product_id, cart_item, user)

    try:
        await callback_query.message.edit_reply_markup(reply_markup=updated_markup)
    except TelegramBadRequest as e:
        if action == 'user_save_item':
            await callback_query.answer("Saqlanganlar ro'yxatida o'zgarish yo'q.")
    else:
        await callback_query.answer(success_message)


@user_cart_router.callback_query(IsUserFilter(), F.data.startswith(('user_remove_saved_item_from_list:', 'user_clear_saved_items_list:')))
async def user_manage_saved_items_in_cart_keyboard(callback_query: CallbackQuery):
    action, item_id = callback_query.data.split(':')
    user = await get_user_from_db(callback_query.from_user.id)

    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user, name="Wishlist").first)()

    if action == 'user_remove_saved_item_from_list':
        if saved_item_list:
            saved_item = await sync_to_async(SavedItem.objects.filter(id=item_id, saved_item_list=saved_item_list).first)()

            if saved_item:
                await sync_to_async(saved_item.delete)()
                success_message = "Mahsulot saqlanganlar ro'yxatidan olib tashlandi! 💔"
            else:
                success_message = "Mahsulot saqlanganlar ro'yxatida topilmadi."
                await callback_query.answer(success_message)
                return

            saved_items = await sync_to_async(list)(
                SavedItem.objects.filter(saved_item_list=saved_item_list)
                .values('id', 'product__name')
            )
            if not saved_items:
                await callback_query.message.edit_text("Saqlanganlar ro'yxati bo'sh.")
            updated_markup = await user_saved_items_list_keyboard(saved_items)
            try:
                await callback_query.message.edit_reply_markup(reply_markup=updated_markup)
            except TelegramBadRequest:
                await callback_query.answer(success_message)
        else:
            await callback_query.answer("Saqlanganlar ro'yxati bo'sh.")
    elif action == 'user_clear_saved_items_list':
        if saved_item_list:
            deleted_count, _ = await sync_to_async(SavedItem.objects.filter(saved_item_list=saved_item_list).delete)()

            if deleted_count > 0:
                await callback_query.answer("Saqlangan ro'yxati tozalandi")
                try:
                    await callback_query.message.edit_text("Saqlanganlar ro'yxati bo'sh.")
                except TelegramBadRequest:
                    await callback_query.answer("Saqlanganlar ro'yxati allaqachon bo'sh.")
            else:
                await callback_query.answer("Saqlanganlar ro'yxati allaqachon bo'sh.")
        else:
            await callback_query.answer("Saqlanganlar ro'yxati bo'sh.")
