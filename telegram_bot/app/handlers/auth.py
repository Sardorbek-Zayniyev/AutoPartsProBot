from aiogram import Router, F, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from telegram_app.models import User
from handlers.utils import get_user_from_db
from asgiref.sync import sync_to_async

# Create a router for auth handlers
auth_router = Router()

register_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Telefon raqamini yuborish",
                        request_contact=True)],
    ],
    resize_keyboard=True
)

# @auth_router.message(Command(commands=["register"]))
# async def handle_register(message: types.Message):
#     """
#     Handles the /register command.
#     """
#     existing_user = await get_user_from_db(message.from_user.id)

#     if existing_user:
#         await message.answer(
#             f"{message.from_user.full_name}, siz allaqachon ro'yxatdan o'tgansiz.",
#             reply_markup=None  # Hide the keyboard
#         )
#     else:
#         await start_register(message)


async def start_register(message: types.Message):
    """
    Prompts the user to send their phone number for registration.
    """
    await message.answer(
        "Ro'yxatdan o'tish uchun telefon raqamingizni yuborish tugmasini bosing.",
        reply_markup=register_keyboard
    )


@auth_router.message(F.contact)
async def handle_contact(message: types.Message):
    """
    Handles contact input during registration.
    """
    
    await register_user(message)


async def register_user(message: types.Message):
    """
    Handles the user registration process using the provided phone number.
    """
    contact = message.contact

    # Verify that the contact belongs to the sender
    if contact and contact.user_id == message.from_user.id:
        existing_user = await get_user_from_db(message.from_user.id)

        if not existing_user:
            new_user = await sync_to_async(User.objects.create)(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                phone_number=contact.phone_number,
            )
            await message.answer(
                "Ro'yxatdan o'tdingiz!\nEndi sizning profilingiz tayyor.",
                reply_markup=None  # Hide the keyboard
            )
        else:
            await message.answer("Siz allaqachon ro'yxatdan o'tgansiz.")
    else:
        await message.answer(
            'Bu profil sizga tegishli emas.\nIltimos, hozir yozayotgan telegram profilingiz raqamini yuboring.\n'
            'Buning uchun quyidagi "📞 Telefon raqamini yuborish" tugmasini bosing.'
        )


def include_auth_handlers(router: Router):
    """
    Includes auth handlers in the provided router.
    """
    router.include_router(auth_router)
