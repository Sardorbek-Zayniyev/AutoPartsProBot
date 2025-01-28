from aiogram import Router
import os
from django.core.files import File
from django.conf import settings
from django.db.models import Q
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message

from django.db import IntegrityError
from aiogram.types import FSInputFile
from aiogram.filters.state import StateFilter
from asgiref.sync import sync_to_async
from handlers.utils import get_user_from_db
from telegram_app.models import Category, CarBrand, CarModel, Product, Cart, CartItem

# Create a router for admin handlers
user_router = Router()
cart_router = Router()

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
    waiting_removing_from_cart = State()


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
    one_time_keyboard=True

)

SEARCH_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya"), KeyboardButton(text="🔤 Ehtiyot qism nomi")], 
        [KeyboardButton(text="🚘 Mashina brendi"), KeyboardButton(text="🚗 Mashina modeli")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
ORDERS_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏳ Joriy buyurtmalar"), KeyboardButton(text="📜 Buyurtma tarixi")],
        [KeyboardButton(text="🚫 Buyurtmani bekor qilish")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

CART_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👁️ Savatni ko'rish"), KeyboardButton(text="🗑️ Savatni tozalash")],
        # [KeyboardButton(text="✅ Buyurtma berish")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
# [KeyboardButton(text="👁️ Savatni ko'rish")] ichiga kirgandan kn mahsulotni olib tashlash

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
#Utils
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
        f"Mavjudligi: {'Sotuvda bor' if product.available else 'Sotuvda yo\'q'}\n"
        f"Tavsifi: {product.description or 'Yo\'q'}\n"
    )
##
#Control handlers
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



#search by category
@user_router.message(StateFilter(SearchFSM.waiting_category_search))
async def category_search(message: Message, state: FSMContext):
    categories = await sync_to_async(list)(Category.objects.all())  
    category_buttons = []
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                row.append(InlineKeyboardButton(text=categories[i+j].name, callback_data=f"category:{categories[i+j].id}"))
        category_buttons.append(row)
    
    back_button = InlineKeyboardButton(text="⬅ Bosh menu", callback_data="back_to_main")
    category_buttons.append([back_button])
    
    category_keyboard = InlineKeyboardMarkup(inline_keyboard=category_buttons)
    await message.answer("Kategoriyalar:", reply_markup=category_keyboard)

@user_router.callback_query(lambda c: c.data.startswith('category:'))
async def process_category_callback(callback_query: CallbackQuery, state: FSMContext):
    category_id = int(callback_query.data.split(':')[1])
    products = await sync_to_async(list)(Product.objects.filter(category_id=category_id))  # No need to order by ID here
    
    if not products:
        await callback_query.message.answer("Ushbu kategoriyada mahsulotlar yo'q.")
        return

    # Add sequential numbering to products
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]  # Create sequential numbers

    # Calculate total pages
    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
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
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page

    # Display specified page
    await display_page(page_num, callback_query, products_with_numbers, category_id, total_pages, products_per_page)
    await callback_query.answer()

@user_router.callback_query(lambda c: c.data.startswith('category:'))
async def process_category_callback(callback_query: CallbackQuery, state: FSMContext):
    category_id = int(callback_query.data.split(':')[1])
    products = await sync_to_async(list)(Product.objects.filter(category_id=category_id)[:10])
    
    if not products:
        await callback_query.message.answer("Ushbu kategoriyada mahsulotlar yo'q.")
        return

    product_buttons = []
    for i, product in enumerate(products):
      product_buttons.append([InlineKeyboardButton(text=str(i+1), callback_data=f"product:{product.id}")])
    
    product_keyboard = InlineKeyboardMarkup(inline_keyboard=product_buttons)
    await callback_query.message.answer("Mahsulotlar ro'yxati:", reply_markup=product_keyboard)
    await callback_query.answer()

@user_router.callback_query(lambda c: c.data.startswith('product:'))
async def process_product_callback(callback_query: CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split(':')[1])
    product = await sync_to_async(Product.objects.get)(id=product_id)
    product_info = await format_product_info(product)

    user = await get_user_from_db(callback_query.from_user.id)
    cart, created = await sync_to_async(Cart.objects.get_or_create)(user=user)
    cart_item, item_created = await sync_to_async(CartItem.objects.get_or_create)(cart=cart, product=product)

    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(product.photo.path, filename=os.path.basename(product.photo.path))
            await callback_query.message.answer_photo(input_file, caption=product_info)
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(f"Mahsulot rasmi mavjud emas.\n\n{product_info}")

    await callback_query.answer()

async def display_page(page_num, callback_query_or_message, products_with_numbers, category_id, total_pages, products_per_page):
    start_index = (page_num - 1) * products_per_page
    end_index = min(start_index + products_per_page, len(products_with_numbers))
    page_products = products_with_numbers[start_index:end_index]
    
    # message_text = f"<b>{callback_query.message.text.split('(')[0]} (Sahifa {page_num}/{total_pages})</b>\n\n"  # Updated line
    message_text = (
        f"🔍 Umumiy natija: {len(products_with_numbers)} ta mahsulot topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{min(start_index + products_per_page, len(products_with_numbers))}:\n\n"
    )

    for number, product in page_products:
        car_model_name = await sync_to_async(lambda: product.car_model.name)() 
        message_text += f"{number}.  {car_model_name} — {product.name}\n"

    # Create product grid layout (2 rows with 5 items each)
    product_buttons = []
    row = []
    for number, product in page_products:
        row.append(InlineKeyboardButton(text=str(number), callback_data=f"product:{product.id}"))
        if len(row) == 5:  # Add a row after every 5 buttons
            product_buttons.append(row)
            row = []

    if row:  # Add any remaining buttons as the last row
        product_buttons.append(row)
    # Add pagination buttons (⬅️, ❌, ➡️) in a separate row
    pagination_buttons = []
    if page_num > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"category_page:{category_id}:{page_num - 1}"))
    pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))
    if page_num < total_pages:
        pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"category_page:{category_id}:{page_num + 1}"))

    product_keyboard = InlineKeyboardMarkup(inline_keyboard=product_buttons + [pagination_buttons])

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

@user_router.callback_query(lambda c: c.data.startswith("category_delete:"))
async def delete_category_message(callback_query: CallbackQuery, state: FSMContext):
  await callback_query.message.delete()
  await callback_query.answer()

#search by part_name
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

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    current_page = 1

    await display_page(current_page, message, products_with_numbers, None, total_pages, products_per_page)

#search by car_brand
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
    
    brand_keyboard = ReplyKeyboardMarkup(keyboard=brand_buttons, resize_keyboard=True)
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

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    current_page = 1

    await display_page(current_page, message, products_with_numbers, None, total_pages, products_per_page)

#search by car_model
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
    
    brand_keyboard = ReplyKeyboardMarkup(keyboard=brand_buttons, resize_keyboard=True)
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

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    current_page = 1

    await display_page(current_page, message, products_with_numbers, None, total_pages, products_per_page)


