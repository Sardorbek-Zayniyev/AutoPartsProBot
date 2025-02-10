from aiogram import Router, F
import os, asyncio
from django.utils import timezone
from django.core.files import File
from django.conf import settings
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message,  FSInputFile, InputMediaPhoto
from django.db import IntegrityError
from asgiref.sync import sync_to_async
from handlers.utils import get_user_from_db
from telegram_app.models import Category, CarBrand, CarModel, Product, Discount

# Create a router for admin handlers
admin_router = Router()


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
    
    # product editing by fields
    waiting_edit_products = State()
    waiting_edit_products_by_category = State()
    waiting_edit_products_by_brand_name = State()
    waiting_edit_products_by_model_name = State()
    waiting_edit_products_by_part_name = State()

    # product searching by fields
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



# Buttons
ADMIN_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya"), KeyboardButton(text="📦 Mahsulot bo'limi")],
        [KeyboardButton(text="🏷️ Chegirmalar bo'limi") ],
    ],
    resize_keyboard=True,
)

DISCOUNT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Chegirma qo'shish"), KeyboardButton(text="✒️ Chegirmalarni tahrirlash")],
        [KeyboardButton(text="✨ Barcha chegirmalarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

CATEGORY_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Kategoriya qo'shish"), KeyboardButton(text="✒️ Kategoriyani tahrirlash")],
        [KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    # one_time_keyboard=True
)

PRODUCT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="✒️ Mahsulotni tahrirlash")],
        [KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True
)

PRODUCT_EDIT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriyasi"), KeyboardButton(text="🔤 Mahsulotni nomi")],
        [KeyboardButton(text="🚘 Mashina brendi"), KeyboardButton(text="🚗 Mashina modeli")],
        [KeyboardButton(text="📦 Mahsulot bo'limi"), KeyboardButton(text="◀️ Bosh menu")],
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

DISCOUNT_ACTIVIVITY_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Faol"), KeyboardButton(text="❌ Nofaol")],
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
    "📦 Mahsulot bo'limi": {
        "text": "Mahsulot boshqaruvi uchun tugmalar:",
        "keyboard": PRODUCT_CONTROLS_KEYBOARD
    },
    "🏷️ Chegirmalar bo'limi": {
        "text": "Chegirmalarni boshqaruvi uchun tugmalar:",
        "keyboard": DISCOUNT_CONTROLS_KEYBOARD
    },
    "◀️ Bosh menu": {
        "text": "Asosiy menuga xush kelibsiz!",
        "keyboard": ADMIN_MAIN_CONTROLS_KEYBOARD,
        "clear_state": True 
    }
}

quality_choices = {
        "Yangi 🆕": "new",
        "Yangilangan 🔄": "renewed",
        "Zo'r 👍": "excellent",
        "Yaxshi ✨": "good",
        "Qoniqarli 👌": "acceptable"
    }

@admin_router.message(F.text.in_(MAIN_CONTROLS_RESPONSES))
async def main_controls_handler(message: Message, state: FSMContext):
    response = MAIN_CONTROLS_RESPONSES[message.text]
    await message.answer(response["text"], reply_markup=response["keyboard"])
    if response.get("clear_state"):
        await state.clear()

@admin_router.callback_query(F.data == "◀️ Bosh menu")
async def main_menu(callback_query: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.answer('Asosiy menuga xush kelibsiz!', reply_markup=ADMIN_MAIN_CONTROLS_KEYBOARD)
    await callback_query.answer()



# Control handlers
@admin_router.message(F.text.in_(("➕ Kategoriya qo'shish", "✒️ Kategoriyani tahrirlash")))
async def category_controls_handler(message: Message, state: FSMContext):
    """
    Handle category management actions (add, edit, delete).
    """
    actions = {
        "➕ Kategoriya qo'shish": (ProductFSM.waiting_get_category, get_category),
        "✒️ Kategoriyani tahrirlash": (ProductFSM.waiting_show_categories_for_edition, show_categories_for_edition),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

@admin_router.message(F.text.in_(("➕ Mahsulot qo'shish", "✒️ Mahsulotni tahrirlash")))
async def product_controls_handler(message: Message, state: FSMContext):
    """
    Handle product management actions (add, edit).
    """
    actions = {
        "➕ Mahsulot qo'shish": (ProductFSM.waiting_show_category, show_category),
        "✒️ Mahsulotni tahrirlash": (ProductFSM.waiting_edit_products, product_edit_options_keyboard),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

async def product_edit_options_keyboard(message: Message, state: FSMContext):
    await message.answer("Mahsulotni qaysi maydoni bo'yicha qidirmoqchisiz tanlang? 👇", reply_markup=PRODUCT_EDIT_CONTROLS_KEYBOARD)

@admin_router.message(F.text.in_(("📂 Kategoriyasi", "🔤 Mahsulotni nomi", "🚘 Mashina brendi", "🚗 Mashina modeli")))
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



# Category part started
# Util functions
@admin_router.callback_query(F.data == "category_buttons")
async def category_buttons_callback(callback_query: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.answer('Kategoriya boshqaruvi uchun tugmalar:', reply_markup=CATEGORY_CONTROLS_KEYBOARD)
    await callback_query.answer()

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
    back_button = KeyboardButton(text="◀️ Bosh menu")

    # Yangi kategoriya tugmalarini yaratish
    category_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )
    return category_keyboard

# async def delete_previous_messages(message: Message, count: int, delay: float = 0.3):
#     """
#     Oldingi xabarlarni o'chiradigan funksiya.
#     :param message: Aiogram Message obyekti
#     :param count: O'chiriladigan xabarlar soni
#     """
#     delete_tasks = []
#     for i in range(1, count + 1):
#         delete_tasks.append(
#             message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - i)
#         )
#     await asyncio.sleep(delay)
#     await asyncio.gather(*delete_tasks, return_exceptions=True)

# async def delete_message_after_delay(message: Message, delay: int):
#     """
#     Xabarni berilgan vaqtdan keyin o'chiradigan funksiya.
#     :param message: Aiogram Message obyekti
#     :param delay: Sekundlarda kutish vaqti
#     """
#     await asyncio.sleep(delay)  
#     await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id) 

# Adding part
@admin_router.message(ProductFSM.waiting_get_category)
async def get_category(message: Message, state: FSMContext):
    """
    Yangi kategoriya qo'shish jarayonini boshlaydi.
    """
    await message.answer("Yangi kategoriya nomini kiriting:")
    await state.set_state(ProductFSM.waiting_save_get_category)

@admin_router.message(ProductFSM.waiting_save_get_category)
async def save_get_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi kiritgan yangi kategoriyani ma'lumotlar bazasiga qo'shadi.
    """
    category_name = message.text.strip()
    if not category_name:
        await message.answer("Kategoriya nomi bo'sh bo'lishi mumkin emas. Admin, qayta kiriting.")
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

# Upadating part
async def get_categories_keyboard(callback_data_prefix: str, state: FSMContext) -> InlineKeyboardMarkup:

    categories = await sync_to_async(list)(Category.objects.all())
    category_buttons = []
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                row.append(InlineKeyboardButton(
                    text=categories[i + j].name, callback_data=f"{callback_data_prefix}:{categories[i + j].id}"))
        category_buttons.append(row)
    # if await state.get_state() == ProductFSM.waiting_show_categories_for_edition:
    #     category_buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"category_buttons"),
    #                              InlineKeyboardButton(text="◀️ Bosh menu", callback_data=f"◀️ Bosh menu")])
    return InlineKeyboardMarkup(inline_keyboard=category_buttons)

async def category_edit_keyboard(category_id):
    edit_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✒️ Nomini tahrirlash", callback_data=f"edit_category:{category_id}"),
         InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_category:{category_id}")],
        [InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"show_categories")]
         ]) 
    return edit_button

async def update_and_clean_messages_category(message: Message, chat_id: int, message_id: int, text: str, category_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=(await category_edit_keyboard(category_id))
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

@admin_router.message(ProductFSM.waiting_show_categories_for_edition)
async def show_categories_for_edition(message: Message, state: FSMContext): 
    await message.answer("Tahrirlanadigan kategoriyani tanlang:", reply_markup=await get_categories_keyboard("category_edit", state))
    
@admin_router.callback_query(F.data == "show_categories")
async def show_categories_menu_for_edition_callback(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(ProductFSM.waiting_show_categories_for_edition)
    await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))

@admin_router.callback_query(F.data.startswith("category_edit:"))
async def category_edit(callback_query: CallbackQuery, state: FSMContext):
  
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if not category:
        await callback_query.answer('❌ Ushbu kategoriya mavjud emas')
        return

    
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id

    await state.update_data(category_id=category_id, chat_id=chat_id, message_id=message_id)
    await callback_query.message.edit_text(f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇", reply_markup=await category_edit_keyboard(category_id))
    await state.set_state(ProductFSM.waiting_save_updated_category)

@admin_router.callback_query(F.data.startswith("edit_category:"))
async def edit_category_callback(callback_query: CallbackQuery, state: FSMContext):
 
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if not category:
        await callback_query.answer('❌ Ushbu kategoriya mavjud emas')
        return

    await callback_query.message.edit_text(f"Tanlangan kategoriya: {category.name}\n\nYangi nomni kiriting: 👇")
    await callback_query.answer()
    await state.update_data(category_id=category_id)
    await state.set_state(ProductFSM.waiting_save_updated_category)

@admin_router.message(ProductFSM.waiting_save_updated_category)
async def save_updated_category(message: Message, state: FSMContext):
  
    new_category_name = message.text.strip().title()

    if not new_category_name:
        await message.answer("Kategoriya nomi bo'sh bo'lishi mumkin emas. Admin, qayta kiriting.👇")
        return
    
    if new_category_name.isdigit():
        await message.answer("❌ Kategoriya nomifaqat raqamlardan iborat bo‘lishi mumkin emas. Admin, boshqa nom kiriting!👇")
        return

    data = await state.get_data()
    chat_id, message_id, category_id = data.get("chat_id"), data.get("message_id"), data.get("category_id")


    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if category.name == new_category_name:
        await message.answer(f"⚠️ '{new_category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom kiriting.")
        return
    
    try:
        category.name = new_category_name
        await sync_to_async(category.save)()
        await message.answer(f"✅ Kategoriya '{new_category_name}' nomiga o'zgartirildi 👆")
        
        text = f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇"
        await update_and_clean_messages_category(message, chat_id, message_id, text, category_id )
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Kategoriya nomini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_router.callback_query(F.data.startswith("delete_category"))
async def delete_category_callback(callback_query: CallbackQuery, state: FSMContext):
 
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    await state.update_data(category_id=category.id)
    await callback_query.message.edit_text(f"'{category.name}' kategoriyasini o‘chirmoqchimisiz?", reply_markup=await confirmation_keyboard(category_id))
    
async def confirmation_keyboard(category_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
              [InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_delete:{category_id}"),
              InlineKeyboardButton(text="❌ Yo‘q", callback_data=f"cancel_delete:{category_id}")],])
    return keyboard

@admin_router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_category(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id, message_id = data.get("chat_id"), data.get("message_id")
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if not category:
        await callback_query.answer(f"⚠️ Kategoriya topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    try:
        await sync_to_async(category.delete)()  
        await callback_query.answer(f"✅ '{category.name}' kategoriyasi o‘chirildi.")

        if message_id and chat_id:
            await callback_query.bot.delete_message(chat_id=chat_id, message_id=callback_query.message.message_id)
            for msg_id in range(callback_query.message.message_id, message_id, -1):
                await callback_query.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            await callback_query.message.answer("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))
        else:
            await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))
        await state.clear()
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Kategoriya o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_router.callback_query(F.data.startswith("cancel_delete:"))
async def cancel_delete_category(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id, message_id = data.get("chat_id"), data.get("message_id")
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()
    
    if not category:
        await callback_query.answer(f"⚠️ Kategoriya topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇", reply_markup=await category_edit_keyboard(category_id))

    if message_id and chat_id:
        text = f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇"
        await update_and_clean_messages_category(callback_query.message, chat_id, message_id, text, category_id )

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

# Adding
@admin_router.message(ProductFSM.waiting_show_category)
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

@admin_router.message(ProductFSM.waiting_set_category)
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

@admin_router.message(ProductFSM.waiting_show_car_brand)
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

@admin_router.message(ProductFSM.waiting_set_car_brand)
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

@admin_router.message(ProductFSM.waiting_show_car_model)
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

@admin_router.message(ProductFSM.waiting_set_car_model)
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

@admin_router.message(ProductFSM.waiting_for_part_name)
async def set_part_name(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    await state.update_data(part_name=part_name)
    await message.answer("Narxni kiriting (so'mda):")
    await state.set_state(ProductFSM.waiting_for_price)

@admin_router.message(ProductFSM.waiting_for_price)
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

@admin_router.message(ProductFSM.waiting_for_availability)
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
 
@admin_router.message(ProductFSM.waiting_for_stock)
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

@admin_router.message(ProductFSM.waiting_for_set_quality)
async def set_quality(message: Message, state: FSMContext):
    selected_quality = message.text.strip()

    if selected_quality in quality_choices:
        await state.update_data(quality=quality_choices[selected_quality])
        await message.answer("Mahsulotning rasmini yuboring:")
        await state.set_state(ProductFSM.waiting_for_photo)
    else:
        await message.answer("Admin, faqat ko'rsatilgan sifatlardan tanlang.")

@admin_router.message(ProductFSM.waiting_for_photo)
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

@admin_router.message(ProductFSM.waiting_for_description)
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

#Edit products
#Util functions
# async def format_product_info(product):
#     """
#     Format product details for display.
#     """
#     quality_choices = {
#         "new": "Yangi 🆕 ",
#         "renewed": "Yangilangan 🔄 ",
#         "excellent": "Zo'r 👍  ",
#         "good": "Yaxshi ✨",
#         "acceptable": "Qoniqarli 👌"
#     }
#     category_name = await sync_to_async(lambda: product.category.name)()
#     brand_name = await sync_to_async(lambda: product.car_brand.name)()
#     model_name = await sync_to_async(lambda: product.car_model.name)()


#     return (
#     f"🛠 <b>Mahsulot nomi: </b> {product.name}\n"
#     f"📦 <b>Kategoriyasi:</b> {category_name}\n"
#     f"🏷 <b>Brandi:</b> {brand_name}\n"
#     f"🚘 <b>Modeli:</b> {model_name}\n"
#     f"💲 <b>Narxi:</b> {product.price} so'm\n"
#     f"📊 <b>Mavjudligi:</b> "
#     f"{(
#         'Sotuvda yo‘q' if not product.available else 
#         f'Sotuvda qolmadi.' if product.available_stock == 0 else 
#         f'Sotuvda <b>{product.available_stock}</b> ta qoldi' if product.available_stock < 20 else 
#         f'Sotuvda <b>{product.available_stock}</b> ta bor'
#     )}\n"    
#     f"🌟 <b>Holati:</b> {quality_choices[product.quality]}\n"
#     f"📝 <b>Tavsifi</b>: {product.description or 'Yo\'q'}\n"
# )

async def format_product_info(product):
    """
    Format product details for display.
    """
    quality_choices = {
        "new": "Yangi 🆕",
        "renewed": "Yangilangan 🔄",
        "excellent": "Zo'r 👍",
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

async def send_category_keyboard(message: Message, prefix: str, state: FSMContext):
    keyboard = await get_categories_keyboard(callback_data_prefix=f"{prefix}_first_page", state=state)
    await message.answer("Kategoriyalar:", reply_markup=keyboard)

async def fetch_products(category_id: int):
    filter_params = {"category_id": category_id, "available": True}
    return await sync_to_async(list)(Product.objects.filter(**filter_params))

async def fetch_object(model, **filter_kwargs):
    try:
        return await sync_to_async(model.objects.get)(**filter_kwargs)
    except model.DoesNotExist:
        return None

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

async def handle_search_results(message: Message, products, state: FSMContext):
    if not products:
        await message.answer("Mahsulot Topilmadi")
        return
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    total_pages = ((len(products_with_numbers) + 9) // 10)
    await display_products_page(1, message, products_with_numbers, None, total_pages , 10, "search", state)

async def handle_product_page(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
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

async def handle_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    _, category_id, page_num = callback_query.data.split(':')
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
            pagination_buttons.append(InlineKeyboardButton(
                text="⬅️", callback_data=f"{callback_prefix}_other_pages:{category_id}:{page_num - 1}"))

        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))

        if page_num < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="➡️", callback_data=f"{callback_prefix}_other_pages:{category_id}:{page_num + 1}"))
    else:
        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))
    
    if await state.get_state() == ProductFSM.waiting_edit_products_by_category:
        product_keyboard = InlineKeyboardMarkup(inline_keyboard=[pagination_buttons, [InlineKeyboardButton(text="⬅️ Ortga", callback_data="categories")]])
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
        reply_markup=(await product_keyboard(product_id))
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

@admin_router.callback_query(F.data.in_("delete_message"))
async def callback_message_handlers(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == 'delete_message':
        await callback_query.message.delete()

 
#Edit by category
@admin_router.message(ProductFSM.waiting_edit_products_by_category)
async def get_all_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "all_products", state)

@admin_router.callback_query(F.data == "categories")
async def show_categories(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await get_categories_keyboard(callback_data_prefix="all_products_first_page", state=state))

#Edit by part name
@admin_router.message(ProductFSM.waiting_edit_products_by_part_name)
async def get_all_products_by_part_name(message: Message, state: FSMContext):
    await message.answer("Mahsulotning, ehtiyot qism nomini kiriting: 👇")
    await state.set_state(ProductFSM.waiting_part_name_search)

@admin_router.message(ProductFSM.waiting_part_name_search)
async def search_product_by_part_name(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    products = await sync_to_async(list)(Product.objects.filter(name__icontains=part_name))
    await handle_search_results(message, products, state)

#Edit by car brand_name
@admin_router.message(ProductFSM.waiting_get_car_brand)
async def get_all_products_by_car_brand(message: Message, state: FSMContext):
    car_brands = await sync_to_async(list)(CarBrand.objects.all())
    await send_keyboard_options(message, car_brands, "Mashina brendlarini tanlang yoki kiriting:")
    await state.set_state(ProductFSM.waiting_car_brand_search)

@admin_router.message(ProductFSM.waiting_car_brand_search)
async def search_product_by_car_brand(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()
    car_brand = await fetch_object(CarBrand, name__iexact=car_brand_name)
    if not car_brand:
        await message.answer(f"Kechirasiz, {car_brand_name} brendi topilmadi.")
        return
    products = await sync_to_async(list)(Product.objects.filter(car_brand=car_brand))
    await handle_search_results(message, products, state)

#Edit by car model
@admin_router.message(ProductFSM.waiting_get_car_model)
async def get_all_products_by_car_model(message: Message, state: FSMContext):
    car_models = await sync_to_async(list)(CarModel.objects.all())
    await send_keyboard_options(message, car_models, "Mashina modellerini tanlang yoki kiriting:")
    await state.set_state(ProductFSM.waiting_car_model_search)

@admin_router.message(ProductFSM.waiting_car_model_search)
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

    await handle_search_results(message, products, state)

#...
@admin_router.callback_query(F.data.startswith('all_products_first_page:'))
async def get_all_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, callback_prefix="all_products")

@admin_router.callback_query(F.data.startswith('all_products_other_pages:'))
async def get_all_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_other_pages(callback_query, state, callback_prefix="all_products")

async def product_keyboard(product_id):

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

@admin_router.callback_query(F.data.startswith('product:'))
async def get_single_product(callback_query: CallbackQuery):
    product_id = int(callback_query.data.split(':')[1])
    product = await sync_to_async(Product.objects.filter(id=product_id).first)()

    if not product:
        await callback_query.message.answer("❌ Xatolik: Mahsulot topilmadi.")
        return
    
    product_info = await format_product_info(product)


    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(
                product.photo.path, filename=os.path.basename(product.photo.path))
            await callback_query.message.answer_photo(input_file, parse_mode='HTML', caption=product_info, reply_markup=(await product_keyboard(product_id)))
        
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(parse_mode='HTML' , text=f"Mahsulot rasmi mavjud emas.\n\n{product_info}", reply_markup=(await product_keyboard(product_id)))

    await callback_query.answer()

@admin_router.callback_query(F.data.startswith('field_'))
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

@admin_router.message(ProductFSM.waiting_product_category_edit)
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

@admin_router.message(ProductFSM.waiting_product_brand_edit)
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

@admin_router.message(ProductFSM.waiting_product_model_edit)
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

@admin_router.message(ProductFSM.waiting_product_partname_edit)
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

@admin_router.message(ProductFSM.waiting_product_price_edit)
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
    
@admin_router.message(ProductFSM.waiting_product_availability_edit)
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

@admin_router.message(ProductFSM.waiting_product_stock_edit)
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

@admin_router.message(ProductFSM.waiting_product_quality_edit)
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

@admin_router.message(ProductFSM.waiting_product_photo_edit)
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
        await message.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=await product_keyboard(product.id))

        await message.answer("✅ Mahsulotning yangi rasmi muvaffaqiyatli yangilandi 👆")

        delete_tasks = [message.bot.delete_message(chat_id, msg_id) for msg_id in range(message.message_id, message_id, -1)]
        await asyncio.gather(*delete_tasks, return_exceptions=True)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot rasmini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@admin_router.message(ProductFSM.waiting_product_description_edit)
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
       
@admin_router.message(ProductFSM.waiting_product_delete)
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

#Discount



class DiscountFSM(StatesGroup):
    #add
    waiting_discount_add = State()
    waiting_discount_percentage = State()
    waiting_discount_start_date = State()
    waiting_discount_end_date = State()
    waiting_discount_name = State()
    waiting_discount_name_input = State()
    waiting_discount_activity = State()
    #edit
    waiting_get_all_discounts = State ()
    waiting_edit_discounts_by_name = State()
    waiting_edit_discounts_by_name_search = State()
    waiting_discount_edit_percentage = State()
    waiting_discount_edit_start_date = State()
    waiting_discount_edit_end_date = State()
    waiting_discount_edit_name = State()
    waiting_discount_edit_activity = State()
    waiting_discount_delete = State()

#Discount part started
@admin_router.message(F.text.in_(("➕ Chegirma qo'shish", "✒️ Chegirmalarni tahrirlash", "✨ Barcha chegirmalarni ko'rish")))
async def discount_controls_handler(message: Message, state: FSMContext):
    """
    Handle discount management actions (add, edit).
    """
    actions = {
        "➕ Chegirma qo'shish": (DiscountFSM.waiting_discount_add, add_discount),
        "✒️ Chegirmalarni tahrirlash": (DiscountFSM.waiting_edit_discounts_by_name, get_all_discounts_by_name),
        "✨ Barcha chegirmalarni ko'rish": (DiscountFSM.waiting_get_all_discounts, get_all_discounts),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#adding part
@admin_router.message(DiscountFSM.waiting_discount_add)
async def add_discount(message: Message, state: FSMContext):
    """
    Chegirma yaratishni boshlash.
    """
    discount_template = (
        "📝 *Chegirma yaratish quyidagi tartibda bo'ladi: 👇*\n\n"
        "📉 *Miqdori (%)da:* \n"
        "📅🕙 *Boshlanish sanasi va soati:* \n"
        "📅🕛 *Tugash sanasi va soati:* \n"
        "📝 *Chegirma nomi:*\n"
        "✅ *Faollik:* \n\n"
        "Chegirma yaratish uchun kerakli ma'lumotlarni kiriting!"
    )

    await message.answer(text=discount_template, parse_mode='Markdown')

    try:
        await message.answer("Chegirma miqdorini kiriting (masalan, 10 yoki 15.5):")
        await state.set_state(DiscountFSM.waiting_discount_percentage)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma qo'shishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@admin_router.message(DiscountFSM.waiting_discount_percentage)
async def set_discount_percentage(message: Message, state: FSMContext):
    """
    Chegirma miqdorini qabul qilish va saqlash.
    """
    try:
        percentage = float(message.text.strip())
        if not (0 < percentage <= 100):
            await message.answer("❌ Chegirma miqdori 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        
        await state.update_data(percentage=percentage)

        await message.answer("Chegirma boshlanish sanasini kiriting (masalan, 2025-05-15 10:00):")
        await state.set_state(DiscountFSM.waiting_discount_start_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")

@admin_router.message(DiscountFSM.waiting_discount_start_date)
async def set_discount_start_date(message: Message, state: FSMContext):
    """
    Chegirma boshlanish sanasini qabul qilish va saqlash.
    """
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)  

        await state.update_data(start_date=start_date)

        await message.answer("Chegirma tugash sanasini kiriting (masalan, 2025-05-25 23:59):")
        await state.set_state(DiscountFSM.waiting_discount_end_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")

@admin_router.message(DiscountFSM.waiting_discount_end_date)
async def set_discount_end_date(message: Message, state: FSMContext):
    """
    Chegirma tugash sanasini qabul qilish.
    """
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)  

        await state.update_data(end_date=end_date)
        await message.answer("Chegirma faolligini tanlang. (Faol/Nofaol) 👇", reply_markup=DISCOUNT_ACTIVIVITY_KEYBOARD)
        await state.set_state(DiscountFSM.waiting_discount_activity)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")

@admin_router.message(DiscountFSM.waiting_discount_activity)
async def set_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        isactive = activity == "✅ Faol"
        await state.update_data(isactive=isactive)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Nom kiritish", callback_data="enter_name")],
            [InlineKeyboardButton(text="O'tkazib yuborish", callback_data="skip_name")]
        ])

        await message.answer("Chegirma nomini kiriting yoki o'tkazib yuboring:", reply_markup=keyboard)
        await state.set_state(DiscountFSM.waiting_discount_name)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")
 
@admin_router.callback_query(DiscountFSM.waiting_discount_name)
async def process_discount_name(callback_query: CallbackQuery, state: FSMContext):
    """
    Chegirma nomini qabul qilish yoki o'tkazib yuborish.
    """
    action = callback_query.data

    if action == "enter_name":
        await callback_query.message.answer("Chegirma nomini kiriting:")
        await callback_query.answer()
        await state.set_state(DiscountFSM.waiting_discount_name_input)
    elif action == "skip_name":
        await state.update_data(name=None)
        await callback_query.answer()
        await save_discount(callback_query, state)

@admin_router.message(DiscountFSM.waiting_discount_name_input)
async def set_discount_name(message: Message, state: FSMContext):
    """
    Chegirma nomini qabul qilish va saqlash.
    """
    name = message.text.strip()
    await state.update_data(name=name)

    await save_discount(message, state)

async def save_discount(message, state):
    """
    Chegirma ma'lumotlarini saqlash.
    """
    user = await get_user_from_db(message.from_user.id)

    data = await state.get_data()
    percentage = data.get("percentage")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    isactive = data.get("isactive")
    name = data.get("name")
   
    discount = await sync_to_async(Discount.objects.create)(
        owner=user,
        updated_by=user,
        percentage=percentage,
        start_date=start_date,
        end_date=end_date,
        is_active=isactive,
        name=name,
    )
    text = f"✅ '{discount.name or discount}' Chegirmasi muvaffaqiyatli yaratildi.\n "

    if isinstance(message, CallbackQuery):
        await message.message.answer(text=text, reply_markup=DISCOUNT_CONTROLS_KEYBOARD)
    else:  
        await message.answer(text=text, reply_markup=DISCOUNT_CONTROLS_KEYBOARD)

    await state.update_data(discount_id=discount.id)
# --------------------------------------------------
#Utils
async def format_discount_info(discount):
    return (
        f"📝 Chegirma nomi: *{discount.name}*\n"
        f"📉 Miqrdori (% da): *{int(discount.percentage) if discount.percentage % 1 == 0 else discount.percentage} %* \n"
        f"📅🕙 Boshlanish sanasi va soati: *{discount.start_date_normalize}* \n"
        f"📅🕛Tugash sanasi va soati: *{discount.end_date_normalize}* \n"
        f"✨ Faollik: *{'Faol ✅' if discount.is_active else 'Muddati oʻtgan ❌'}* \n\n"
    )

async def discount_keyboard(discount_id):

    fields = ['Miqdori', 'Boshlanish sanasi', 'Nomi', 'Tugash sanasi','Faolligi']

    keyboard = [[InlineKeyboardButton(text="Tahrirlash uchun tanlang 👇", callback_data="noop")]]
    for i in range(0, len(fields), 2):
        row = [
            InlineKeyboardButton(text=fields[i], callback_data=f"dicount_field_{fields[i]}:{discount_id}")
        ]
        if i + 1 < len(fields): 
            row.append(InlineKeyboardButton(text=fields[i + 1], callback_data=f"dicount_field_{fields[i+1]}:{discount_id}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🗑 Chegirmani o'chirish", callback_data=f"dicount_field_deletediscount:{discount_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Bosh menu", callback_data="◀️ Bosh menu"), InlineKeyboardButton(text="❌ Ushbu xabarni o'chirish", callback_data="delete_message")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def handle_discount_search_results(message: Message, discounts, state: FSMContext):
    if not discounts:
        await message.answer("❌ Chegirma topilmadi.")
        return
    discounts_with_numbers = [(index + 1, discount) for index, discount in enumerate(discounts)]
    total_pages = ((len(discounts_with_numbers) + 9) // 10)
    await display_discount_page(1, message, discounts_with_numbers, None, total_pages , 10, "search", state)

async def display_discount_page(page_num, callback_query_or_message, discounts_with_numbers, discount_id, total_pages, discounts_per_page, callback_prefix, state):
    start_index = (page_num - 1) * discounts_per_page
    end_index = min(start_index + discounts_per_page, len(discounts_with_numbers))
    page_discounts = discounts_with_numbers[start_index:end_index]

    message_text = (
        f"🔍 Umumiy natija: {len(discounts_with_numbers)} ta chegirmalar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, discount in page_discounts:
        message_text += f"{number}. {discount.name}\n"

    discount_buttons = []
    row = []
    for number, discount in page_discounts:
        row.append(InlineKeyboardButton(text=str(number), callback_data=f"discount:{discount.id}"))
        if len(row) == 5:
            discount_buttons.append(row)
            row = []

    if row:
        discount_buttons.append(row)

    pagination_buttons = []

    if total_pages > 1:
        if page_num > 1:
            pagination_buttons.append(InlineKeyboardButton(
                text="⬅️", callback_data=f"{callback_prefix}_other_pages:{discount_id}:{page_num - 1}"))

        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))

        if page_num < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="➡️", callback_data=f"{callback_prefix}_other_pages:{discount_id}:{page_num + 1}"))
    else:
        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))
    
  
    keyboard = InlineKeyboardMarkup(inline_keyboard=discount_buttons + [pagination_buttons])
    
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )

async def update_and_clean_messages_discount(message: Message, chat_id: int, message_id: int, text: str, discount_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=(await discount_keyboard(discount_id))
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

# --------------------------------------------------
#search all discounts
@admin_router.message(DiscountFSM.waiting_get_all_discounts)
async def get_all_discounts(message: Message, state: FSMContext):
    discounts = await sync_to_async(list)(Discount.objects.all())
    await handle_discount_search_results(message, discounts, state)

#search discount by name
@admin_router.message(DiscountFSM.waiting_edit_discounts_by_name)
async def get_all_discounts_by_name(message: Message, state: FSMContext):
    await message.answer("Chegirmaning nomini kiriting: 👇")
    await state.set_state(DiscountFSM.waiting_edit_discounts_by_name_search)

@admin_router.message(DiscountFSM.waiting_edit_discounts_by_name_search)
async def search_discount_by_name(message: Message, state: FSMContext):
    name = message.text.strip().title()
    discounts = await sync_to_async(list)(Discount.objects.filter(name__icontains=name))
    await handle_discount_search_results(message, discounts, state)

#show single discount
@admin_router.callback_query(F.data.startswith('discount:'))
async def get_single_discount(callback_query: CallbackQuery):
    discount_id = int(callback_query.data.split(':')[1])
    discount = await sync_to_async(Discount.objects.filter(id=discount_id).first)()

    if not discount:
        await callback_query.message.answer("❌ Xatolik: Chegirma topilmadi.")
        await callback_query.answer()
        return
    
    discount_info = await format_discount_info(discount)

    try:
        await callback_query.message.answer(text=discount_info, parse_mode='Markdown', reply_markup=(await discount_keyboard(discount_id)))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Discountni yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    await callback_query.answer()

#...
@admin_router.callback_query(F.data.startswith('dicount_field_'))
async def discount_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[2]
    discount_id = int(callback_query.data.split(":")[1])

    user = await get_user_from_db(callback_query.from_user.id)
    discount = await sync_to_async(Discount.objects.filter(id=discount_id).first)()
    if not discount:
        await callback_query.answer("❌ Xatolik: Chegirma topilmadi.")
        return
    
    field_actions = {
        "Miqdori":              (DiscountFSM.waiting_discount_edit_percentage),
        "Boshlanish sanasi":    (DiscountFSM.waiting_discount_edit_start_date),
        "Nomi":                 (DiscountFSM.waiting_discount_edit_name),
        "Tugash sanasi":        (DiscountFSM.waiting_discount_edit_end_date),
        "Faolligi":             (DiscountFSM.waiting_discount_edit_activity), 
        "deletediscount":       (DiscountFSM.waiting_discount_delete),
    }   
        
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, mahsulotni kategoriya bo‘limidan qaytadan tanlang.")
        return
    
    await state.update_data(message_id=message_id, chat_id=chat_id, discount=discount, user=user)

    next_state = field_actions[field]
    await state.set_state(next_state)



    if field == "deletediscount":
        await callback_query.message.answer(f"Ushbu chegirmani o‘chirmoqchimisiz? 🗑", reply_markup=CONFIRM_KEYBOARD)
    elif field == "Faolligi":
        await callback_query.message.answer(f"{discount} chegirmasining yangi {field.lower()}ni tanlang:", reply_markup=DISCOUNT_ACTIVIVITY_KEYBOARD)
    else:
        await callback_query.message.answer(f"{discount} chegirmasining yangi {field.lower()}ni kiriting:", reply_markup=ReplyKeyboardRemove())

    await callback_query.answer()

@admin_router.message(DiscountFSM.waiting_discount_edit_percentage)
async def edit_discount_percentage(message: Message, state: FSMContext):
    """
    Chegirma miqdorini tahrirlash.
    """
    try:
        percentage = float(message.text.strip())
        if not (0 < percentage <= 100):
            await message.answer("❌ Chegirma miqdori 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return

        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')

        if discount:
            discount.percentage = percentage
            discount.updated_by = user
            await sync_to_async(discount.save)()

            await message.answer(f"✅ Chegirma miqdori {percentage}% ga yangilandi. 👆")
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma miqdorini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_router.message(DiscountFSM.waiting_discount_edit_start_date)
async def edit_discount_start_date(message: Message, state: FSMContext):
    """
    Chegirma boshlanish sanasini tahrirlash.
    """
    try:
        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        if discount:
            discount.start_date = start_date
            discount.updated_by = user
            await sync_to_async(discount.save)()

            await message.answer(f"✅ Chegirma boshlanish sanasi {start_date.strftime('%Y-%m-%d %H:%M')} ga yangilandi. 👆")
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma boshlanish sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_router.message(DiscountFSM.waiting_discount_edit_end_date)
async def edit_discount_end_date(message: Message, state: FSMContext):
    """
    Chegirma tugash sanasini tahrirlash.
    """
    try:
        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)

        if discount:
            discount.end_date = end_date
            discount.updated_by = user
            await sync_to_async(discount.save)()

            await message.answer(f"✅ Chegirma tugash sanasi {end_date.strftime('%Y-%m-%d %H:%M')} ga yangilandi. 👆")
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma tugash sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_router.message(DiscountFSM.waiting_discount_edit_activity)
async def edit_discount_activity(message: Message, state: FSMContext):
    try:
        activity = message.text.strip()
        if activity in ["✅ Faol", "❌ Nofaol"]:
            isactive = activity == "✅ Faol"

            data = await state.get_data()
            discount = data.get("discount")
            chat_id = data.get("chat_id")
            message_id = data.get("message_id")
            user = data.get('user')

            if discount.is_active == isactive:
                await message.answer(f"❌ Chegirma faolligi o'zi {"nofaol" if activity=='ha' else "faol"} turibdi. 👆")
                return
            
            if discount:
                discount.is_active = isactive
                discount.updated_by = user
                await sync_to_async(discount.save)()
                await message.answer(f"✅ Chegirma {"nofaol" if activity=='ha' else "faol"} bo'ldi. 👆")
                text = await format_discount_info(discount)
                await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
            else:
                await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
        else:
            await message.answer("Admin, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma faolligini  yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_router.message(DiscountFSM.waiting_discount_edit_name)
async def edit_discount_name(message: Message, state: FSMContext):
    """
    Chegirma nomini tahrirlash.
    """
    try:
        name = message.text.strip()
        if name.isdigit():
            await message.answer("❌ Noto'g'ri format. Admin chegirma nomi faqat raqamdan iborat bo'lishi mumkin emas!")
            return
        data = await state.get_data()
        discount = data.get("discount")
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        
        if discount:
            discount.name = name
            discount.updated_by = user
            await sync_to_async(discount.save)()
            await message.answer(f"✅ Chegirma nomi '{name}' ga yangilandi. 👆")
            
            text = await format_discount_info(discount)
            await update_and_clean_messages_discount(message, chat_id, message_id, text, discount.id)
        else:
            await message.answer("❌ Chegirma topilmadi Admin, qayta urinib ko'ring.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirma tugash sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_router.message(DiscountFSM.waiting_discount_delete)
async def discount_delete(message: Message, state: FSMContext):

    confirm_text = message.text.strip().lower()
    data = await state.get_data()

    discount = data.get('discount')
    message_id = data.get('message_id')
    chat_id = data.get('chat_id')

    if not discount:
        await message.answer("❌ Bunday chegirma topilmadi. Admin, qayta urinib ko'ring.")
        await state.clear()
        return

    if confirm_text not in ["ha", "yo'q"]:
        await message.answer("Admin, faqat 'Ha' yoki 'Yo'q' deb javob bering.")
        return
    
    try:
        if confirm_text == "ha":
            await sync_to_async(discount.delete)()

            delete_tasks = [
                message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                for msg_id in range(message.message_id, message_id - 1, -1)
            ]
            await asyncio.gather(*delete_tasks, return_exceptions=True)

            await message.answer(f"✅ Chegirma '{discount.name}' muvaffaqiyatli o'chirildi!", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer(f"❌ Chegirmaning o'chirilishi bekor qilindi.", reply_markup=ReplyKeyboardRemove())

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Chegirmani o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    finally:
        await state.clear()

#Discount part end
