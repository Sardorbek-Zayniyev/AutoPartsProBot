from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from telegram_bot.app.utils import IsUserFilter
from telegram_bot.app.user.product import user_send_catalog_inline_keyboard

user_catalog_router = Router()

class UserCatalogFSM(StatesGroup):
    user_waiting_get_new_products = State()
    user_waiting_get_used_products = State()
    user_waiting_get_discounted_products = State()

# Search by new products
@user_catalog_router.message(UserCatalogFSM.user_waiting_get_new_products)
async def user_display_parent_category_selection_for_get_new_products_category(message: Message, state: FSMContext):
    await user_send_catalog_inline_keyboard(message, "user_get_sub_categories_new_products", state, 'user_parent_category')

@user_catalog_router.callback_query(IsUserFilter(), F.data.startswith('user_get_sub_categories_new_products_first_page:'))
async def user_display_sub_category_selection_for_get_new_products(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    try:
        id = int(callback_query.data.split(':')[1])
        await state.update_data(parent_category_id=id)
    except:
        pass
    await user_send_catalog_inline_keyboard(callback_query.message, "user_all_products", state, 'user_sub_category', quality="new")

# Search by used products
@user_catalog_router.message(UserCatalogFSM.user_waiting_get_used_products)
async def user_display_parent_category_selection_for_get_used_products_category(message: Message, state: FSMContext):
    await user_send_catalog_inline_keyboard(message, "user_get_sub_categories_used_products", state, 'user_parent_category')

@user_catalog_router.callback_query(IsUserFilter(), F.data.startswith('user_get_sub_categories_used_products_first_page:'))
async def user_display_sub_category_selection_for_get_used_products(callback_query: CallbackQuery, state: FSMContext):
    quality__in = "renewed, excellent, good, acceptable"
    await callback_query.answer()
    try:
        id = int(callback_query.data.split(':')[1])
        await state.update_data(parent_category_id=id)
    except:
        pass
    await user_send_catalog_inline_keyboard(callback_query.message, "user_all_products", state, 'user_sub_category', quality=quality__in)

# Search by discounted products
@user_catalog_router.message(UserCatalogFSM.user_waiting_get_discounted_products)
async def user_display_parent_category_selection_for_get_discounted_products_category(message: Message, state: FSMContext):
    await user_send_catalog_inline_keyboard(message, "user_get_sub_categories_discounted_products", state, 'user_parent_category', quality='discounted_products')

@user_catalog_router.callback_query(IsUserFilter(), F.data.startswith('user_get_sub_categories_discounted_products_first_page:'))
async def user_display_sub_category_selection_for_get_used_products(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    try:
        id = int(callback_query.data.split(':')[1])
        await state.update_data(parent_category_id=id)
    except:
        pass
    await user_send_catalog_inline_keyboard(callback_query.message, "user_all_products", state, 'user_sub_category', quality='discounted_products')

