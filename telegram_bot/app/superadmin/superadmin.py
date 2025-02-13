from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from telegram_bot.app.utils import get_user_from_db, set_as_admin, set_as_user

# Create a router for admin handlers
superadmin_router = Router()

# Define the FSM with StatesGroup


class AdminFSM(StatesGroup):
    adding_admin = State()
    removing_admin = State()


# Admin controls keyboard for Super Admin
SUPERADMIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Admin qo'shish")],
        [KeyboardButton(text="❌ Admin o'chirish")]
    ],
    resize_keyboard=True
)

# Handle button presses for adding/removing admins


@superadmin_router.message(lambda message: message.text in ["📝 Admin qo'shish", "❌ Admin o'chirish"])
async def start_admin_action(message: types.Message, state: FSMContext):
    """
    Initiates the process to add or remove an admin based on the button pressed.
    """
    existing_user = await get_user_from_db(message.from_user.id)

    if existing_user and existing_user.role == 'Superadmin':
        # Set the state for the user based on the action
        if message.text == "📝 Admin qo'shish":
            await state.set_state(AdminFSM.adding_admin)
            await message.answer("Admin qo'shish uchun foydalanuvchining telefon raqamini yuboring.")
        else:
            await state.set_state(AdminFSM.removing_admin)
            await message.answer("Adminni o'chirish uchun foydalanuvchining telefon raqamini yuboring.")
    else:
        await message.answer("Sizda bunday huquqlar yo'q.")

# Handle received contact and add/remove user based on the contact
@superadmin_router.message(lambda message: message.contact is not None)
async def handle_contact_for_admin(message: types.Message, state: FSMContext):
    """
    Handles contact input for adding/removing admins based on user's action.
    """
    contact = message.contact
    existing_user = await get_user_from_db(contact.user_id)

    if not existing_user:
        await message.answer("Siz ro'yxatdan o'tmagan foydalanuvchini yubordingiz.")
        return

    # Handle adding or removing the user based on the current state
    current_state = await state.get_state()

    if current_state == AdminFSM.adding_admin:
        if existing_user.role == 'Admin':
            await message.answer("Siz yuborgan foydalanuvchi allaqachon admin.")
        elif existing_user.role == 'User':
            user = await set_as_admin(contact.user_id)
            await message.answer(f"{user.full_name} admin sifatida qo'shildi!")
        await state.clear()  # Reset the FSM state after the action

    elif current_state == AdminFSM.removing_admin:
        if existing_user.role == 'User':
            await message.answer("Siz yuborgan foydalanuvchi allaqachon admin emas.")
        elif existing_user.role == 'Admin':
            user = await set_as_user(contact.user_id)
            await message.answer(f"{user.full_name} admin ro'lidan o'chirildi.")
        await state.clear()  # Reset the FSM state after the action

    else:
        await message.answer(f"{message.from_user.first_name} avval admin qo'shish yoki o'chirish tugmalaridan birini tanlang.")
