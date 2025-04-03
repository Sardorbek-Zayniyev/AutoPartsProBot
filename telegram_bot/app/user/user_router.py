from aiogram import Router
from telegram_bot.app.user.main_controls import main_controls_router
from telegram_bot.app.user.utils import user_utils_router 
from telegram_bot.app.user.product import user_product_router
from telegram_bot.app.user.cart import user_cart_router
from telegram_bot.app.user.catalog import user_catalog_router
from telegram_bot.app.user.user_profile import user_profile_router
from telegram_bot.app.user.reward import user_reward_router
from telegram_bot.app.user.order import user_order_router
from telegram_bot.app.user.help import user_help_router





user_router = Router()

user_router.include_router(main_controls_router)
user_router.include_router(user_utils_router)
user_router.include_router(user_product_router)
user_router.include_router(user_cart_router)
user_router.include_router(user_catalog_router)
user_router.include_router(user_profile_router)
user_router.include_router(user_reward_router)
user_router.include_router(user_order_router)
user_router.include_router(user_help_router)













