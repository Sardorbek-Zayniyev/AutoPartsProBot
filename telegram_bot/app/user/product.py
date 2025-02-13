from aiogram import Router, F
import os
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.types import FSInputFile
from aiogram.filters.state import StateFilter
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Category, CarBrand, CarModel, Product, Cart, CartItem, SavedItemList, SavedItem, Discount
from django.utils import timezone
from telegram_bot.app.user.main_controls import PRODUCT_SEARCH_CONTROLS_KEYBOARD

product_router = Router()



class ProductFSM(StatesGroup):
    waiting_all_products = State()
    waiting_get_part_name = State()
    waiting_part_name_search = State()
    waiting_get_car_brand = State()
    waiting_car_brand_search = State()
    waiting_get_car_model = State()
    waiting_car_model_search = State()




async def product_keyboard(product_id, cart_item=None, user=None):
    saved_item_list = await sync_to_async(SavedItemList.objects.filter(user=user).first)()
    saved_item = await sync_to_async(SavedItem.objects.filter(saved_item_list=saved_item_list, product_id=product_id).first)() if saved_item_list else None

    cart_item_keyboard = []
    if not cart_item:
        cart_item_keyboard = [[InlineKeyboardButton(
            text="Savatga qo'shish", callback_data=f"increase_product_quantity:{product_id}")]]
    else:
        from telegram_bot.app.user.cart import get_quantity
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

@product_router.message(F.text.in_(("📂 Kategoriya", "🔤 Ehtiyot qism nomi", "🚘 Mashina brendi", "🚗 Mashina modeli")))
async def product_search_controls_handler(message: Message, state: FSMContext):
    """
    Handle search control actions (category, part name, car brand, car model).
    """
    actions = {
        "📂 Kategoriya": (ProductFSM.waiting_all_products, show_all_products_category),
        "🔤 Ehtiyot qism nomi": (ProductFSM.waiting_part_name_search, get_part_name),
        "🚘 Mashina brendi": (ProductFSM.waiting_car_brand_search, get_car_brand),
        "🚗 Mashina modeli": (ProductFSM.waiting_car_model_search, get_car_model),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)







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

async def fetch_object(model, **filter_kwargs):
    try:
        return await sync_to_async(model.objects.get)(**filter_kwargs)
    except model.DoesNotExist:
        return None

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

async def handle_search_results(message: Message, products, state):
    if not products:
        await message.answer("Mahsulot Topilmadi")
        return
    await state.update_data(search_results=products)
    
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    total_pages = ((len(products_with_numbers) + 9) // 10)
    await display_products_page(1, message, products_with_numbers, None, total_pages, 10, "search_product", state)

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

    await display_products_page(current_page, callback_query, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix, state)
    await callback_query.answer()

async def handle_product_other_pages(callback_query: CallbackQuery, state: FSMContext, quality: str, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    if callback_prefix == "search_product":
        if len(data_parts) != 2:
            await callback_query.answer("Invalid callback data format.")
            return
        
        page_num = int(data_parts[1])
        state_data = await state.get_data()
        products = state_data.get("search_results", [])
        category_id = None  
    else:
        if len(data_parts) != 3:
            await callback_query.answer("Invalid callback data format.")
            return
        
        _, category_id, page_num = data_parts
        category_id = int(category_id)
        page_num = int(page_num)
        products = await fetch_products(category_id, quality)
    
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    
    await display_products_page(page_num, callback_query, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix, state)
    await callback_query.answer()

async def display_products_page(page_num, callback_query_or_message, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix, state):
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

    if total_pages > 1:
        if page_num > 1:
            if callback_prefix == "search_product":
                pagination_buttons.append(InlineKeyboardButton(
                    text="⬅️", callback_data=f"{callback_prefix}_other_pages:{page_num - 1}"))
            else:
                pagination_buttons.append(InlineKeyboardButton(
                    text="⬅️", callback_data=f"{callback_prefix}_other_pages:{category_id}:{page_num - 1}"))

        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))

        if page_num < total_pages:
            if callback_prefix == "search_product":
                pagination_buttons.append(InlineKeyboardButton(
                    text="➡️", callback_data=f"{callback_prefix}_other_pages:{page_num + 1}"))
            else:
                pagination_buttons.append(InlineKeyboardButton(
                    text="➡️", callback_data=f"{callback_prefix}_other_pages:{category_id}:{page_num + 1}"))
    else:
        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))
  
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
@product_router.message(StateFilter(ProductFSM.waiting_all_products))
async def show_all_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "all_products")

@product_router.callback_query(F.data.startswith('all_products_first_page:'))
async def show_all_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality=None, callback_prefix="all_products")

@product_router.callback_query(F.data.startswith('all_products_other_pages:'))
async def show_all_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_other_pages(callback_query, state, quality=None, callback_prefix="all_products")

@product_router.callback_query(F.data.startswith('search_product_other_pages:'))
async def show_all_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_other_pages(callback_query, state, quality=None, callback_prefix="search_product")

@product_router.callback_query(F.data.startswith(("product:", "item:")))
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


# Search by part name
@product_router.message(StateFilter(ProductFSM.waiting_get_part_name))
async def get_part_name(message: Message, state: FSMContext):
    await message.answer("Mahsulotning, ehtiyot qism nomini kiriting:")
    await state.set_state(ProductFSM.waiting_part_name_search)

@product_router.message(StateFilter(ProductFSM.waiting_part_name_search))
async def part_name_search(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    products = await sync_to_async(list)(Product.objects.filter(name__icontains=part_name))
    await handle_search_results(message, products, state)

# Search by car brand
@product_router.message(StateFilter(ProductFSM.waiting_get_car_brand))
async def get_car_brand(message: Message, state: FSMContext):
    car_brands = await sync_to_async(list)(CarBrand.objects.all())
    await send_keyboard_options(message, car_brands, "Mashina brendlarini tanlang yoki kiriting:")
    await state.set_state(ProductFSM.waiting_car_brand_search)

@product_router.message(StateFilter(ProductFSM.waiting_car_brand_search))
async def car_brand_search(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()
    car_brand = await fetch_object(CarBrand, name__icontains=car_brand_name)
    if not car_brand:
        await message.answer(f"Kechirasiz, {car_brand_name} brendi topilmadi.")
        return
    products = await sync_to_async(list)(Product.objects.filter(car_brand=car_brand))
    await handle_search_results(message, products, state)

# Search by car model
@product_router.message(StateFilter(ProductFSM.waiting_get_car_model))
async def get_car_model(message: Message, state: FSMContext):
    car_models = await sync_to_async(list)(CarModel.objects.all())
    await send_keyboard_options(message, car_models, "Mashina modellerini tanlang yoki kiriting:")
    await state.set_state(ProductFSM.waiting_car_model_search)

@product_router.message(StateFilter(ProductFSM.waiting_car_model_search))
async def car_model_search(message: Message, state: FSMContext):
    car_model_name = message.text.strip().title()
    car_models = await sync_to_async(list)(CarModel.objects.filter(name__icontains=car_model_name))
    
    if not car_models:
        await message.answer(f"Kechirasiz, {car_model_name} modeli topilmadi.")
        return

    products = []
    for car_model in car_models:
        car_model_products = await sync_to_async(list)(Product.objects.filter(car_model=car_model))
        products.extend(car_model_products)

    await handle_search_results(message, products, state)

