from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from handlers.utils import get_user_from_db, set_as_admin, set_as_user

# Create a router for admin handlers
superadmin_router = Router()

# Define the FSM with StatesGroup


class AdminFSM(StatesGroup):
    adding_admin = State()
    removing_admin = State()


# Admin controls keyboard for Super Admin
superadmin_controls_keyboard = ReplyKeyboardMarkup(
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


# from aiogram import Router, types, F
# from aiogram.filters import Command
# from telegram_app.models import User
# from handlers.utils import get_user_from_db, set_as_admin, set_as_user, save_user
# from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
# from asgiref.sync import sync_to_async

# # Create a router for admin handlers
# admin_router = Router()

# # Admin controls keyboard for Super Admin
# admin_controls_keyboard = ReplyKeyboardMarkup(
#     keyboard=[
#         [KeyboardButton(text="📝 Admin qo'shish")],
#         [KeyboardButton(text="❌ Admin o'chirish")]
#     ],
#     resize_keyboard=True
# )

# # Handle button presses for adding admins


# @admin_router.message(lambda message: message.text == "📝 Admin qo'shish")
# async def start_adding_admin(message: types.Message):
#     """
#     Initiates the process to add an admin after the button press.
#     """
#     existing_user = await get_user_from_db(message.from_user.id)
#     if existing_user and existing_user.role == 'Superadmin':
#         # Update the user's state to 'adding_admin' in the database
#         existing_user.action = 'adding_admin'
#         await save_user(existing_user)
#         await message.answer("Admin qo'shish uchun foydalanuvchining telefon raqamini yuboring.")
#     else:
#         await message.answer("Sizda bunday huquqlar yo'q.")

# # Handle button presses for removing admins


# @admin_router.message(lambda message: message.text == "❌ Admin o'chirish")
# async def start_removing_admin(message: types.Message):
#     """
#     Initiates the process to remove an admin after the button press.
#     """
#     existing_user = await get_user_from_db(message.from_user.id)
#     if existing_user and existing_user.role == 'Superadmin':
#         # Update the user's state to 'removing_admin' in the database
#         existing_user.action = 'removing_admin'
#         await save_user(existing_user)
#         await message.answer("Adminni o'chirish uchun foydalanuvchining telefon raqamini yuboring.")
#     else:
#         await message.answer("Sizda bunday huquqlar yo'q.")


# # Handle the received contact and add/remove user based on telegram contact
# @admin_router.message(F.contact)
# async def handle_contact_for_admin(message: types.Message):
#     """
#     Handles contact input for adding/removing admins.
#     """
#     contact = message.contact
#     if contact:
#         existing_user = await get_user_from_db(contact.user_id)
#         if not existing_user:
#             await message.answer("Siz ro'yxatdan o'tmagan foydalanuvchini yubordingiz.")
#             return
#         elif existing_user and existing_user.role == 'Admin':
#             await message.answer("Siz yuborgan foydalanuvchi allaqachon admin.")
#             return
#         elif existing_user and existing_user.role == 'User':
#             if existing_user.action == 'adding_admin':
#                 user = await set_as_admin(contact.user_id)
#                 await message.answer(f"{user.full_name} endi admin sifatida qo'shildi!")
#                 del existing_user.action
#                 await save_user(existing_user)
#             elif existing_user.action == 'removing_admin':
#                 user = await set_as_user(contact.user_id)
#                 await message.answer(f"{user.full_name} endi admin ro'lidan o'chirildi.")
#                 del existing_user.action
#                 await save_user(existing_user)
#             else:
#                 await message.answer("Iltimos, admin qo'shish yoki o'chirish amallarini tanlang.")
