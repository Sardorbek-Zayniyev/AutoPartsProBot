from aiogram import Router, types
from aiogram.filters import Command
from telegram_bot.app.superadmin.superadmin import SUPERADMIN_CONTROLS_KEYBOARD
from telegram_bot.app.auth import REGISTER_KEYBOARD
from telegram_bot.app.utils import get_user_from_db
from telegram_bot.app.admin.main_controls import ADMIN_MAIN_CONTROLS_KEYBOARD
from telegram_bot.app.user.main_controls import USER_MAIN_CONTROLS_KEYBOARD

start_router = Router()


@start_router.message(Command(commands=['start']))
async def start(message: types.Message):
    """
    Handle the /start command.
    """
    # Check if the user is in the database
    existing_user = await get_user_from_db(message.from_user.id)

    if existing_user and existing_user.role == 'Superadmin':
        await message.reply(
            "Xush kelibsiz, Super Admin!\nQuyidagilardan birini tanlang:",
            reply_markup=SUPERADMIN_CONTROLS_KEYBOARD
        )
    elif existing_user and existing_user.role == 'Admin':
        await message.reply(
            "Xush kelibsiz, Admin!\nQuyidagilardan birini tanlang:",
            reply_markup=ADMIN_MAIN_CONTROLS_KEYBOARD  # Admin tugmalarini ko'rsatish
        )
    # Registered user logic
    elif existing_user:
        await message.reply(
            f"{message.from_user.full_name} xush kelibsiz!\nSizni qayta ko'rganimizdan xursandmiz 😊",
            reply_markup=USER_MAIN_CONTROLS_KEYBOARD  # Remove buttons for registered users
        )
    else:
        # Unregistered user logic
        await message.reply(
            f"Assalomu alaykum! {
                message.from_user.full_name} AutoPartPro botiga xush kelibsiz!\n\n"
            "Ro'yxatdan o'tish uchun quyidagi tugmani bosing.",
            reply_markup=REGISTER_KEYBOARD  # Show register button
        )
