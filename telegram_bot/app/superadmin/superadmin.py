from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from telegram_bot.app.utils import get_user_from_db, IsSuperAdminFilter
from asgiref.sync import sync_to_async
from telegram_app.models import User

superadmin_router = Router()

class AdminFSM(StatesGroup):
    adding_admin = State()
    removing_admin = State()

#Utils
SUPERADMIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Admin qo'shish"), KeyboardButton(text="❌ Admin o'chirish")],
    ],
    resize_keyboard=True
)

@sync_to_async
def set_as_admin(telegram_id):
    user = User.objects.get(telegram_id=telegram_id)
    user.role = User.ADMIN
    user.save()
    return user

@sync_to_async
def set_as_user(telegram_id):
    user = User.objects.get(telegram_id=telegram_id)
    user.role = User.USER
    user.save()
    return user

@superadmin_router.message(IsSuperAdminFilter(), F.text.in_(("📝 Admin qo'shish", "❌ Admin o'chirish")))
async def start_admin_action(message: Message, state: FSMContext):
 
    existing_user = await get_user_from_db(message.from_user.id)

    if existing_user and existing_user.role == 'Superadmin':
        if message.text.strip() == "📝 Admin qo'shish":
            await state.set_state(AdminFSM.adding_admin)
            await message.answer("Admin qo'shish uchun foydalanuvchining telegram kontaktini.")
        else:
            await state.set_state(AdminFSM.removing_admin)
            await message.answer("Adminni o'chirish uchun foydalanuvchining telegram kontaktini.")
    else:
        await message.answer("Sizda bunday huquqlar yo'q.")

@superadmin_router.message(IsSuperAdminFilter(), F.contact)
async def handle_contact_for_admin(message: Message, state: FSMContext):
    contact = message.contact
    existing_user = await get_user_from_db(contact.user_id)

    if not existing_user:
        await message.answer("Siz ro'yxatdan o'tmagan foydalanuvchini yubordingiz.")
        return

    current_state = await state.get_state()

    if current_state == AdminFSM.adding_admin:
        if existing_user.role == 'Admin':
            await message.answer("Siz yuborgan foydalanuvchi allaqachon admin.")
        elif existing_user.role == 'User':
            user = await set_as_admin(contact.user_id)
            await message.answer(f"{user.full_name} admin sifatida qo'shildi!")
        await state.clear()

    elif current_state == AdminFSM.removing_admin:
        if existing_user.role == 'User':
            await message.answer("Siz yuborgan foydalanuvchi allaqachon admin emas.")
        elif existing_user.role == 'Admin':
            user = await set_as_user(contact.user_id)
            await message.answer(f"{user.full_name} admin ro'lidan o'chirildi.")
        await state.clear() 
    else:
        await message.answer(f"{message.from_user.first_name} avval admin qo'shish yoki o'chirish tugmalaridan birini tanlang.")

