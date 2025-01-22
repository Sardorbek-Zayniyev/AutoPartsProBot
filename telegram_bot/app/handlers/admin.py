from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram_app.models import User
from handlers.utils import get_user_from_db

# Create a router for admin handlers
admin_router = Router()

# Admin Controls Keyboard


def admin_controls_keyboard():
    """
    Returns the inline keyboard markup for admin controls.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Add Admin",
                    callback_data="add_admin:add"
                ),
                InlineKeyboardButton(
                    text="Remove Admin",
                    callback_data="remove_admin:remove"
                ),
            ]
        ]
    )

# Add Admin Handler


@admin_router.callback_query(F.data == "add_admin")
async def add_admin_handler(callback: CallbackQuery):
    """
    Handles the Add Admin button click.
    """
    await callback.message.answer(
        "Iltimos, admin sifatida qo'shmoqchi bo'lgan foydalanuvchining kontaktini yuboring."
    )
    await callback.answer()


# Remove Admin Handler
@admin_router.callback_query(F.data == "remove_admin")
async def remove_admin_handler(callback: CallbackQuery):
    """
    Handles the Remove Admin button click.
    """
    await callback.message.answer(
        "Iltimos, adminlikdan olib tashlamoqchi bo'lgan foydalanuvchining kontaktini yuboring."
    )
    await callback.answer()


@admin_router.message(F.contact)
async def handle_admin_input(message: types.Message):

    contact = message.contact
    user = User.objects.get(User.phone_number == contact.phone_number)
    callback_data = message.get_callback_query().data

    if callback_data and callback_data.startswith("add_admin:add"):
        if user:
            user.is_admin = True
            user.save()
            await message.answer(f"Foydalanuvchi {user.full_name} admin sifatida belgilandi.")
        else:
            await message.answer("Bunday foydalanuvchi topilmadi yoki u ro'yxatdan o'tmagan.")
    elif callback_data and callback_data.startswith("remove_admin:remove"):
        if user:
            if user.is_admin:
                user.is_admin = False
                user.save()
                await message.answer(f"Foydalanuvchi {user.full_name} adminlikdan olib tashlandi.")
            else:
                await message.answer("Foydalanuvchi allaqachon admin emas.")
        else:
            await message.answer("Bunday foydalanuvchi topilmadi yoki u ro'yxatdan o'tmagan.")
    else:
        await message.answer("Unexpected action. Please try again using the buttons provided.")