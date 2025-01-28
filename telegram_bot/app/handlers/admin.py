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
from telegram_app.models import Category, CarBrand, CarModel, Product

# Create a router for admin handlers
admin_router = Router()

# Define FSM for product actions

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
    waiting_product_photo_edit = State()
    waiting_product_description_edit = State()

    # product deleting
    waiting_show_product_for_delete = State()
    waiting_product_delete_confirm = State()
    waiting_product_delete = State()

# Buttons
ADMIN_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya"), KeyboardButton(text="📦 Mahsulot")],
    ],
    resize_keyboard=True,
)

CATEGORY_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Kategoriya qo'shish"), KeyboardButton(text="✏️ Kategoriyani tahrirlash")],
        [KeyboardButton(text="❌ Kategoriyani o'chirish"), KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

PRODUCT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="✏️ Mahsulotni tahrirlash")],
        [KeyboardButton(text="❌ Mahsulotni o'chirish"), KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True
)

CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)

# Main control handlers
MAIN_CONTROLS_RESPONSES = {
    "📂 Kategoriya": {
        "text": "Kategoriya boshqaruvi uchun tugmalar:",
        "keyboard": CATEGORY_CONTROLS_KEYBOARD
    },
    "📦 Mahsulot": {
        "text": "Mahsulot boshqaruvi uchun tugmalar:",
        "keyboard": PRODUCT_CONTROLS_KEYBOARD
    },
    "⬅ Bosh menu": {
        "text": "Asosiy menuga xush kelibsiz!",
        "keyboard": ADMIN_MAIN_CONTROLS_KEYBOARD,
        "clear_state": True 
    }
}

@admin_router.message(lambda message: message.text in MAIN_CONTROLS_RESPONSES)
async def main_controls_handler(message: Message, state: FSMContext):
    response = MAIN_CONTROLS_RESPONSES[message.text]
    await message.answer(response["text"], reply_markup=response["keyboard"])
    if response.get("clear_state"):
        await state.clear()

# Category part started
@admin_router.message(lambda message: message.text in ["➕ Kategoriya qo'shish", "✏️ Kategoriyani tahrirlash", "❌ Kategoriyani o'chirish"])
async def category_controls_handler(message: Message, state: FSMContext):
    """
    Handle category management actions (add, edit, delete).
    """
    actions = {
        "➕ Kategoriya qo'shish": (ProductFSM.waiting_get_category, get_category),
        "✏️ Kategoriyani tahrirlash": (ProductFSM.waiting_show_categories_for_edition, show_categories_for_edition),
        "❌ Kategoriyani o'chirish": (ProductFSM.waiting_show_categories_for_deletion, show_categories_for_deletion),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)
# Util functions
async def show_category_list(message: Message):
    """
    Kategoriyalar ro'yxatini qayta yangilaydi va foydalanuvchiga ko'rsatadi.
    """
    categories = await sync_to_async(lambda: list(Category.objects.all()))()
    if not categories:
        await message.answer("Hozircha kategoriyalar mavjud emas.")
        return

    category_names = [category.name for category in categories]
    buttons = [KeyboardButton(text=name) for name in category_names]
    back_button = KeyboardButton(text="⬅ Bosh menu")

    # Yangi kategoriya tugmalarini yaratish
    category_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )
    return category_keyboard

# Adding part
@admin_router.message(StateFilter(ProductFSM.waiting_get_category))
async def get_category(message: Message, state: FSMContext):
    """
    Yangi kategoriya qo'shish jarayonini boshlaydi.
    """
    await message.answer("Yangi kategoriya nomini kiriting:")
    await state.set_state(ProductFSM.waiting_save_get_category)

@admin_router.message(StateFilter(ProductFSM.waiting_save_get_category))
async def save_get_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi kiritgan yangi kategoriyani ma'lumotlar bazasiga qo'shadi.
    """
    category_name = message.text.strip()
    if not category_name:
        await message.answer("Kategoriya nomi bo'sh bo'lishi mumkin emas. Iltimos, qayta kiriting.")
        return

    try:
        category = await sync_to_async(Category.objects.create)(name=category_name)
        await message.answer(f"✅ '{category.name}' kategoriyasi muvaffaqiyatli qo'shildi!")
        await message.answer("Kategoriya ro'yxati yangilandi 👇", reply_markup=(await show_category_list(message)))
    except IntegrityError:
        await message.answer(f"⚠️ '{category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom kiriting.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()

# Upadating 
@admin_router.message(StateFilter(ProductFSM.waiting_show_categories_for_edition))
async def show_categories_for_edition(message: Message, state: FSMContext):
    """
    Mavjud kategoriyalarni chiqaradi va foydalanuvchini tahrirlash jarayoniga yo'naltiradi.
    """
    await message.answer("Tahrirlanadigan kategoriyani tanlang yoki nomini kiriting:", reply_markup=(await show_category_list(message)))
    await state.set_state(ProductFSM.waiting_update_category)

@admin_router.message(StateFilter(ProductFSM.waiting_update_category))
async def update_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi tanlagan yoki yozgan kategoriya asosida tahrirlash jarayonini boshlaydi.
    """
    selected_category_name = message.text.strip().title()

    # Ma'lumotlar bazasida kategoriya nomini tekshirish
    category = await sync_to_async(Category.objects.filter(name=selected_category_name).first)()
    if not category:
        await message.answer("Bunday kategoriya topilmadi. Iltimos, ro'yxatdan tanlang.")
        return

    # Kategoriya ma'lumotlarini tahrirlash
    await state.update_data(category_id=category.id)
    await message.answer(f"Tanlangan kategoriya: {category.name}\nYangi nomni kiriting:")
    await state.set_state(ProductFSM.waiting_save_updated_category)

@admin_router.message(StateFilter(ProductFSM.waiting_save_updated_category))
async def save_updated_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi kiritgan yangi kategoriya nomini saqlaydi.
    """
    new_category_name = message.text.strip().title()
    if not new_category_name:
        await message.answer("Kategoriya nomi bo'sh bo'lishi mumkin emas. Iltimos, qayta kiriting.")
        return

    data = await state.get_data()
    category_id = data.get("category_id")

    try:
        # Kategoriya nomini yangilash
        category = await sync_to_async(Category.objects.get)(id=category_id)
        category.name = new_category_name
        await sync_to_async(category.save)()

        await message.answer(f"✅ Tanlangan kategoriya nomi '{new_category_name}' nomiga o'zgartirildi. ")
        await message.answer("Kategoriya ro'yxati yangilandi 👇", reply_markup=(await show_category_list(message)))
    except IntegrityError:
        await message.answer(f"⚠️ '{new_category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom kiriting.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()

# Deleting part
@admin_router.message(StateFilter(ProductFSM.waiting_show_categories_for_deletion))
async def show_categories_for_deletion(message: Message, state: FSMContext):
    """
    Mavjud kategoriyalarni chiqaradi va foydalanuvchini o'chirish jarayoniga yo'naltiradi.
    """
    await message.answer("O'chirmoqchi bo'lgan kategoriyani tanlang yoki nomini kiriting:", reply_markup=(await show_category_list(message)))
    await state.set_state(ProductFSM.waiting_category_delete_confirm)
    
@admin_router.message(ProductFSM.waiting_category_delete_confirm)
async def category_delete_confirm(message: Message, state: FSMContext):
    """
    Confirm deletion of a category.
    """
    selected_category_name = message.text.strip().title()
    category = await sync_to_async(Category.objects.filter(name=selected_category_name).first)()
    if not category:
        await message.answer("Bunday kategoriya topilmadi. Iltimos, ro'yxatdan tanlang yoki to'g'ri nom kiriting.")
        return
    
    await state.update_data(category=category)
    await message.answer(f"Ushbu '{category}' kategoriyani o'chirmoqchimisiz? 🗑", reply_markup=CONFIRM_KEYBOARD)
    await state.set_state(ProductFSM.waiting_delete_category)
   
@admin_router.message(StateFilter(ProductFSM.waiting_delete_category))
async def delete_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi tanlagan yoki yozgan kategoriyani o'chiradi.
    """
    confirm_text = message.text.strip().lower()
 
    data = await state.get_data()
    category = data.get('category')

    if confirm_text in ["ha", "yo'q"]:
        yes = confirm_text == "ha"
        back_button = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅ Bosh menu")]], 
            resize_keyboard=True, 
            # one_time_keyboard=True 
        )
        if yes:
            await sync_to_async(category.delete)()
            await message.answer(f"✅ Kategoriya '{category.name}' muvaffaqiyatli o'chirildi!", reply_markup=back_button)
            await message.answer("Kategoriya ro'yxati yangilandi 👇", reply_markup=(await show_category_list(message)))
        else:
            await message.answer(f"❌ Kategoriyaning o'chirilishi bekor qilindi ", reply_markup=back_button)
            await state.clear()
            return
    else:
        await message.answer("Iltimos, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
        return
    await state.clear()
# Category part ended

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
    back_button = KeyboardButton(text="⬅ Bosh menu")
    # Brendlarni ikki ustunli formatda chiqarish
    car_brand_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
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
    back_button = KeyboardButton(text="⬅ Bosh menu")
    # Modellarni ikki ustunli formatda chiqarish
    car_model_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )
    return car_model_keyboard

# Adding
@admin_router.message(lambda message: message.text in ["➕ Mahsulot qo'shish", "✏️ Mahsulotni tahrirlash", "❌ Mahsulotni o'chirish"])
async def product_controls_handler(message: Message, state: FSMContext):
    """
    Handle product management actions (add, edit, delete).
    """
    actions = {
        "➕ Mahsulot qo'shish": (ProductFSM.waiting_show_category, show_category),
        "✏️ Mahsulotni tahrirlash": (ProductFSM.waiting_show_product_for_edit, show_product_for_edit),
        "❌ Mahsulotni o'chirish": (ProductFSM.waiting_show_product_for_delete, show_product_for_delete),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

@admin_router.message(StateFilter(ProductFSM.waiting_show_category))
async def show_category(message: Message, state: FSMContext):
    """
    Handles the addition of a new product.
    """
    await message.answer("Qo'shiladigan mahsulotning kategoriyasini tanlang yoki kiriting:", reply_markup=(await show_category_list(message)))
    await state.set_state(ProductFSM.waiting_set_category)

@admin_router.message(StateFilter(ProductFSM.waiting_set_category))
async def set_category(message: Message, state: FSMContext):
    """
    Handle the selected category and ask for the car brand.
    """

    category_name = message.text.strip().title()

    category = await sync_to_async(Category.objects.filter(name=category_name).first)()
    if not category:
        await message.answer("Kiritilgan kategoriya mavjud emas. Iltimos, qaytadan urinib ko'ring.")
        return
    
    await state.update_data(category_id=category.id)
    await message.answer(f"Kategoriya: '{category.name}' tanlandi.")

    await state.set_state(ProductFSM.waiting_show_car_brand)
    await show_car_brand(message, state)

@admin_router.message(StateFilter(ProductFSM.waiting_show_car_brand))
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

@admin_router.message(StateFilter(ProductFSM.waiting_set_car_brand))
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

@admin_router.message(StateFilter(ProductFSM.waiting_show_car_model))
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

@admin_router.message(StateFilter(ProductFSM.waiting_set_car_model))
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

@admin_router.message(StateFilter(ProductFSM.waiting_for_part_name))
async def set_part_name(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    await state.update_data(part_name=part_name)
    await message.answer("Narxni kiriting (so'mda):")
    await state.set_state(ProductFSM.waiting_for_price)

@admin_router.message(StateFilter(ProductFSM.waiting_for_price))
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
        await message.answer("Iltimos, narxni to'g'ri formatda kiriting (faqat raqam).")

@admin_router.message(StateFilter(ProductFSM.waiting_for_availability))
async def set_availability(message: Message, state: FSMContext):
    availability = message.text.strip().lower()
    if availability in ["ha", "yo'q"]:
        available = availability == "ha"
        await state.update_data(available=available)
        await message.answer("Mahsulotning rasmini yuboring:")
        await state.set_state(ProductFSM.waiting_for_photo)
    else:
        await message.answer("Iltimos, faqat 'Ha' yoki 'Yo'q' deb javob bering.")

@admin_router.message(StateFilter(ProductFSM.waiting_for_photo))
async def set_photo(message: Message, state: FSMContext):
    
    # Checking if the incoming message is a photo
    if not message.photo:
        await message.answer("Iltimos, mahsulotning rasmini yuboring.")
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

@admin_router.message(StateFilter(ProductFSM.waiting_for_description))
async def set_description_and_save(message: Message, state: FSMContext):
    description = message.text.capitalize()

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
                category_id=data["category_id"],
                car_brand_id=data["car_brand_id"],
                car_model_id=data["car_model_id"],
                name=data["part_name"],
                price=data["price"],
                available=data["available"],
                photo=File(f, name=os.path.basename(file_path)),
                description=description,
            )

    finally:
        # Ensure the temporary file is always deleted
        if os.path.exists(file_path):
            os.remove(file_path)


    await message.answer(f"Mahsulot '{product.name}' muvaffaqiyatli qo'shildi!", reply_markup=PRODUCT_CONTROLS_KEYBOARD)
    await state.clear()

# Editing
#Util functions
async def show_product_list(message: Message):
    """
    Shows product list.
    """
    products = await sync_to_async(lambda: list(Product.objects.all()))()
    if not products:
        await message.answer("Hozircha mahsulotlar mavjud emas. Iltimos, avval mahsulot qo'shing.", reply_markup=PRODUCT_CONTROLS_KEYBOARD)
        return

    product_names = [product.name for product in products]
    buttons = [KeyboardButton(text=name) for name in product_names]
    back_button = KeyboardButton(text="⬅ Bosh menu")
    # Tugmalarni ikki ustunli klaviaturaga bo'lish
    product_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )
    return product_keyboard

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
#...
@admin_router.message(StateFilter(ProductFSM.waiting_show_product_for_edit))
async def show_product_for_edit(message: Message, state: FSMContext):
    """
    Handles the edition of the product.
    """
    await message.answer("Tahrirlanadigan mahsulotni tanlang yoki kiriting:", reply_markup=(await show_product_list(message)))
    await state.set_state(ProductFSM.waiting_editing_product)

@admin_router.message(ProductFSM.waiting_editing_product)
async def edit_product(message: Message, state: FSMContext):
    data = await state.get_data()
    product = data.get('product')

    if not product:
        product_name = message.text.strip().title()
        product = await sync_to_async(Product.objects.filter(name=product_name).first)()

        if not product:
            await message.answer("Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")
            return
        
        await state.update_data(product=product)
    
    fields = ['Kategoriyasi', 'Brandi', 'Modeli', 'Nomi', 'Narxi', 'Mavjudligi', 'Rasmi', 'Tavsifi']
    back_button = KeyboardButton(text="⬅ Bosh menu")
    fields_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=fields[i]), KeyboardButton(text=fields[i + 1])] 
        for i in range(0, len(fields), 2)] + [[back_button]],
    resize_keyboard=True,
    )

    # Gather product details
    product_info = await format_product_info(product)
    
    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(product.photo.path, filename=os.path.basename(product.photo.path))
            await message.answer_photo(input_file, caption=product_info)
        except Exception as e:
            await message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await message.answer(f"Mahsulot rasmi mavjud emas.\n\n{product_info}")


    await message.answer(f"Qaysi maydonini tahrirlamoqchisiz 👇:", reply_markup=fields_keyboard)
    await state.set_state(ProductFSM.waiting_choose_product_field)

@admin_router.message(StateFilter(ProductFSM.waiting_choose_product_field))
async def choose_field(message: Message, state: FSMContext):
    field_name = message.text.strip().capitalize()

    field_actions = {
        "Kategoriyasi": (ProductFSM.waiting_product_category_edit,(await show_category_list(message))),
        "Brandi": (ProductFSM.waiting_product_brand_edit,(await show_car_brands_list(message))),
        "Modeli": (ProductFSM.waiting_product_model_edit,(await show_car_models_list(message))),
        "Nomi": (ProductFSM.waiting_product_partname_edit, None),
        "Narxi": (ProductFSM.waiting_product_price_edit, None),
        "Mavjudligi": (ProductFSM.waiting_product_availability_edit, CONFIRM_KEYBOARD), 
        "Rasmi": (ProductFSM.waiting_product_photo_edit, None),
        "Tavsifi": (ProductFSM.waiting_product_description_edit, None),
    }

    if field_name in field_actions:
        next_state, markup = field_actions[field_name] 
        await state.set_state(next_state)

        if markup:
            await message.answer(f"Mahsulotning yangi {field_name.lower()}ni tanlang yoki kiriting:", 
                                reply_markup=markup) 
        else:
            await message.answer(f"Mahsulotning yangi {field_name.lower()}ni kiriting:")
    else:
        await message.answer("❌ Noto'g'ri maydon tanlandi. Iltimos, ro'yxatdan birini tanlang.")

@admin_router.message(ProductFSM.waiting_product_category_edit)
async def product_category_edit(message: Message, state: FSMContext):
    category_name = message.text.strip().title()

    data = await state.get_data()
    product = data.get('product')

    category = await sync_to_async(Category.objects.filter(name=category_name).first)()
    if category:
        product.category = category
        await sync_to_async(product.save)()
        await message.answer(f"✅ Mahsulot kategoriyasi '{category_name}'ga  muvaffaqiyatli yangilandi: ")
    else:
        await message.answer("❌ Bunday kategoriya topilmadi. Iltimos, qayta urinib ko'ring yoki kategoriya bo'limidan yangi kategoriya qo'shing.")

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

@admin_router.message(ProductFSM.waiting_product_brand_edit)
async def product_brand_edit(message: Message, state: FSMContext):
    brand_name = message.text.strip().upper()

    data = await state.get_data()
    product = data.get('product')

    brand = await sync_to_async(CarBrand.objects.filter(name=brand_name).first)()
    if not brand:
        brand = await sync_to_async(CarBrand.objects.create)(name=brand_name)
        await message.answer(f"✅ Mahsulot uchun yangi brend '{brand}' yaratildi va tayinlandi.")    
    elif brand:
        await message.answer(f"✅ Mahsulot brendi '{brand_name}'ga muvaffaqiyatli yangilandi.")
        
    product.car_brand = brand

    # Ensure the car model is associated with the new brand
    if product.car_model:
        current_model = await sync_to_async(lambda: product.car_model)()
        current_brand = await sync_to_async(lambda: current_model.brand)()
        # Check if the current car model belongs to the new brand
        if current_brand != brand:
            # Attempt to find a car model with the same name under the new brand
            car_model = await sync_to_async(
                CarModel.objects.filter(name=current_model.name, brand=brand).first
            )()
            if not car_model:
                # Create a new car model under the new brand
                car_model = await sync_to_async(CarModel.objects.create)(
                    name=current_model.name, brand=brand
                )
            product.car_model = car_model

    # Save the product with the updated brand and model
    await sync_to_async(product.save)()

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

@admin_router.message(ProductFSM.waiting_product_model_edit)
async def product_model_edit(message: Message, state: FSMContext):
    model_name = message.text.strip().title()

    data = await state.get_data()
    product = data.get('product')
    product_brand = product.car_brand

    try:
        # Efficiently check for existing model within the brand
        car_model = await sync_to_async(CarModel.objects.filter(
            Q(brand=product_brand), Q(name=model_name)
        ).first)()

        if car_model:
            # Update product model if it exists
            product.car_model = car_model
            await sync_to_async(product.save)()
            await message.answer(f"✅ Mahsulot modeli '{model_name}'ga muvaffaqiyatli yangilandi.")
        else:
            # Create new model if it doesn't exist
            new_model = await sync_to_async(CarModel.objects.create)(
                brand=product_brand,
                name=model_name
            )
            product.car_model = new_model
            await sync_to_async(product.save)()
            await message.answer(f"✅ Mahsulot uchun yangi model '{model_name}' yaratildi va tayinlandi.")

    except Exception as e:
        # Handle potential errors gracefully
        print(f"Error updating product model: {e}")
        await message.answer("❌ Mahsulot modelini yangilashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

@admin_router.message(ProductFSM.waiting_product_partname_edit)
async def product_partname_edit(message: Message, state: FSMContext):
    part_name = message.text.strip().title()

    data = await state.get_data()
    product = data.get('product')

    if product:
        product.name = part_name
        await sync_to_async(product.save)()
        await message.answer(f"✅ Mahsulot nomi '{part_name}'ga muvaffaqiyatli yangilandi.")
    else:
        await message.answer("❌ Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

@admin_router.message(ProductFSM.waiting_product_price_edit)
async def product_price_edit(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())

        data = await state.get_data()
        product = data.get('product')

        if product:
            product.price = price
            await sync_to_async(product.save)()
            await message.answer(f"✅ Mahsulot narxi '{price}' so'mga  muvaffaqiyatli yangilandi. ")
        else:
            await message.answer("❌ Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")
    except ValueError:
        await message.answer("Iltimos, narxni to'g'ri formatda kiriting (faqat raqam).")

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

@admin_router.message(ProductFSM.waiting_product_availability_edit)
async def product_availability_edit(message: Message, state: FSMContext):
    availability = message.text.strip().lower()

    data = await state.get_data()
    product = data.get('product')

    if product:
        if availability in ["ha", "yo'q"]:
            available = availability == "ha"
            product.available = available
            await sync_to_async(product.save)()
        else:
            await message.answer("Iltimos, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
    else:
        await message.answer("❌ Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

@admin_router.message(ProductFSM.waiting_product_photo_edit)
async def product_photo_edit(message: Message, state: FSMContext):

    if not message.photo:
        await message.answer("Iltimos, mahsulotning rasmini yuboring.")
        return

    photo = message.photo[-1]
    photo_file_id = photo.file_id

    await message.answer("Rasm muvaffaqiyatli qabul qilindi.")

    data = await state.get_data()
    product = data.get('product')

    if product:
        try:
            # Download and save the file locally
            file = await message.bot.get_file(photo_file_id)
            file_path = os.path.join(settings.MEDIA_ROOT, 'product_photos', f"{file.file_id}.jpg")
            await message.bot.download_file(file.file_path, file_path)

            # Open the downloaded file in binary read mode
            with open(file_path, 'rb') as f:
                # Update the product.photo field with the file content
                await sync_to_async(product.photo.save)(f"{file.file_id}.jpg", f) 
            await sync_to_async(product.save)() 

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    else:
        await message.answer("❌ Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

@admin_router.message(ProductFSM.waiting_product_description_edit)
async def product_description_edit(message: Message, state: FSMContext):
    description = message.text.strip().capitalize()

    data = await state.get_data()
    product = data.get('product')

    if product:
        product.description = description
        await sync_to_async(product.save)()
        await message.answer(f"✅ Mahsulot tavsifi\n'{description}'\n-ga muvaffaqiyatli yangilandi.")
    else:
        await message.answer("❌ Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")

    await state.set_state(ProductFSM.waiting_editing_product)
    await edit_product(message, state)

# Product deletion
@admin_router.message(StateFilter(ProductFSM.waiting_show_product_for_delete))
async def show_product_for_delete(message: Message, state: FSMContext):
    """
    Handles showing product for deletion of the product.
    """
    await message.answer("O'chirmoqchi bo'lgan mahsulot nomini yuboring yoki tanlang:", reply_markup=(await show_product_list(message)))
    await state.set_state(ProductFSM.waiting_product_delete_confirm)

@admin_router.message(ProductFSM.waiting_product_delete_confirm)
async def product_delete_confirm(message: Message, state: FSMContext):
    """
    Confirm deletion of a product.
    """
    product_name = message.text

    try:
        product = await sync_to_async(Product.objects.get)(name=product_name)

        # Gather product details
        product_info = await format_product_info(product)

        if product.photo and os.path.exists(product.photo.path):
            try:
                input_file = FSInputFile(product.photo.path, filename=os.path.basename(product.photo.path))
                await message.answer_photo(input_file, caption=product_info)
            except Exception as e:
                await message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
                print(f"Error loading photo: {e}")
        else:
            await message.answer(f"Mahsulot rasmi mavjud emas.\n\n{product_info}")
        await state.update_data(product=product)
        await message.answer(f"Ushbu mahsulotni o'chirmoqchimisiz? 🗑", reply_markup=CONFIRM_KEYBOARD)
        await state.set_state(ProductFSM.waiting_product_delete)
    except Product.DoesNotExist:
        await message.answer("Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")   
       
@admin_router.message(StateFilter(ProductFSM.waiting_product_delete))
async def product_delete(message: Message, state: FSMContext):
    """
    Handles the deletion of the product.
    """
    confirm_text = message.text.strip().lower()
 
    data = await state.get_data()
    product = data.get('product')

    if confirm_text in ["ha", "yo'q"]:
        yes = confirm_text == "ha"
        back_button = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅ Bosh menu")]], 
            resize_keyboard=True, 
            # one_time_keyboard=True 
        )
        if yes:
            await sync_to_async(product.delete)()
            await message.answer(f"✅ Mahsulot '{product.name}' muvaffaqiyatli o'chirildi!", reply_markup=back_button)
        else:
            await message.answer(f"❌ Mahsulotning o'chirilishi bekor qilindi ", reply_markup=back_button)
            await state.clear()
            return
    else:
        await message.answer("Iltimos, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
        return
    await state.clear()
   
# Product part ended