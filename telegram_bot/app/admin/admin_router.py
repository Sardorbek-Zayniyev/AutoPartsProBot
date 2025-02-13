from aiogram import Router
from telegram_bot.app.admin.main_controls import main_controls_router
from telegram_bot.app.admin.category import category_router
from telegram_bot.app.admin.product import product_router
from telegram_bot.app.admin.discount import discount_router
from telegram_bot.app.admin.promocode import promocode_router
from telegram_bot.app.admin.reward import reward_router



admin_router = Router()

admin_router.include_router(main_controls_router)
admin_router.include_router(category_router)
admin_router.include_router(product_router)
admin_router.include_router(discount_router)
admin_router.include_router(promocode_router)
admin_router.include_router(reward_router)