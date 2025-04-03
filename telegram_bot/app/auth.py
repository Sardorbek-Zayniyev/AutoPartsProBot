from aiogram import Router, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from telegram_app.models import User
from telegram_bot.app.utils import get_user_from_db
from asgiref.sync import sync_to_async
from aiogram.filters import BaseFilter
from telegram_bot.app.user.main_controls import USER_PROFILE_CONTROLS_KEYBOARD

class IsNotRegisteredUser(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = await get_user_from_db(message.from_user.id)
        return user is None

auth_router = Router()

REGISTER_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📞 Telefon raqamini yuborish", request_contact=True)],],
    resize_keyboard=True,
    one_time_keyboard=True
)

async def start_register(message: Message):
    await message.answer( "Ro'yxatdan o'tish uchun telefon raqamingizni yuborish tugmasini bosing. 👇",
        reply_markup=REGISTER_KEYBOARD
    )

async def register_user(message: Message):
    """
    Handles the user registration process using the provided phone number.
    """
    contact = message.contact
    clean_phone_number = message.contact.phone_number.lstrip("+")
    # Verify that the contact belongs to the sender
    if contact and contact.user_id == message.from_user.id:
        existing_user = await get_user_from_db(message.from_user.id)

        if not existing_user:
            new_user = await sync_to_async(User.objects.create)(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                phone_number=clean_phone_number,
            )
            await message.answer(
                f"Tabrilaymiz {new_user.full_name} 😊\nRo'yxatdan muvaffaqqiyatli o'tdingiz!\nEndi sizning profilingiz tayyor.\n\nKelgusidagi qulayliklar uchun profil ma'lumotlaringizni to'ldirib olishni maslahat beramiz.",
                reply_markup=USER_PROFILE_CONTROLS_KEYBOARD
            )
        else:
            await message.answer("Siz allaqachon ro'yxatdan o'tgansiz.")
    else:
        await message.answer(
            'Bu profil sizga tegishli emas❗️\n\nHurmatli foydalanuvchi, hozir yozayotgan telegram profilingiz raqamini yuboring.\n\n'
            'Buning uchun quyidagi "📞 Telefon raqamini yuborish" tugmasini bosing 👇'
        )

@auth_router.message(IsNotRegisteredUser(), F.contact)
async def handle_contact(message: Message):
    """
    Handles contact input during registration.
    """
    await register_user(message)
