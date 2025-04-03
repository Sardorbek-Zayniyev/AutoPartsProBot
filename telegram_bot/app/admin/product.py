from aiogram import Router, F
import os, asyncio
from django.core.files import File
from decimal import Decimal
from django.conf import settings
from aiogram.fsm.context import FSMContext
from collections import defaultdict
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message,  FSInputFile, InputMediaPhoto
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_app.models import Category, CarBrand, CarModel, Product
from telegram_bot.app.admin.discount import AdminDiscountFSM
from telegram_bot.app.admin.utils import (
    admin_check_state_data,
    admin_single_item_buttons, 
    admin_delete_confirmation_keyboard, 
    admin_keyboard_back_to_product, 
    admin_keyboard_back_to_product_edit,
    admin_keyboard_back_to_search_by_brand,
    admin_keyboard_back_to_search_by_model,
    admin_keyboard_back_to_parent_or_sub_categories,
    admin_keyboard_back_to_found_results,
    admin_escape_markdown, 
    admin_get_cancel_reply_keyboard,
    admin_skip_inline_button,
    admin_keyboard_get_all_car_brands,
    admin_keyboard_get_all_car_models,
    admin_keyboard_get_new_saved_item,
    admin_keyboard_back_to_users_products,
    admin_keyboard_add_products_to_discount,
    ADMIN_CONFIRM_KEYBOARD, 
    ADMIN_ACTIVITY_KEYBOARD,
    admin_product_not_found_message,
)

admin_product_router = Router()

admin_quality_choices = {
        "Yangi 🆕": "new",
        "Yangilangan 🔄": "renewed",
        "Zo'r 👍": "excellent",
        "Yaxshi ✨": "good",
        "Qoniqarli 👌": "acceptable"
    }

class AdminProductFSM(StatesGroup):
    # Get
    admin_waiting_get_all_products = State ()

    # Add   
    admin_waiting_show_category = State() 
    admin_waiting_set_subcategory = State()
    admin_waiting_set_category = State()
    admin_waiting_show_car_brand = State()
    admin_waiting_set_car_brand = State()
    admin_waiting_show_car_model = State()
    admin_waiting_set_car_model = State()
    admin_waiting_for_set_part_name = State()
    admin_waiting_for_set_price = State()
    admin_waiting_for_set_availability = State()
    admin_waiting_for_set_stock = State()
    admin_waiting_for_show_quality = State()
    admin_waiting_for_set_quality = State()
    admin_waiting_for_set_photo = State()
    admin_waiting_for_set_description = State()
    admin_waiting_product_activity = State()

    
    # Edit by fields
    admin_waiting_choose_field_product_to_search = State()
    admin_waiting_edit_product_by_category = State()
    admin_waiting_edit_product_subcategory = State()
    admin_waiting_edit_product_by_brand_name = State()
    admin_waiting_edit_product_by_model_name = State()
    admin_waiting_edit_product_by_part_name = State()

    # Editing by part_name, car_brand, car_model
    admin_waiting_get_all_products_by_part_name = State()
    admin_waiting_all_products_search_by_part_name = State()

    admin_waiting_get_all_product_by_car_brand_name = State()
    admin_waiting_get_all_product_by_car_brand_name_search = State()

    admin_waiting_get_all_products_by_car_model_name = State()
    admin_waiting_all_products_by_car_model_name_search = State()
    admin_waiting_get_all_car_brands = State()
    admin_waiting_get_all_product_by_car_brand_id = State()

    admin_waiting_get_all_car_models = State()
    admin_waiting_get_all_products_by_car_model_id = State()

    #Editing process 
    admin_waiting_edit_product_category_field = State()
    admin_waiting_edit_product_brand_field = State()
    admin_waiting_edit_product_model_field = State()
    admin_waiting_edit_product_partname_field = State()
    admin_waiting_edit_product_price_field = State()
    admin_waiting_edit_product_availability = State()
    admin_waiting_edit_product_stock = State()
    admin_waiting_edit_product_quality = State()
    admin_waiting_edit_product_photo = State()
    admin_waiting_edit_product_description = State()
    admin_waiting_edit_product_activity = State()

    # Deleting
    admin_waiting_product_delete = State()

#Utils
async def admin_show_parent_categories(message: Message):
    """
    Faqat parent kategoriyalarni ko‘rsatadi.
    """
    categories = await sync_to_async(lambda: list(Category.objects.filter(parent_category__isnull=True).order_by('name')))()

    if not categories:
        await message.answer("Hozircha parent kategoriyalar mavjud emas.")
        return

    builder = ReplyKeyboardBuilder()

    for category in categories:
        builder.button(text=category.name)

    builder.adjust(2)
    cancel_builder = admin_get_cancel_reply_keyboard()
    cancel_builder.attach(builder)

    return cancel_builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def admin_show_subcategories(message: Message, parent_category_id: int):
    """
    Tanlangan parent kategoriya bo‘yicha subkategoriyalarni chiqaradi.
    """
    categories = await sync_to_async(lambda: list(Category.objects.filter(parent_category_id=parent_category_id).order_by('name')))()

    if not categories:
        await message.answer("Bu kategoriyada subkategoriyalar mavjud emas.")
        return

    builder = ReplyKeyboardBuilder()

    for category in categories:
        builder.button(text=category.name)

    builder.adjust(2)
    cancel_builder = admin_get_cancel_reply_keyboard()
    cancel_builder.attach(builder)
    return cancel_builder.as_markup(resize_keyboard=True)

async def admin_get_car_brands_list_reply_keyboard(message: Message):
    """
    CarBrandlarning listini chiqaruvchi klaviatura (Keyboard Builder yordamida).
    """
    car_brands = await sync_to_async(lambda: list(CarBrand.objects.order_by('name')))()

    if not car_brands:
        await message.answer("Hozircha avtomobil brendlari mavjud emas.")
        return None

    builder = ReplyKeyboardBuilder()

    for brand in car_brands:
        builder.add(KeyboardButton(text=brand.name))

    builder.adjust(3, repeat=True)

    cancel_builder = admin_get_cancel_reply_keyboard()
    cancel_builder.attach(builder)

    return cancel_builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def admin_show_car_models_list_reply_keyboard(message: Message, car_models=None, car_brand_id=None):
    """
    Bazadagi barcha CarModellarni chiqaruvchi klaviatura (Keyboard Builder yordamida).
    """
    if not car_models:
        car_brand = await sync_to_async(lambda: CarBrand.objects.filter(id=car_brand_id).prefetch_related('car_models').first())() 
        car_models = car_brand.car_models.all()
        
    builder = ReplyKeyboardBuilder()

    for model in car_models:
        builder.add(KeyboardButton(text=model.name))

    builder.adjust(3, repeat=True)

    cancel_builder = admin_get_cancel_reply_keyboard()
    cancel_builder.attach(builder)


    return cancel_builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def admin_show_quality_type_reply_keyboard():
    """
    Mahsulot sifatini tanlash uchun klaviatura (Keyboard Builder yordamida).
    """
    builder = ReplyKeyboardBuilder()

    for value in admin_quality_choices.keys():
        builder.add(KeyboardButton(text=value))

    builder.adjust(3, repeat=True)

    cancel_builder = admin_get_cancel_reply_keyboard()
    cancel_builder.attach(builder)


    return cancel_builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def admin_get_product_by_id(product_id):
    return await sync_to_async(lambda: Product.objects.select_related(
            "category", "car_brand", "car_model", "owner", "updated_by").filter(id=product_id).first())()

async def admin_format_product_info(product, active=None):
    admin_quality_choices = {
        "new": "Yangi 🆕",
        "renewed": "Yangilangan 🔄",
        "excellent": "Zo'r 👍",
        "good": "Yaxshi ✨",
        "acceptable": "Qoniqarli 👌"
    }

    price_info = await sync_to_async(product.original_and_discounted_price)()

    price_text = (
        f"💰 <b>Asl narxi:</b> <s>{price_info['original_price']} so'm</s>\n"
        f"🤑 <b>Chegirmali narx:</b> {price_info['discounted_price']} so'm 🔥"
        if price_info["discounted_price"]
        else f"💵 <b>Narxi:</b> {price_info['original_price']} so'm"
    )

    availability_text = (
        '❌ Sotuvda yo‘q'
        if not product.available else
        '⚠️ Sotuvda qolmadi.'
        if product.available_stock == 0 else
        f'Sotuvda <b>{product.available_stock}</b> ta qoldi'
        if product.available_stock < 20 else
        f'Sotuvda <b>{product.available_stock}</b> ta bor'
    )
    status_text = None
    if active:
        status = product.status
        rejection_reason_text = product.rejection_reason or "Noma'lum 🤷🏻"
        status_text = {
            "pending": "Ko'rib chiqilmoqda ⏳",
            "approved": "Joylashtirilgan 📌",
            "rejected": f"Rad etilgan 🚫\n📄 <b>Rad etish sababi:</b> {rejection_reason_text}" 
        }.get(status, "Noma’lum")

    owner_name = admin_escape_markdown(product.owner.full_name)
    updated_by_name = admin_escape_markdown(product.updated_by.full_name)

    return (
        f"🛠 <b>Mahsulot nomi:</b> {product.name}\n"
        f"📂 <b>Kategoriya:</b> {product.category.name}\n"
        f"🏷 <b>Brend:</b> {product.car_brand.name}\n"
        f"🚘 <b>Model:</b> {product.car_model.name}\n"
        f"{price_text}\n"  
        f"📊 <b>Mavjudligi:</b> {availability_text}\n"
        f"🌟 <b>Holati:</b> {admin_quality_choices.get(product.quality, 'Noma’lum')}\n"
        f"📝 <b>Tavsif:</b> {product.description or 'Yo‘q'}\n"
        f"⚡️ <b>Aktivligi:</b> {'Faol' if product.is_active else 'Nofaol' }\n"
        f"👤 <b>Yaratgan:</b> <a href='tg://user?id={product.owner.telegram_id}'>{owner_name}</a>\n"
        f"✏️ <b>Oxirgi tahrir:</b> <a href='tg://user?id={product.updated_by.telegram_id}'>{updated_by_name}</a>\n"
        + (f"📢 <b>E'lon holati:</b> {status_text}\n" if status_text else "")
    )

def admin_edit_product_inline_keyboard(product_id):
    fields = ['Kategoriyasi', 'Brandi', 'Modeli', 'Nomi', 'Narxi', 
              'Mavjudligi', 'Soni', 'Holati', 'Rasmi', 'Tavsifi', 'Faolligi']

    builder = InlineKeyboardBuilder()

    builder.button(text="Tahrirlash uchun tanlang 👇", callback_data="noop")

    for i in range(0, len(fields), 2):
        builder.button(text=fields[i], callback_data=f"admin_product_field_{fields[i]}:{product_id}")
        if i + 1 < len(fields):
            builder.button(text=fields[i + 1], callback_data=f"admin_product_field_{fields[i+1]}:{product_id}")

    builder.button(text="🗑 Mahsulotni o'chirish", callback_data=f"admin_product_field_delete:{product_id}")
    builder.adjust(1,2,2,2,2,2,1,1) 
    # builder.adjust(1, *[2] * 5, 1)
    return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_single_item_buttons().inline_keyboard)

async def admin_get_catalog_keyboard(message: Message, callback_data_prefix: str, state: FSMContext, action, retrived_message) -> InlineKeyboardMarkup:  
    data = await state.get_data() or {}
  
    if action == 'parent_category':
        parent_category_dict= data.get('parent_category_dict')
        if not parent_category_dict:
            parent_category_dict = defaultdict(lambda: {"name": "", "products": []})
            parent_categories = await sync_to_async(lambda: list(
                Category.objects.filter(parent_category__isnull=True)
                .order_by("name")
                .values("id", "name")
            ))()

            for category in parent_categories:
                category_id = category["id"]
                parent_category_dict[category_id]["name"] = category["name"]
            await state.update_data(parent_category_dict=parent_category_dict)
                
        data_dict=parent_category_dict
        builder = InlineKeyboardBuilder()
        for item_id, item in data_dict.items():
            builder.button(
                text=item["name"],
                callback_data=f"{callback_data_prefix}:{item_id}"
            )
        builder.adjust(2)
        return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_keyboard_back_to_product_edit().inline_keyboard)
    
    elif action == 'sub_category':
        sub_category_dict = data.get('sub_category_dict')
        if not sub_category_dict:
            parent_category_id = data.get('parent_category_id')
            sub_category_dict = defaultdict(lambda: {"name": "", "products": []})
            categories = await sync_to_async(lambda: list(
            Category.objects.filter(parent_category_id=parent_category_id, products__isnull=False)
            .order_by("name")
            .prefetch_related("products__car_brand", "products__car_model")
            .values('id', 'name', 'products__id', 'products__name', 'products__car_brand__name', 'products__car_model__name')
            ))()
            for product in categories:
                category_id = product["id"]
                sub_category_dict[category_id]["name"] = product["name"]  
                sub_category_dict[category_id]["products"].append({
                    "id": product["products__id"],
                    "name": product["products__name"],
                    "car_brand": product["products__car_brand__name"],
                    "car_model": product["products__car_model__name"],
                })
            await state.update_data(sub_category_dict=sub_category_dict)
        data_dict = sub_category_dict
    elif action == 'car_brand':
        if retrived_message:
            car_brand_dict = None
        else:
            car_brand_dict = data.get('car_brand_dict')
        if not car_brand_dict:
            car_brand_dict = defaultdict(lambda: {"name": "", "products": []})
            car_brands = await sync_to_async(lambda: list(CarBrand.objects.filter(name__icontains=retrived_message, products__isnull=False)
            .order_by("name").prefetch_related('products__car_model')
            .values('id', 'name', 'products__id', 'products__name', 'products__car_model__name')
                ))()
            if not car_brands:
                message = await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\nKiritilgan brend topilmadi. Boshqa nom yozing....")
                await state.update_data(message_ids=message.message_id)
                return
            for product in car_brands:
                car_brand_id = product["id"]
                car_brand_dict[car_brand_id]["name"] = product["name"]  
                car_brand_dict[car_brand_id]["products"].append({
                    "id": product["products__id"],
                    "name": product["products__name"],
                    "car_brand": product["name"],
                    "car_model": product["products__car_model__name"],
                })
            await state.update_data(car_brand_dict=car_brand_dict)
        data_dict=car_brand_dict
    elif action == 'car_model':
        if retrived_message:
            car_model_dict = None
        else:
            car_model_dict = data.get('car_model_dict')
        if not car_model_dict:
            car_model_dict = defaultdict(lambda: {"name": "", "products": []})
            car_models = await sync_to_async(lambda: list(CarModel.objects.filter(name__icontains=retrived_message, products__isnull=False)
            .order_by("name").prefetch_related('products__car_brand')
            .values('id', 'name', 'products__id', 'products__name', 'products__car_brand__name')
                ))()

            if not car_models:
                message = await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\nKiritilgan model topilmadi. Boshqa nom yozing....")
                await state.update_data(message_ids=message.message_id)
                return

            for product in car_models:
                car_model_id = product["id"]
                car_model_dict[car_model_id]["name"] = product["name"]  
                car_model_dict[car_model_id]["products"].append({
                    "id": product["products__id"],
                    "name": product["products__name"],
                    "car_brand": product["products__car_brand__name"],
                    "car_model": product["name"],
                })
            await state.update_data(car_model_dict=car_model_dict)
        data_dict=car_model_dict 
    await state.update_data(data_dict=data_dict)
    
    builder = InlineKeyboardBuilder()
    for item_id, item in data_dict.items():
        builder.button(
            text=item["name"],
            callback_data=f"{callback_data_prefix}:{item_id}"
        )
    builder.adjust(2)
    back_button = InlineKeyboardBuilder()

    if action=='sub_category':
        back_button.button(text='↩️ Orqaga', callback_data='admin_back_to_parent_categories')
        return InlineKeyboardMarkup(inline_keyboard=builder.export() + back_button.export() + admin_keyboard_back_to_product_edit().inline_keyboard)
    else:
        return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_keyboard_back_to_product_edit().inline_keyboard)

async def admin_send_catalog_inline_keyboard(message: Message, prefix: str, state: FSMContext, action, retrived_message=None):
    keyboard = await admin_get_catalog_keyboard(message, callback_data_prefix=f"{prefix}_first_page", state=state, action=action, retrived_message=retrived_message)
    catalog_dict = {
        'parent_category':'asosiy kategoriyalar 📂',
        'sub_category':'sub kategoriyalar 🗂',
        'car_brand':'mashina brendlari',
        'car_model':'mashina modellari',
    }
    data = await state.get_data()
    message_id = data.get("catalog_message_id") if data else None 

    if keyboard:
        text = f"Mahsulotlar biriktirilgan {catalog_dict[action]}:"
        
        if message_id:  
            try:
                await message.bot.edit_message_text(text=text, chat_id=message.chat.id, message_id=message_id, reply_markup=keyboard)
            except:
                new_message = await message.answer(text, reply_markup=keyboard)
                await state.update_data(catalog_message_id=new_message.message_id)
        else:  
            new_message = await message.answer(text, reply_markup=keyboard)
            await state.update_data(catalog_message_id=new_message.message_id)
        
async def admin_handle_search_brand_or_model_result(callback_query: CallbackQuery, items, state: FSMContext, action):
    if not items:
        await callback_query.message.answer(f"❌ Mahsulot {action}lari topilmadi")
        return
    if action == 'brand':
        await state.update_data(admin_brands=items)
    elif action == 'model':
        await state.update_data(admin_models=items)
        
    products_with_numbers = [(index + 1, product) for index, product in enumerate(items)]
    
    total_pages = ((len(products_with_numbers) + 9) // 10)
    await admin_display_fetched_products_list(1, callback_query, products_with_numbers, None, total_pages , 10, f"admin_search_{action}", state)
    
async def admin_handle_search_products_result(callback_query_or_message, products, state: FSMContext, previous_message_id=None):
    if not products:
        text = "❌ Mahsulotlar topilmadi."
        if isinstance(callback_query_or_message, CallbackQuery):
            await callback_query_or_message.message.answer(text)
        else:    
            await callback_query_or_message.answer(text)
        return
    await state.update_data(search_results=products)
    
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    
    total_pages = ((len(products_with_numbers) + 9) // 10)
    if previous_message_id:
        await admin_display_fetched_products_list(1, callback_query_or_message, products_with_numbers, None, total_pages, 10, "admin_search_product", state, previous_message_id)
    else:
        await admin_display_fetched_products_list(1, callback_query_or_message, products_with_numbers, None, total_pages, 10, "admin_search_product", state)

async def admin_handle_get_all_products_by_catalog_first_page(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    item_id = int(callback_query.data.split(':')[1])

    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    data = data.get("data_dict", {})  
    
    item = data.get(item_id)
    if not item:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
        return
    
    products = item["products"]
    
    if not products:
        await callback_query.answer("Mahsulotlar yo‘q.")
        return
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]

    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    current_page = 1

    await admin_display_fetched_products_list(current_page, callback_query, products_with_numbers, item_id, total_pages, products_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_handle_get_all_products_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    if not (data := await admin_check_state_data(state, callback_query)):
        return 

    if callback_prefix == "admin_search_product":
        if len(data_parts) != 2:
            await callback_query.answer("Invalid callback data format.")
            return
        page_num = int(data_parts[1])
        products = data.get("search_results", [])
        if not products:
            await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
            return 
        catalog_id = None  
    elif callback_prefix == "admin_search_brand":
        if len(data_parts) != 2:
            await callback_query.answer("Invalid callback data format.")
            return
        
        page_num = int(data_parts[1])
        products = data.get("admin_brands", [])
        if not products:
            await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
            return 
        catalog_id = None
    elif callback_prefix == "admin_search_model":
        if len(data_parts) != 2:
            await callback_query.answer("Invalid callback data format.")
            return
        
        page_num = int(data_parts[1])
        products = data.get("admin_models", [])
        if not products:
            await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
            return 
        catalog_id = None   
    else:
        if len(data_parts) != 3:
            await callback_query.answer("Invalid callback data format.")
            return
        
        _, catalog_id, page_num = data_parts
        catalog_id = int(catalog_id)
        page_num = int(page_num)

        data = data.get("data_dict", {}) 

        data = data.get(catalog_id)
        if not data:
            await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
            return 
        
        products = data['products'] 
        if not products:
            await callback_query.answer("Mahsulotlar yo‘q.")
            return
    
    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    products_per_page = 10
    total_pages = (len(products_with_numbers) + products_per_page - 1) // products_per_page
    
    await admin_display_fetched_products_list(page_num, callback_query, products_with_numbers, catalog_id, total_pages, products_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_display_fetched_products_list(page_num, callback_query_or_message, item_with_numbers, catalog_id, total_pages, item_per_page, callback_prefix, state, previous_message_id=None):
    start_index = (page_num - 1) * item_per_page
    end_index = min(start_index + item_per_page, len(item_with_numbers))
    page_items = item_with_numbers[start_index:end_index]

    category_state = all_products_state = all_car_brand_state = all_car_model_state = car_brand_state = car_model_state = all_products_by_car_brand_id = all_products_by_car_model_id = products_added_by_user_state = set_product_to_discount = False
    current_state = await state.get_state()
    if not current_state:
        text = "❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang."
        if isinstance(callback_query_or_message, CallbackQuery):
            await callback_query_or_message.answer(text, show_alert=True)
        else:
            await callback_query_or_message.answer(text)  
        return
    
    if current_state == AdminProductFSM.admin_waiting_edit_product_by_category:
        category_state = True
    elif current_state == AdminProductFSM.admin_waiting_get_all_products:
        all_products_state = True
    elif current_state == AdminProductFSM.admin_waiting_get_all_car_brands:
        all_car_brand_state = True
    elif current_state == AdminProductFSM.admin_waiting_get_all_car_models:
        all_car_model_state = True
    elif current_state == AdminProductFSM.admin_waiting_get_all_product_by_car_brand_name_search:
        car_brand_state = True
    elif current_state == AdminProductFSM.admin_waiting_all_products_by_car_model_name_search:
        car_model_state = True
    elif current_state == AdminProductFSM.admin_waiting_get_all_product_by_car_brand_id:
        all_products_by_car_brand_id = True
    elif current_state == AdminProductFSM.admin_waiting_get_all_products_by_car_model_id:
        all_products_by_car_model_id = True
    elif current_state.startswith('AdminUserProductsFSM'):
        products_added_by_user_state = True
    elif current_state == AdminDiscountFSM.admin_waiting_add_product_to_discount:
        set_product_to_discount = True

    if all_car_brand_state:
        message_text = (
            f"🔍 Umumiy natija: {len(item_with_numbers)} ta brend topildi.\n\n"
            f"📜 Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
        )
        
        for number, brand in page_items:
            message_text += f"{number}. *{brand['name']}*\n"
    elif all_car_model_state:
        message_text = (
            f"🔍 Umumiy natija: {len(item_with_numbers)} ta model topildi.\n\n"
            f"📜 Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
        )

        for number, model in page_items:
            message_text += f"{number}. *{model['name']}*\n"
    else:
        if set_product_to_discount:
            message_text = (
                f"🏷️ Mahsulotlarni chegirmaga qo'shish bo'limi\n"
                f"Bir nechta mahsulot tanlash imkoniyati mavjud:\n\n"
                f"🔍 Umumiy natija: {len(item_with_numbers)} ta mahsulotlar topildi.\n\n"
            )
        else:
            message_text = (
                f"✨ Mahsulotlarni ko'rish bo'limi:\n\n"
                f"🔍 Umumiy natija: {len(item_with_numbers)} ta mahsulotlar topildi.\n\n"
            )

        message_text += f"📜 Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"

        for number, product in page_items:
            message_text += f"{number}. _{product['car_brand']}_ : _{product['car_model']}_ — *{product['name']}*\n"

    
    # **Tugmalar yasash**
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()
    for number, item in page_items:
        callback_data = (
            f"admin_selected_car_brand:{item['id']}:none" if all_car_brand_state else
            f"admin_selected_car_model:{item['id']}:none" if all_car_model_state else
            f"admin_selected_product:{item['id']}:users_products" if products_added_by_user_state else
            f"admin_add_product_to_discount:{item['id']}" if set_product_to_discount else
            f"admin_selected_product:{item['id']}:none"
        )
        builder.button(text=str(number), callback_data=callback_data)

    builder.adjust(5)
    
    # Navigatsiya tugmalarini qo'shamiz
    if total_pages > 1:
       
        navigation_buttons = []
        
        if page_num > 1:
            prev_callback = f"{callback_prefix}_other_pages:{page_num - 1}" if callback_prefix in ["admin_search_product", "admin_search_brand", "admin_search_model"] else f"{callback_prefix}_other_pages:{catalog_id}:{page_num - 1}"
            navigation_buttons.append({"text": "⬅️", "callback_data": prev_callback})
        
        navigation_buttons.append({"text": "❌", "callback_data": "admin_delete_message"})
        
        if page_num < total_pages:
            next_callback = f"{callback_prefix}_other_pages:{page_num + 1}" if callback_prefix in ["admin_search_product", "admin_search_brand", "admin_search_model"]  else f"{callback_prefix}_other_pages:{catalog_id}:{page_num + 1}"
            navigation_buttons.append({"text": "➡️", "callback_data": next_callback})
        
        # Navigatsiya tugmalarini qatorga joylashtiramiz
        for btn in navigation_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(navigation_buttons))  # 5 tadan mahsulot tugmalari + navigatsiya qatori
    else:
        pagination.button(text="❌", callback_data="admin_delete_message")
        pagination.adjust(5, 5, 1)  # 5 tadan mahsulot tugmalari + faqat ❌ tugmasi
    
    additional_buttons = (
        admin_keyboard_back_to_parent_or_sub_categories().inline_keyboard if category_state else
        admin_keyboard_back_to_product().inline_keyboard if all_products_state else
        admin_keyboard_back_to_search_by_brand().inline_keyboard if all_car_brand_state else
        admin_keyboard_back_to_search_by_model().inline_keyboard if all_car_model_state else
        admin_keyboard_back_to_found_results('admin_back_to_all_car_brands_result').inline_keyboard +
        admin_keyboard_back_to_search_by_brand().inline_keyboard if all_products_by_car_brand_id else
        admin_keyboard_back_to_found_results('admin_back_to_all_car_models_result').inline_keyboard +
        admin_keyboard_back_to_search_by_model().inline_keyboard if all_products_by_car_model_id else
        admin_keyboard_back_to_found_results('admin_back_to_found_car_brands_result').inline_keyboard + 
        admin_keyboard_back_to_product_edit().inline_keyboard if car_brand_state else
        admin_keyboard_back_to_found_results('admin_back_to_found_car_models_result').inline_keyboard + 
        admin_keyboard_back_to_product_edit().inline_keyboard if car_model_state else
        admin_keyboard_back_to_users_products().inline_keyboard if products_added_by_user_state else      
        admin_keyboard_add_products_to_discount().inline_keyboard if set_product_to_discount else      
        admin_keyboard_back_to_product_edit().inline_keyboard
    )

    product_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export()+ pagination.export() + additional_buttons)

    # **Xabarni yangilash yoki yangi xabar jo‘natish**
    if isinstance(callback_query_or_message, CallbackQuery):
        message = callback_query_or_message.message
        if message.photo: 
            new_message = await message.edit_caption(
                caption=message_text, reply_markup=product_keyboard, parse_mode="Markdown"
            )
        else:  
            new_message = await message.edit_text(
                text=message_text, reply_markup=product_keyboard, parse_mode="Markdown"
            )
    elif previous_message_id:
        chat_id = callback_query_or_message.chat.id
        bot = callback_query_or_message.bot

        msg = await bot.get_messages(chat_id=chat_id, message_ids=previous_message_id)

        if msg.photo: 
            new_message = await bot.edit_message_caption(
                chat_id=chat_id, 
                message_id=previous_message_id, 
                caption=message_text, 
                reply_markup=product_keyboard, 
                parse_mode="Markdown"
            )
        else:  
            new_message = await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=previous_message_id, 
                text=message_text, 
                reply_markup=product_keyboard, 
                parse_mode="Markdown"
            )
    else:
        new_message = await callback_query_or_message.answer(
            text=message_text, reply_markup=product_keyboard, parse_mode="Markdown"
        )
        await state.update_data(search_result_message_id=new_message.message_id)
    
    await state.update_data(message_ids=[new_message.message_id])

async def admin_update_and_clean_message_products(message: Message, chat_id: int, message_id: int, product_info: str, product_id: int, state: FSMContext = None):

    new_message_id = message_id

    try:
        await message.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=product_info,
            parse_mode='HTML',
            reply_markup=admin_edit_product_inline_keyboard(product_id)
        )
    except Exception:
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=product_info,
                parse_mode='HTML',
                reply_markup=admin_edit_product_inline_keyboard(product_id)
            )
        except Exception as e:
            print(f"❌ Mahsulot xabarini yangilashda xatolik: {e}")
            new_message = await message.bot.send_message(
                chat_id=chat_id,
                text=product_info,
                parse_mode='HTML',
                reply_markup=admin_edit_product_inline_keyboard(product_id)
            )
            new_message_id = new_message.message_id
    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )
    await asyncio.gather(*delete_tasks, return_exceptions=True)

    if state:
        await state.update_data(message_id=new_message_id, message_ids=[new_message_id])
        
#1 Get all products
@admin_product_router.message(AdminProductFSM.admin_waiting_get_all_products)
async def admin_get_all_products(message: Message, state: FSMContext):
    products = await sync_to_async(lambda: list(
            Product.objects.select_related('car_brand', 'car_model').order_by('car_brand__name').values('id', 'name', 'car_brand__name', 'car_model__name')))()
    products = [{  "id": product["id"],
                        "name": product["name"],
                        "car_brand": product["car_brand__name"],
                        "car_model": product["car_model__name"]
                    }
                    for product in products]
    await admin_handle_search_products_result(message, products, state)

@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_product_other_pages:'))
async def admin_get_all_products_other_pages_callback(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_get_all_products_other_pages(callback_query, state, callback_prefix="admin_search_product")

# Get single product from page
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_selected_product:'))
async def admin_get_selected_product_callback(callback_query: CallbackQuery, state: FSMContext):    
    product_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    await callback_query.answer()
    
    product = await admin_get_product_by_id(product_id)
    
    if not product:
        if await state.get_state() == AdminProductFSM.admin_waiting_get_all_products:
            await callback_query.message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product())
        else:
            await callback_query.message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return
    
    product_info = await admin_format_product_info(product)
    if action == 'users_products':
        from telegram_bot.app.admin.users_products import admin_user_product_action_keyboard
        keyboard = admin_user_product_action_keyboard(product_id, product.status)
    else:
        keyboard = admin_edit_product_inline_keyboard(product_id)

    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(
                product.photo.path, filename=os.path.basename(product.photo.path))
            sent_message = await callback_query.message.answer_photo(input_file, parse_mode='HTML', caption=product_info, reply_markup=keyboard)
            await state.update_data(message_id=sent_message.message_id)
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}", parse_mode='HTML')
            print(f"Error loading photo: {e}")
    else:
        sent_message = await callback_query.message.answer(parse_mode='HTML', text=f"Mahsulot rasmi mavjud emas.\n\n{product_info}", reply_markup=keyboard)
        await state.update_data(message_id=sent_message.message_id)

# Adding part
@admin_product_router.message(AdminProductFSM.admin_waiting_show_category)
async def admin_select_or_input_category_for_adding_product(message: Message, state: FSMContext):
    """
    Handles the addition of a new product.
    """
    product_template = (
    "📝 Mahsulotni quyidagi maydonlar bo\'yicha to\'ldirishingiz kerak bo\'ladi.👇\n\n"
    "📦 *Kategoriyasi:* \n"
    "🏷 *Brandi:* \n"
    "🚘 *Modeli:* \n"
    "🛠 *Mahsulot nomi:* \n"
    "💲 *Narxi (so\'m):* \n"
    "📊 *Mavjudligi va Soni:*\n"
    "🌟 *Holati:* \n"
    "📝 *Tavsifi:*\n"
    )
    await message.answer(text=product_template, parse_mode='Markdown')
    await message.answer("Mahsulotning mavjud kategoriyasini yozing yoki tanlang 👇", reply_markup=await admin_show_parent_categories(message))
    await state.set_state(AdminProductFSM.admin_waiting_set_category)

@admin_product_router.message(AdminProductFSM.admin_waiting_set_category)
async def admin_set_category_to_product(message: Message, state: FSMContext):
    """
    Foydalanuvchi parent kategoriyani tanlaydi.
    Agar parentning subkategoriyalari bo'lsa, ularni tanlash talab qilinadi.
    Aks holda, parent kategoriya yakuniy kategoriya sifatida qabul qilinadi.
    """
   
    category_name = message.text.strip().title()
    category = await sync_to_async(Category.objects.filter(name=category_name, parent_category__isnull=True).first)()

    if not category:
        await message.reply(
            "❌ Kiritilgan kategoriya mavjud emas. Mavjud kategoriyalardan tanlang 👇", 
            reply_markup=await admin_show_parent_categories(message)
        )
        return

    subcategories = await sync_to_async(lambda: list(Category.objects.filter(parent_category=category)))()

    if subcategories:
        await state.update_data(parent_category_id=category.id)
        await message.reply(f"Ushbu kategoriya tanlandi ✅")
        await message.answer("Endi subkategoriya tanlang 👇", reply_markup=await admin_show_subcategories(message, parent_category_id=category.id))
        await state.set_state(AdminProductFSM.admin_waiting_set_subcategory)
    else:
        await state.update_data(category_id=category.id)
        await message.reply(f"Ushbu kategoriya tanlandi ✅")
        await state.set_state(AdminProductFSM.admin_waiting_show_car_brand)
        await admin_select_or_input_car_brand(message, state)

@admin_product_router.message(AdminProductFSM.admin_waiting_set_subcategory)
async def admin_set_subcategory_to_product(message: Message, state: FSMContext):
    """
    Foydalanuvchi parent kategoriya ichidagi subkategoriya tanlaydi.
    """
    if not (data := await admin_check_state_data(state, message)):
        return 
    subcategory_name = message.text.strip().title()
    parent_category_id = data.get("parent_category_id")

    subcategory = await sync_to_async(Category.objects.filter(name=subcategory_name, parent_category_id=parent_category_id).first)()

    if not subcategory:
        await message.reply(
            "❌ Kiritilgan subkategoriya mavjud emas. Mavjud subkategoriyalardan tanlang 👇", 
            reply_markup=await admin_show_subcategories(message, parent_category_id=parent_category_id)
        )
        return

    await state.update_data(category_id=subcategory.id)
    await message.reply(f"Ushbu subkategoriya tanlandi. ✅")

    await state.set_state(AdminProductFSM.admin_waiting_show_car_brand)
    await admin_select_or_input_car_brand(message, state)

@admin_product_router.message(AdminProductFSM.admin_waiting_show_car_brand)
async def admin_select_or_input_car_brand(message: Message, state: FSMContext):
    """
    Bazadagi barcha CarBrandlarni chiqaruvchi klaviatura.
    """
    has_car_brands = await sync_to_async(CarBrand.objects.exists)()

    if has_car_brands:
        await message.answer("Endi avtomobilning yangi brendini yozing yoki mavjudlaridan tanlang 👇", 
                             reply_markup=await admin_get_car_brands_list_reply_keyboard(message))
    else:
        await message.answer("Yangi avtomobil brendini yozing:")
    await state.set_state(AdminProductFSM.admin_waiting_set_car_brand)

@admin_product_router.message(AdminProductFSM.admin_waiting_set_car_brand)
async def admin_set_car_brand_to_product(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()

    user = await get_user_from_db(message.from_user.id)
    if not user:
        await message.answer("Sizning ma'lumotlaringiz topilmadi. Iltimos, avval ro‘yxatdan o‘ting yoki qaytadan urinib ko‘ring.")
        return
    
    if car_brand_name.isdigit():
      await message.reply("❌ Mashina brendi nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
      return
    
    car_brand = await sync_to_async(lambda: CarBrand.objects.filter(name=car_brand_name).prefetch_related('car_models').first())()

    if car_brand:
        await message.reply(f"Ushbu brend tanlandi. ✅")
        await state.update_data(car_models=car_brand.car_models.all())
        await state.update_data(car_brand_id=car_brand.id)   
    else:
        await state.update_data(new_car_brand_name=car_brand_name)
        await message.reply(f"Yangi avtomobil brend qo‘shildi va tanlandi. ✅")
    
    await state.set_state(AdminProductFSM.admin_waiting_show_car_model)
    await admin_select_or_input_car_model(message, state)

@admin_product_router.message(AdminProductFSM.admin_waiting_show_car_model)
async def admin_select_or_input_car_model(message: Message, state: FSMContext):
    """
    Bazadagi barcha CarModellarni chiqaruvchi klaviatura.
    """
    data = await state.get_data()
    car_models = data.get("car_models") if data else None 

    if car_models:
        await message.answer("Endi avtomobilning yangi modelini yozing yoki tanlang 👇", reply_markup=await admin_show_car_models_list_reply_keyboard(message, car_models))
    elif not car_models:
        await message.reply(f"Hozircha ushbu brendda avtomobil modellari mavjud emas.\nUshbu brendning yangi modelini yozing 👇", reply_markup=ReplyKeyboardRemove())

    await state.set_state(AdminProductFSM.admin_waiting_set_car_model)

@admin_product_router.message(AdminProductFSM.admin_waiting_set_car_model)
async def admin_set_car_model_to_product(message: Message, state: FSMContext):
    car_model_name = message.text.strip().title()
    user = await get_user_from_db(message.from_user.id)
    if not user:
        await message.answer("Sizning ma'lumotlaringiz topilmadi. Iltimos, avval ro‘yxatdan o‘ting yoki qaytadan urinib ko‘ring.")
        return
    if car_model_name.isdigit():
      await message.reply("❌ Mashina modeli nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
      return
    
    data = await state.get_data()
    car_brand_id = data.get("car_brand_id") if data else None 

    car_model = await sync_to_async(CarModel.objects.filter(brand_id=car_brand_id, name=car_model_name).first)()

    if car_model:
        await message.reply(f"Ushbu model tanlandi. ✅")
        await state.update_data(car_model_id=car_model.id)
    else:
        await state.update_data(new_car_model_name=car_model_name)
        await message.reply(f"Yangi model qo'shildi va saqlandi. ✅")

    await message.answer("Endi mahsulotning ehtiyot qismining nomini yozing:", reply_markup=admin_get_cancel_reply_keyboard().as_markup(resize_keyboard=True))
    await state.set_state(AdminProductFSM.admin_waiting_for_set_part_name)

@admin_product_router.message(AdminProductFSM.admin_waiting_for_set_part_name)
async def admin_retrieve_and_assign_part_name_to_product(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    if part_name.isdigit():
      await message.reply("❌ Mahsulot ehtiyot qismi nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
      return
    await state.update_data(part_name=part_name)
    await message.reply("Mahsulotning nomi saqlandi. ✅")
    await message.answer("Endi narxni yozing (so'mda):")
    await state.set_state(AdminProductFSM.admin_waiting_for_set_price)

@admin_product_router.message(AdminProductFSM.admin_waiting_for_set_price)
async def admin_retrieve_and_assign_price_to_product(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        await state.update_data(price=price)
        await message.reply("Mahsulotning narxi saqlandi. ✅")
        await message.answer("Mahsulot mavjudmi? Tanlang (Ha/Yo'q):", reply_markup=ADMIN_CONFIRM_KEYBOARD)        
        await state.set_state(AdminProductFSM.admin_waiting_for_set_availability)
    except ValueError:
        await message.answer("❌ Admin, narxni to'g'ri formatda yozing (faqat musbat raqam).")

@admin_product_router.message(AdminProductFSM.admin_waiting_for_set_availability)
async def admin_retrieve_and_assign_availability_to_product(message: Message, state: FSMContext):
    availability = message.text.strip().lower()
    if availability in ["ha", "yo'q"]:
        available = availability == "ha"
        await state.update_data(available=available)
        await message.reply("Mahsulotning mavjudligi saqlandi. ✅")
        if available:
            await message.answer("Sotuvda qancha mahsulot bor ❔", reply_markup=admin_get_cancel_reply_keyboard().as_markup(resize_keyboard=True))
            await state.set_state(AdminProductFSM.admin_waiting_for_set_stock)
        else:
            await state.update_data(in_stock=0)
            await message.answer("Endi mahsulot holatini tanlang 👇", reply_markup=await admin_show_quality_type_reply_keyboard())
            await state.set_state(AdminProductFSM.admin_waiting_for_set_quality)
    else:
        await message.answer("❌ Admin, faqat 'Ha' yoki 'Yo'q' deb javob bering.", reply_markup=ADMIN_CONFIRM_KEYBOARD)
 
@admin_product_router.message(AdminProductFSM.admin_waiting_for_set_stock)
async def admin_retrieve_and_assign_in_stock_to_product(message: Message, state: FSMContext):
    try:
        in_stock = int(message.text.strip())
        if in_stock > 0:
            await state.update_data(in_stock=in_stock)
            await message.reply("Mahsulotning soni saqlandi. ✅")
            await message.answer("Endi mahsulot holatini tanlang 👇", reply_markup=await admin_show_quality_type_reply_keyboard())
            await state.set_state(AdminProductFSM.admin_waiting_for_set_quality)
        else:
            await message.answer("❌ Admin, mahsulot mavjud bo'lishi uchun 0 dan katta son yozishingiz kerak ‼️\nMahsulot mavjud bo'lmasa mavjudmi deb so'ralganda yo'q deb tanlash kerak.")
    except ValueError:
        await message.answer("Admin, mahsulot sonini to'g'ri formatda yozing (faqat musbat raqam).")

@admin_product_router.message(AdminProductFSM.admin_waiting_for_set_quality)
async def admin_retrieve_and_assign_quality_to_product(message: Message, state: FSMContext):
    selected_quality = message.text.strip()

    if selected_quality in admin_quality_choices:
        await state.update_data(quality=admin_quality_choices[selected_quality])
        await message.reply("Mahsulotning holati saqlandi. ✅", reply_markup=ReplyKeyboardRemove())
        await message.answer("Mahsulotning rasmini yuboring 📸:", reply_markup=admin_skip_inline_button('admin_product_photo'))
        await state.set_state(AdminProductFSM.admin_waiting_for_set_photo)
    else:
        await message.answer("Admin, faqat ko'rsatilgan sifatlardan tanlang.")

@admin_product_router.message(AdminProductFSM.admin_waiting_for_set_photo)
async def admin_retrieve_and_assign_photo_to_product(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Admin, mahsulotning rasmini yuboring (JPG yoki PNG formatda) yoki o'tkazib yuboring.",
                            reply_markup=admin_skip_inline_button('admin_product_photo'))
        return
    else:
        # Get the highest resolution photo and its file_id
        photo = message.photo[-1]
        file_id = photo.file_id
        await state.update_data(photo=file_id)  
        await message.reply("Rasm muvaffaqiyatli qabul qilindi va saqlandi. ✅")
    await message.answer("Mahsulot haqida qisqacha tavsif yozing:", reply_markup=admin_skip_inline_button('admin_product_description'))
    await state.set_state(AdminProductFSM.admin_waiting_for_set_description)

@admin_product_router.callback_query(IsAdminFilter(), F.data == "admin_product_photo_skip_step")
async def admin_product_photo_skip(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("✅ Mahsulot rasm maydoni o‘tkazib yuborildi. Davom etamiz...")
    await state.update_data(photo=None)
    await callback_query.message.answer("Mahsulot haqida qisqacha tavsif yozing:", reply_markup=admin_skip_inline_button('admin_product_description'))
    await state.set_state(AdminProductFSM.admin_waiting_for_set_description)

@admin_product_router.message(AdminProductFSM.admin_waiting_for_set_description)
async def admin_retrieve_and_assign_description_to_product(message: Message, state: FSMContext):
    description = message.text.capitalize()
    await state.update_data(description=description)
    await message.reply("Mahsulot tavsifi saqlandi. ✅")
    await message.answer("Endi mahsulot faolligini tanlang (Faol/Nofaol):", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    await state.set_state(AdminProductFSM.admin_waiting_product_activity)
    
@admin_product_router.callback_query(IsAdminFilter(), F.data == "admin_product_description_skip_step")
async def admin_product_description_skip(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("✅ Mahsulot tavsifi o‘tkazib yuborildi. Davom etamiz...")
    await state.update_data(description=None)
    await callback_query.message.answer("Mahsulot faolligini tanlang (Faol/Nofaol):", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    await state.set_state(AdminProductFSM.admin_waiting_product_activity)
    
@admin_product_router.message(AdminProductFSM.admin_waiting_product_activity)
async def admin_set_product_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        is_active = activity == "✅ Faol"
        await state.update_data(is_active=is_active)
        await admin_save_new_product(message, state)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")

async def admin_save_new_product(message, state):
    if not (data := await admin_check_state_data(state, message)):
        return 
    user = await get_user_from_db(message.from_user.id)
    if not user:
        await message.answer("Sizning ma'lumotlaringiz topilmadi. Iltimos, avval ro‘yxatdan o‘ting yoki qaytadan urinib ko‘ring.")
        return
    
    car_brand_name = data.get("new_car_brand_name")
    if car_brand_name:
        car_brand = await sync_to_async(CarBrand.objects.create)(name=car_brand_name, owner=user, updated_by=user)
        await state.update_data(car_brand_id=car_brand.id)
    
    data = await state.get_data()

    car_model_name = data.get("new_car_model_name")
    if car_model_name:
        car_brand_id = data.get("car_brand_id")
        car_model = await sync_to_async(CarModel.objects.create)(brand_id=car_brand_id, name=car_model_name, owner=user, updated_by=user)
        await state.update_data(car_model_id=car_model.id)

    data = await state.get_data()

    photo_file_id = data.get("photo")
    if photo_file_id:
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
                    description = data["description"],
                    is_active=data['is_active']
                )

        finally:
            # Ensure the temporary file is always deleted
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
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
                    photo=photo_file_id,
                    description = data["description"],
                    is_active=data['is_active']
                )
        
    msg = message.message if isinstance(message, CallbackQuery) else message
    from telegram_bot.app.admin.main_controls import ADMIN_PRODUCT_CONTROLS_KEYBOARD
    await msg.answer(f"✅ Mahsulot '{product.name}' muvaffaqiyatli qo'shildi!", reply_markup=ADMIN_PRODUCT_CONTROLS_KEYBOARD)
    await msg.answer(f"Mahsulot '{product.name}' 👇", reply_markup=admin_keyboard_get_new_saved_item(f'admin_selected_product:{product.id}:none'))

    await state.clear()

# Editing part
#1 Get all parent categories
@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_by_category)
async def admin_display_parent_category_selection_for_edit_product(message: Message, state: FSMContext):
    await admin_send_catalog_inline_keyboard(message, "admin_get_sub_categories", state, 'parent_category')

#2 Get parent_categories's sub_categories
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_get_sub_categories_first_page:'))
async def admin_display_sub_category_selection_for_edit_product(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    try:
        id = int(callback_query.data.split(':')[1])
        await state.update_data(parent_category_id=id)
    except:
        pass
    await admin_send_catalog_inline_keyboard(callback_query.message, "admin_all_products", state, 'sub_category')

#3 Back to parent_categories
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_back_to_parent_categories'))
async def admin_back_to_parent_categories(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await admin_send_catalog_inline_keyboard(message=callback_query.message, prefix="admin_get_sub_categories", state=state, action="parent_category")

# ----------------------------------------------------------------------------------------------------------

#1 Retrieve product car_brand name from user
@admin_product_router.message(AdminProductFSM.admin_waiting_get_all_product_by_car_brand_name)
async def admin_display_car_brand_selection_for_edit_product(message: Message, state: FSMContext):
    await message.answer("Barcha mashina brendlarini ko'rish uchun quyidagi tugmani bosing", 
    reply_markup=InlineKeyboardMarkup(inline_keyboard=admin_keyboard_get_all_car_brands().inline_keyboard +
                                                      admin_keyboard_back_to_product_edit().inline_keyboard))
    sent_message = await message.reply("Mashina brendini topish uchun uning nomini yozib yuboring 👇")
    await state.update_data(admin_search_car_brand_message_id=sent_message.message_id)
    await state.set_state(AdminProductFSM.admin_waiting_get_all_product_by_car_brand_name_search)

#2 Get products page by retrieved car_brand name
@admin_product_router.message(AdminProductFSM.admin_waiting_get_all_product_by_car_brand_name_search)
async def admin_fetch_all_products_by_retrieved_car_brand_name(message: Message, state: FSMContext):
    car_brand_name = message.text.strip().upper()
    await admin_send_catalog_inline_keyboard(message, "admin_all_products", state, 'car_brand', retrived_message=car_brand_name)
    await asyncio.sleep(0.3)
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

#3 Back to found_car_brands
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_back_to_found_car_brands_result'))
async def admin_back_to_found_car_brands_result(callback_query: CallbackQuery, state: FSMContext):
    await admin_send_catalog_inline_keyboard(message=callback_query.message, prefix="admin_all_products", state=state, action="car_brand")

#4 Get all cars brands page
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith(("admin_get_all_car_brands", 'admin_back_to_all_car_brands_result')))
async def admin_get_all_car_brands_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    car_brands = data.get('admin_brands')
    sent_message = data.get('admin_search_car_brand_message_id')
    if sent_message:
        try:
            await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message)
        except:
            pass 
    if not car_brands:
        car_brands = await sync_to_async(lambda: list(CarBrand.objects.filter(products__isnull=False)
        .order_by("name").distinct()
        .values('id', 'name')
            ))()
        if not car_brands:
            message = await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\nKiritilgan brend topilmadi. Boshqa nom yozing....")
            return
    await state.set_state(AdminProductFSM.admin_waiting_get_all_car_brands)
    await admin_handle_search_brand_or_model_result(callback_query, car_brands, state, 'brand')

#5 Get all cars brands other pages
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_brand_other_pages:'))
async def admin_get_all_car_brands_section_keyboard_other_page(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_get_all_products_other_pages(callback_query, state, callback_prefix="admin_search_brand")

#6 Get page selected brand's all products 
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_selected_car_brand:'))
async def admin_get_all_products_selected_car_brand_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    brand_id = int(callback_query.data.split(':')[1])
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    products = data.get('search_results')
    if not products:
        products = await sync_to_async(lambda: list(CarBrand.objects.filter(id=brand_id, products__isnull=False)
        .order_by("name").prefetch_related('products__car_model')
        .values('id', 'name', 'products__id', 'products__name', 'products__car_model__name')
            ))()
        if not products:
            message = await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\nKiritilgan brend bo'yicha mahsulot topilmadi. Boshqa nom yozing....")
            await state.update_data(message_ids=message.message_id)
            return
        products = [{
            "car_brand": product["name"],
            "car_model": product["products__car_model__name"],
            "id": product["products__id"],
            "name": product["products__name"]
        } for product in products]
    await state.set_state(AdminProductFSM.admin_waiting_get_all_product_by_car_brand_id)
    await admin_handle_search_products_result(callback_query, products, state)


#--------------------------------------------------------------------------------------------------------------

#1 Retrieve product car_model name from user
@admin_product_router.message(AdminProductFSM.admin_waiting_get_all_products_by_car_model_name)
async def admin_display_car_model_selection_for_edit_product(message: Message, state: FSMContext):
    await message.answer("Barcha mashina modellarini ko'rish uchun quyidagi tugmani bosing.",
    reply_markup=InlineKeyboardMarkup(inline_keyboard=admin_keyboard_get_all_car_models().inline_keyboard +
                                                      admin_keyboard_back_to_product_edit().inline_keyboard))
    sent_message = await message.reply("Mashina modelini topish uchun uning nomini yozib yuboring 👇")
    await state.update_data(admin_search_car_model_message_id=sent_message.message_id)
    await state.set_state(AdminProductFSM.admin_waiting_all_products_by_car_model_name_search)

#2 Get products page by retrieved car_model name
@admin_product_router.message(AdminProductFSM.admin_waiting_all_products_by_car_model_name_search)
async def admin_fetch_all_products_by_retrieved_car_model_name(message: Message, state: FSMContext):
    car_model_name = message.text.strip().title()
    await admin_send_catalog_inline_keyboard(message, "admin_all_products", state, 'car_model', retrived_message=car_model_name)
    await asyncio.sleep(0.3)
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

#3 Back to found_car_models
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_back_to_found_car_models_result'))
async def admin_back_to_found_car_models_result(callback_query: CallbackQuery, state: FSMContext):
    await admin_send_catalog_inline_keyboard(message=callback_query.message, prefix="admin_all_products", state=state, action="car_model")

#4 Get all car's models page
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith(("admin_get_all_car_models", 'admin_back_to_all_car_models_result')))
async def admin_handler_back_to_reward_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    car_models = data.get('admin_models')
    sent_message = data.get('admin_search_car_model_message_id')
    if sent_message:
        try:
            await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message)
        except:
            pass 
    if not car_models:
        car_models = await sync_to_async(lambda: list(CarModel.objects.filter(products__isnull=False)
        .order_by("name").distinct()
        .values('id', 'name')
            ))()
        if not car_models:
            message = await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\nKiritilgan model topilmadi. Boshqa nom yozing....")
            return
    await state.set_state(AdminProductFSM.admin_waiting_get_all_car_models)
    await admin_handle_search_brand_or_model_result(callback_query, car_models, state, 'model')

#5 Get all cars models other pages
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_model_other_pages:'))
async def admin_get_all_car_models_section_keyboard_other_page(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_get_all_products_other_pages(callback_query, state, callback_prefix="admin_search_model")

#6 Get page selected car_model's all products
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_selected_car_model:'))
async def admin_fetch_products_by_selected_model_callback(callback_query: CallbackQuery, state: FSMContext):
    car_model_id = int(callback_query.data.split(':')[1])
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    products = data.get('search_results')
    if not products:
        products = await sync_to_async(lambda: list(CarModel.objects.filter(id=car_model_id, products__isnull=False)
        .order_by("name").prefetch_related('products__car_brand')
        .values('id', 'name', 'products__id', 'products__name', 'products__car_brand__name')
            ))()
        if not products:
            message = await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\nKiritilgan model bo'yicha mahsulot topilmadi. Boshqa nom yozing....")
            return
        products = [{
            "car_model": product["name"],
            "car_brand": product["products__car_brand__name"],
            "id": product["products__id"],
            "name": product["products__name"]
        } for product in products]
    await state.set_state(AdminProductFSM.admin_waiting_get_all_products_by_car_model_id)
    await admin_handle_search_products_result(callback_query, products, state)
    # await state.clear()

#----------------------------------------------------------------------------------------------

#1 Retrieve product part_name from user
@admin_product_router.message(AdminProductFSM.admin_waiting_get_all_products_by_part_name)
async def admin_retrieve_products_part_name(message: Message, state: FSMContext):
    message = await message.reply("Mahsulotning, ehtiyot qismini nomini yozing...", reply_markup=admin_keyboard_back_to_product_edit())
    await state.update_data(message_ids=message.message_id)
    await state.set_state(AdminProductFSM.admin_waiting_all_products_search_by_part_name)

#2 Get products page by retrieved part_name
@admin_product_router.message(AdminProductFSM.admin_waiting_all_products_search_by_part_name, AdminDiscountFSM.admin_waiting_add_product_to_discount)
async def admin_fetch_all_products_page_by_retrieved_name(message: Message, state: FSMContext):
    part_name = message.text.strip().title()
    data = await state.get_data()
    previous_message_id = data.get("search_result_message_id")  
    
    if part_name:
        products = await sync_to_async(lambda: list(
            Product.objects.filter(name__icontains=part_name)
                    .select_related('car_brand', 'car_model')
                    .values('id', 'name', 'car_brand__name', 'car_model__name')))()
        products = [{"id": product["id"], "name": product["name"], "car_brand": product["car_brand__name"], "car_model": product["car_model__name"]}
                    for product in products]
        
        if previous_message_id:
            try:
                await message.bot.edit_message_text(
                    text="Mahsulotlar qidirilmoqda... ⏳",  
                    chat_id=message.chat.id,
                    message_id=previous_message_id,
                    reply_markup=None
                )
                await asyncio.sleep(0.3)
                await admin_handle_search_products_result(message, products, state, previous_message_id)
            except:
                await admin_handle_search_products_result(message, products, state)
        else:
            await admin_handle_search_products_result(message, products, state)
        await asyncio.sleep(0.3)
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
#----------------------------------------------------------------------------------------------

# First page pagination
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_all_products_first_page:'))
async def admin_get_all_products_by_catalog_first_page_callback(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_get_all_products_by_catalog_first_page(callback_query, state, callback_prefix="admin_all_products")

# Other pages pagination
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_all_products_other_pages:'))
async def admin_get_all_products_by_catalog_other_pages_callback(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_get_all_products_other_pages(callback_query, state, callback_prefix="admin_all_products")

#----------------------------------------------------------------------------------------------

#Product's field editing
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith('admin_product_field_'))
async def admin_product_field_selection_for_edit_callback(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[3]
    product_id = int(callback_query.data.split(":")[1])

    user = await get_user_from_db(callback_query.from_user.id)
    product = await admin_get_product_by_id(product_id)
    
    if not product:
        await callback_query.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return

    if not product.available and field == "Soni":
        await callback_query.answer("📌 Mahsulot hozirda mavjud emas. Avval 'Mavjudligi' ni 'Ha' ga o'zgartiring.", show_alert=True)
        return
    
    field_actions = {
        "Kategoriyasi": (AdminProductFSM.admin_waiting_edit_product_category_field, await admin_show_parent_categories(callback_query.message)),
        "Brandi": (AdminProductFSM.admin_waiting_edit_product_brand_field, await admin_get_car_brands_list_reply_keyboard(callback_query.message)),
        "Modeli": (AdminProductFSM.admin_waiting_edit_product_model_field, await admin_show_car_models_list_reply_keyboard(callback_query.message, None, product.car_brand.id)),
        "Nomi": (AdminProductFSM.admin_waiting_edit_product_partname_field, None),
        "Narxi": (AdminProductFSM.admin_waiting_edit_product_price_field, None), 
        "Mavjudligi": (AdminProductFSM.admin_waiting_edit_product_availability, ADMIN_CONFIRM_KEYBOARD), 
        "Soni": (AdminProductFSM.admin_waiting_edit_product_stock, None), 
        "Holati": (AdminProductFSM.admin_waiting_edit_product_quality, await admin_show_quality_type_reply_keyboard()), 
        "Rasmi": (AdminProductFSM.admin_waiting_edit_product_photo, None),
        "Tavsifi": (AdminProductFSM.admin_waiting_edit_product_description, None),
        "Faolligi": (AdminProductFSM.admin_waiting_edit_product_activity, ADMIN_ACTIVITY_KEYBOARD),
        "delete": (AdminProductFSM.admin_waiting_product_delete, None),
    }

    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, mahsulotni qaytadan yuklang.",
                                            reply_markup=admin_keyboard_back_to_product_edit())
        return
    
    await state.update_data(message_id=message_id, chat_id=chat_id, product=product, user=user)

    next_state, markup = field_actions[field]
    await state.set_state(next_state)
    if field == "delete":
        if callback_query.message.content_type == "photo":
            await callback_query.message.edit_caption(
                caption=f"{product.name}\nUshbu mahsulotni o‘chirmoqchimisiz? 🗑",
                reply_markup=admin_delete_confirmation_keyboard("admin_product", product_id)
            )
        else:
            await callback_query.message.edit_text(
                text=f"{product.name}\nUshbu mahsulotni o‘chirmoqchimisiz? 🗑",
                reply_markup=admin_delete_confirmation_keyboard("admin_product", product_id)
            )
    elif markup:
        await callback_query.message.answer(f"{product} mahsulotining yangi {field.lower()}ni tanlang yoki yozing:", 
                                    reply_markup=markup) 
    else:
        await callback_query.message.answer(f"{product} mahsulotining yangi {field.lower()}ni yozing:", reply_markup=ReplyKeyboardRemove())
    await callback_query.answer()

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_category_field)
async def admin_product_category_edit(message: Message, state: FSMContext):
    category_name = message.text.strip().title()
    if not category_name:
        await message.answer("❌ Kategoriya nomi bo‘sh bo‘lishi mumkin emas. Admin, mavjud kategoriya nomini yozing!")
        return

    if category_name.isdigit():
      await message.answer("❌ Kategoriya nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
      return

    data = await state.get_data()
    product = data.get("product") if data else None 
    
    if not product:
        await message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return

    try:
        category = await sync_to_async(Category.objects.filter(name=category_name, parent_category__isnull=True).first)()
        if not category:
            await message.reply(
            "❌ Kiritilgan kategoriya mavjud emas. Mavjud kategoriyalardan tanlang 👇", 
            reply_markup=await admin_show_parent_categories(message))
            return
        await state.update_data(parent_category_id=category.id)
        await message.answer("Endi subkategoriya tanlang 👇", reply_markup=await admin_show_subcategories(message, parent_category_id=category.id))
        await state.set_state(AdminProductFSM.admin_waiting_edit_product_subcategory)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot kategoriyasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")
        
@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_subcategory)
async def admin_edit_subcategory_to_product(message: Message, state: FSMContext):
    """
    Foydalanuvchi parent kategoriya ichidagi subkategoriya tanlaydi.
    """
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return
    
    subcategory_name = message.text.strip().title()
    parent_category_id = data.get("parent_category_id")
    
    subcategory = await sync_to_async(Category.objects.filter(name=subcategory_name, parent_category_id=parent_category_id).first)()

    if not subcategory:
        await message.reply(
            "❌ Kiritilgan subkategoriya mavjud emas. Mavjud subkategoriyalardan tanlang 👇", 
            reply_markup=await admin_show_subcategories(message, parent_category_id=parent_category_id))
        return
    
    if subcategory == product.category:
        await message.answer(
            f"❌ Mahsulot kategoriyasi allaqachon '{subcategory.name}'ga biriktirilgan.\n"
            "Boshqa kategoriyani tanlang 👇",
            reply_markup=await admin_show_subcategories(message, parent_category_id))
        return
    try:
        product.category = subcategory
        product.updated_by = user
        await sync_to_async(product.save)()
        await message.answer(f"✅ Mahsulot kategoriyasi '{subcategory.name}'ga muvaffaqiyatli yangilandi. 👆")
        product_info = await admin_format_product_info(product)
        await admin_update_and_clean_message_products(message, chat_id, message_id, product_info, product.id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot kategoriyasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_brand_field)
async def admin_product_brand_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    
    product = data.get("product")

    if not product:
        await message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return
    
    brand_name = message.text.strip().upper()

    if not brand_name:
        await message.answer("❌ Brend nomi bo‘sh bo‘lishi mumkin emas. Admin, brand nomini tanlang yoki yozing!")
        return

    if brand_name.isdigit():
        await message.answer("❌ Brend nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
        return

    try:
        brand = await sync_to_async(lambda: CarBrand.objects.filter(name=brand_name).prefetch_related('car_models').first())()
        if not brand:
            brand = await sync_to_async(CarBrand.objects.create)(name=brand_name)
            await message.answer(f"✅ Mahsulot uchun yangi brend '{brand_name}' yaratildi va tayinlandi.")    
        elif brand == product.car_brand:
            await message.answer(
                f"❌ Mahsulot brendi allaqachon '{brand_name}'ga biriktirilgan.\n"
                "Boshqa brendni tanlang yoki yozing 👇",
                reply_markup=await admin_get_car_brands_list_reply_keyboard(message))
            return
        else:
            car_models = brand.car_models.all()
            await message.answer(f"✅ Mahsulot brendi '{brand_name}'ga muvaffaqiyatli yangilandi.\n Endi shu brendning modelini tanlang yoki kiriting 👇",
                                 reply_markup=await admin_show_car_models_list_reply_keyboard(message,car_models))
            await state.update_data(car_models=car_models, car_brand=brand)
            await state.set_state(AdminProductFSM.admin_waiting_edit_product_model_field)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot brendini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_model_field)
async def admin_product_model_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id, car_models, car_brand = data.get("product"), data.get("user"), data.get("message_id"), data.get("chat_id"), data.get('car_models'), data.get('car_brand')

    new_car_model = message.text.strip().title()

    if new_car_model.isdigit():
        await message.answer("❌ Model nomida hech bo‘lmaganda bitta harf bo‘lishi kerak!")
        return

    if not product:
        await message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return

    try:
        existing_model = None
        if car_models:
            existing_model = next((m for m in car_models if m.name == new_car_model), None)
        if existing_model:
            if existing_model == product.car_model:
                await message.answer(
                    f"❌ Mahsulot modeli allaqachon '{new_car_model}'ga biriktirilgan.\n"
                    "Boshqa modelni tanlang yoki yozing 👇",
                    reply_markup=await admin_show_car_models_list_reply_keyboard(message, car_models)
                )
                return
            product.car_model = existing_model
            msg_text = f"✅ Mahsulot modeli '{new_car_model}'ga muvaffaqiyatli yangilandi."
        else:
            existing_model = await sync_to_async(
                lambda: CarModel.objects.filter(brand=product.car_brand, name=new_car_model).first())()
            if existing_model:
                if existing_model == product.car_model:
                    await message.answer(
                        f"❌ Mahsulot modeli allaqachon '{new_car_model}'ga biriktirilgan.\n"
                        "Boshqa modelni tanlang yoki yozing 👇",
                        reply_markup=await admin_show_car_models_list_reply_keyboard(message))
                    return
                product.car_model = existing_model
                msg_text = f"✅ Mahsulot modeli '{new_car_model}'ga muvaffaqiyatli yangilandi."
            else:
                new_created_model = await sync_to_async(CarModel.objects.create)(
                    brand=product.car_brand, name=new_car_model
                )
                product.car_model = new_created_model
                msg_text = f"✅ Mahsulot uchun yangi model '{new_car_model}' yaratildi va tayinlandi."
        if car_brand:
            product.car_brand = car_brand
        product.updated_by = user
        await sync_to_async(product.save)()

        product_info = await admin_format_product_info(product)
        await admin_update_and_clean_message_products(message, chat_id, message_id, product_info, product.id)
        await message.answer(msg_text)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot modelini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_partname_field)
async def admin_product_part_name_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))

    if not product:
        await message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return
    
    part_name = message.text.strip()

    if not part_name:
        await message.answer("❌ Mahsulot nomi bo‘sh bo‘lishi mumkin emas. Admin, nom yozing!")
        return
    elif part_name.isdigit(): 
        await message.answer("❌ Mahsulot nomi faqat raqamlardan iborat bo‘lishi mumkin emas. Admin, boshqa nom yozing!")
        return
    elif len(part_name) < 2 or len(part_name) > 100:
        await message.answer("❌ Mahsulot nomi 2 dan 255 tagacha belgidan iborat bo‘lishi kerak.")
        return

    part_name = part_name.title()

    

    if part_name == product.name:
        await message.answer(f"❌ Mahsulot nomi allaqachon '{part_name}' turibdi.\nBoshqa nom yozing 👇")
        return
    
    try:
        product.name = part_name
        product.updated_by = user
        await sync_to_async(product.save)()

        await message.answer(f"✅ Mahsulot nomi '{part_name}' ga muvaffaqiyatli yangilandi.")

        product_info = await admin_format_product_info(product)
        await admin_update_and_clean_message_products(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot nomini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_price_field)
async def admin_product_price_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("❌ Mahsulot narxi musbat bo'lishi kerak! Qayta yozing.")
            return
    except ValueError:
        await message.answer("📌 Admin, narxni to'g'ri formatda yozing (faqat raqam).")
        return

    if price == product.price:
        await message.answer(f"❌ Mahsulot narxi allaqachon \"{price} so'm\" edi! Boshqa narx yozing 👇")
        return
    
    try:
        product.price = Decimal(str(price))
        product.updated_by = user
        await sync_to_async(product.save)()

        await message.answer(f"✅ Mahsulot narxi \"{price}\" so'mga muvaffaqiyatli yangilandi.")
        product_info = await admin_format_product_info(product)
        await admin_update_and_clean_message_products(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot narxini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")
    
@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_availability)
async def admin_product_availability_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer(text=admin_product_not_found_message, reply_markup=admin_keyboard_back_to_product_edit())
        return
    
    availability = message.text.strip().lower()

    if availability not in ["ha", "yo'q"]:
        await message.answer("📌 Admin, faqat 'Ha' yoki 'Yo‘q' deb javob bering.", reply_markup=ADMIN_CONFIRM_KEYBOARD)
        return

    available = availability == "ha"
    
    if product.available == available:
        await message.answer(f"❌ Mahsulot mavjudligi allaqachon '{availability}' holatda. 👆\nBoshqa tugmani tanlang 👇", reply_markup=ADMIN_CONFIRM_KEYBOARD)
        return
    
    try:
        product.available = available
        product.updated_by = user
        await sync_to_async(product.save)()

        product_info = await admin_format_product_info(product)
        await admin_update_and_clean_message_products(message, chat_id, message_id, product_info, product.id)

        await message.answer(f"✅ Mahsulot mavjudligi '{availability}' ga muvaffaqiyatli yangilandi. 👆")

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot mavjudligini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_stock)
async def admin_product_stock_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return
    
    try:
        in_stock = int(message.text.strip())
    except ValueError:
        await message.answer("📌 Admin, mahsulot sonini to'g'ri formatda yozing (faqat musbat raqam).")
        return

    if product.stock == in_stock:
        await message.answer(f"❌ Mahsulotning soni allaqachon {in_stock} ta edi! Boshqa miqdor yozing 👇")
        return

    if not product.available:
        await message.answer("📌 Oldin mahsulotni mavjudligini 'Ha' ga o'zgartiring!")
        return

    if in_stock > 0:
        product.stock = in_stock
        product.updated_by = user
        await sync_to_async(product.save)()
        product_info = await admin_format_product_info(product)
        await admin_update_and_clean_message_products(message, chat_id, message_id, product_info, product.id)
        await message.answer(f"✅ Mahsulot soni '{in_stock}' taga muvaffaqiyatli yangilandi. ")
    elif in_stock == 0:
        await message.answer("📌 Admin, agar mahsulot qolmagan bo'lsa, mavjudligini 'Yo'q' ga o'zgartiring.")
    else:
        await message.answer("❌ Admin, musbat sonni yozing!!!")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_quality)
async def admin_product_quality_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return
    
    selected_quality = message.text.strip()

    new_quality = admin_quality_choices.get(selected_quality)
    if not new_quality:
        await message.answer("📌 Admin, faqat ko'rsatilgan sifatlardan tanlang.", reply_markup=await admin_show_quality_type_reply_keyboard())
        return

    

    if product.quality == new_quality:
        await message.answer(f"❌ Mahsulot sifati allaqachon '{selected_quality}' holatda edi.\nBoshqa holatni tanlang 👇", reply_markup=await admin_show_quality_type_reply_keyboard())
        return
    try:
        product.quality = new_quality
        product.updated_by = user
        await sync_to_async(product.save)()

        product_info = await admin_format_product_info(product)
        await admin_update_and_clean_message_products(message, chat_id, message_id, product_info, product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot sifatini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    await message.answer(f"✅ Mahsulot sifati '{selected_quality}' holatiga muvaffaqiyatli yangilandi.")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_photo)
async def admin_product_photo_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return
    
    if not message.photo:
        await message.answer("📸 Admin, mahsulotning rasmini yuboring.")
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

        media = InputMediaPhoto(media=FSInputFile(file_path), caption=await admin_format_product_info(product), parse_mode="HTML")
        await message.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=admin_edit_product_inline_keyboard(product.id))

        await message.answer("✅ Mahsulotning yangi rasmi muvaffaqiyatli yangilandi 👆")

        delete_tasks = [message.bot.delete_message(chat_id, msg_id) for msg_id in range(message.message_id, message_id, -1)]
        await asyncio.gather(*delete_tasks, return_exceptions=True)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot rasmini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_description)
async def admin_product_description_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    description = message.text.strip().capitalize()
    
    if description == product.description:
        await message.reply("❌ Mahsulotning tavsifi allaqachon shunday edi.\nBoshqa tavsif yozing 👇")
        return
    
    try:
        product.description, product.updated_by = description, user
        await sync_to_async(product.save)()

        await message.answer(f"✅ Mahsulot tavsifi\n'{description}'\n-ga muvaffaqiyatli yangilandi.")
        await admin_update_and_clean_message_products(message, chat_id, message_id, await admin_format_product_info(product), product.id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot tavsifini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_product_router.message(AdminProductFSM.admin_waiting_edit_product_activity)
async def admin_product_activity_edit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    product, user, message_id, chat_id = (data.get(key) for key in ("product", "user", "message_id", "chat_id"))
    if not product:
        await message.answer("❌ Bunday mahsulot topilmadi. Admin, qayta urinib ko'ring.")
        return

    activity = message.text.strip()
    
    try:
        if activity in ["✅ Faol", "❌ Nofaol"]:
            is_active = activity == "✅ Faol"
            if product.is_active == is_active:
                await message.answer(f"❌ Mahsulot faolligi allaqachon '{activity}'da turibdi. Boshqa holat kiriting:", 
                                     reply_markup=ADMIN_ACTIVITY_KEYBOARD)
                return
            product.is_active = is_active
            product.updated_by = user
            await sync_to_async(product.save)()
            await message.answer(f"✅ Mahsulot faolligi {'faol' if is_active else 'nofaol'} holatga yangilandi👆")
            await admin_update_and_clean_message_products(message, chat_id, message_id, await admin_format_product_info(product), product.id)
        else:
            await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Mahsulot faollogini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

# Deleting part
@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith("admin_product_confirm_delete:"))
async def admin_product_confirm_delete_callback(callback_query: CallbackQuery, state: FSMContext):
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    product = data.get('product')
    if not product:
        await callback_query.answer(f"⚠️ Mahsulot topilmadi yoki allaqachon o'chirilgan. Admin qaytadan urinib ko'ring.",
                                    reply_markup=admin_keyboard_back_to_product_edit())
        return
    try:
        await sync_to_async(product.delete)()  
        await callback_query.answer(f"✅ '{product.name}' mahsulot o‘chirildi.")
        await callback_query.bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Mahsulotni o'chirishda xatolik yuz berdi yoki allaqachon o'chgan. Admin, qayta urinib ko'ring.")

@admin_product_router.callback_query(IsAdminFilter(), F.data.startswith("admin_product_cancel_delete:"))
async def admin_product_cancel_delete_callback(callback_query: CallbackQuery, state: FSMContext):
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    product = data.get('product')
    text = await admin_format_product_info(product)
    if not product:
        await callback_query.answer(f"⚠️ Mahsulot topilmadi yoki allaqachon o'chirilgan. Admin qaytadan urinib ko'ring.",
                                    reply_markup=admin_keyboard_back_to_product_edit())
        return
    await callback_query.answer("🚯 O‘chirish bekor qilindi.")
    if callback_query.message.content_type == "photo":
        await callback_query.message.edit_caption(
            caption=text,
            parse_mode='HTML',
            reply_markup=admin_edit_product_inline_keyboard(product.id)
        )
    else:
        await callback_query.message.edit_text(
            text=text,
            parse_mode='HTML',
            reply_markup=admin_edit_product_inline_keyboard(product.id)
        )

# Product part ended