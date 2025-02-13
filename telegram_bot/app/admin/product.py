from aiogram import Router, F
import os, asyncio
from django.core.files import File
from django.conf import settings
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message,  FSInputFile, InputMediaPhoto
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Category, CarBrand, CarModel, Product
from telegram_bot.app.admin.utils import skip_inline_button, single_item_buttons, confirmation_keyboard, ACTIVITY_KEYBOARD, CONFIRM_KEYBOARD
from telegram_bot.app.admin.category import get_categories_keyboard, show_category_list
from telegram_bot.app.admin.main_controls import PRODUCT_CONTROLS_KEYBOARD

product_router = Router()

quality_choices = {
        "Yangi 🆕": "new",
        "Yangilangan 🔄": "renewed",
        "Zo'r 👍": "excellent",
        "Yaxshi ✨": "good",
        "Qoniqarli 👌": "acceptable"
    }

class ProductFSM(StatesGroup):

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
    
    # product editing by fields
    waiting_edit_products = State()
    waiting_edit_products_by_category = State()
    waiting_edit_products_by_brand_name = State()
    waiting_edit_products_by_model_name = State()
    waiting_edit_products_by_part_name = State()

    # product searching by fields
    waiting_get_all_products = State ()
    waiting_get_part_name = State()
    waiting_part_name_search = State()
    waiting_get_car_brand = State()
    waiting_car_brand_search = State()
    waiting_get_car_model = State()
    waiting_car_model_search = State()

    #prodcut editing process 
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
    waiting_product_delete = State()


#Reply keyaboards



PRODUCT_EDIT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriyasi"), KeyboardButton(text="🔤 Mahsulotni nomi")],
        [KeyboardButton(text="🚘 Mashina brendi"), KeyboardButton(text="🚗 Mashina modeli")],
        [KeyboardButton(text="📦 Mahsulot bo'limi"), KeyboardButton(text="◀️ Bosh menu")],
    ],    
    resize_keyboard=True
)

@product_router.message(F.text.in_(("➕ Mahsulot qo'shish", "✒️ Mahsulotni tahrirlash", "✨ Barcha mahsulotlarni ko'rish")))
async def product_controls_handler(message: Message, state: FSMContext):
    """
    Handle product management actions (add, edit).
    """
    actions = {
        "➕ Mahsulot qo'shish": (ProductFSM.waiting_show_category, show_category),
        "✒️ Mahsulotni tahrirlash": (ProductFSM.waiting_edit_products, product_edit_options_keyboard),
        "✨ Barcha mahsulotlarni ko'rish": (ProductFSM.waiting_get_all_products, get_all_products),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

async def product_edit_options_keyboard(message: Message, state: FSMContext):
    await message.answer("Mahsulotni qaysi maydoni bo'yicha qidirmoqchisiz tanlang? 👇", reply_markup=PRODUCT_EDIT_CONTROLS_KEYBOARD)

@product_router.message(F.text.in_(("📂 Kategoriyasi", "🔤 Mahsulotni nomi", "🚘 Mashina brendi", "🚗 Mashina modeli")))
async def product_edit_controls_handler(message: Message, state: FSMContext):

    actions = {
        "📂 Kategoriyasi": (ProductFSM.waiting_edit_products_by_category, get_all_products_category),
        "🔤 Mahsulotni nomi": (ProductFSM.waiting_edit_products_by_part_name, get_all_products_by_part_name),
        "🚘 Mashina brendi": (ProductFSM.waiting_edit_products_by_brand_name, get_all_products_by_car_brand),
        "🚗 Mashina modeli": (ProductFSM.waiting_edit_products_by_model_name, get_all_products_by_car_model),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)




# Product part started

#Utils
async def show_car_brands_list(message: Message):
    """
    CarBrandlarning listini chiqaruvchi klaviatura.
    """
    car_brands = await sync_to_async(lambda: list(CarBrand.objects.all()))()

    if not car_brands:
        await message.answer("Hozircha avtomobil brendlari mavjud emas.")
        return
    
    brand_names = [brand.name for brand in car_brands]
    buttons = [KeyboardButton(text=name) for name in brand_names]
    back_button = KeyboardButton(text="◀️ Bosh menu")
    
    # Brendlarni ikki ustunli formatda chiqarish
    car_brand_keyboard = ReplyKeyboardMarkup(
        keyboard=[[back_button]]+[buttons[i:i + 2] for i in range(0, len(buttons), 2)],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return car_brand_keyboard

async def show_car_models_list(message: Message):
    """
    Bazadagi barcha CarModellarni chiqaruvchi klaviatura.
    """
    car_models = await sync_to_async(lambda: list(CarModel.objects.all()))()

    if not car_models:
        await message.answer("Hozircha avtomobil modellari mavjud emas.")
        return
    
    model_names = [model.name for model in car_models]
    buttons = [KeyboardButton(text=name) for name in model_names]
    back_button = KeyboardButton(text="◀️ Bosh menu")
    # Modellarni ikki ustunli formatda chiqarish
    car_model_keyboard = ReplyKeyboardMarkup(
        keyboard=[[back_button]]+[buttons[i:i + 2] for i in range(0, len(buttons), 2)],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return car_model_keyboard

async def show_quality_list():
    """
    Mahsulot sifatini tanlash uchun klaviatura.
    """
    buttons = [KeyboardButton(text=value) for value in quality_choices.keys()]
    back_button = KeyboardButton(text="◀️ Bosh menu")

    # Sifat tanlash tugmalarini ikki ustunli formatda chiqarish
    quality_keyboard = ReplyKeyboardMarkup(
        keyboard=[[back_button]]+[buttons[i:i + 2] for i in range(0, len(buttons), 2)],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return quality_keyboard

async def format_product_info(product):
    quality_choices = {
        "new": "Yangi 🆕",
        "renewed": "Yangilangan 🔄",
        "excellent": "Zo'r 👍",
        "good": "Yaxshi ✨",
        "acceptable": "Qoniqarli 👌"
    }

    product_data = await sync_to_async(lambda p: {
        "category_name": p.category.name,
        "brand_name": p.car_brand.name,
        "model_name": p.car_model.name,
        "price_info": p.original_and_discounted_price(),
    })(product)
    
    price_text = (
      f"💰 <b>Asl narxi:</b> <s>{product_data['price_info']['original_price']} so'm</s>\n"
      f"📉 <b>Chegirmali narx:</b> {product_data['price_info']['discounted_price']} so'm 🔥"
      if product_data['price_info']["discounted_price"]
      else f"💲 <b>Narxi:</b> {product_data['price_info']['original_price']} so'm"
    )

    availability_text = (
        'Sotuvda yo‘q'
        if not product.available else
        f'Sotuvda qolmadi.'
        if product.available_stock == 0 else
        f'Sotuvda <b>{product.available_stock}</b> ta qoldi'
        if product.available_stock < 20 else
        f'Sotuvda <b>{product.available_stock}</b> ta bor'
    )


    return (
        f"🛠 <b>Mahsulot nomi:</b> {product.name}\n"
        f"📦 <b>Kategoriyasi:</b> {product_data['category_name']}\n"
        f"🏷 <b>Brandi:</b> {product_data['brand_name']}\n"
        f"🚘 <b>Modeli:</b> {product_data['model_name']}\n"
        f"{price_text}\n"  
        f"📊 <b>Mavjudligi:</b> {availability_text}\n"
        f"🌟 <b>Holati:</b> {quality_choices[product.quality]}\n"
        f"📝 <b>Tavsifi:</b> {product.description or 'Yo‘q'}\n"
    )

async def send_category_keyboard(message: Message, prefix: str, state: FSMContext):
    keyboard = await get_categories_keyboard(callback_data_prefix=f"{prefix}_first_page", state=state)
    await message.answer("Kategoriyalar:", reply_markup=keyboard)

async def fetch_products(category_id: int):
    filter_params = {"category_id": category_id, "available": True}
    return await sync_to_async(list)(Product.objects.filter(**filter_params))

async def send_keyboard_options(message: Message, items, prompt_text):
    buttons = []
    back_button = [KeyboardButton(text="◀️ Bosh menu"), KeyboardButton(text="✒️ Mahsulotni tahrirlash") ]
    buttons.append(back_button)

    row = []
    for i, item in enumerate(items):
        row.append(KeyboardButton(text=item.name))
        if (i + 1) % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer(prompt_text, reply_markup=keyboard)

async def handle_product_search_results(message: Message, products, state: FSMContext):
    if not products:
        await message.answer("Mahsulot Topilmadi")
        return
    
    await state.update_data(search_results=products)

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    total_pages = ((len(products_with_numbers) + 9) // 10)
    await display_products_page(1, message, products_with_numbers, None, total_pages , 10, "search_product", state)

async def handle_product_first_page(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    category_id = int(callback_query.data.split(':')[1])
    products = await fetch_products(category_id)

    if not products:
        await callback_query.answer("Mahsulotlar yo‘q.")
        await callback_query.answer()
        return

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    current_page = 1

    await display_products_page(current_page, callback_query, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix, state)
    await callback_query.answer()

async def handle_product_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
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
        products = await fetch_products(category_id)
    
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    
    await display_products_page(page_num, callback_query, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix, state)
    await callback_query.answer()

async def display_products_page(page_num, callback_query_or_message, products_with_numbers, category_id, total_pages, products_per_page, callback_prefix, state):
    start_index = (page_num - 1) * products_per_page
    end_index = min(start_index + products_per_page, len(products_with_numbers))
    page_products = products_with_numbers[start_index:end_index]
    
    getting_process = await state.get_state() == ProductFSM.waiting_get_all_products
    

    message_text = (
        f"{ '✨ Mahsulotni ko\'rish bo\'limi:\n\n' if getting_process else '✒️ Mahsulotni tahrirlash bo\'limi: \n\n'} 🔍 Umumiy natija: {len(products_with_numbers)} ta mahsulotlar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, product in page_products:
        car_model_name = await sync_to_async(lambda: product.car_model.name)()
        message_text += f"{number}. {car_model_name} — {product.name}\n"

    product_buttons = []
    row = []
    for number, product in page_products:
        if getting_process:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"product:{product.id}:get"))
        else:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"product:{product.id}:none"))

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
    
    if await state.get_state() == ProductFSM.waiting_edit_products_by_category:
        product_keyboard = InlineKeyboardMarkup(inline_keyboard=product_buttons + [pagination_buttons, [InlineKeyboardButton(text="⬅️ Ortga", callback_data="categories")]])
    else:    
        product_keyboard = InlineKeyboardMarkup(inline_keyboard=product_buttons + [pagination_buttons])
    
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=product_keyboard, parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text, reply_markup=product_keyboard, parse_mode="HTML"
        )

async def update_and_clean_messages(message: Message, chat_id: int, message_id: int, product_info: str, product_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_caption(
        chat_id=chat_id,
        message_id=message_id,
        caption=product_info,
        parse_mode='HTML',
        reply_markup=(await product_edit_keyboard(product_id))
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

async def product_edit_keyboard(product_id):

    fields = ['Kategoriyasi', 'Brandi', 'Modeli', 'Nomi', 'Narxi', 
              'Mavjudligi', 'Soni', 'Holati', 'Rasmi', 'Tavsifi']

    keyboard = [[InlineKeyboardButton(text="Tahrirlash uchun tanlang 👇", callback_data="noop")]]
    for i in range(0, len(fields), 2):
        row = [
            InlineKeyboardButton(text=fields[i], callback_data=f"field_{fields[i]}:{product_id}")
        ]
        if i + 1 < len(fields): 
            row.append(InlineKeyboardButton(text=fields[i + 1], callback_data=f"field_{fields[i+1]}:{product_id}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🗑 Mahsulotni o'chirish", callback_data=f"field_deleteproduct:{product_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Bosh menu", callback_data="◀️ Bosh menu"), InlineKeyboardButton(text="❌ Ushbu xabarni o'chirish", callback_data="delete_message")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


#Show
@product_router.message(ProductFSM.waiting_get_all_products)
async def get_all_products(message: Message, state: FSMContext):
    products = await sync_to_async(list)(Product.objects.all())
    await handle_product_search_results(message, products, state)

# Adding
@product_router.message(ProductFSM.waiting_show_category)
async def show_category(message: Message, state: FSMContext):
    """
    Handles the addition of a new product.
    """
    text =  (
    "📝 Mahsulotni quyidagi maydonlar bo'yicha to'ldirishingiz kerak bo'ladi.👇\n\n"
    f"📦 <b>Kategoriyasi:</b> \n"
    f"🏷 <b>Brandi:</b> \n"
    f"🚘 <b>Modeli:</b> \n"
    f"🛠 <b>Mahsulot nomi: </b> \n"
    f"💲 <b>Narxi:</b> so'm\n"
    f"📊 <b>Mavjudligi va Soni:\n</b> "
    f"🌟 <b>Holati:</b> \n"
    f"📝 <b>Tavsifi</b>:\n"
 
    )
    await message.answer(text=text, parse_mode='HTML')
    await message.answer("Qo'shiladigan mahsulotning kategoriyasini tanlang yoki kiriting:", reply_markup=(await show_category_list(message)))
    await state.set_state(ProductFSM.waiting_set_category)

@product_router.message(ProductFSM.waiting_set_category)
async def set_category(message: Message, state: FSMContext):
    """
    Handle the selected category and ask for the car brand.
    """

    category_name = message.text.strip().title()

    category = await sync_to_async(Category.objects.filter(name=category_name).first)()
    if not category:
        await message.answer("Kiritilgan kategoriya mavjud emas. Admin, qaytadan urinib ko'ring.")
        return
    
    await state.update_data(category_id=category.id)
    await message.answer(f"Kategoriya: '{category.name}' tanlandi.")

    await state.set_state(ProductFSM.waiting_show_car_brand)
    await show_car_brand(message, state)

@product_router.message(ProductFSM.waiting_show_car_brand)
async def show_car_brand(message: Message, state: FSMContext):
    """
    Bazadagi barcha CarBrandlarni chiqaruvchi klaviatura.
    """
    car_brands = await sync_to_async(lambda: list(CarBrand.objects.all()))()
    if car_brands:
        await message.answer("Endi avtomobil brendini tanlang yoki kiriting:", reply_markup=(await show_car_brands_list(message)))
    elif not car_brands:
        await message.answer("Avtomobil brendini kiriting:")

    await state.set_state(ProductFSM.waiting_set_car_brand)

@product_router.message(ProductFSM.waiting_set_car_brand)
async def set_car_brand(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()

    car_brand = await sync_to_async(CarBrand.objects.filter(name=car_brand_name).first)()

    if car_brand:
        await message.answer(f"Brend: '{car_brand.name}' tanlandi.")
    else:
        car_brand = await sync_to_async(CarBrand.objects.create)(name=car_brand)
        await message.answer(f"Yangi brend qo‘shildi: {car_brand.name}.")
    await state.update_data(car_brand_id=car_brand.id)   
 
    await state.set_state(ProductFSM.waiting_show_car_model)
    await show_car_model(message, state)

@product_router.message(ProductFSM.waiting_show_car_model)
async def show_car_model(message: Message, state: FSMContext):
    """
    Bazadagi barcha CarModellarni chiqaruvchi klaviatura.
    """
    car_models = await sync_to_async(lambda: list(CarModel.objects.all()))()

    if car_models:
        await message.answer("Endi avtomobil modelini tanlang yoki kiriting:", reply_markup=(await show_car_models_list(message)))
    elif not car_models:
        await message.answer("Avtomobil modelini kiriting:")

    await state.set_state(ProductFSM.waiting_set_car_model)

@product_router.message(ProductFSM.waiting_set_car_model)
async def set_car_model(message: Message, state: FSMContext):
    car_model_name = message.text.strip().title()

    data = await state.get_data()
    car_brand_id = data["car_brand_id"] 

    car_model = await sync_to_async(CarModel.objects.filter(brand_id=car_brand_id, name=car_model_name).first)()

    if car_model:
        await message.answer(f"Model: '{car_model.name}' tanlandi.")
    else:
        car_model = await sync_to_async(CarModel.objects.create)(brand_id=car_brand_id, name=car_model_name)
        await message.answer(f"Yangi model qo‘shildi: {car_model.name}.")
    await state.update_data(car_model_id=car_model.id)

    await message.answer("Ehtiyot qism nomini kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ProductFSM.waiting_for_part_name)

@product_router.message(ProductFSM.waiting_for_part_name)
async def set_part_name(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    await state.update_data(part_name=part_name)
    await message.answer("Narxni kiriting (so'mda):")
    await state.set_state(ProductFSM.waiting_for_price)

@product_router.message(ProductFSM.waiting_for_price)
async def set_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        await state.update_data(price=price)
        await message.answer(
            "Mahsulot mavjudmi? (Ha/Yo'q):",
            reply_markup=CONFIRM_KEYBOARD
        )        
        await state.set_state(ProductFSM.waiting_for_availability)
    except ValueError:
        await message.answer("Admin, narxni to'g'ri formatda kiriting (faqat raqam).")

@product_router.message(ProductFSM.waiting_for_availability)
async def set_availability(message: Message, state: FSMContext):
    availability = message.text.strip().lower()
    if availability in ["ha", "yo'q"]:
        available = availability == "ha"
        await state.update_data(available=available)
        if available:
            await message.answer("Sotuvda qancha mahsulot bor? :")
            await state.set_state(ProductFSM.waiting_for_stock)
        else:
            await state.update_data(in_stock=0)
            await message.answer("Mahsulot holatini tanlang: ", reply_markup=(await show_quality_list()))
            await state.set_state(ProductFSM.waiting_for_set_quality)
    else:
        await message.answer("Admin, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
 
@product_router.message(ProductFSM.waiting_for_stock)
async def set_in_stock(message: Message, state: FSMContext):
    try:
        in_stock = int(message.text.strip())
        if in_stock > 0:
            await state.update_data(in_stock=in_stock)
            await message.answer("Mahsulot holatini tanlang: ", reply_markup=(await show_quality_list()))
            await state.set_state(ProductFSM.waiting_for_set_quality)
        else:
            await message.answer("Admin, faqat 0 dan yuqori mavjud mahsulot sonni kiriting:")
    except ValueError:
        await message.answer("Admin, mahsulot sonini to'g'ri formatda kiriting (faqat raqam).")

@product_router.message(ProductFSM.waiting_for_set_quality)
async def set_quality(message: Message, state: FSMContext):
    selected_quality = message.text.strip()

    if selected_quality in quality_choices:
        await state.update_data(quality=quality_choices[selected_quality])
        await message.answer("Mahsulotning rasmini yuboring:")
        await state.set_state(ProductFSM.waiting_for_photo)
    else:
        await message.answer("Admin, faqat ko'rsatilgan sifatlardan tanlang.")

@product_router.message(ProductFSM.waiting_for_photo)
async def set_photo(message: Message, state: FSMContext):
    
    # Checking if the incoming message is a photo
    if not message.photo:
        await message.answer("Admin, mahsulotning rasmini yuboring.")
        return

    # Get the highest resolution photo and its file_id
    photo = message.photo[-1]
    file_id = photo.file_id

    # Save the file_id to FSM context
    await state.update_data(photo=file_id)  

    # Send confirmation to the user
    await message.answer("Rasm muvaffaqiyatli qabul qilindi.")
    await message.answer("Mahsulot haqida qisqacha tavsif yozing:")

    await state.set_state(ProductFSM.waiting_for_description)

@product_router.message(ProductFSM.waiting_for_description)
async def set_description_and_save(message: Message, state: FSMContext):
    description = message.text.capitalize()
    user = await get_user_from_db(message.from_user.id)
    # Get the data from FSM context
    data = await state.get_data()
    photo_file_id = data.get("photo")

    # Get the file from Telegram
    file = await message.bot.get_file(photo_file_id)
    file_path = os.path.join(settings.MEDIA_ROOT, 'product_photos', f"{file.file_id}.jpg")

    try:
        # Download and save the file locally
        await message.bot.download_file(file.file_path, file_path)

        # Open the file and save it to the database
        with open(file_path, 'rb') as f:
            product = await sync_to_async(Product.objects.create)(
                owner_id = user.id,
                updated_by_id = user.id,
                category_id=data["category_id"],
                car_brand_id=data["car_brand_id"],
                car_model_id=data["car_model_id"],
                name=data["part_name"],
                price=data["price"],
                available=data["available"],
                stock=data["in_stock"],
                quality=data["quality"],
                photo=File(f, name=os.path.basename(file_path)),
                description=description,
            )

    finally:
        # Ensure the temporary file is always deleted
        if os.path.exists(file_path):
            os.remove(file_path)


    await message.answer(f"Mahsulot '{product.name}' muvaffaqiyatli qo'shildi!", reply_markup=PRODUCT_CONTROLS_KEYBOARD)
    await state.clear()

#Edit 

#By category
@product_router.message(ProductFSM.waiting_edit_products_by_category)
async def get_all_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "all_products", state)

@product_router.callback_query(F.data == "categories")
async def show_categories(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await get_categories_keyboard(callback_data_prefix="all_products_first_page", state=state))

#By part_name
@product_router.message(ProductFSM.waiting_edit_products_by_part_name)
async def get_all_products_by_part_name(message: Message, state: FSMContext):
    await message.answer("Mahsulotning, ehtiyot qism nomini kiriting: 👇")
    await state.set_state(ProductFSM.waiting_part_name_search)

@product_router.message(ProductFSM.waiting_part_name_search)
async def search_product_by_part_name(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    products = await sync_to_async(list)(Product.objects.filter(name__icontains=part_name))
    await handle_product_search_results(message, products, state)

#By car brand_name
@product_router.message(ProductFSM.waiting_get_car_brand)
async def get_all_products_by_car_brand(message: Message, state: FSMContext):
    car_brands = await sync_to_async(list)(CarBrand.objects.all())
    await send_keyboard_options(message, car_brands, "Mashina brendlarini tanlang yoki kiriting:")
    await state.set_state(ProductFSM.waiting_car_brand_search)

@product_router.message(ProductFSM.waiting_car_brand_search)
async def search_product_by_car_brand(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()
    car_brand = await sync_to_async(CarBrand.objects.get)(name__icontains=car_brand_name)
    if not car_brand:
        await message.answer(f"Kechirasiz, {car_brand_name} brendi topilmadi.")
        return
    products = await sync_to_async(list)(Product.objects.filter(car_brand=car_brand))
    await handle_product_search_results(message, products, state)

#Edit by car model
@product_router.message(ProductFSM.waiting_get_car_model)
async def get_all_products_by_car_model(message: Message, state: FSMContext):
    car_models = await sync_to_async(list)(CarModel.objects.all())
    await send_keyboard_options(message, car_models, "Mashina modellerini tanlang yoki kiriting:")
    await state.set_state(ProductFSM.waiting_car_model_search)

@product_router.message(ProductFSM.waiting_car_model_search)
async def search_product_by_car_model(message: Message, state: FSMContext):
    car_model_name = message.text.strip().title()
    car_models = await sync_to_async(list)(CarModel.objects.filter(name__iexact=car_model_name))
    
    if not car_models:
        await message.answer(f"Kechirasiz, {car_model_name} modeli topilmadi.")
        return

    products = []
    for car_model in car_models:
        car_model_products = await sync_to_async(list)(Product.objects.filter(car_model=car_model))
        products.extend(car_model_products)

    await handle_product_search_results(message, products, state)

#...
@product_router.callback_query(F.data.startswith('all_products_first_page:'))
async def get_all_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_first_page(callback_query, state, callback_prefix="all_products")

@product_router.callback_query(F.data.startswith('all_products_other_pages:'))
async def get_all_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_other_pages(callback_query, state, callback_prefix="all_products")

@product_router.callback_query(F.data.startswith('search_product_other_pages:'))
async def get_search_product_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_other_pages(callback_query, state, callback_prefix="search_product")

@product_router.callback_query(F.data.startswith('product:'))
async def get_single_product(callback_query: CallbackQuery):
    product_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    product = await sync_to_async(Product.objects.filter(id=product_id).first)()

    if not product:
        await callback_query.message.answer("❌ Xatolik: Mahsulot topilmadi.")
        return
    
    product_info = await format_product_info(product)

    if action == "get":
        keyboard = await single_item_buttons()
    else:
        keyboard = await product_edit_keyboard(product_id)

    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(
                product.photo.path, filename=os.path.basename(product.photo.path))
            await callback_query.message.answer_photo(input_file, parse_mode='HTML', caption=product_info, reply_markup=keyboard)
        
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(parse_mode='HTML' , text=f"Mahsulot rasmi mavjud emas.\n\n{product_info}", reply_markup=keyboard)

    await callback_query.answer()

@product_router.callback_query(F.data.startswith('field_'))
async def product_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[1]
    product_id = int(callback_query.data.split(":")[1])

    user = await get_user_from_db(callback_query.from_user.id)
    product = await sync_to_async(Product.objects.filter(id=product_id).first)()
    
    if not product:
        await callback_query.answer("❌ Xatolik: Mahsulot topilmadi.")
        return

    if not product.available and field == "Soni":
        await callback_query.answer("📌 Mahsulot hozirda mavjud emas. Avval 'Mavjudligi' ni 'Ha' ga o'zgartiring.")
        await callback_query.answer()
        return
    
    field_actions = {
        "Kategoriyasi": (ProductFSM.waiting_product_category_edit, await show_category_list(callback_query.message)),
        "Brandi": (ProductFSM.waiting_product_brand_edit, await show_car_brands_list(callback_query.message)),
        "Modeli": (ProductFSM.waiting_product_model_edit, await show_car_models_list(callback_query.message)),
        "Nomi": (ProductFSM.waiting_product_partname_edit, None),
        "Narxi": (ProductFSM.waiting_product_price_edit, None), 
        "Mavjudligi": (ProductFSM.waiting_product_availability_edit, CONFIRM_KEYBOARD), 
        "Soni": (ProductFSM.waiting_product_stock_edit, None), 
        "Holati": (ProductFSM.waiting_product_quality_edit, await show_quality_list()), 
        "Rasmi": (ProductFSM.waiting_product_photo_edit, None),
        "Tavsifi": (ProductFSM.waiting_product_description_edit, None),
        "deleteproduct": (ProductFSM.waiting_product_delete, CONFIRM_KEYBOARD),
    }

    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, mahsulotni kategoriya bo‘limidan qaytadan tanlang.")
        return
    
    await state.update_data(message_id=message_id, chat_id=chat_id, product=product, user=user)

    next_state, markup = field_actions[field]
    await state.set_state(next_state)

    if field == "deleteproduct":
        await callback_query.message.answer(f"Ushbu mahsulotni o‘chirmoqchimisiz? 🗑", reply_markup=CONFIRM_KEYBOARD)
    elif markup:
        await callback_query.message.answer(f"{product} mahsulotining yangi {field.lower()}ni tanlang yoki kiriting:", 
                                    reply_markup=markup) 
    else:
        await callback_query.message.answer(f"{product} mahsulotining yangi {field.lower()}ni kiriting:", reply_markup=ReplyKeyboardRemove())

    await callback_query.answer()

@product_router.message(ProductFSM.waiting_product_category_edit)
async def product_category_edit(message: Message, state: FSMContext):
    category_name = message.text.strip().title()

    if not category_name:
        await message.answer("❌ Kategoriya nomi bo‘sh bo‘lishi mumkin emas. Admin, nom kiriting!")
        return

    if category_name.isdigit():
      await message.answer("❌ Kategoriya nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
      return

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")
    

    if not product:
        await message.answer("❌ Mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    try:
        category = await sync_to_async(Category.objects.filter(name=category_name).first)()

        if not category:
            await message.answer(
                "❌ Bunday kategoriya topilmadi. Admin, qayta urinib ko'ring yoki kategoriya bo'limidan yangi kategoriya qo'shing."
            )
            return

        if category == await sync_to_async(lambda: product.category)():
            await message.answer(
                f"❌ Mahsulot kategoriyasi allaqachon '{category_name}'ga biriktirilgan.\n"
                "Boshqa kategoriyani tanlang 👇",
                reply_markup=await show_category_list(message)
            )
            return

        product.category = category
        product.updated_by = user
        await sync_to_async(product.save)()

        await message.answer(f"✅ Mahsulot kategoriyasi '{category_name}'ga muvaffaqiyatli yangilandi. 👆")

        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot kategoriyasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@product_router.message(ProductFSM.waiting_product_brand_edit)
async def product_brand_edit(message: Message, state: FSMContext):
    brand_name = message.text.strip().upper()

    if not brand_name:
        await message.answer("❌ Brend nomi bo‘sh bo‘lishi mumkin emas. Admin, nom kiriting!")
        return

    if brand_name.isdigit():
        await message.answer("❌ Brend nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
        return

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")
    

    if not product:
        await message.answer("❌ Mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    try:
        brand = await sync_to_async(CarBrand.objects.filter(name=brand_name).first)()
        
        if not brand:
            brand = await sync_to_async(CarBrand.objects.create)(name=brand_name)
            await message.answer(f"✅ Mahsulot uchun yangi brend '{brand_name}' yaratildi va tayinlandi.")    
        elif brand == product.car_brand:
            await message.answer(
                f"❌ Mahsulot brendi allaqachon '{brand_name}'ga biriktirilgan.\n"
                "Boshqa brendni tanlang yoki kiriting 👇",
                reply_markup=await show_car_brands_list(message)
            )
            return
        else:
            await message.answer(f"✅ Mahsulot brendi '{brand_name}'ga muvaffaqiyatli yangilandi.")

        product.car_brand = brand

        if await sync_to_async(lambda: product.car_model_id)():
            current_model = await sync_to_async(lambda: product.car_model_id)()
            if await sync_to_async(lambda: current_model.brand)() != brand:
                car_model = await sync_to_async(CarModel.objects.filter(
                    name=current_model.name, brand=brand
                ).first)()

                if not car_model:
                    car_model = await sync_to_async(CarModel.objects.create)(
                        name=current_model.name, brand=brand
                    )

                product.car_model = car_model

        product.updated_by = user
        await sync_to_async(product.save)()

        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot brendini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@product_router.message(ProductFSM.waiting_product_model_edit)
async def product_model_edit(message: Message, state: FSMContext):
    model_name = message.text.strip().title()

    if model_name.isdigit():
        await message.answer("❌ Model nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
        return

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")
    

    if not product:
        await message.answer("❌ Mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    try:
        product_brand = await sync_to_async(lambda: product.car_brand)()
        existing_model = await sync_to_async(
            lambda: CarModel.objects.filter(brand=product_brand, name=model_name).first()
        )()

        if existing_model:
            
            if existing_model == await sync_to_async(lambda: product.car_model)():
                await message.answer(
                    f"❌ Mahsulot modeli allaqachon '{model_name}'ga biriktirilgan.\n"
                    "Boshqa modelni tanlang yoki kiriting 👇",
                    reply_markup=await show_car_models_list(message)
                )
                return
            product.car_model = existing_model
            msg_text = f"✅ Mahsulot modeli '{model_name}'ga muvaffaqiyatli yangilandi."
        else:
            new_model = await sync_to_async(CarModel.objects.create)(
                brand=product_brand,
                name=model_name
            )
            product.car_model = new_model
            msg_text = f"✅ Mahsulot uchun yangi model '{model_name}' yaratildi va tayinlandi."

        product.updated_by = user
        await sync_to_async(product.save)()

        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)
        await message.answer(msg_text)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot modelini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@product_router.message(ProductFSM.waiting_product_partname_edit)
async def product_partname_edit(message: Message, state: FSMContext):
    part_name = message.text.strip()

    if not part_name:
        await message.answer("❌ Mahsulot nomi bo‘sh bo‘lishi mumkin emas. Admin, nom kiriting!")
        return
    if part_name.isdigit(): 
        await message.answer("❌ Mahsulot nomi faqat raqamlardan iborat bo‘lishi mumkin emas. Admin, boshqa nom kiriting!")
        return

    if len(part_name) < 2 or len(part_name) > 100:
        await message.answer("❌ Mahsulot nomi 2 dan 255 tagacha belgidan iborat bo‘lishi kerak.")
        return

    part_name = part_name.title()

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")
    

    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko‘ring.")
        return

    if part_name == product.name:
        await message.answer(f"❌ Mahsulot nomi allaqachon '{part_name}' turibdi.\nBoshqa nom yozing 👇")
        return
    
    try:
        product.name = part_name
        product.updated_by = user
        await sync_to_async(product.save)()

        await message.answer(f"✅ Mahsulot nomi '{part_name}' ga muvaffaqiyatli yangilandi.")

        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot nomini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@product_router.message(ProductFSM.waiting_product_price_edit)
async def product_price_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")

    if not product:
        await message.answer("❌ Xatolik: Mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("❌ Mahsulot narxi musbat bo'lishi kerak! Qayta kiriting.")
            return
    except ValueError:
        await message.answer("📌 Admin, narxni to'g'ri formatda kiriting (faqat raqam).")
        return

    if price == product.price:
        await message.answer(f"❌ Mahsulot narxi allaqachon \"{price} so'm\" edi! Boshqa narx kiriting 👇")
        return
    
    try:
        product.price = price
        product.updated_by = user
        await sync_to_async(product.save)()

        await message.answer(f"✅ Mahsulot narxi \"{price}\" so'mga muvaffaqiyatli yangilandi.")
        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot narxini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")
    
@product_router.message(ProductFSM.waiting_product_availability_edit)
async def product_availability_edit(message: Message, state: FSMContext):
    availability = message.text.strip().lower()

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")

    if not product:
        await message.answer("❌ Xatolik: Mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    if availability not in ["ha", "yo'q"]:
        await message.answer("📌 Admin, faqat 'Ha' yoki 'Yo‘q' deb javob bering.", reply_markup=CONFIRM_KEYBOARD)
        return

    available = availability == "ha"
    
    if product.available == available:
        await message.answer(f"❌ Mahsulot mavjudligi allaqachon '{availability}' holatda. 👆\nBoshqa tugmani tanlang 👇", reply_markup=CONFIRM_KEYBOARD)
        return
    
    try:
        product.available = available
        product.updated_by = user
        await sync_to_async(product.save)()

        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)

        await message.answer(f"✅ Mahsulot mavjudligi '{availability}' ga muvaffaqiyatli yangilandi. 👆")

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot mavjudligini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@product_router.message(ProductFSM.waiting_product_stock_edit)
async def product_stock_edit(message: Message, state: FSMContext):
    try:
        in_stock = int(message.text.strip())
    except ValueError:
        await message.answer("📌 Admin, mahsulot sonini to'g'ri formatda kiriting (faqat musbat raqam).")
        return

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")

    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    if product.stock == in_stock:
        await message.answer(f"❌ Mahsulotning soni allaqachon {in_stock} ta edi! Boshqa miqdor kiriting 👇")
        return

    if not product.available:
        await message.answer("📌 Oldin mahsulotni mavjudligini 'Ha' ga o'zgartiring!")
        return

    if in_stock > 0:
        product.stock = in_stock
        product.updated_by = user
        await sync_to_async(product.save)()
        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)
        await message.answer(f"✅ Mahsulot soni '{in_stock}' taga muvaffaqiyatli yangilandi. ")
    elif in_stock == 0:
        await message.answer("📌 Admin, agar mahsulot qolmagan bo'lsa, mavjudligini 'Yo'q' ga o'zgartiring.")
    else:
        await message.answer("❌ Admin, musbat sonni kiriting!!!")

@product_router.message(ProductFSM.waiting_product_quality_edit)
async def product_quality_edit(message: Message, state: FSMContext):
    selected_quality = message.text.strip()

    new_quality = quality_choices.get(selected_quality)
    if not new_quality:
        await message.answer("📌 Admin, faqat ko'rsatilgan sifatlardan tanlang.", reply_markup=await show_quality_list())
        return

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")

    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    if product.quality == new_quality:
        await message.answer(f"❌ Mahsulot sifati allaqachon '{selected_quality}' holatda edi.\nBoshqa holatni tanlang 👇", reply_markup=await show_quality_list())
        return
    try:
        product.quality = new_quality
        product.updated_by = user
        await sync_to_async(product.save)()

        product_info = await format_product_info(product)
        await update_and_clean_messages(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot sifatini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    await message.answer(f"✅ Mahsulot sifati '{selected_quality}' holatiga muvaffaqiyatli yangilandi.")

@product_router.message(ProductFSM.waiting_product_photo_edit)
async def product_photo_edit(message: Message, state: FSMContext):

    if not message.photo:
        await message.answer("📸 Admin, mahsulotning rasmini yuboring.")
        return

    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")

    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_path = os.path.join(settings.MEDIA_ROOT, "product_photos", f"{file.file_unique_id}.jpg")

    try:
        await message.bot.download_file(file.file_path, file_path)
        with open(file_path, "rb") as f:
            await sync_to_async(product.photo.save)(f"{file.file_unique_id}.jpg", f)

        product.updated_by = user
        await sync_to_async(product.save)()

        media = InputMediaPhoto(media=FSInputFile(file_path), caption=await format_product_info(product), parse_mode="HTML")
        await message.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=await product_edit_keyboard(product.id))

        await message.answer("✅ Mahsulotning yangi rasmi muvaffaqiyatli yangilandi 👆")

        delete_tasks = [message.bot.delete_message(chat_id, msg_id) for msg_id in range(message.message_id, message_id, -1)]
        await asyncio.gather(*delete_tasks, return_exceptions=True)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot rasmini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@product_router.message(ProductFSM.waiting_product_description_edit)
async def product_description_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    product, user, message_id, chat_id = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id")

    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    description = message.text.strip().capitalize()
    
    if description == product.description:
        await message.answer("❌ Bunday mahsulot tavsifi allaqachon yozilgan.\nBoshqa tavsifi yozing 👇")
        return
    
    try:
        product.description, product.updated_by = description, user
        await sync_to_async(product.save)()

        await message.answer(f"✅ Mahsulot tavsifi\n'{description}'\n-ga muvaffaqiyatli yangilandi.")
        await update_and_clean_messages(message, chat_id, message_id, await format_product_info(product), product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot tavsifini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")
       
@product_router.message(ProductFSM.waiting_product_delete)
async def product_delete(message: Message, state: FSMContext):

    confirm_text = message.text.strip().lower()
    data = await state.get_data()

    product = data.get('product')
    message_id = data.get('message_id')
    chat_id = data.get('chat_id')

    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        await state.clear()
        return

    if confirm_text not in ["ha", "yo'q"]:
        await message.answer("Admin, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
        return
    
    try:
        if confirm_text == "ha":
            await sync_to_async(product.delete)()

            delete_tasks = [
                message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                for msg_id in range(message.message_id, message_id - 1, -1)
            ]
            await asyncio.gather(*delete_tasks, return_exceptions=True)

            await message.answer(f"✅ Mahsulot '{product.name}' muvaffaqiyatli o'chirildi!", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer(f"❌ Mahsulotning o'chirilishi bekor qilindi.", reply_markup=ReplyKeyboardRemove())

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulotni o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    finally:
        await state.clear()

# Product part ended