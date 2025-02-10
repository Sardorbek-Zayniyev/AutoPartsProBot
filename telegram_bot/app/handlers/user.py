from aiogram import Router, F
import os
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile
from aiogram.filters.state import StateFilter
from asgiref.sync import sync_to_async
from handlers.utils import get_user_from_db
from telegram_app.models import Category, CarBrand, CarModel, Product, Cart, CartItem, SavedItemList, SavedItem, Order, OrderItem, Discount
from django.utils import timezone
# Create a router for admin handlers
user_router = Router()


class SearchFSM(StatesGroup):
    waiting_all_products = State()
    waiting_get_part_name = State()
    waiting_part_name_search = State()
    waiting_get_car_brand = State()
    waiting_car_brand_search = State()
    waiting_get_car_model = State()
    waiting_car_model_search = State()


class CartFSM(StatesGroup):
    waiting_viewing_cart = State()
    waiting_viewing_saved_items = State()

class ProfileFSM(StatesGroup):
    waiting_viewing_profile = State()
    waiting_edit_full_name = State()
    waiting_new_full_name = State()
    waiting_edit_phone_number = State()
    waiting_new_phone_number = State()
    waiting_editing_address = State()
    waiting_choose_address_field = State()
    waiting_region_edit = State()
    waiting_city_edit = State()
    waiting_street_address_edit = State()

class CatalogFSM(StatesGroup):
    waiting_show_discounts = State()
    waiting_new_products_category = State()
    waiting_new_products = State()
    waiting_used_products = State()

class ProductFSM(StatesGroup):

    # category
    waiting_get_category = State()
    waiting_save_get_category = State()
    waiting_show_categories_for_edition = State()
    waiting_update_category = State()
    waiting_save_updated_category = State()
    waiting_show_categories_for_deletion = State()
    waiting_category_delete_confirm = State()
    waiting_delete_category = State()

    # product adding   
    waiting_show_category = State() 
    waiting_set_category = State()
    waiting_show_car_brand = State()
    waiting_set_car_brand = State()
    waiting_show_car_model = State()
    waiting_set_car_model = State()
    waiting_for_part_name = State()
    waiting_for_price = State()
    waiting_for_availability = State()
    waiting_for_stock = State()
    waiting_for_show_quality = State()
    waiting_for_set_quality = State()
    waiting_for_photo = State()
    waiting_for_description = State()

    # product editing
    waiting_show_product_for_edit = State()
    waiting_editing_product = State() 
    waiting_choose_product_field = State()
    waiting_product_category_edit = State()
    waiting_product_brand_edit = State()
    waiting_product_model_edit = State()
    waiting_product_partname_edit = State()
    waiting_product_price_edit = State()
    waiting_product_availability_edit = State()
    waiting_product_stock_edit = State()
    waiting_product_quality_edit = State()
    waiting_product_photo_edit = State()
    waiting_product_description_edit = State()

    # product deleting
    waiting_show_product_for_delete = State()
    waiting_product_delete_confirm = State()
    waiting_product_delete = State()


USER_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗂 Katalog"), KeyboardButton(text="🔎 Qidiruv")],
        [KeyboardButton(text="📜 Mening buyurtmalarim"),
         KeyboardButton(text="🛒 Savat")],
        [KeyboardButton(text="👤 Profil"),  KeyboardButton(text="❓ Yordam")],
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

CART_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👁️ Savatni ko'rish"), KeyboardButton(
            text="♥️ Saqlangan mahsulotlar")],
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

PROFILE_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Manzil"), KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

PROFILE_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Profil ma'lumotlari"), KeyboardButton(text="📍 Manzilni yangilash")],
        [KeyboardButton(text="📝 Ismni yangilash"), KeyboardButton(text="📱 Qo'shimcha raqam kiritish")],
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
    "👤 Profil": {
        "text": "Profil sozlamalari uchun tugmalar:",
        "keyboard": PROFILE_CONTROLS_KEYBOARD
    },
    "⬅ Bosh menu": {
        "text": "Asosiy menuga xush kelibsiz!",
        "keyboard": USER_MAIN_CONTROLS_KEYBOARD,
        "clear_state": True
    }
}


@user_router.message(F.text.in_(MAIN_CONTROLS_RESPONSES))
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
    quality_choices = {
        "new": "Yangi 🆕 ",
        "renewed": "Yangilangan 🔄 ",
        "excellent": "Zo'r 👍  ",
        "good": "Yaxshi ✨",
        "acceptable": "Qoniqarli 👌"
    }
    category_name = await sync_to_async(lambda: product.category.name)()
    brand_name = await sync_to_async(lambda: product.car_brand.name)()
    model_name = await sync_to_async(lambda: product.car_model.name)()

    price_info = await sync_to_async(product.original_and_discounted_price)()
    
    if price_info["discounted_price"]:
        price_text = (
            f"💰 <b>Asl narxi:</b> <s>{price_info['original_price']} so'm</s>\n"
            f"📉 <b>Chegirmali narx:</b> {price_info['discounted_price']} so'm 🔥"
        )
    else:
        price_text = f"💲 <b>Narxi:</b> {price_info['original_price']} so'm"

    return (
        f"🛠 <b>Mahsulot nomi:</b> {product.name}\n"
        f"📦 <b>Kategoriyasi:</b> {category_name}\n"
        f"🏷 <b>Brandi:</b> {brand_name}\n"
        f"🚘 <b>Modeli:</b> {model_name}\n"
        f"{price_text}\n"  
        f"📊 <b>Mavjudligi:</b> "
        f"{(
            'Sotuvda yo‘q' if not product.available else 
            f'Sotuvda qolmadi.' if product.available_stock == 0 else 
            f'Sotuvda <b>{product.available_stock}</b> ta qoldi' if product.available_stock < 20 else 
            f'Sotuvda <b>{product.available_stock}</b> ta bor'
        )}\n"
        f"🌟 <b>Holati:</b> {quality_choices[product.quality]}\n"
        f"📝 <b>Tavsifi:</b> {product.description or 'Yo‘q'}\n"
    )

# Control handlers
@user_router.message(F.text.in_(("📂 Kategoriya", "🔤 Ehtiyot qism nomi", "🚘 Mashina brendi", "🚗 Mashina modeli")))
async def search_controls_handler(message: Message, state: FSMContext):
    """
    Handle search control actions (category, part name, car brand, car model).
    """
    actions = {
        "📂 Kategoriya": (SearchFSM.waiting_all_products, show_all_products_category),
        "🔤 Ehtiyot qism nomi": (SearchFSM.waiting_part_name_search, get_part_name),
        "🚘 Mashina brendi": (SearchFSM.waiting_car_brand_search, get_car_brand),
        "🚗 Mashina modeli": (SearchFSM.waiting_car_model_search, get_car_model),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)

@user_router.message(F.text.in_(("👁️ Savatni ko'rish", "♥️ Saqlangan mahsulotlar")))
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

@user_router.message(F.text.in_(("👤 Profil ma'lumotlari", "📍 Manzilni yangilash", "📱 Qo'shimcha raqam kiritish", "📝 Ismni yangilash")))
async def profile_controls_handler(message: Message, state: FSMContext):
    actions = {
        "👤 Profil ma'lumotlari": (ProfileFSM.waiting_viewing_profile, show_profile),
        "📍 Manzilni yangilash": (ProfileFSM.waiting_editing_address, edit_address),
        "📱 Qo'shimcha raqam kiritish": (ProfileFSM.waiting_edit_phone_number, edit_phone),
        "📝 Ismni yangilash": (ProfileFSM.waiting_edit_full_name, edit_name),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)

@user_router.message(F.text.in_(("🔥 Aksiyalar", "🆕 Yangi", "🔄 B/U")))
async def catalog_controls_handler(message: Message, state: FSMContext):
    actions = {
        "🔥 Aksiyalar": (CatalogFSM.waiting_show_discounts, show_discounted_products_category),  
        "🆕 Yangi": (CatalogFSM.waiting_new_products, show_new_products_category), 
        "🔄 B/U": (CatalogFSM.waiting_used_products, show_used_products_category),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)

#Profile update part start
@user_router.message(StateFilter(ProfileFSM.waiting_viewing_profile))
async def show_profile(message: Message, state: FSMContext):
    """
    Displays the user's profile information.
    """
    user = await get_user_from_db(message.from_user.id)
    if user:
        profile_info = (
            f"<b>Ismingiz:</b> <b>{user.full_name}</b>\n"
            f"<b>Telefon raqamingiz:</b> <b>{user.phone_number}</b>\n"
            f"<b>Qo'shimcha telefon raqamingiz:</b> <b>{user.extra_phone_number or 'Yo\'q'}</b>\n"
            f"<b>Manzilingiz:</b>\n" 
            f"<b>1.Viloyat:</b> <b>{(user.region) or 'Yo\'q'}</b>\n"
            f"<b>2.Shahar:</b> <b>{(user.city) or 'Yo\'q'}</b>\n"
            f"<b>3.Ko'cha nomi va uy raqami:</b> <b>{(user.street_address) or 'Yo\'q'}</b>\n"
        )
        await message.answer(profile_info, parse_mode="HTML")
       
    else:
        await message.answer("Profil ma'lumotlari topilmadi.")
    await state.clear()

# Edit address
@user_router.message(ProfileFSM.waiting_editing_address)
async def edit_address(message: Message, state: FSMContext):
    address_keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Viloyat"), KeyboardButton(text="Shahar")],
        [KeyboardButton(text="Ko'cha"), KeyboardButton(text="👤 Profil")],
    ],
    resize_keyboard=True)
  
    await message.answer(f"Qaysi maydonini tahrirlamoqchisiz 👇:", reply_markup=address_keyboard)
    await state.set_state(ProfileFSM.waiting_choose_address_field)

@user_router.message(ProfileFSM.waiting_choose_address_field)
async def choose_address_field(message: Message, state: FSMContext):
    field_name = message.text.strip().capitalize()

    field_actions = {
        "Viloyat": (ProfileFSM.waiting_region_edit, "region"),
        "Shahar": (ProfileFSM.waiting_city_edit, "city"),
        "Ko'cha": (ProfileFSM.waiting_street_address_edit, "street_address"),
    }

    if field_name in field_actions:
        next_state, field = field_actions[field_name]
        await state.set_state(next_state)

        if field_name.lower() == "ko'cha":
            await message.answer(f"Yangi {field_name.lower()}ning nomini, uy va xonodon raqamini kiriting:")
        else:
            await message.answer(f"Yangi {field_name.lower()}ning nomini kiriting:")
    else:
        await message.answer("❌ Noto'g'ri maydon tanlandi. Iltimos, ro'yxatdan birini tanlang.")

@user_router.message(ProfileFSM.waiting_region_edit)
async def edit_region(message: Message, state: FSMContext):
    await update_user_address_field(message, state, "region", message.text.strip().capitalize())

@user_router.message(ProfileFSM.waiting_city_edit)  
async def edit_city(message: Message, state: FSMContext):
    await update_user_address_field(message, state, "city", message.text.strip().capitalize())

@user_router.message(ProfileFSM.waiting_street_address_edit)
async def edit_street(message: Message, state: FSMContext):
    await update_user_address_field(message, state, "street_address", message.text.strip().capitalize())

async def update_user_address_field(message: Message, state: FSMContext, field: str, new_value: str):
    user = await get_user_from_db(message.from_user.id)
    if user:
        setattr(user, field, new_value)
        await message.answer(f"Yangi '{new_value.capitalize()}' {field}i muvaffaqqiyatli saqlandi.")
        await sync_to_async(user.save)()
    else:
        await message.answer("User topilmadi.")
    await state.set_state(ProfileFSM.waiting_editing_address)
    await edit_address(message, state)
#Phone
@user_router.message(ProfileFSM.waiting_edit_phone_number)
async def edit_phone(message: Message, state: FSMContext):
    await message.answer("Qo'shimcha telefon raqamingizni kiriting:")
    await state.set_state(ProfileFSM.waiting_new_phone_number)

@user_router.message(ProfileFSM.waiting_new_phone_number)
async def update_phone_number(message: Message, state: FSMContext):
    new_phone_number = message.text.strip()
    try:
        # Ensure the input contains only digits
        if not new_phone_number.isdigit():
            raise ValueError("Faqat raqamlardan iborat telefon raqam kiriting.")

        # Ensure the phone number has at least 9 digits
        if len(new_phone_number) != 9 and len(new_phone_number) != 12:
            raise ValueError("Telefon raqam kamida 9 yoki 12 ta raqamdan iborat bo‘lishi kerak.\n1-na'muna. 998991234567\n2-na'muna 991234567")

        # If the phone number is 9 digits, prepend '998'
        if len(new_phone_number) == 9:
            new_phone_number = f"998{new_phone_number}"

        user = await get_user_from_db(message.from_user.id)
        if user:
            user.extra_phone_number = new_phone_number
            await sync_to_async(user.save)()
            await message.answer(f"Yangi telefon raqamingiz '{new_phone_number}' muvaffaqiyatli saqlandi.")
        else:
            await message.answer("User topilmadi.")

        await state.clear()

    except ValueError as e:
        await message.answer(str(e))
#Name
@user_router.message(ProfileFSM.waiting_edit_full_name)
async def edit_name(message: Message, state: FSMContext):
    await message.answer("Yangi ismingizni kiriting:")
    await state.set_state(ProfileFSM.waiting_new_full_name)

@user_router.message(ProfileFSM.waiting_new_full_name)
async def update_full_name(message: Message, state: FSMContext):
    new_full_name = message.text.strip()
    user = await get_user_from_db(message.from_user.id)
    if user:
        user.full_name = new_full_name
        await sync_to_async(user.save)()
        await message.answer(f"Yangi ismingiz '{new_full_name}' muvaffaqqiyatli saqlandi.")
    else:
        await message.answer("User topilmadi.")
    await state.clear()

#Profile update part end

async def get_categories_keyboard(callback_data_prefix: str, back_button_text: str) -> InlineKeyboardMarkup:
    """
    Generates a keyboard of categories with a back button.
    """
    categories = await sync_to_async(list)(Category.objects.all())
    category_buttons = []
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                row.append(InlineKeyboardButton(
                    text=categories[i + j].name, callback_data=f"{callback_data_prefix}:{categories[i + j].id}"))
        category_buttons.append(row)

    back_button = InlineKeyboardButton(
        text=back_button_text, callback_data="back_to_main")
    category_buttons.append([back_button])
    return InlineKeyboardMarkup(inline_keyboard=category_buttons)

async def send_category_keyboard(message: Message, prefix: str):
    keyboard = await get_categories_keyboard(callback_data_prefix=f"{prefix}_first_page", back_button_text="⬅ Bosh menu")
    await message.answer("Kategoriyalar:", reply_markup=keyboard)

async def fetch_products(category_id: int, quality: str = None):
    filter_params = {"category_id": category_id, "available": True}
    
    if quality:
        quality_list = quality.split(",")
        filter_params["quality__in"] = [q.strip() for q in quality_list]

    return await sync_to_async(list)(Product.objects.filter(**filter_params))

async def fetch_discounted_products():
    valid_discounts = await sync_to_async(
        lambda: list(
            Discount.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).prefetch_related('products')
        )
    )()

    discounted_products = []

    for discount in valid_discounts:
        products = await sync_to_async(lambda: list(discount.products.all()))()
        discounted_products.extend(products)

    return discounted_products

async def handle_product_page(callback_query: CallbackQuery, state: FSMContext, quality: str, callback_prefix: str):
    category_id = int(callback_query.data.split(':')[1])
    if callback_prefix == 'discounted_products':
        products = await fetch_discounted_products()
    else:
        products = await fetch_products(category_id, quality)

    if not products:
        await callback_query.message.answer("Mahsulotlar yo‘q.")
        return

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    current_page = 1

    await display_products_page(current_page, callback_query, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix)
    await callback_query.answer()

async def handle_other_pages(callback_query: CallbackQuery, state: FSMContext, quality: str, callback_prefix: str):
    _, category_id, page_num = callback_query.data.split(':')
    category_id = int(category_id)
    page_num = int(page_num)

    products = await fetch_products(category_id, quality)
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page

    await display_products_page(page_num, callback_query, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix)
    await callback_query.answer()

async def display_products_page(page_num, callback_query_or_message, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix):
    start_index = (page_num - 1) * products_per_page
    end_index = min(start_index + products_per_page, len(products_with_numbers))
    page_products = products_with_numbers[start_index:end_index]

    message_text = (
        f"🔍 Umumiy natija: {len(products_with_numbers)} ta mahsulot topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, product in page_products:
        car_model_name = await sync_to_async(lambda: product.car_model.name)()
        message_text += f"{number}. {car_model_name} — {product.name}\n"

    product_buttons = []
    row = []
    for number, product in page_products:
        row.append(InlineKeyboardButton(text=str(number), callback_data=f"product:{product.id}"))
        if len(row) == 5:
            product_buttons.append(row)
            row = []

    if row:
        product_buttons.append(row)

    pagination_buttons = []
    if page_num > 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="⬅️", callback_data=f"{callback_prefix}_other_pages:{category_id}:{page_num - 1}"))
    pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))
    if page_num < total_pages:
        pagination_buttons.append(InlineKeyboardButton(
            text="➡️", callback_data=f"{callback_prefix}_other_pages:{category_id}:{page_num + 1}"))

    product_keyboard = InlineKeyboardMarkup(inline_keyboard=product_buttons + [pagination_buttons])

    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=product_keyboard, parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text, reply_markup=product_keyboard, parse_mode="HTML"
        )

# search by all products
@user_router.message(StateFilter(SearchFSM.waiting_all_products))
async def show_all_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "all_products")

@user_router.callback_query(F.data.startswith('all_products_first_page:'))
async def show_all_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality=None, callback_prefix="all_products")

@user_router.callback_query(F.data.startswith('all_products_other_pages:'))
async def show_all_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_other_pages(callback_query, state, quality=None, callback_prefix="all_products")

# search by new products
@user_router.message(StateFilter(CatalogFSM.waiting_new_products))
async def show_new_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "new_products")

@user_router.callback_query(F.data.startswith('new_products_first_page:'))
async def show_new_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality="new", callback_prefix="new_products")

@user_router.callback_query(F.data.startswith('new_products_other_pages:'))
async def show_new_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_other_pages(callback_query, state, quality="new", callback_prefix="new_products")

# search by new used products
@user_router.message(StateFilter(CatalogFSM.waiting_used_products))
async def show_used_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "used_products")

@user_router.callback_query(F.data.startswith('used_products_first_page:'))
async def show_used_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    quality__in="renewed, excellent, good, acceptable"
    await handle_product_page(callback_query, state, quality=quality__in, callback_prefix="used_products")

@user_router.callback_query(F.data.startswith('used_products_other_pages:'))
async def show_used_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    quality__in="renewed, excellent, good, acceptable"
    await handle_other_pages(callback_query, state, quality=quality__in, callback_prefix="used_products")

#Discounted products
@user_router.message(StateFilter(CatalogFSM.waiting_show_discounts))
async def show_discounted_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "discounted_products")

@user_router.callback_query(F.data.startswith('discounted_products_first_page:'))
async def show_discounted_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality=None, callback_prefix="discounted_products")

@user_router.callback_query(F.data.startswith('discounted_products_other_pages:'))
async def show_discounted_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality=None, callback_prefix="discounted_products")

#
@user_router.callback_query(F.data.in_(("product:", "item:")))
async def show_single_product(callback_query: CallbackQuery, state: FSMContext):
    action = callback_query.data.split(':')[0]
    user = await get_user_from_db(callback_query.from_user.id)
    cart = await sync_to_async(Cart.objects.filter(user=user).first)()

    if action == 'item':
        item_id = int(callback_query.data.split(':')[1])
        item = await sync_to_async(CartItem.objects.filter(id=item_id, cart=cart).first)()
        product = await sync_to_async(item.get_product)()
        product_id = product.id
    else:
        product_id = int(callback_query.data.split(':')[1])
        product = await sync_to_async(Product.objects.get)(id=product_id)

    product_info = await format_product_info(product)

    cart_item = await sync_to_async(CartItem.objects.filter(cart=cart, product=product).first)()

    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(
                product.photo.path, filename=os.path.basename(product.photo.path))
            await callback_query.message.answer_photo(input_file,parse_mode='HTML' ,caption=product_info, reply_markup=(await product_keyboard(product_id, cart_item, user)))
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(f"Mahsulot rasmi mavjud emas.\n\n{product_info}")

    await callback_query.answer()

@user_router.callback_query(F.data == 'delete_message')
async def delete_message_handler(callback_query: CallbackQuery):
    await callback_query.message.delete()

# Search by part name
@user_router.message(StateFilter(SearchFSM.waiting_get_part_name))
async def get_part_name(message: Message, state: FSMContext):
    await message.answer("Mahsulotning, ehtiyot qism nomini kiriting:")
    await state.set_state(SearchFSM.waiting_part_name_search)

@user_router.message(StateFilter(SearchFSM.waiting_part_name_search))
async def part_name_search(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    products = await sync_to_async(list)(Product.objects.filter(name__icontains=part_name))
    await handle_search_results(message, products)

# Search by car brand
@user_router.message(StateFilter(SearchFSM.waiting_get_car_brand))
async def get_car_brand(message: Message, state: FSMContext):
    car_brands = await sync_to_async(list)(CarBrand.objects.all())
    await send_keyboard_options(message, car_brands, "Mashina brendlarini tanlang yoki kiriting:")
    await state.set_state(SearchFSM.waiting_car_brand_search)

@user_router.message(StateFilter(SearchFSM.waiting_car_brand_search))
async def car_brand_search(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()
    car_brand = await fetch_object(CarBrand, name__iexact=car_brand_name)
    if not car_brand:
        await message.answer(f"Kechirasiz, {car_brand_name} brendi topilmadi.")
        return
    products = await sync_to_async(list)(Product.objects.filter(car_brand=car_brand))
    await handle_search_results(message, products)

# Search by car model
@user_router.message(StateFilter(SearchFSM.waiting_get_car_model))
async def get_car_model(message: Message, state: FSMContext):
    car_models = await sync_to_async(list)(CarModel.objects.all())
    await send_keyboard_options(message, car_models, "Mashina modellerini tanlang yoki kiriting:")
    await state.set_state(SearchFSM.waiting_car_model_search)

@user_router.message(StateFilter(SearchFSM.waiting_car_model_search))
async def car_model_search(message: Message, state: FSMContext):
    car_model_name = message.text.strip().title()
    car_models = await sync_to_async(list)(CarModel.objects.filter(name__iexact=car_model_name))
    
    if not car_models:
        await message.answer(f"Kechirasiz, {car_model_name} modeli topilmadi.")
        return

    products = []
    for car_model in car_models:
        car_model_products = await sync_to_async(list)(Product.objects.filter(car_model=car_model))
        products.extend(car_model_products)

    await handle_search_results(message, products)

# Helper functions for searching
async def fetch_object(model, **filter_kwargs):
    try:
        return await sync_to_async(model.objects.get)(**filter_kwargs)
    except model.DoesNotExist:
        return None

async def send_keyboard_options(message: Message, items, prompt_text):
    buttons = []
    row = []
    for i, item in enumerate(items):
        row.append(KeyboardButton(text=item.name))
        if (i + 1) % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    back_button = KeyboardButton(text="⬅ Bosh menu")
    buttons.append([back_button])
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer(prompt_text, reply_markup=keyboard)

async def handle_search_results(message: Message, products):
    if not products:
        await message.answer("Mahsulot Topilmadi")
        return
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    total_pages = ((len(products_with_numbers) + 9) // 10)
    await display_products_page(1, message, products_with_numbers, None, total_pages, 10, "search")

# Cart list
@sync_to_async
def get_total_price(cart):
    return cart.total_price()

@sync_to_async
def get_quantity(cart_item):
    return cart_item.get_quantity()

# Main Cart
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

@user_router.callback_query(F.data_in(('increase_cart_item_quantity:', 'decrease_cart_item_quantity:', 'remove_item_from_cart')))
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

@user_router.callback_query(F.data == "clear_cart")
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
@user_router.callback_query(F.data == "view_cart")
async def view_cart_callback(callback_query: CallbackQuery, state: FSMContext):
    user = await get_user_from_db(callback_query.from_user.id)
    await update_cart_message(callback_query.message, user)

@user_router.callback_query(F.data.startswith(('increase_product_quantity:', 'decrease_product_quantity:', 'delete_product:')))
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

async def product_keyboard(product_id, cart_item=None, user=None):
    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user).first)()
    saved_item = await sync_to_async(SavedItem.objects.filter(saved_item_list=saved_item_list, product_id=product_id).first)() if saved_item_list else None

    cart_item_keyboard = []
    if not cart_item:
        cart_item_keyboard = [[InlineKeyboardButton(
            text="Savatga qo'shish", callback_data=f"increase_product_quantity:{product_id}")]]
    else:
        quantity = await get_quantity(cart_item)
        cart_item_keyboard.append(
            [InlineKeyboardButton(text=f"➖", callback_data=f"decrease_product_quantity:{product_id}"),
             InlineKeyboardButton(
                 text=f"🛒 {quantity} ta", callback_data="view_cart"),
             InlineKeyboardButton(
                text="➕", callback_data=f"increase_product_quantity:{product_id}")
             ])
        cart_item_keyboard.append([InlineKeyboardButton(
            text="🗑️ Savatni tozalash", callback_data=f"delete_product:{product_id}")])

    if saved_item:
        cart_item_keyboard.append([InlineKeyboardButton(
            text="💔", callback_data=f"remove_saved_item:{product_id}"), InlineKeyboardButton(text="❌", callback_data="delete_message")])
    else:
         cart_item_keyboard.append([InlineKeyboardButton(
                text="❤️", callback_data=f"save_item:{product_id}"), InlineKeyboardButton(text="❌", callback_data="delete_message")])
        
    return InlineKeyboardMarkup(inline_keyboard=cart_item_keyboard)

# Saved Items start
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
        ] + [[InlineKeyboardButton(text="🗑️ Saqlanganlarni tozalash", callback_data="clear_saved_items_list:None")]]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    else:
        return None

@user_router.callback_query(F.data.startswith('remove_saved_item_from_list:', 'clear_saved_items_list:'))
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

@user_router.callback_query(F.data.startswith('save_item:', 'remove_saved_item:'))
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


# Order functionlity
@user_router.callback_query(F.data.startswith('proceed_to_order:'))
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


