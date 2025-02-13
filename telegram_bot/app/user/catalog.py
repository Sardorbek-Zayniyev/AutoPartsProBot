from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,CallbackQuery, Message
from aiogram.filters.state import StateFilter
from telegram_bot.app.utils import get_user_from_db
from telegram_bot.app.user.product import send_category_keyboard,handle_product_page,handle_product_other_pages
from telegram_bot.app.user.main_controls import CATALOG_CONTROLS_KEYBOARD
catalog_router = Router()


class CatalogFSM(StatesGroup):
    waiting_show_discounts = State()
    waiting_new_products_category = State()
    waiting_new_products = State()
    waiting_used_products = State()




@catalog_router.message(F.text.in_(("🔥 Aksiyalar", "🆕 Yangi", "🔄 B/U")))
async def catalog_controls_handler(message: Message, state: FSMContext):
    actions = {
        "🔥 Aksiyalar": (CatalogFSM.waiting_show_discounts, show_discounted_products_category),  
        "🆕 Yangi": (CatalogFSM.waiting_new_products, show_new_products_category), 
        "🔄 B/U": (CatalogFSM.waiting_used_products, show_used_products_category),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)




# search by new products
@catalog_router.message(StateFilter(CatalogFSM.waiting_new_products))
async def show_new_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "new_products")

@catalog_router.callback_query(F.data.startswith('new_products_first_page:'))
async def show_new_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality="new", callback_prefix="new_products")

@catalog_router.callback_query(F.data.startswith('new_products_other_pages:'))
async def show_new_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_other_pages(callback_query, state, quality="new", callback_prefix="new_products")

# search by new used products
@catalog_router.message(StateFilter(CatalogFSM.waiting_used_products))
async def show_used_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "used_products")

@catalog_router.callback_query(F.data.startswith('used_products_first_page:'))
async def show_used_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    quality__in="renewed, excellent, good, acceptable"
    await handle_product_page(callback_query, state, quality=quality__in, callback_prefix="used_products")

@catalog_router.callback_query(F.data.startswith('used_products_other_pages:'))
async def show_used_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    quality__in="renewed, excellent, good, acceptable"
    await handle_product_other_pages(callback_query, state, quality=quality__in, callback_prefix="used_products")

#Discounted products
@catalog_router.message(StateFilter(CatalogFSM.waiting_show_discounts))
async def show_discounted_products_category(message: Message, state: FSMContext):
    await send_category_keyboard(message, "discounted_products")

@catalog_router.callback_query(F.data.startswith('discounted_products_first_page:'))
async def show_discounted_products_first_page(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality=None, callback_prefix="discounted_products")

@catalog_router.callback_query(F.data.startswith('discounted_products_other_pages:'))
async def show_discounted_products_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_product_page(callback_query, state, quality=None, callback_prefix="discounted_products")
