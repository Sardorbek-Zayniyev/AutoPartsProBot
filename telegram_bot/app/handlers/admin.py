from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, Message
from django.db import IntegrityError
from aiogram.filters.state import StateFilter
from asgiref.sync import sync_to_async
from handlers.utils import get_user_from_db
from telegram_app.models import Category, CarBrand, CarModel, Product

# Create a router for admin handlers
admin_router = Router()

# Define FSM for product actions


class ProductFSM(StatesGroup):
    # category
    waiting_adding_category = State()
    waiting_show_category = State()
    waiting_saving_category = State()
    waiting_editing_category = State()
    waiting_updating_category = State()
    waiting_deleting_category = State()
    # product
    waiting_show_category = State()
    waiting_set_category = State()
    waiting_show_car_brand = State()
    waiting_set_car_brand = State()
    waiting_show_car_model = State()
    waiting_set_car_model = State()
    waiting_for_part_name = State()
    waiting_for_price = State()
    waiting_for_availability = State()
    waiting_for_photos = State()
    waiting_for_description = State()
    waiting_editing_product = State()
    waiting_deleting_product = State()

#Buttons
main_controls_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya")],
        [KeyboardButton(text="📦 Mahsulot")],
    ],
    resize_keyboard=True
)
category_controls_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Kategoriya qo'shish")],
        [KeyboardButton(text="✏️ Kategoriyani tahrirlash")],
        [KeyboardButton(text="❌ Kategoriyani o'chirish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ],
    resize_keyboard=True
)
product_controls_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish")],
        [KeyboardButton(text="✏️ Mahsulotni tahrirlash")],
        [KeyboardButton(text="❌ Mahsulotni o'chirish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ],
    resize_keyboard=True
)

availability_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)

# Main control handlers
@admin_router.message(lambda message: message.text in ["📂 Kategoriya", "📦 Mahsulot", "🔙 Orqaga"])
async def main_controls_handler(message: Message):
    if message.text == "📂 Kategoriya":
        await message.answer("Kategoriya boshqaruvi uchun tugmalar:", reply_markup=category_controls_keyboard)
    elif message.text == "📦 Mahsulot":
        await message.answer("Mahsulot boshqaruvi uchun tugmalar:", reply_markup=product_controls_keyboard)
    elif message.text == "🔙 Orqaga":
        await message.answer("Asosiy boshqaruvga qaytildi:", reply_markup=main_controls_keyboard)



@admin_router.message(lambda message: message.text == "⬅ Orqaga")
async def back_to_menu(message: types.Message):
    await message.answer("Asosiy menuga xush kelibsiz!", reply_markup=main_controls_keyboard)

# Category part started
@admin_router.message(lambda message: message.text in ["➕ Kategoriya qo'shish", "✏️ Kategoriyani tahrirlash", "❌ Kategoriyani o'chirish"])
async def category_controls_handler(message: Message,  state: FSMContext):
    if message.text == "➕ Kategoriya qo'shish":
        await state.set_state(ProductFSM.waiting_adding_category)
        await add_category(message, state)
    elif message.text == "✏️ Kategoriyani tahrirlash":
        await show_categories_for_edition(message, state)
    elif message.text == "❌ Kategoriyani o'chirish":
        await show_categories_for_deletion(message, state)

# Util functions
async def refresh_category_list(message: Message, state: FSMContext,):
    """
    Kategoriyalar ro'yxatini qayta yangilaydi va foydalanuvchiga ko'rsatadi.
    """
    categories = await sync_to_async(lambda: list(Category.objects.all()))()
    if not categories:
        await message.answer("Hozircha kategoriyalar mavjud emas.")
        return

    category_names = [category.name for category in categories]
    buttons = [KeyboardButton(text=name) for name in category_names]
    back_button = KeyboardButton(text="⬅ Orqaga")

    # Yangi kategoriya tugmalarini yaratish
    category_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )

    await message.answer("Kategoriya ro'yxati yangilandi 👇", reply_markup=category_keyboard)

# Adding part
@admin_router.message(StateFilter(ProductFSM.waiting_adding_category))
async def add_category(message: Message, state: FSMContext):
    """
    Yangi kategoriya qo'shish jarayonini boshlaydi.
    """
    await message.answer("Yangi kategoriya nomini kiriting:")
    await state.set_state(ProductFSM.waiting_saving_category)

@admin_router.message(StateFilter(ProductFSM.waiting_saving_category))
async def save_added_category(message: Message, state: FSMContext):
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
        await refresh_category_list(message, state)
    except IntegrityError:
        await message.answer(f"⚠️ '{category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom kiriting.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()

# Upadating part
@admin_router.message(lambda message: message.text == "✏️ Kategoriyani tahrirlash")
async def show_categories_for_edition(message: Message, state: FSMContext):
    """
    Mavjud kategoriyalarni chiqaradi va foydalanuvchini tahrirlash jarayoniga yo'naltiradi.
    """
    categories = await sync_to_async(lambda: list(Category.objects.all()))()
    if not categories:
        await message.answer("Hozircha kategoriyalar mavjud emas. Iltimos, avval kategoriya qo'shing.")
        return

    category_names = [category.name for category in categories]
    buttons = [KeyboardButton(text=name) for name in category_names]
    back_button = KeyboardButton(text="⬅ Orqaga")

    # Kategoriyalarni ikki ustunli formatda chiqarish
    category_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )

    await message.answer("Tahrirlanadigan kategoriyani tanlang yoki nomini kiriting:", reply_markup=category_keyboard)
    await state.set_state(ProductFSM.waiting_editing_category)

@admin_router.message(StateFilter(ProductFSM.waiting_editing_category))
async def update_selected_or_written_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi tanlagan yoki yozgan kategoriya asosida tahrirlash jarayonini boshlaydi.
    """
    selected_category_name = message.text.strip().capitalize()

    # Orqaga tugmasini bosganda
    if selected_category_name == "⬅ Orqaga":
        await state.clear()
        await message.answer("Bosh menyuga qaytdingiz.", reply_markup=main_controls_handler)
        return

    # Ma'lumotlar bazasida kategoriya nomini tekshirish
    category = await sync_to_async(Category.objects.filter(name=selected_category_name).first)()
    if not category:
        await message.answer("Bunday kategoriya topilmadi. Iltimos, ro'yxatdan tanlang.")
        return

    # Kategoriya ma'lumotlarini tahrirlash
    await state.update_data(category_id=category.id)
    await message.answer(f"Tanlangan kategoriya: {category.name}\nYangi nomni kiriting:")
    await state.set_state(ProductFSM.waiting_updating_category)

@admin_router.message(StateFilter(ProductFSM.waiting_updating_category))
async def save_selected_or_written_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi kiritgan yangi kategoriya nomini saqlaydi.
    """
    new_category_name = message.text.strip().capitalize()
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
        await refresh_category_list(message, state)
    except IntegrityError:
        await message.answer(f"⚠️ '{new_category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom kiriting.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()
        await message.answer("Bosh menyuga qaytishingiz mumkin.", reply_markup=main_controls_handler)

# Deleting part
@admin_router.message(lambda message: message.text == "❌ Kategoriyani o'chirish")
async def show_categories_for_deletion(message: Message, state: FSMContext):
    """
    Mavjud kategoriyalarni chiqaradi va foydalanuvchini o'chirish jarayoniga yo'naltiradi.
    """
    categories = await sync_to_async(lambda: list(Category.objects.all()))()
    if not categories:
        await message.answer("Hozircha kategoriyalar mavjud emas. Iltimos, avval kategoriya qo'shing.")
        return

    category_names = [category.name for category in categories]
    buttons = [KeyboardButton(text=name) for name in category_names]
    back_button = KeyboardButton(text="⬅ Orqaga")

    # Kategoriyalarni ikki ustunli formatda chiqarish
    category_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )

    await message.answer("O'chirmoqchi bo'lgan kategoriyani tanlang yoki nomini kiriting:", reply_markup=category_keyboard)
    await state.set_state(ProductFSM.waiting_deleting_category)

@admin_router.message(StateFilter(ProductFSM.waiting_deleting_category))
async def delete_selected_or_written_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi tanlagan yoki yozgan kategoriyani o'chiradi.
    """
    selected_category_name = message.text.strip().capitalize()

    # Orqaga tugmasini bosganda
    if selected_category_name == "⬅ Orqaga":
        await state.clear()
        await message.answer("Bosh menyuga qaytdingiz.", reply_markup=main_controls_handler)
        return

    # Ma'lumotlar bazasida kategoriya mavjudligini tekshirish
    category = await sync_to_async(Category.objects.filter(name=selected_category_name).first)()
    if not category:
        await message.answer("Bunday kategoriya topilmadi. Iltimos, ro'yxatdan tanlang yoki to'g'ri nom kiriting.")
        return

    try:
        # Kategoriyani o'chirish
        await sync_to_async(category.delete)()
        await message.answer(f"✅ '{selected_category_name}' kategoriyasi muvaffaqiyatli o'chirildi!")
        await refresh_category_list(message, state)
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()
        await message.answer("Bosh menyuga qaytishingiz mumkin.", reply_markup=main_controls_handler)
# Category part ended

# Product part started
@admin_router.message(lambda message: message.text in ["➕ Mahsulot qo'shish", "✏️ Mahsulot tahrirlash", "❌ Mahsulotni o'chirish"])
async def product_controls_handler(message: types.Message, state: FSMContext):
    """
    Handle product management actions (add, edit, delete).
    """
    existing_user = await get_user_from_db(message.from_user.id)

    if not (existing_user and existing_user.role == 'Admin'):
        await message.answer("Sizda bu amalni bajarish uchun ruxsat yo'q.")
        return

    action = message.text
    if action == "➕ Mahsulot qo'shish":
        await state.set_state(ProductFSM.waiting_show_category)
        await show_category(message, state)
    elif action == "✏️ Mahsulot tahrirlash":
        await state.set_state(ProductFSM.waiting_editing_product)
        await message.answer("Tahrirlamoqchi bo'lgan mahsulot ID yoki nomini yuboring:")
    elif action == "❌ Mahsulotni o'chirish":
        await state.set_state(ProductFSM.waiting_deleting_product)
        await message.answer("O'chirmoqchi bo'lgan mahsulot ID yoki nomini yuboring:")

@admin_router.message(ProductFSM.waiting_show_category)
async def show_category(message: types.Message, state: FSMContext):
    """
    Handles the addition of a new product.
    """
    categories = await sync_to_async(lambda: list(Category.objects.all()))()
    if not categories:
        await message.answer("Hozircha kategoriyalar mavjud emas. Iltimos, avval kategoriya qo'shing.", reply_markup=category_controls_keyboard)
        await add_category(message, state)
        return

    category_names = [category.name for category in categories]
    buttons = [KeyboardButton(text=name) for name in category_names]
    back_button = KeyboardButton(text="⬅ Orqaga")
    # Tugmalarni ikki ustunli klaviaturaga bo'lish
    category_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )
    await message.answer("Qo'shiladigan mahsulotning kategoriyasini tanlang yoki kiriting:", reply_markup=category_keyboard)

    await state.set_state(ProductFSM.waiting_set_category)

@admin_router.message(ProductFSM.waiting_set_category)
async def set_category(message: types.Message, state: FSMContext):
    """
    Handle the selected category and ask for the car brand.
    """
    
    category_name = message.text.strip().capitalize()

    category = await sync_to_async(Category.objects.filter(name=category_name).first)()
    if not category:
        await message.answer("Kiritilgan kategoriya mavjud emas. Iltimos, qaytadan urinib ko'ring.")
        return
    
    await state.update_data(category_id=category.id)
    await message.answer(f"Kategoriya: '{category.name}' tanlandi.")

    await state.set_state(ProductFSM.waiting_show_car_brand)
    await show_car_brand(message, state)

@admin_router.message(ProductFSM.waiting_show_car_brand)
async def show_car_brand(message: types.Message, state: FSMContext):
    """
    Bazadagi barcha CarBrandlarni chiqaruvchi klaviatura.
    """
    car_brands = await sync_to_async(lambda: list(CarBrand.objects.all()))()

    if car_brands:
        brand_names = [brand.name for brand in car_brands]
        buttons = [KeyboardButton(text=name) for name in brand_names]
        back_button = KeyboardButton(text="⬅ Orqaga")

        # Brendlarni ikki ustunli formatda chiqarish
        car_brand_keyboard = ReplyKeyboardMarkup(
            keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)] + [[back_button]],
            resize_keyboard=True
        )
        await message.answer("Endi avtomobil brendini tanlang yoki kiriting:", reply_markup=car_brand_keyboard)

    elif not car_brands:
        await message.answer("Avtomobil brendini kiriting:")

    await state.set_state(ProductFSM.waiting_set_car_brand)

@admin_router.message(ProductFSM.waiting_set_car_brand)
async def set_car_brand(message: types.Message, state: FSMContext):
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

@admin_router.message(ProductFSM.waiting_show_car_model)
async def show_car_model(message: types.Message, state: FSMContext):
    """
    Bazadagi barcha CarModellarni chiqaruvchi klaviatura.
    """
    car_models = await sync_to_async(lambda: list(CarModel.objects.all()))()

    if car_models:
        model_names = [model.name for model in car_models]
        buttons = [KeyboardButton(text=name) for name in model_names]
        back_button = KeyboardButton(text="⬅ Orqaga")

        # Brendlarni ikki ustunli formatda chiqarish
        car_model_keyboard = ReplyKeyboardMarkup(
            keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)] + [[back_button]],
            resize_keyboard=True
        )
        await message.answer("Endi avtomobil modelini tanlang yoki kiriting:", reply_markup=car_model_keyboard)

    elif not car_models:
        await message.answer("Avtomobil modelini kiriting:")

    await state.set_state(ProductFSM.waiting_set_car_model)

@admin_router.message(ProductFSM.waiting_set_car_model)
async def set_car_model(message: types.Message, state: FSMContext):
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

@admin_router.message(ProductFSM.waiting_for_part_name)
async def set_part_name(message: types.Message, state: FSMContext):
    part_name = message.text.strip().title()
    await state.update_data(part_name=part_name)
    await message.answer("Narxni kiriting (so'mda):")
    await state.set_state(ProductFSM.waiting_for_price)

@admin_router.message(ProductFSM.waiting_for_price)
async def set_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        await state.update_data(price=price)
        await message.answer(
            "Mahsulot mavjudmi? (Ha/Yo'q):",
            reply_markup=availability_keyboard
        )        
        await state.set_state(ProductFSM.waiting_for_availability)
    except ValueError:
        await message.answer("Iltimos, narxni to'g'ri formatda kiriting (faqat raqam).")

@admin_router.message(ProductFSM.waiting_for_availability)
async def set_availability(message: types.Message, state: FSMContext):
    availability = message.text.strip().lower()
    if availability in ["ha", "yo'q"]:
        available = availability == "ha"
        await state.update_data(available=available)
        await message.answer("Mahsulot haqida qisqacha tavsif yozing:")
        await state.set_state(ProductFSM.waiting_for_description)
    else:
        await message.answer("Iltimos, faqat 'Ha' yoki 'Yo'q' deb javob bering.")

@admin_router.message(ProductFSM.waiting_for_description)
async def set_description_and_save(message: types.Message, state: FSMContext):
    description = message.text.capitalize()

    data = await state.get_data()

    product = await sync_to_async(Product.objects.create)(
        category_id=data["category_id"],
        car_brand_id=data["car_brand_id"],
        car_model_id=data["car_model_id"],
        name=data["part_name"],
        price=data["price"],
        available=data["available"],
        description=description
    )
    await message.answer(f"Mahsulot '{product.name}' muvaffaqiyatli qo'shildi!", reply_markup=product_controls_keyboard)
    await state.clear()

# Handle product editing
@admin_router.message(ProductFSM.waiting_editing_product)
async def handle_edit_product(message: types.Message, state: FSMContext):
    product_identifier = message.text
    try:
        product = await sync_to_async(Product.objects.get)(id=product_identifier)
        await message.answer(f"Mahsulotni tahrirlash uchun yangi ma'lumotlarni yuboring: {product.part_name}")
        # Further editing logic here
        await state.clear()
    except Product.DoesNotExist:
        await message.answer("Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")

# Handle product deletion
@admin_router.message(ProductFSM.waiting_deleting_product)
async def handle_delete_product(message: types.Message, state: FSMContext):
    product_identifier = message.text
    try:
        product = await sync_to_async(Product.objects.get)(id=product_identifier)
        await sync_to_async(product.delete)()
        await message.answer(f"Mahsulot '{product.part_name}' muvaffaqiyatli o'chirildi!")
        await state.clear()
    except Product.DoesNotExist:
        await message.answer("Bunday mahsulot topilmadi. Iltimos, qayta urinib ko'ring.")
# Product part ended