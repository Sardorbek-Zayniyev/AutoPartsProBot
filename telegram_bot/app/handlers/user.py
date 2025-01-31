from aiogram import Router
import os
from django.core.files import File
from django.conf import settings
from django.db.models import Q
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from django.db import IntegrityError
from aiogram.types import FSInputFile
from aiogram.filters.state import StateFilter
from asgiref.sync import sync_to_async
from handlers.utils import get_user_from_db
from telegram_app.models import Category, CarBrand, CarModel, Product, Cart, CartItem, SavedItemList, SavedItem

# Create a router for admin handlers
user_router = Router()


class SearchFSM(StatesGroup):
    waiting_category_search = State()
    waiting_get_part_name = State()
    waiting_part_name_search = State()
    waiting_get_car_brand = State()
    waiting_car_brand_search = State()
    waiting_get_car_model = State()
    waiting_car_model_search = State()


class CartFSM(StatesGroup):
    waiting_viewing_cart = State()
    waiting_viewing_saved_items = State()


USER_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗂 Katalog"), KeyboardButton(text="🔎 Qidiruv")],
        [KeyboardButton(text="📜 Mening buyurtmalarim"),
         KeyboardButton(text="🛒 Savat")],
        [KeyboardButton(text="❓ Yordam")],
    ],
    resize_keyboard=True,
)

CATALOG_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Aksiyalar")],
        [KeyboardButton(text="🆕 Yangi"), KeyboardButton(text="🔄 B/U")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,

)

SEARCH_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya"), KeyboardButton(
            text="🔤 Ehtiyot qism nomi")],
        [KeyboardButton(text="🚘 Mashina brendi"),
         KeyboardButton(text="🚗 Mashina modeli")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)
ORDERS_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏳ Joriy buyurtmalar"),
         KeyboardButton(text="📜 Buyurtma tarixi")],
        [KeyboardButton(text="🚫 Buyurtmani bekor qilish")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

CART_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👁️ Savatni ko'rish"), KeyboardButton(
            text="♥️ Saqlangan mahsulotlar")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

# Main control handlers
MAIN_CONTROLS_RESPONSES = {
    "🗂 Katalog": {
        "text": "Katalog boshqaruvi uchun tugmalar:",
        "keyboard": CATALOG_CONTROLS_KEYBOARD,
    },
    "🔎 Qidiruv": {
        "text": "Mahsulot qidiruvi uchun tugmalar:",
        "keyboard": SEARCH_CONTROLS_KEYBOARD
    },
    "📜 Mening buyurtmalarim": {
        "text": "Buyurtmalar boshqaruvi uchun tugmalar:",
        "keyboard": ORDERS_CONTROLS_KEYBOARD
    },
    "🛒 Savat": {
        "text": "Savat boshqaruvi uchun tugmalar:",
        "keyboard": CART_CONTROLS_KEYBOARD
    },
    "⬅ Bosh menu": {
        "text": "Asosiy menuga xush kelibsiz!",
        "keyboard": USER_MAIN_CONTROLS_KEYBOARD,
        "clear_state": True
    }
}


@user_router.message(lambda message: message.text in MAIN_CONTROLS_RESPONSES)
async def main_controls_handler(message: Message, state: FSMContext):
    response = MAIN_CONTROLS_RESPONSES[message.text]
    await message.answer(response["text"], reply_markup=response["keyboard"])
    if response.get("clear_state"):
        await state.clear()
# Utils


async def format_product_info(product):
    """
    Format product details for display.
    """
    category_name = await sync_to_async(lambda: product.category.name)()
    brand_name = await sync_to_async(lambda: product.car_brand.name)()
    model_name = await sync_to_async(lambda: product.car_model.name)()

    return (
        f"Mahsulot nomi: {product.name}\n"
        f"Kategoriyasi: {category_name}\n"
        f"Brandi: {brand_name}\n"
        f"Modeli: {model_name}\n"
        f"Narxi: {product.price} so'm\n"
        f"Mavjudligi: {
            'Sotuvda bor' if product.available else 'Sotuvda yo\'q'}\n"
        f"Tavsifi: {product.description or 'Yo\'q'}\n"
    )

# Control handlers


@user_router.message(lambda message: message.text in ["📂 Kategoriya", "🔤 Ehtiyot qism nomi", "🚘 Mashina brendi", "🚗 Mashina modeli"])
async def search_controls_handler(message: Message, state: FSMContext):
    """
    Handle search control actions (category, part name, car brand, car model).
    """
    actions = {
        "📂 Kategoriya": (SearchFSM.waiting_category_search, category_search),
        "🔤 Ehtiyot qism nomi": (SearchFSM.waiting_part_name_search, get_part_name),
        "🚘 Mashina brendi": (SearchFSM.waiting_car_brand_search, get_car_brand),
        "🚗 Mashina modeli": (SearchFSM.waiting_car_model_search, get_car_model),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)


@user_router.message(lambda message: message.text in ["👁️ Savatni ko'rish", "♥️ Saqlangan mahsulotlar"])
async def cart_controls_handler(message: Message, state: FSMContext):
    """
    Handle cart control actions (view cart, clear cart)
    """
    user_id = message.from_user.id  # Get the user's Telegram ID
    cart = await sync_to_async(Cart.objects.filter)(user_id=user_id)

    actions = {
        "👁️ Savatni ko'rish": (CartFSM.waiting_viewing_cart, show_cart),
        "♥️ Saqlangan mahsulotlar": (CartFSM.waiting_viewing_saved_items, show_saved_items_list),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)


# search by category
@user_router.message(StateFilter(SearchFSM.waiting_category_search))
async def category_search(message: Message, state: FSMContext):
    categories = await sync_to_async(list)(Category.objects.all())
    category_buttons = []
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                row.append(InlineKeyboardButton(
                    text=categories[i+j].name, callback_data=f"category:{categories[i+j].id}"))
        category_buttons.append(row)

    back_button = InlineKeyboardButton(
        text="⬅ Bosh menu", callback_data="back_to_main")
    category_buttons.append([back_button])

    category_keyboard = InlineKeyboardMarkup(inline_keyboard=category_buttons)
    await message.answer("Kategoriyalar:", reply_markup=category_keyboard)


@user_router.callback_query(lambda c: c.data.startswith('category:'))
async def process_category_callback(callback_query: CallbackQuery, state: FSMContext):
    category_id = int(callback_query.data.split(':')[1])
    products = await sync_to_async(list)(Product.objects.filter(category_id=category_id))

    if not products:
        await callback_query.message.answer("Ushbu kategoriyada mahsulotlar yo'q.")
        return

    # Add sequential numbering to products
    products_with_numbers = [(index + 1, product) for index,
                             # Create sequential numbers
                             product in enumerate(products)]

    # Calculate total pages
    products_per_page = 10
    total_pages = (len(products_with_numbers) +
                   products_per_page - 1) // products_per_page
    current_page = 1

    await display_page(current_page, callback_query, products_with_numbers, category_id, total_pages, products_per_page)
    await callback_query.answer()


@user_router.callback_query(lambda c: c.data.startswith('category_page:'))
async def process_category_page_callback(callback_query: CallbackQuery, state: FSMContext):
    _, category_id, page_num = callback_query.data.split(':')
    category_id = int(category_id)
    page_num = int(page_num)

    # Fetch products and add sequential numbering
    products = await sync_to_async(list)(Product.objects.filter(category_id=category_id))
    products_with_numbers = [(index + 1, product)
                             for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) +
                   products_per_page - 1) // products_per_page

    # Display specified page
    await display_page(page_num, callback_query, products_with_numbers, category_id, total_pages, products_per_page)
    await callback_query.answer()


@user_router.callback_query(lambda c: c.data.startswith('product:'))
async def process_product_callback(callback_query: CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split(':')[1])
    product = await sync_to_async(Product.objects.get)(id=product_id)
    product_info = await format_product_info(product)

    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()
    cart_item = await sync_to_async(CartItem.objects.filter(cart=cart, product=product).first)()

    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(
                product.photo.path, filename=os.path.basename(product.photo.path))
            await callback_query.message.answer_photo(input_file, caption=product_info, reply_markup=(await product_keyboard(product_id, cart_item, user)))
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(f"Mahsulot rasmi mavjud emas.\n\n{product_info}")

    await callback_query.answer()


# search by part_name


@user_router.message(StateFilter(SearchFSM.waiting_get_part_name))
async def get_part_name(message: Message, state: FSMContext):
    await message.answer("Mahsulotning, ehtiyot qism nomini kiriting:")
    await state.set_state(SearchFSM.waiting_part_name_search)


@user_router.message(StateFilter(SearchFSM.waiting_part_name_search))
async def part_name_search(message: Message, state: FSMContext):
    part_name = message.text.strip().title()

    products = await sync_to_async(list)(Product.objects.filter(name__icontains=part_name))

    if not products:
        await message.answer("Topilmadi")
        return

    products_with_numbers = [(index + 1, product)
                             for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) +
                   products_per_page - 1) // products_per_page
    current_page = 1

    await display_page(current_page, message, products_with_numbers, None, total_pages, products_per_page)

# search by car_brand


@user_router.message(StateFilter(SearchFSM.waiting_get_car_brand))
async def get_car_brand(message: Message, state: FSMContext):
    car_brands = await sync_to_async(list)(CarBrand.objects.all())

    brand_buttons = []
    row = []
    for i, brand in enumerate(car_brands):
        row.append(KeyboardButton(text=brand.name))
        if (i + 1) % 2 == 0:
            brand_buttons.append(row)
            row = []
    if row:
        brand_buttons.append(row)

    brand_keyboard = ReplyKeyboardMarkup(
        keyboard=brand_buttons, resize_keyboard=True)
    await message.answer("Mashina brendlarini tanlang yoki kiriting:", reply_markup=brand_keyboard)
    await state.set_state(SearchFSM.waiting_car_brand_search)


@user_router.message(StateFilter(SearchFSM.waiting_car_brand_search))
async def car_brand_search(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()
    try:
        car_brand = await sync_to_async(CarBrand.objects.get)(name__iexact=car_brand_name)
    except CarBrand.DoesNotExist:
        await message.answer(f"Kechirasiz, {car_brand_name} brendi topilmadi.")
        return

    products = await sync_to_async(list)(Product.objects.filter(car_brand=car_brand))

    if not products:
        await message.answer(f"{car_brand.name} brendi uchun mahsulotlar topilmadi.")
        return

    products_with_numbers = [(index + 1, product)
                             for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) +
                   products_per_page - 1) // products_per_page
    current_page = 1

    await display_page(current_page, message, products_with_numbers, None, total_pages, products_per_page)

# search by car_model


@user_router.message(StateFilter(SearchFSM.waiting_get_car_model))
async def get_car_model(message: Message, state: FSMContext):
    car_models = await sync_to_async(list)(CarModel.objects.all())

    brand_buttons = []
    row = []
    for i, brand in enumerate(car_models):
        row.append(KeyboardButton(text=brand.name))
        if (i + 1) % 2 == 0:
            brand_buttons.append(row)
            row = []
    if row:
        brand_buttons.append(row)

    brand_keyboard = ReplyKeyboardMarkup(
        keyboard=brand_buttons, resize_keyboard=True)
    await message.answer("Mashina modellerini tanlang yoki kiriting:", reply_markup=brand_keyboard)
    await state.set_state(SearchFSM.waiting_car_model_search)


@user_router.message(StateFilter(SearchFSM.waiting_car_model_search))
async def car_model_search(message: Message, state: FSMContext):
    car_model_name = message.text.strip().title()
    try:
        car_model = await sync_to_async(CarModel.objects.get)(name__iexact=car_model_name)
    except CarModel.DoesNotExist:
        await message.answer(f"Kechirasiz, {car_model_name} modeli topilmadi.")
        return

    products = await sync_to_async(list)(Product.objects.filter(car_model=car_model))

    if not products:
        await message.answer(f"{car_model.name} modeli uchun mahsulotlar topilmadi.")
        return

    products_with_numbers = [(index + 1, product)
                             for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) +
                   products_per_page - 1) // products_per_page
    current_page = 1

    await display_page(current_page, message, products_with_numbers, None, total_pages, products_per_page)


async def display_page(page_num, callback_query_or_message, products_with_numbers, category_id, total_pages, products_per_page):
    start_index = (page_num - 1) * products_per_page
    end_index = min(start_index + products_per_page,
                    len(products_with_numbers))
    page_products = products_with_numbers[start_index:end_index]

    # message_text = f"<b>{callback_query.message.text.split('(')[0]} (Sahifa {page_num}/{total_pages})</b>\n\n"  # Updated line
    message_text = (
        f"🔍 Umumiy natija: {len(products_with_numbers)
                            } ta mahsulot topildi.\n\n"
        f"Sahifa natijasi: {
            start_index + 1}-{min(start_index + products_per_page, len(products_with_numbers))}:\n\n"
    )

    for number, product in page_products:
        car_model_name = await sync_to_async(lambda: product.car_model.name)()
        message_text += f"{number}.  {car_model_name} — {product.name}\n"

    # Create product grid layout (2 rows with 5 items each)
    product_buttons = []
    row = []
    for number, product in page_products:
        row.append(InlineKeyboardButton(text=str(number),
                   callback_data=f"product:{product.id}"))
        if len(row) == 5:  # Add a row after every 5 buttons
            product_buttons.append(row)
            row = []

    if row:  # Add any remaining buttons as the last row
        product_buttons.append(row)
    # Add pagination buttons (⬅️, ❌, ➡️) in a separate row
    pagination_buttons = []
    if page_num > 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="⬅️", callback_data=f"category_page:{category_id}:{page_num - 1}"))
    pagination_buttons.append(InlineKeyboardButton(
        text="❌", callback_data="delete_message"))
    if page_num < total_pages:
        pagination_buttons.append(InlineKeyboardButton(
            text="➡️", callback_data=f"category_page:{category_id}:{page_num + 1}"))

    product_keyboard = InlineKeyboardMarkup(
        inline_keyboard=product_buttons + [pagination_buttons])

    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text,
            reply_markup=product_keyboard,
            parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text,
            reply_markup=product_keyboard,
            parse_mode="HTML"
        )


# Cart list
@sync_to_async
def get_total_price(cart):
    return cart.total_price()


@sync_to_async
def get_quantity(cart_item):
    return cart_item.get_quantity()


@user_router.message(StateFilter(CartFSM.waiting_viewing_cart))
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

    cart_text = "Sizning savatingiz:\n\n"
    total_price = 0

    for index, item in enumerate(cart_items, start=1):
        product = await sync_to_async(lambda: item.product)()
        subtotal = item.subtotal()
        total_price += subtotal
        cart_text += (f"{index}. {product.name}: {product.price} x {
                      item.quantity} = {subtotal} so'm\n")

    cart_text += f"\nJami: {total_price} so'm"

    try:
        await message.edit_text(cart_text, reply_markup=(await cart_keyboard(cart)))
    except TelegramBadRequest:
        await message.answer(cart_text, reply_markup=(await cart_keyboard(cart)))


@user_router.callback_query(lambda c: c.data.startswith('increase_cart_item_quantity:') or c.data.startswith('decrease_cart_item_quantity:') or c.data.startswith('remove_item_from_cart:'))
async def update_cart_item_quantity(callback_query: CallbackQuery):
    action = callback_query.data.split(':')[0]
    item_id = int(callback_query.data.split(':')[1])
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()
    item = await sync_to_async(CartItem.objects.filter(id=item_id, cart=cart).first)()

    if not item:
        await callback_query.answer("Mahsulot mavjud emas")
        return

    if action == 'increase_cart_item_quantity':
        item.quantity += 1
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
    elif action == 'remove_item_from_cart':
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
                    text=f"🛒 {item.quantity}", callback_data="noop"),
                InlineKeyboardButton(
                    text=f"➕", callback_data=f"increase_cart_item_quantity:{item.id}"),
                InlineKeyboardButton(
                    text="❌", callback_data=f"remove_item_from_cart:{item.id}"),
            ] for item in cart_items
        ] + [[InlineKeyboardButton(text="🗑️ Savatni tozalash", callback_data="clear_cart")]]
        return InlineKeyboardMarkup(inline_keyboard=cart_keyboards)
    else:
        return None


@user_router.callback_query(lambda c: c.data == "clear_cart")
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


# Cart for each products


@user_router.callback_query(lambda c: c.data.startswith('increase_product_quantity:') or c.data.startswith('decrease_product_quantity:'))
async def update_product_quantity(callback_query: CallbackQuery):
    action = callback_query.data.split(':')[0]
    product_id = int(callback_query.data.split(':')[1])
    product = await sync_to_async(Product.objects.get)(id=product_id)
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()

    if not cart:
        cart = await sync_to_async(Cart.objects.create)(user=user)

    cart_item, created = await sync_to_async(CartItem.objects.get_or_create)(cart=cart, product=product, defaults={'quantity': 1})

    if action == 'increase_product_quantity':
        if not created:
            cart_item.quantity += 1
            await sync_to_async(cart_item.save)()
        await callback_query.answer(f"Mahsulot savatga qo'shildi")
    elif action == 'decrease_product_quantity':
        if cart_item:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                await sync_to_async(cart_item.save)()
                await callback_query.answer("Mahsulot kamaytirildi")
            else:
                await sync_to_async(cart_item.delete)()
                cart_item = None
                await callback_query.answer("Mahsulot savatdan o'chirildi")
        else:
            await callback_query.answer("Mahsulot savatda yo'q.")
            return

    try:
        new_markup = await product_keyboard(product_id, cart_item, user)
        if callback_query.message.reply_markup != new_markup:
            await callback_query.message.edit_reply_markup(reply_markup=new_markup)
            if action == 'increase_item':
                await callback_query.answer("Mahsulot savatga qo'shildi")
            elif action == 'decrease_item':
                await callback_query.answer("Mahsulot savatdan o'chirildi")
        else:
            await callback_query.answer("Savat yangilandi, ammo hech narsa o'zgarmadi.")

    except TelegramBadRequest as e:
        await callback_query.answer("Savatda o'zgarish yo'q.")


async def product_keyboard(product_id, cart_item=None, user=None):
    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user).first)()
    saved_item = None

    if saved_item_list:
        saved_item = await sync_to_async(SavedItem.objects.filter(saved_item_list=saved_item_list, product_id=product_id).first)()

    cart_item_keyboard = []
    if not cart_item:
        cart_item_keyboard = [[InlineKeyboardButton(
            text="Savatga qo'shish", callback_data=f"increase_product_quantity:{product_id}")]]
        if not saved_item:
            cart_item_keyboard.append([InlineKeyboardButton(
                text="❤️", callback_data=f"save_item:{product_id}")])
        else:
            cart_item_keyboard.append([InlineKeyboardButton(
                text="💔", callback_data=f"remove_saved_item:{product_id}")])
    else:
        quantity = await get_quantity(cart_item)
        cart_item_keyboard.append(
            [InlineKeyboardButton(text=f"➖", callback_data=f"decrease_product_quantity:{product_id}"),
             InlineKeyboardButton(
                 text=f"🛒 {quantity} ta", callback_data="noop"),
             InlineKeyboardButton(
                text="➕", callback_data=f"increase_product_quantity:{product_id}")
             ])
        cart_item_keyboard.append([InlineKeyboardButton(
            text="🗑️ Savatni tozalash", callback_data=f"delete_product:{product_id}")])
        if not saved_item:
            cart_item_keyboard.append([InlineKeyboardButton(
                text="❤️", callback_data=f"save_item:{product_id}")])
        else:
            cart_item_keyboard.append([InlineKeyboardButton(
                text="💔", callback_data=f"remove_saved_item:{product_id}")])
    return InlineKeyboardMarkup(inline_keyboard=cart_item_keyboard)


@user_router.callback_query(lambda c: c.data.startswith("delete_product"))
async def clear_product_item_from_cart(callback_query: CallbackQuery):
    product_id = int(callback_query.data.split(':')[1])
    product = await sync_to_async(Product.objects.get)(id=product_id)
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()
    cart_item = await sync_to_async(CartItem.objects.filter(cart=cart, product=product).first)()

    if not user:
        await callback_query.answer("Iltimos, avval ro'yxatdan o'ting.")
        return

    if cart_item:
        await sync_to_async(cart_item.delete)()
        cart_item = None
        await callback_query.answer("Mahsulot savatdan o'chirildi")
    try:
        # Try to edit the message's reply markup
        new_markup = await product_keyboard(product_id, cart_item, user)
        if callback_query.message.reply_markup != new_markup:
            await callback_query.message.edit_reply_markup(reply_markup=new_markup)
            await callback_query.answer("Mahsulot savatdan o'chirildi")
        else:
            # If the reply markup is the same, still answer the callback
            await callback_query.answer("Savat yangilandi, ammo hech narsa o'zgarmadi.")
    except TelegramBadRequest as e:
        # Catch the exception if the message is not modified
        await callback_query.answer("Savatda o'zgarish yo'q.")


# Saved Items

@user_router.message(StateFilter(CartFSM.waiting_viewing_saved_items))
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
        ] + [[InlineKeyboardButton(text="🗑️ Saqlanganlarni tozalash", callback_data="clear_saved_items_list")]]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    else:
        return None


@user_router.callback_query(lambda c: c.data.startswith('remove_saved_item_from_list:'))
async def remove_saved_item_from_list(callback_query: CallbackQuery):
    product_id = int(callback_query.data.split(':')[1])
    user = await get_user_from_db(callback_query.from_user.id)
    product = await sync_to_async(Product.objects.get)(id=product_id)

    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user, name="Wishlist").first)()

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


@user_router.callback_query(lambda c: c.data == "clear_saved_items_list")
async def clear_saved_items_list_handler(callback_query: CallbackQuery, state: FSMContext):
    user = await get_user_from_db(callback_query.from_user.id)
    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user, name="Wishlist").first)()

    if saved_item_list:
        # Use QuerySet `.delete()` instead of converting to a list
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

# Saved Item in product management


@user_router.callback_query(lambda c: c.data.startswith('save_item:') or c.data.startswith('remove_saved_item:'))
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
