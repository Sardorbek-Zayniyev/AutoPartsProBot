from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, CallbackQuery
from telegram_bot.app.admin.category import AdminCategoryFSM, admin_get_category_name, admin_get_categories_for_edition, admin_get_all_categories
from telegram_bot.app.admin.product import AdminProductFSM, admin_select_or_input_category_for_adding_product,admin_get_all_products,admin_display_parent_category_selection_for_edit_product,admin_display_car_brand_selection_for_edit_product,admin_display_car_model_selection_for_edit_product, admin_retrieve_products_part_name
from telegram_bot.app.admin.order import AdminOrderFSM, DELIVERY_STATUS_CHOICES, PAYMENT_STATUS_CHOICES, PAYMENT_METHOD_CHOICES, admin_filter_by_delivery_status, admin_filter_by_payment_status, admin_filter_by_payment_method, admin_filter_by_user, admin_filter_by_date, admin_search_order_by_delivery_status, admin_search_order_by_payment_status, admin_search_order_by_payment_method
from telegram_bot.app.admin.promocode import AdminPromocodeFSM, admin_add_promocode,admin_edit_or_set_promocode,admin_get_all_promocodes
from telegram_bot.app.admin.discount import AdminDiscountFSM, admin_add_discount,admin_edit_discount,admin_get_all_discounts
from telegram_bot.app.admin.reward import AdminRewardFSM, admin_add_reward, admin_edit_reward, admin_get_all_rewards
from telegram_bot.app.admin.announcement import AdminAnnouncementFSM, admin_announce_new_product, admin_announce_discounted_product, admin_announce_custom_text_message
from telegram_bot.app.admin.users_products import AdminUserProductsFSM, admin_get_user_products_by_status, admin_show_user_products_statistics
from telegram_bot.app.admin.help import AdminHelpFSM, admin_help_start, admin_select_category, CATEGORY_MAPPING, admin_show_statistics
from telegram_bot.app.admin.utils import admin_delete_previous_messages
from telegram_bot.app.utils import IsAdminFilter
from telegram_app.models import Product



admin_main_controls_router = Router()
# Buttons

ADMIN_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya"), KeyboardButton(text="📦 Mahsulot bo'limi")],
        [KeyboardButton(text="📢 Foydalanuvchi mahsulotlarini boshqarish"), KeyboardButton(text="📜 Buyurtmalar bo'limi")],
        [KeyboardButton(text="🏷️ Chegirmalar bo'limi"), KeyboardButton(text="🔖 Promokodlar bo'limi")],
        [KeyboardButton(text="🎁 Sovg'alar bo'limi") , KeyboardButton(text="📣  E'lon berish")],
        [KeyboardButton(text="❓ Murojaatlar")],
    ],
    resize_keyboard=True,
)

ADMIN_CATEGORY_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Kategoriya qo'shish"), KeyboardButton(text="✒️ Kategoriyani tahrirlash")],
        [KeyboardButton(text="✨ Barcha kategoriyalarni ko'rish"),KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_PRODUCT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="✒️ Mahsulotni tahrirlash")],
        [KeyboardButton(text="✨ Barcha mahsulotlarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_PRODUCT_EDIT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriyasi"), KeyboardButton(text="🔤 Mahsulotni nomi")],
        [KeyboardButton(text="🚘 Mashina brendi"), KeyboardButton(text="🚗 Mashina modeli")],
        [KeyboardButton(text="📦 Mahsulot bo'limi"), KeyboardButton(text="◀️ Bosh menu")],
    ],    
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_ORDER_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏳🔎 Buyurtma holati bo'yicha"), KeyboardButton(text="💳🔎 To'lov holati bo'yicha")],
        [KeyboardButton(text="💸🔎 To'lov usuli bo'yicha"), KeyboardButton(text="👤🔎 Foydalanuvchi bo'yicha")],
        [KeyboardButton(text="📅🔎 Sanasi bo'yicha"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_DISCOUNT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Chegirma qo'shish"), KeyboardButton(text="✒️ Chegirmalarni tahrirlash")],
        [KeyboardButton(text="➕ Chegirmaga mahsulot qo‘shish"), KeyboardButton(text="➖ Chegirmadan mahsulot olib tashlash")],
        [KeyboardButton(text="✨ Barcha chegirmalarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_PROMOCODE_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Promokod qo'shish"), KeyboardButton(text="✒️ Promokodni tahrirlash")],
        [KeyboardButton(text="✨ Barcha promokodlarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_REWARD_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Sovg'a qo'shish"), KeyboardButton(text="✒️ Sovg'ani tahrirlash")],
        [KeyboardButton(text="✨ Barcha sovg'alarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
        
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_ANNOUNCEMENT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Yangi mahsulot"), KeyboardButton(text="🏷️ Chegirmali mahsulot")],
        [KeyboardButton(text="📝 Matn ko'rinishda sms xabar"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

ADMIN_PRODUCTS_ADDED_BY_USER_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Tasdiqlangan mahsulotlar"), KeyboardButton(text="🚫 Rad etilgan mahsulotlar")],
        [KeyboardButton(text="⏳ Kutilayotgan mahsulotlar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Main control handlers
ADMIN_MAIN_CONTROLS_RESPONSES = {
    "📂 Kategoriya": {
        "text": "Kategoriya boshqaruvi uchun tugmalar:",
        "keyboard": ADMIN_CATEGORY_CONTROLS_KEYBOARD
    },
    "📦 Mahsulot bo'limi": {
        "text": "Mahsulot boshqaruvi uchun tugmalar:",
        "keyboard": ADMIN_PRODUCT_CONTROLS_KEYBOARD
    },
    "📜 Buyurtmalar bo'limi": {  
        "text": "Buyurtmalarni boshqarish uchun tugmalar:",
        "keyboard": ADMIN_ORDER_CONTROLS_KEYBOARD
    },
    "🏷️ Chegirmalar bo'limi": {
        "text": "Chegirmalarni boshqaruvi uchun tugmalar:",
        "keyboard": ADMIN_DISCOUNT_CONTROLS_KEYBOARD
    },
    "🔖 Promokodlar bo'limi": {
        "text": "Pomokodlarni boshqaruvi uchun tugmalar:",
        "keyboard": ADMIN_PROMOCODE_CONTROLS_KEYBOARD
    },
    "🎁 Sovg'alar bo'limi": {
        "text": "Sovg'alar boshqaruvi uchun tugmalar:",
        "keyboard": ADMIN_REWARD_CONTROLS_KEYBOARD
    },
    "📣  E'lon berish": {
        "text": "E'lon berish uchun tugmalar:",
        "keyboard": ADMIN_ANNOUNCEMENT_CONTROLS_KEYBOARD,
    },
    "📢 Foydalanuvchi mahsulotlarini boshqarish": {
        "text": "Foydalanuvchilarning mahsulotlarini boshqarish uchun tugmalar:",
        "keyboard": ADMIN_PRODUCTS_ADDED_BY_USER_CONTROLS_KEYBOARD,
    }
}

@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(ADMIN_MAIN_CONTROLS_RESPONSES))
async def admin_main_controls_handler(message: Message, state: FSMContext):
    response = ADMIN_MAIN_CONTROLS_RESPONSES[message.text]
    await message.answer(response["text"], reply_markup=response["keyboard"])

#Utils
#handles back to main section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_main_menu"))
async def admin_main_menu(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer('🏘 Asosiy menuga xush kelibsiz!', reply_markup=ADMIN_MAIN_CONTROLS_KEYBOARD)
    await callback_query.answer()

@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("🚫 Jarayonni bekor qilish", "◀️ Bosh menu")))
async def admin_cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state() 
    if message.text == "◀️ Bosh menu":
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_MAIN_CONTROLS_KEYBOARD)
    elif current_state and current_state.startswith('AdminCategoryFSM'):     
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_CATEGORY_CONTROLS_KEYBOARD)
    elif current_state and current_state.startswith('AdminProductFSM'):     
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_PRODUCT_CONTROLS_KEYBOARD)
    elif current_state and current_state.startswith('AdminOrderFSM'):     
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_ORDER_CONTROLS_KEYBOARD)
    elif current_state and current_state.startswith('AdminPromocodeFSM'):     
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_PROMOCODE_CONTROLS_KEYBOARD)
    elif current_state and current_state.startswith('AdminDiscountFSM'):     
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_DISCOUNT_CONTROLS_KEYBOARD)
    elif current_state and current_state.startswith('AdminRewardFSM'):     
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_REWARD_CONTROLS_KEYBOARD)
    else:
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=ADMIN_MAIN_CONTROLS_KEYBOARD)
    await state.clear() 

#handles back to category section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_category_section"))
async def admin_handler_back_to_category_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("📂 Kategoriya bo'limiga qaytdingiz.", reply_markup=ADMIN_CATEGORY_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to discount section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_discount_section"))
async def admin_handler_back_to_discount_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("🏷️ Chegirmalar bo'limiga qaytdingiz.", reply_markup=ADMIN_DISCOUNT_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to product section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_product_section"))
async def admin_handler_back_to_product_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("📦 Mahsulot bo'limiga qaytdingiz.", reply_markup=ADMIN_PRODUCT_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to product_edit section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_product_edit_section"))
async def admin_handler_back_to_product_edit_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("✒️ Mahsulot tahrirlash bo'limiga qaytdingiz.", reply_markup=ADMIN_PRODUCT_EDIT_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to order section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_order_section"))
async def admin_handler_back_to_order_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer("📜 Buyurtmalar bo'limiga qaytdingiz.", reply_markup=ADMIN_ORDER_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to promocode section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_promocode_section"))
async def admin_handler_back_to_promocode_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("🔖 Promokodlar bo'limiga qaytdingiz.", reply_markup=ADMIN_PROMOCODE_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to reward section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_reward_section"))
async def admin_handler_back_to_reward_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("🎁 Sovg'alar bo'limiga qaytdingiz.", reply_markup=ADMIN_REWARD_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to announce section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_announce_section"))
async def admin_handler_back_to_announce_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("📣  E'lon berish bo'limiga qaytdingiz.", reply_markup=ADMIN_ANNOUNCEMENT_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to users_products section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_users_products_section"))
async def admin_handler_back_to_user_products_section(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer(
        "📢 Foydalanuvchilarning mahsulotlarini boshqarish uchun tugmalar:",
        reply_markup=ADMIN_PRODUCTS_ADDED_BY_USER_CONTROLS_KEYBOARD
    )
    await callback_query.answer()

#handles back to help section
@admin_main_controls_router.callback_query(IsAdminFilter(), F.data.startswith("admin_help_section"))
async def admin_handler_back_to_help_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    await state.clear()
    from telegram_bot.app.admin.help import admin_help_menu_keyboard
    await callback_query.message.answer("❓ Murojaatlar bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇", reply_markup=admin_help_menu_keyboard())
    await callback_query.answer()
####
#Category control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("➕ Kategoriya qo'shish", "✒️ Kategoriyani tahrirlash", "✨ Barcha kategoriyalarni ko'rish")))
async def admin_category_controls_handler(message: Message, state: FSMContext):
    """
    Handle category management actions (add, edit, delete).
    """
    actions = {
        "➕ Kategoriya qo'shish": (AdminCategoryFSM.admin_waiting_get_category_name, admin_get_category_name),
        "✒️ Kategoriyani tahrirlash": (AdminCategoryFSM.admin_waiting_get_parent_categories_for_edition, admin_get_categories_for_edition),
        "✨ Barcha kategoriyalarni ko'rish": (AdminCategoryFSM.admin_waiting_get_all_categories, admin_get_all_categories),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)

    if await state.get_state() == AdminCategoryFSM.admin_waiting_get_all_categories:
        await handler_function(message, state, 'name')
    else:
        await handler_function(message, state)

#Product control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("➕ Mahsulot qo'shish", "✒️ Mahsulotni tahrirlash", "✨ Barcha mahsulotlarni ko'rish")))
async def admin_products_control_handler(message: Message, state: FSMContext):
    """
    Handle product management actions (add, edit).
    """
    actions = {
        "➕ Mahsulot qo'shish": (AdminProductFSM.admin_waiting_show_category, admin_select_or_input_category_for_adding_product),
        "✒️ Mahsulotni tahrirlash": (AdminProductFSM.admin_waiting_choose_field_product_to_search, None),
        "✨ Barcha mahsulotlarni ko'rish": (AdminProductFSM.admin_waiting_get_all_products, admin_get_all_products),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    if handler_function:
        await handler_function(message, state)
    elif next_state == AdminProductFSM.admin_waiting_choose_field_product_to_search:
        await message.answer("Mahsulotni qaysi maydoni bo'yicha qidirmoqchisiz tanlang? 👇", reply_markup=ADMIN_PRODUCT_EDIT_CONTROLS_KEYBOARD)

@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("📂 Kategoriyasi", "🔤 Mahsulotni nomi", "🚘 Mashina brendi", "🚗 Mashina modeli")))
async def admin_products_edit_control_handler(message: Message, state: FSMContext):
    actions = {
        "📂 Kategoriyasi": (AdminProductFSM.admin_waiting_edit_product_by_category, admin_display_parent_category_selection_for_edit_product),
        "🚘 Mashina brendi": (AdminProductFSM.admin_waiting_edit_product_by_brand_name, admin_display_car_brand_selection_for_edit_product),
        "🚗 Mashina modeli": (AdminProductFSM.admin_waiting_edit_product_by_model_name, admin_display_car_model_selection_for_edit_product),
        "🔤 Mahsulotni nomi": (AdminProductFSM.admin_waiting_edit_product_by_part_name, admin_retrieve_products_part_name),
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    await state.set_state(next_state)
    await handler_function(message, state)

#Order control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("⏳🔎 Buyurtma holati bo'yicha", "💳🔎 To'lov holati bo'yicha", "💸🔎 To'lov usuli bo'yicha", "👤🔎 Foydalanuvchi bo'yicha", "📅🔎 Sanasi bo'yicha", *DELIVERY_STATUS_CHOICES.values(), *PAYMENT_STATUS_CHOICES.values(), *PAYMENT_METHOD_CHOICES.values())))
async def admin_order_controls_handler(message: Message, state: FSMContext):
    actions = {
        "⏳🔎 Buyurtma holati bo'yicha": (AdminOrderFSM.admin_waiting_filter_by_status, admin_filter_by_delivery_status),
        "💳🔎 To'lov holati bo'yicha": (AdminOrderFSM.admin_waiting_filter_by_payment_status, admin_filter_by_payment_status),
        "💸🔎 To'lov usuli bo'yicha": (AdminOrderFSM.admin_waiting_filter_by_payment_method, admin_filter_by_payment_method),
        "👤🔎 Foydalanuvchi bo'yicha": (AdminOrderFSM.admin_waiting_filter_by_user, admin_filter_by_user),
        "📅🔎 Sanasi bo'yicha": (AdminOrderFSM.admin_waiting_filter_by_date, admin_filter_by_date),
    }
    if await state.get_state() != AdminOrderFSM.admin_waiting_edit_order_field:
        for delivery_status in DELIVERY_STATUS_CHOICES.values():
            actions[delivery_status] = (AdminOrderFSM.admin_waiting_search_order_by_delivery_status, admin_search_order_by_delivery_status)
        for payment_status in PAYMENT_STATUS_CHOICES.values():
            actions[payment_status] = (AdminOrderFSM.admin_waiting_search_order_by_payment_status, admin_search_order_by_payment_status)
        for payment_method in PAYMENT_METHOD_CHOICES.values():
            actions[payment_method] = (AdminOrderFSM.admin_waiting_search_order_by_delivery_status, admin_search_order_by_payment_method)

    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#Promocode control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("➕ Promokod qo'shish", "✒️ Promokodni tahrirlash", "✨ Barcha promokodlarni ko'rish")))
async def admin_promocode_controls_handler(message: Message, state: FSMContext):
    actions = {
        "➕ Promokod qo'shish": (AdminPromocodeFSM.admin_waiting_promocode_add, admin_add_promocode),
        "✒️ Promokodni tahrirlash": (AdminPromocodeFSM.admin_waiting_edit_promocode, admin_edit_or_set_promocode),
        "✨ Barcha promokodlarni ko'rish": (AdminPromocodeFSM.admin_waiting_get_all_promocode, admin_get_all_promocodes),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#Discount control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("➕ Chegirma qo'shish", "✒️ Chegirmalarni tahrirlash", "✨ Barcha chegirmalarni ko'rish", "➕ Chegirmaga mahsulot qo‘shish", "➖ Chegirmadan mahsulot olib tashlash")))
async def admin_discount_controls_handler(message: Message, state: FSMContext):
    actions = {
        "➕ Chegirma qo'shish": (AdminDiscountFSM.admin_waiting_discount_add, admin_add_discount),
        "✒️ Chegirmalarni tahrirlash": (AdminDiscountFSM.admin_waiting_edit_discount, admin_edit_discount),
        "✨ Barcha chegirmalarni ko'rish": (AdminDiscountFSM.admin_waiting_get_all_discounts, admin_get_all_discounts),
        "➕ Chegirmaga mahsulot qo‘shish": (AdminDiscountFSM.admin_waiting_add_product_to_discount, admin_get_all_discounts),
        "➖ Chegirmadan mahsulot olib tashlash": (AdminDiscountFSM.admin_waiting_remove_product_from_discount, admin_get_all_discounts),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#Reward control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("➕ Sovg'a qo'shish", "✒️ Sovg'ani tahrirlash", "✨ Barcha sovg'alarni ko'rish")))
async def admin_reward_controls_handler(message: Message, state: FSMContext):
    actions = {
        "➕ Sovg'a qo'shish": (AdminRewardFSM.admin_waiting_reward_add, admin_add_reward),
        "✒️ Sovg'ani tahrirlash": (AdminRewardFSM.admin_waiting_edit_reward, admin_edit_reward),
        "✨ Barcha sovg'alarni ko'rish": (AdminRewardFSM.admin_waiting_get_all_reward, admin_get_all_rewards),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#Announcment control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("🆕 Yangi mahsulot", "🏷️ Chegirmali mahsulot", "📝 Matn ko'rinishda sms xabar")))
async def admin_reward_controls_handler(message: Message, state: FSMContext):
    actions = {
        "🆕 Yangi mahsulot": (AdminAnnouncementFSM.admin_waiting_select_new_product, admin_announce_new_product),
        "🏷️ Chegirmali mahsulot": (AdminAnnouncementFSM.admin_waiting_select_discounted_product, admin_announce_discounted_product),
        "📝 Matn ko'rinishda sms xabar": (AdminAnnouncementFSM.admin_waiting_custom_text, admin_announce_custom_text_message),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#Users' products control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("✅ Tasdiqlangan mahsulotlar", "🚫 Rad etilgan mahsulotlar", "⏳ Kutilayotgan mahsulotlar", "📊 Statistika")))
async def admin_user_products_controls_handler(message: Message, state: FSMContext):
    """
    Foydalanuvchi mahsulotlarini boshqarish bo'limidagi tugmalarni boshqaradi.
    """
    actions = {
        "✅ Tasdiqlangan mahsulotlar": (AdminUserProductsFSM.admin_waiting_get_approved_products, admin_get_user_products_by_status, Product.STATUS_APPROVED),
        "🚫 Rad etilgan mahsulotlar": (AdminUserProductsFSM.admin_waiting_get_rejected_products, admin_get_user_products_by_status, Product.STATUS_REJECTED),
        "⏳ Kutilayotgan mahsulotlar": (AdminUserProductsFSM.admin_waiting_get_pending_products, admin_get_user_products_by_status, Product.STATUS_PENDING),
    }
    if message.text == "📊 Statistika":
        await admin_show_user_products_statistics(message, state)
    else:
        next_state, handler_function, status = actions[message.text]
        await state.set_state(next_state)
        await handler_function(message, state, status)

#Help control_handler
@admin_main_controls_router.message(IsAdminFilter(), F.text.in_(("❓ Murojaatlar", "📊 Savollar statistikasi", *CATEGORY_MAPPING.keys())))
async def admin_help_controls_handler(message: Message, state: FSMContext):
    actions = {
        "❓ Murojaatlar": (AdminHelpFSM.admin_waiting_help_start, admin_help_start),
        **{category: AdminHelpFSM.admin_waiting_category_selection for category in CATEGORY_MAPPING.keys()}
        
    }
    await state.clear()
    if message.text == "📊 Savollar statistikasi":
        await admin_show_statistics(message)
    else:
        await state.set_state(actions[message.text])
        if message.text == "❓ Murojaatlar":
            await admin_help_start(message, state)
        elif message.text in CATEGORY_MAPPING:
            await admin_select_category(message, state)
 



