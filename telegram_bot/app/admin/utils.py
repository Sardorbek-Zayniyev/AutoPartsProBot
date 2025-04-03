from aiogram import Router, F
import re, asyncio
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message

admin_utils_router = Router()

#Format info
admin_invalid_command_message = """~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\n
Qidirish uchun tegishli bo‘limga o'ting yoki quyidagi tugmalardan foydalaning 👇"""

admin_product_not_found_message = """~~~~~~~~~~~~~~~❌ Mahsulot topilmadi~~~~~~~~~~~~~~~~\n
Qidirish uchun tegishli bo‘limga o'ting yoki quyidagi tugmalardan foydalaning 👇"""

def admin_escape_markdown(text: str) -> str:
    """Escapes special characters for Telegram MarkdownV2."""
    return re.sub(r'([_*\[\]()~`>#+-=|{}.!])', r'\\\1', text)

async def admin_send_typing_action(callback_query_or_message):
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

async def admin_delete_previous_messages(callback_query_or_message, state: FSMContext):
    data = await state.get_data()
    message_ids = data.get("message_ids", [])  

    if not isinstance(message_ids, list): 
        message_ids = [message_ids]

    await admin_send_typing_action(callback_query_or_message)

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

async def admin_check_state_data(state: FSMContext, message: Message = None, callback_query: CallbackQuery = None):
    data = await state.get_data()
    if not data:
        text = "❌ Xatolik: Ma'lumot topilmadi. Sahifani qayta yuklang."
        if message:
            sent_message = await message.answer(text)
        elif callback_query:
            sent_message = await callback_query.answer(text, show_alert=True)
        try:
            await asyncio.sleep(3)
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)
        except:
            pass
        return None
    return data

#Reply keyboards
ADMIN_CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="◀️ Bosh menu"), KeyboardButton(text="🚫 Jarayonni bekor qilish")],
        [KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)

ADMIN_ACTIVITY_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="◀️ Bosh menu"), KeyboardButton(text="🚫 Jarayonni bekor qilish")],
        [KeyboardButton(text="✅ Faol"), KeyboardButton(text="❌ Nofaol")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)

def admin_get_cancel_reply_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="◀️ Bosh menu"), KeyboardButton(text="🚫 Jarayonni bekor qilish"))
    builder.adjust(2)
    return builder

#Inline keyboards
def admin_create_keyboard(*buttons: list[tuple[str, str]], add_main_menu: bool = False, adjust_sizes: list[int] = None) -> InlineKeyboardMarkup:
    """
    Helper function to create an inline keyboard with the given buttons.
    Args:
        buttons: A list of tuples where each tuple contains (text, callback_data).
        add_main_menu: If True, adds a "◀️ Bosh menu" button.
        adjust_sizes: A list of integers defining the number of buttons per row.
                      If None, defaults to 2 buttons per row.
    Returns:InlineKeyboardMarkup: The generated inline keyboard.
    """
    builder = InlineKeyboardBuilder()
    
    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)
    
    if add_main_menu:
        builder.button(text='◀️ Bosh menu', callback_data='admin_main_menu')
    
    if adjust_sizes:
        builder.adjust(*adjust_sizes)
    else:
        builder.adjust(2)  
    
    return builder.as_markup()

def admin_single_item_buttons() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with a single "❌" button.
    """
    buttons = [
        ("❌", "admin_delete_message"),
        ("◀️ Bosh menu", "admin_main_menu"),
        ]
    return admin_create_keyboard(
        *buttons,
        add_main_menu=False,  
        adjust_sizes=[2] 
    )

def admin_single_item_buttons_markup() -> list[InlineKeyboardButton]:
    """
    Creates a list of InlineKeyboardButton objects.
    """
    return [
        InlineKeyboardButton(text="◀️ Bosh menu", callback_data="main_menu"),
        InlineKeyboardButton(text="❌", callback_data="admin_delete_message"),
    ]

def admin_delete_confirmation_keyboard(callback_prefix: str, model_id: int) -> InlineKeyboardMarkup:
    """
    Creates a confirmation keyboard for deletion with "✅ Ha" and "❌ Yo‘q" buttons.
    """
    buttons = [
        ("✅ Ha", f"{callback_prefix}_confirm_delete:{model_id}"),
        ("❌ Yo‘q", f"{callback_prefix}_cancel_delete:{model_id}"),
    ]
    return admin_create_keyboard(
        *buttons,
        add_main_menu=False,  
        adjust_sizes=[2]  
    )

def admin_skip_inline_button(callback_prefix: str) -> InlineKeyboardMarkup:
    """
    Creates a keyboard with a single "⏭ O‘tkazib yuborish" button.
    """
    return admin_create_keyboard(
        ("⏭ O‘tkazib yuborish", f"{callback_prefix}_skip_step"),
        add_main_menu=False,  
        adjust_sizes=[2]  
    )

def admin_keyboard_back_to_main_menu() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with only the "◀️ Bosh menu" button.
    """
    return admin_create_keyboard(add_main_menu=True, adjust_sizes=[1])

def admin_keyboard_back_to_category() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📂 Kategoriya bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("📂 Kategoriya bo'limi", "admin_category_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_discount() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🏷️ Chegirmalar bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("🏷️ Chegirmalar bo'limi", "admin_discount_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_add_products_to_discount() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "Mahsulotni chegirmaga qo'shish" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("✅ Tanlangan mahsulotlarni qo'shish", "admin_confirm_products_to_discount"),
        ("🏷️ Chegirmalar bo'limi", "admin_discount_section"),
        add_main_menu=True,
        adjust_sizes=[1,2]
    )

def admin_keyboard_remove_products_from_discount() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "Mahsulotni chegirmadan olib tashlash" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("✅ Tanlangan mahsulotlarni olib tashlash", "admin_confirm_remove_discounted_products"),
        ("🏷️ Chegirmalar bo'limi", "admin_discount_section"),
        add_main_menu=True,
        adjust_sizes=[1,2]
    )

def admin_keyboard_back_to_product() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📦 Mahsulot bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("📦 Mahsulot bo'limi", "admin_product_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_search_by_brand() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚘🔍 Brendi bo'yicha" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("🚘🔍 Brendi bo'yicha", "admin_search_by_brand"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_search_by_model() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚗🔍 Modeli bo'yicha" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("🚗🔍 Modeli bo'yicha", "admin_search_by_model"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_product_edit() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "✒️ Mahsulotni tahrirlash bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("✒️ Tahrirlash bo'limi", "admin_product_edit_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_order() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📜 Buyurtmalar bo'limiga qaytish" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("📜 Buyurtmalar bo'limi", "admin_order_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_promocode() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🔖 Promokodlar bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("🔖 Promokodlar bo'limi", "admin_promocode_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_reward() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🎁 Sovg'alar bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("🎁 Sovg'alar bo'limi", "admin_reward_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_announce() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📣  E'lon berish" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("📣  E'lon berish bo'limi", "admin_announce_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_users_products() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📢 Foydalanuvchi mahsulotlarini boshqarish bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("📢 Foydalanuvchi mahsulotlari bo'limi", "admin_users_products_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_parent_or_sub_categories() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "📂 Kategoriyalar bo'limi" and "◀️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("📂 Bosh kategoriyalar", "admin_back_to_parent_categories"),
        ("🗂 Sub kategoriyalar", "admin_get_sub_categories_first_page:"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_found_results(callback_prefix) -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "Back button to already founded results" and "◀️ Bosh menu" buttons.
    """
    text = '↩️ Orqaga'
    return admin_create_keyboard(
        (text, f"{callback_prefix}"),
        add_main_menu=False,
        adjust_sizes=[2]
    )

def admin_keyboard_back_to_appeals_section() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "❓ Murojaatlar bo'limi" and "⬅️ Bosh menu" buttons.
    """
    return admin_create_keyboard(
        ("❓ Murojaatlar bo'limi", "admin_help_section"),
        add_main_menu=True,
        adjust_sizes=[2]
    )

def admin_keyboard_get_new_saved_item(callback_prefix) -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "New saved item" and buttons.
    """
    return admin_create_keyboard(
        ("Ko'rish uchun bosing", f"{callback_prefix}"),
        add_main_menu=False,
        adjust_sizes=[1]
    )

def admin_keyboard_get_all_car_brands() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚗 Barcha mashina modellarini ko'rish" 
    """
    return admin_create_keyboard(
        ("🚘 Barcha mashina brendlarini ko'rish", "admin_get_all_car_brands"),
        add_main_menu=False,
        adjust_sizes=[2]
    )

def admin_keyboard_get_all_car_models() -> InlineKeyboardMarkup:
    """
    Creates a keyboard with "🚗 Barcha mashina modellarini ko'rish"
    """
    return admin_create_keyboard(
        ("🚗 Barcha mashina modellarini ko'rish", "admin_get_all_car_models"),
        add_main_menu=False,
        adjust_sizes=[2]
    )


#Handlers Callback

#handles unclickble keyboards
@admin_utils_router.callback_query(F.data.startswith("admin_noop"))
async def admin_handler_unclickble_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()

#handles ❌ button
@admin_utils_router.callback_query(F.data.startswith("admin_delete_message"))
async def admin_callback_message_handlers(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == 'admin_delete_message':
        await callback_query.message.delete()


@admin_utils_router.callback_query(F.data.startswith("admin_search_by_brand"))
async def admin_handler_back_to_search_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    keyboard = admin_keyboard_get_all_car_brands()
    keyboard.inline_keyboard.extend(admin_keyboard_back_to_product_edit().inline_keyboard)
    await callback_query.message.answer("Barcha mashina brendlarini ko'rish uchun quyidagi tugmani bosing", reply_markup=keyboard)
    sent_message = await callback_query.message.answer("Mashina brendini topish uchun uning nomini yozib yuboring 👇")
    await state.update_data(admin_search_car_brand_message_id=sent_message.message_id)
    from telegram_bot.app.admin.product import AdminProductFSM
    await state.set_state(AdminProductFSM.admin_waiting_get_all_product_by_car_brand_name_search)
    await callback_query.answer()

#handles search by single model
@admin_utils_router.callback_query(F.data.startswith("admin_search_by_model"))
async def admin_handler_back_to_search_section_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_delete_previous_messages(callback_query, state)
    keyboard = admin_keyboard_get_all_car_models()
    keyboard.inline_keyboard.extend(admin_keyboard_back_to_product_edit().inline_keyboard)
    await callback_query.message.answer("Barcha mashina modellarini ko'rish uchun quyidagi tugmani bosing.", reply_markup=keyboard)
    sent_message = await callback_query.message.answer("Mashina modelini topish uchun uning nomini yozib yuboring 👇")
    await state.update_data(admin_search_car_model_message_id=sent_message.message_id)
    from telegram_bot.app.admin.product import AdminProductFSM
    await state.set_state(AdminProductFSM.admin_waiting_all_products_by_car_model_name_search)
    await callback_query.answer()



# #############################################################################
from pprint import pprint
import sqlparse
from django.db import connection
from asgiref.sync import sync_to_async
async def sardor():
    """SQL so‘rovlarni async muhitda loglash"""
    @sync_to_async
    def get_queries():
        return connection.queries
    queries = await get_queries()
    if not queries:
        print("❌ No queries executed.")
        return
    print("\n🔍 SQL QUERIES LOG")
    print("=" * 80)
    for index, query in enumerate(queries, start=1):
        formatted_sql = sqlparse.format(query["sql"], reindent=True, keyword_case="upper")
        print(f"📌 Query {index}:")
        print(f"   ⏳ Time: {query['time']}s")
        print(f"   📄 SQL: \n{formatted_sql}")
        print("-" * 80)
# # ##############################################################################
