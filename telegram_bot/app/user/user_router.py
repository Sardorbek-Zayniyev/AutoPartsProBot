from aiogram import Router
from telegram_bot.app.user.main_controls import main_controls_router
from telegram_bot.app.user.catalog import catalog_router
from telegram_bot.app.user.product import product_router
from telegram_bot.app.user.cart import cart_router
from telegram_bot.app.user.order import order_router
from telegram_bot.app.user.reward import reward_router
from telegram_bot.app.user.user_profile import profile_router



user_router = Router()

user_router.include_router(main_controls_router)
user_router.include_router(catalog_router)
user_router.include_router(product_router)
user_router.include_router(cart_router)
user_router.include_router(order_router)
user_router.include_router(reward_router)
user_router.include_router(profile_router)













