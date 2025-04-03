from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, CallbackQuery
from telegram_bot.app.utils import IsUserFilter
from telegram_bot.app.user.utils import user_delete_previous_messages
from telegram_bot.app.user.cart import UserCartFSM, user_get_cart, user_get_saved_items_list
from telegram_bot.app.user.user_profile import UserProfileFSM, user_show_profile
from telegram_bot.app.user.reward import UserRewardFSM, user_get_points, user_get_all_my_rewards, user_get_all_rewards
from telegram_bot.app.user.help import UserHelpFSM, user_help_start, user_view_my_questions, user_select_category_of_question, CATEGORY_MAPPING, user_help_menu_keyboard
from telegram_bot.app.user.order import UserOrderFSM, user_get_all_orders
from telegram_bot.app.user.catalog import (UserCatalogFSM,
                                           user_display_parent_category_selection_for_get_new_products_category,
                                           user_display_parent_category_selection_for_get_used_products_category,
                                           user_display_parent_category_selection_for_get_discounted_products_category,
                                        )
from telegram_bot.app.user.product import (UserProductFSM,
                                           user_display_parent_category_selection_for_get_product,
                                           user_retrieve_products_part_name, 
                                           user_display_car_brand_selection_for_get_product, 
                                           user_display_car_model_selection_for_get_product, 
                                           user_get_all_products,
                                           user_select_or_input_category_for_adding_product,
                                           user_fetch_products_entered_by_user,
                                        )

main_controls_router = Router ()

USER_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗂 Katalog"), KeyboardButton(text="🔎 Qidiruv")],
        [KeyboardButton(text="📜 Mening buyurtmalarim"), KeyboardButton(text="🛒 Savat")],
        [KeyboardButton(text="🛍️ Mahsulotingizni soting"), KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="🎁 Sovg'alar"), KeyboardButton(text="❓ Yordam")],
    ],
    resize_keyboard=True,
)

USER_PRODUCT_SEARCH_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✨ Barcha mahsulotlarni ko'rish")],
        [KeyboardButton(text="📂 Kategoriya bo'yicha"), KeyboardButton(text="🔤 Ehtiyot qism nomi bo'yicha")],
        [KeyboardButton(text="🚘 Mashina brendi bo'yicha"), KeyboardButton(text="🚗 Mashina modeli bo'yicha")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

USER_PRODUCT_SELL_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulotni qo'shish"), KeyboardButton(text="🖋 Mahsulotni tahrirlash")],
        [KeyboardButton(text="⬅️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

USER_CART_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👁️ Savatni ko'rish"), KeyboardButton(
            text="♥️ Saqlangan mahsulotlar")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    
)

USER_CATALOG_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Aksiyadagi mahsulotlar"),KeyboardButton(text="🆕 Yangi mahsulotlar")],
        [KeyboardButton(text="🔄 Ishlatilgan mahsulotlar"), KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

USER_ORDERS_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏳ Joriy buyurtmalar"), KeyboardButton(text="📜 Buyurtmalar tarixi")],
        [KeyboardButton(text="🚫 Buyurtmani bekor qilish"), KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

USER_PROFILE_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Profil ma'lumotlarini ko'rish"),KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

USER_REWARD_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏆 Mening ballarim"), KeyboardButton(text="⭐ Mening sovg'alarim") ],
        [KeyboardButton(text="🎀 Mavjud sovg'alar"), KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

USER_MAIN_CONTROLS_RESPONSES = {
    "🗂 Katalog": {
        "text": "Katalog boshqaruvi uchun tugmalar:",
        "keyboard": USER_CATALOG_CONTROLS_KEYBOARD,
    },
    "🔎 Qidiruv": {
        "text": "Mahsulotni qidiruvi uchun tugmalar:",
        "keyboard": USER_PRODUCT_SEARCH_CONTROLS_KEYBOARD
    },
    "📜 Mening buyurtmalarim": {
        "text": "Buyurtmalar boshqaruvi uchun tugmalar:",
        "keyboard": USER_ORDERS_CONTROLS_KEYBOARD
    },
    "🛍️ Mahsulotingizni soting": {
        "text": "Buyurtmalar boshqaruvi uchun tugmalar:",
        "keyboard": USER_PRODUCT_SELL_CONTROLS_KEYBOARD
    },    
    "🛒 Savat": {
        "text": "Savat boshqaruvi uchun tugmalar:",
        "keyboard": USER_CART_CONTROLS_KEYBOARD
    },
    "👤 Profil": {
        "text": "Profil sozlamalari bo'limi",
        "keyboard": USER_PROFILE_CONTROLS_KEYBOARD,
    },
    "🎁 Sovg'alar": {
        "text": "Sovg'alar uchun tugmalar:",
        "keyboard": USER_REWARD_CONTROLS_KEYBOARD,
    },
    "⬅ Bosh menu": {
        "text": "Asosiy menuga xush kelibsiz!",
        "keyboard": USER_MAIN_CONTROLS_KEYBOARD,
        "clear_state": True
    }
}


#handles back to main menu
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_main_menu"))
async def user_main_menu(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer('Asosiy menuga xush kelibsiz!', reply_markup=USER_MAIN_CONTROLS_KEYBOARD)
    await callback_query.answer()

@main_controls_router.message(IsUserFilter(), F.text.in_(("🚫 Jarayonni bekor qilish", "⬅️ Bosh menu")))
async def user_cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state() 
    if message.text == "⬅️ Bosh menu":
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=USER_MAIN_CONTROLS_KEYBOARD)
    elif current_state and current_state.startswith('UserProductFSM'):     
        await message.answer("Jarayon bekor qilindi. 🚫", reply_markup=USER_PRODUCT_SELL_CONTROLS_KEYBOARD)
    await state.clear() 

#handles back to search main section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_search_section"))
async def user_handler_back_to_search_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()  
    await callback_query.message.answer("🔎 Qidiruv bo'limiga qaytdingiz.", reply_markup=USER_PRODUCT_SEARCH_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to orders section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_orders_section"))
async def user_handler_back_to_orders_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer(
        "📜 Buyurtmalar bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇",
        reply_markup=USER_ORDERS_CONTROLS_KEYBOARD
    )
    await callback_query.answer()

#handles back to orders section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_cart_section"))
async def user_handler_back_to_cart_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer(
        "🛒 Savat bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇",
        reply_markup=USER_CART_CONTROLS_KEYBOARD    )
    await callback_query.answer()

#handles back to product_sell section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_product_sell_section"))
async def user_handler_back_to_product_sell_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer("🛍️ Mahsulot sotish bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇", reply_markup=USER_PRODUCT_SELL_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to catalog section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_catalog_section"))
async def user_handler_back_to_catalog_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer("🗂 Katalog bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇", reply_markup=USER_CATALOG_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to profile section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_profile_section"))
async def user_handler_back_to_profile_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer("👤 Profil bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇", reply_markup=USER_PROFILE_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to reward section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_reward_section"))
async def user_handler_back_to_reward_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer("🎁 Sovg'alar bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇", reply_markup=USER_REWARD_CONTROLS_KEYBOARD)
    await callback_query.answer()

#handles back to help section
@main_controls_router.callback_query(IsUserFilter(), F.data.startswith("user_help_section"))
async def user_handler_back_to_help_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    await state.clear()
    await callback_query.message.answer("❓ Yordam bo'limiga qaytdingiz.\nQuyidagi tugmalardan birini tanlang👇", reply_markup=user_help_menu_keyboard())
    await callback_query.answer()

@main_controls_router.message(IsUserFilter(), F.text.in_(USER_MAIN_CONTROLS_RESPONSES))
async def user_main_controls_handler(message: Message, state: FSMContext):
    response = USER_MAIN_CONTROLS_RESPONSES[message.text]
    # keyboard = response["keyboard"]
    # if callable(keyboard): 
    #     keyboard = keyboard()
    await message.reply(response["text"], reply_markup=response["keyboard"])
    if response.get("clear_state"):
        await state.clear()

#Product control_handler
@main_controls_router.message(IsUserFilter(), F.text.in_(("📂 Kategoriya bo'yicha", "🔤 Ehtiyot qism nomi bo'yicha", "🚘 Mashina brendi bo'yicha", "🚗 Mashina modeli bo'yicha","✨ Barcha mahsulotlarni ko'rish")))
async def user_product_search_controls_handler(message: Message, state: FSMContext):
    """
    Handle search control actions (category, part name, car brand, car model).
    """
    actions = {
        "📂 Kategoriya bo'yicha": (UserProductFSM.user_waiting_get_product_by_category, user_display_parent_category_selection_for_get_product),
        "🔤 Ehtiyot qism nomi bo'yicha": (UserProductFSM.user_waiting_get_all_products_by_part_name, user_retrieve_products_part_name),
        "🚘 Mashina brendi bo'yicha": (UserProductFSM.user_waiting_get_all_product_by_car_brand_name, user_display_car_brand_selection_for_get_product),
        "🚗 Mashina modeli bo'yicha": (UserProductFSM.user_waiting_get_all_products_by_car_model_name, user_display_car_model_selection_for_get_product),
        "✨ Barcha mahsulotlarni ko'rish": (UserProductFSM.user_waiting_get_all_products, user_get_all_products),
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    await state.set_state(next_state)
    await handler_function(message, state)

@main_controls_router.message(IsUserFilter(), F.text.in_(("➕ Mahsulotni qo'shish", "🖋 Mahsulotni tahrirlash")))
async def user_product_add_edit_control_handler(message: Message, state: FSMContext):
    """
    Handle product management actions (add, edit).
    """
    actions = {
        "➕ Mahsulotni qo'shish": (UserProductFSM.user_waiting_show_category, user_select_or_input_category_for_adding_product),
        "🖋 Mahsulotni tahrirlash": (UserProductFSM.user_waiting_fetch_products_entered_by_user, user_fetch_products_entered_by_user),
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    await state.set_state(next_state)
    await handler_function(message, state)

#Orders control_handler
@main_controls_router.message(IsUserFilter(), F.text.in_(("⏳ Joriy buyurtmalar", "📜 Buyurtmalar tarixi", "🚫 Buyurtmani bekor qilish")))
async def user_orders_controls_handler(message: Message, state: FSMContext):
    """
    Handle order control actions (view current orders, view history, cancel order)
    """
    actions = {
        "⏳ Joriy buyurtmalar": (UserOrderFSM.user_waiting_get_current_orders, user_get_all_orders),
        "📜 Buyurtmalar tarixi": (UserOrderFSM.user_waiting_view_order_history, user_get_all_orders),
        "🚫 Buyurtmani bekor qilish": (UserOrderFSM.user_waiting_start_order_cancellation, user_get_all_orders),
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    if next_state:
        await state.set_state(next_state)
    if next_state == UserOrderFSM.user_waiting_view_order_history:
        await handler_function(message, state)
    else:
        await handler_function(message, state, current_orders=True)

#Cart control_handler
@main_controls_router.message(IsUserFilter(), F.text.in_(("👁️ Savatni ko'rish", "♥️ Saqlangan mahsulotlar")))
async def user_cart_controls_handler(message: Message, state: FSMContext):
    """
    Handle cart control actions (view cart, clear cart)
    """

    actions = {
        "👁️ Savatni ko'rish": (UserCartFSM.user_waiting_get_cart, user_get_cart),
        "♥️ Saqlangan mahsulotlar": (UserCartFSM.user_waiting_get_saved_items, user_get_saved_items_list),
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)

#Catalog control_handler
@main_controls_router.message(IsUserFilter(), F.text.in_(("🆕 Yangi mahsulotlar", "🔄 Ishlatilgan mahsulotlar", "🔥 Aksiyadagi mahsulotlar")))
async def user_catalog_controls_handler(message: Message, state: FSMContext):
    actions = {
        "🆕 Yangi mahsulotlar": (UserCatalogFSM.user_waiting_get_new_products, user_display_parent_category_selection_for_get_new_products_category), 
        "🔄 Ishlatilgan mahsulotlar": (UserCatalogFSM.user_waiting_get_used_products, user_display_parent_category_selection_for_get_used_products_category),
        "🔥 Aksiyadagi mahsulotlar": (UserCatalogFSM.user_waiting_get_discounted_products, user_display_parent_category_selection_for_get_discounted_products_category),  
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)

#Reward control_handler
@main_controls_router.message(IsUserFilter(), F.text.in_(("🏆 Mening ballarim", "⭐ Mening sovg'alarim", "🎀 Mavjud sovg'alar")))
async def user_reward_controls_handler(message: Message, state: FSMContext):
    """
    Handle gamification control actions (My scores, See rewards)
    """
    actions = {
        "🏆 Mening ballarim": (UserRewardFSM.user_waiting_get_my_points, user_get_points),
        "⭐ Mening sovg'alarim": (UserRewardFSM.user_waiting_get_all_my_rewards, user_get_all_my_rewards),
        "🎀 Mavjud sovg'alar": (UserRewardFSM.user_waiting_get_all_rewards, user_get_all_rewards),
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)

#Profile control_handler
@main_controls_router.message(IsUserFilter(), F.text.in_(("👤 Profil ma'lumotlarini ko'rish")))
async def user_profile_controls_handler(message: Message, state: FSMContext):
    actions = {
        "👤 Profil ma'lumotlarini ko'rish": (UserProfileFSM.user_waiting_viewing_profile, user_show_profile),
    }
    next_state, handler_function = actions[message.text]
    await state.clear()
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)
    
#Help control_handler
@main_controls_router.message(IsUserFilter(), F.text.in_(("❓ Yordam", "📝 Mening murojaatlarim", *CATEGORY_MAPPING.keys())))
async def user_help_controls_handler(message: Message, state: FSMContext):
    actions = {
        "❓ Yordam": (UserHelpFSM.user_waiting_help_start, user_help_start),
        "📝 Mening murojaatlarim": (UserHelpFSM.user_waiting_for_my_questions, user_view_my_questions),
        **{category: UserHelpFSM.user_waiting_for_category_of_question for category in CATEGORY_MAPPING.keys()}
    }
    await state.clear()
    await state.set_state(actions[message.text])
    
    if message.text == "❓ Yordam":
        await user_help_start(message, state)
    elif message.text in CATEGORY_MAPPING:
        await user_select_category_of_question(message, state)
    else:
        await user_view_my_questions(message, state)
   













