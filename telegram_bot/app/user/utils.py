import re
from aiogram import Router, F
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, CallbackQuery, Message

user_utils_router = Router()

# for format_infos
user_invalid_command_message = """~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\n
Qidirish uchun tegishli bo‘limga o'ting yoki quyidagi tugmalardan foydalaning 👇"""

user_product_not_found_message = """~~~~~~~~~~~~~~~❌ Mahsulot topilmadi~~~~~~~~~~~~~~~~\n
Qidirish uchun tegishli bo‘limga o'ting yoki quyidagi tugmalardan foydalaning 👇"""

def user_escape_markdown(text: str) -> str:
    """Escapes special characters for Telegram MarkdownV2."""
    return re.sub(r'([_*\[\]()~`>#+-=|{}.!])', r'\\\1', text)

async def user_check_state_data(state: FSMContext, message: Message = None, callback_query: CallbackQuery = None):
    data = await state.get_data()
    if not data:
        text = "❌ Xatolik: Ma'lumot topilmadi. Sahifani qayta yuklang."
        if message:
            await message.answer(text)
        elif callback_query:
            await callback_query.answer(text, show_alert=True)
        return None
    return data

async def user_send_typing_action(callback_query_or_message):
    """
    Foydalanuvchiga "Typing..." animatsiyasini ko'rsatish uchun yordamchi funksiya.
    """
    bot = callback_query_or_message.bot
    chat_id = (
        callback_query_or_message.message.chat.id
        if isinstance(callback_query_or_message, CallbackQuery)
        else callback_query_or_message.chat.id
    )

    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    # await asyncio.sleep(0.5)

async def user_delete_previous_messages(callback_query_or_message, state: FSMContext):
    data = await state.get_data()
    message_ids = data.get("message_ids", [])  

    if not isinstance(message_ids, list): 
        message_ids = [message_ids]

    await user_send_typing_action(callback_query_or_message)

    for message_id in message_ids:
        try:
            if isinstance(callback_query_or_message, CallbackQuery):
                await callback_query_or_message.bot.delete_message(
                    chat_id=callback_query_or_message.message.chat.id, 
                    message_id=message_id
                )
            else:
                await callback_query_or_message.bot.delete_message(
                    chat_id=callback_query_or_message.chat.id, 
                    message_id=message_id
                )
        except Exception:
            pass
    await state.update_data(message_ids=[])

def user_create_keyboard(*buttons: list[tuple[str, str]], add_main_menu: bool = False, adjust_sizes: list[int] = None) -> InlineKeyboardMarkup:
    """
    Helper function to create an inline keyboard with the given buttons.
    Args:
        buttons: A list of tuples where each tuple contains (text, callback_data).
        add_main_menu: If True, adds a "⬅️ Bosh menu" button.
        adjust_sizes: A list of integers defining the number of buttons per row.
                      If None, defaults to 2 buttons per row.
    Returns:InlineKeyboardMarkup: The generated inline keyboard.
    """
    builder = InlineKeyboardBuilder()
    
    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)
    
    if add_main_menu:
        builder.button(text='⬅️ Bosh menu', callback_data='user_main_menu')
    
    if adjust_sizes:
        builder.adjust(*adjust_sizes)
    else:
        builder.adjust(2)  
    
    return builder.as_markup()

def user_keyboard_back_to_main_menu() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with only the "⬅️ Bosh menu" button.
    """
    return user_create_keyboard(add_main_menu=True, adjust_sizes=[1])

def user_single_item_buttons() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with a single "❌" button.
    """
    buttons = [
        ("⬅️ Bosh menu", "user_main_menu"),
        ("❌", "user_delete_message"),
        ]
    return user_create_keyboard(
        *buttons,
        add_main_menu=False,  
        adjust_sizes=[2] 
    )

def user_skip_inline_button(callback_prefix: str) -> InlineKeyboardMarkup:
    """
    Creates a keyboard with a single "⏭ O‘tkazib yuborish" button.
    """
    return user_create_keyboard(
        ("⏭ O‘tkazib yuborish", f"{callback_prefix}_skip_step"),
        add_main_menu=False,  
        adjust_sizes=[2]  
    )

def user_delete_confirmation_keyboard(callback_prefix: str, model_id: int) -> InlineKeyboardMarkup:
    """
    Creates a confirmation keyboard for deletion with "✅ Ha" and "❌ Yo‘q" buttons.
    """
    buttons = [
        ("✅ Ha", f"{callback_prefix}_confirm_delete:{model_id}"),
        ("❌ Yo‘q", f"{callback_prefix}_cancel_delete:{model_id}"),
    ]
    return user_create_keyboard(
        *buttons,
        add_main_menu=False,  
        adjust_sizes=[2]  
    )

#Reply Keyboard
USER_CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️ Bosh menu"), KeyboardButton(text="🚫 Jarayonni bekor qilish")],
        [KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)

USER_ACTIVITY_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️ Bosh menu"), KeyboardButton(text="🚫 Jarayonni bekor qilish")],
        [KeyboardButton(text="✅ Faol"), KeyboardButton(text="❌ Nofaol")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)

def user_get_cancel_reply_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⬅️ Bosh menu"), KeyboardButton(text="🚫 Jarayonni bekor qilish"))
    builder.adjust(2)
    return builder

#Inline Keyboard
def user_create_keyboard(*buttons: list[tuple[str, str]], add_main_menu: bool = False, adjust_sizes: list[int] = None) -> InlineKeyboardMarkup:
    """
    Helper function to create an inline keyboard with the given buttons.
    Args:
        buttons: A list of tuples where each tuple contains (text, callback_data).
        add_main_menu: If True, adds a "⬅️ Bosh menu" button.
        adjust_sizes: A list of integers defining the number of buttons per row.
                      If None, defaults to 2 buttons per row.
    Returns: InlineKeyboardMarkup: The generated inline keyboard.
    """
    builder = InlineKeyboardBuilder()
    
    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)
    
    if add_main_menu:
        builder.button(text='⬅️ Bosh menu', callback_data='user_main_menu')
    
    if adjust_sizes:
        builder.adjust(*adjust_sizes)
    else:
        builder.adjust(2)  
    
    return builder.as_markup()

#search product section
def user_keyboard_back_to_search_section() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🔎 Qidiruv bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("🔎 Qidiruv bo'limi", "user_search_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def user_keyboard_back_to_parent_or_sub_categories() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📂 Kategoriyalar bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("📂 Bosh kategoriyalar", "user_back_to_parent_categories"),
        ("🗂 Sub kategoriyalar", "user_get_sub_categories_first_page:"),
        add_main_menu=False,
        adjust_sizes=[2]
    )

def user_keyboard_back_to_search_by_brand() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚘🔍 Brendi bo'yicha" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("🚘🔍 Brendi bo'yicha", "user_search_by_brand"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def user_keyboard_back_to_search_by_model() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚗🔍 Modeli bo'yicha" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("🚗🔍 Modeli bo'yicha", "user_search_by_model"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def user_keyboard_back_to_found_results(callback_prefix) -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "Back button to already founded results" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ('↩️ Orqaga', f"{callback_prefix}"),
        add_main_menu=False,
        adjust_sizes=[2]
    )

def user_keyboard_get_all_car_brands() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚗 Barcha mashina modellarini ko'rish" 
    """
    return user_create_keyboard(
        ("🚘 Barcha mashina brendlarini ko'rish", "user_get_all_car_brands"),
        add_main_menu=False,
        adjust_sizes=[2]
    )

def user_keyboard_get_all_car_models() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚗 Barcha mashina modellarini ko'rish"
    """
    return user_create_keyboard(
        ("🚗 Barcha mashina modellarini ko'rish", "user_get_all_car_models"),
        add_main_menu=False,
        adjust_sizes=[2]
    )

def user_keyboard_get_new_saved_item(callback_prefix) -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "New saved item" and buttons.
    """
    return user_create_keyboard(
        ("Ko'rish uchun bosing", f"{callback_prefix}"),
        add_main_menu=False,
        adjust_sizes=[1]
    )

#Catalog section
def user_keyboard_back_to_catalog() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🗂 Katalog bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("🗂 Katalog bo'limi", "user_catalog_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

#Profile section
def user_keyboard_back_to_profile() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "👤 Profil bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ('↩️ Orqaga', "user_profile_informations"),
        ("👤 Profil bo'limi", "user_profile_section"),
        add_main_menu=True,
        adjust_sizes=[1,2]
    )

#Orders section
def user_keyboard_back_to_order() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📜 Mening buyurtmalarim bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ('📜 Mening buyurtmalarim', "user_orders_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

#Cart section
def user_keyboard_back_to_cart() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🛒 Savat bo\'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ('🛒 Savat bo\'limi', "user_cart_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

#Product sell section
def user_keyboard_back_to_product_sell() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🛍️ Mahsulot sotish bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("🛍️ Mahsulot sotish bo'limi", "user_product_sell_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

#Reward section
def user_keyboard_back_to_rewards() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🎁 Sovg'alar bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("🎁 Sovg'alar bo'limi", "user_reward_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

#Help section
def user_keyboard_back_to_help_section() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "❓ Yordam" and "⬅️ Bosh menu" buttons.
    """
    return user_create_keyboard(
        ("❓ Yordam bo'limi", "user_help_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

# Handlers
@user_utils_router.callback_query(F.data.startswith("user_noop"))
async def user_handler_unclickble_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()

@user_utils_router.callback_query(F.data.startswith("user_delete_message"))
async def user_callback_message_handlers(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == 'user_delete_message':
        await callback_query.message.delete()

#handles search by single brand
@user_utils_router.callback_query(F.data.startswith("user_search_by_brand"))
async def user_handler_back_to_search_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    keyboard = user_keyboard_get_all_car_brands()
    keyboard.inline_keyboard.extend(user_keyboard_back_to_search_section().inline_keyboard)
    await callback_query.message.answer("Barcha mashina brendlarini ko'rish uchun quyidagi tugmani bosing", reply_markup=keyboard)
    sent_message = await callback_query.message.answer("Mashina brendini topish uchun uning nomini yozib yuboring 👇")
    await state.update_data(user_search_car_brand_message_id=sent_message.message_id)
    from telegram_bot.app.user.product import UserProductFSM
    await state.set_state(UserProductFSM.user_waiting_get_all_product_by_car_brand_name_search)
    await callback_query.answer()

#handles search by single model
@user_utils_router.callback_query(F.data.startswith("user_search_by_model"))
async def user_handler_back_to_search_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await user_delete_previous_messages(callback_query, state)
    keyboard = user_keyboard_get_all_car_models()
    keyboard.inline_keyboard.extend(user_keyboard_back_to_search_section().inline_keyboard)
    await callback_query.message.answer("Barcha mashina modellarini ko'rish uchun quyidagi tugmani bosing.", reply_markup=keyboard)
    sent_message = await callback_query.message.answer("Mashina modelini topish uchun uning nomini yozib yuboring 👇")
    await state.update_data(user_search_car_model_message_id=sent_message.message_id)
    from telegram_bot.app.user.product import UserProductFSM
    await state.set_state(UserProductFSM.user_waiting_all_products_by_car_model_name_search)
    await callback_query.answer()




# def user_single_item_buttons_markup() -> list[InlineKeyboardButton]:
#     """
#     Creates a list of InlineKeyboardButton objects.
#     """
#     return [
#         InlineKeyboardButton(text="⬅️ Bosh menu", callback_data="main_menu"),
#         InlineKeyboardButton(text="❌", callback_data="user_delete_message"),
#     ]

# def user_keyboard_back_to_announce() -> InlineKeyboardMarkup:
#     """
#     Creates a keyboard with "📣  E'lon berish" and "⬅️ Bosh menu" buttons.
#     """
#     return user_create_keyboard(
#         ("📣  E'lon berish bo'limi", "user_announce_section"),
#         add_main_menu=True,
#         adjust_sizes=[2]
#     )

