from aiogram import Router, types
from aiogram.filters import Command
from telegram_app.models import User
from handlers.admin import admin_controls_keyboard
from handlers.auth import register_keyboard
from handlers.utils import get_user_from_db

# Create a router for the start handlers
start_router = Router()

# Super Admin IDs
SUPER_ADMIN_IDS = [6895525941]  # Replace with actual super admin IDs


@start_router.message(Command(commands=['start']))
async def start(message: types.Message):
    """
    Handle the /start command.
    """
    # Check if the user is in the database
    existing_user = get_user_from_db(message.from_user.id)

    # Super admin-specific logic
    if message.from_user.id in SUPER_ADMIN_IDS:
        await message.reply(
            "Xush kelibsiz, Super Admin!\nQuyidagilardan birini tanlang:",
            reply_markup=admin_controls_keyboard()
        )
    # Registered user logic
    elif existing_user:
        await message.reply(
            f"{message.from_user.full_name} xush kelibsiz!\nSizni qayta ko'rganimizdan xursandmiz 😊",
            reply_markup=None  # Remove buttons for registered users
        )
    else:
        # Unregistered user logic
        await message.reply(
            f"Assalomu alaykum! {message.from_user.full_name} AutoPartPro botiga xush kelibsiz!\n\n"
            "Ro'yxatdan o'tish uchun quyidagi tugmani bosing.",
            reply_markup=register_keyboard  # Show register button
        )