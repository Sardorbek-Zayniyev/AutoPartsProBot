from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_bot.app.user.main_controls import PROFILE_CONTROLS_KEYBOARD


profile_router = Router()

class ProfileFSM(StatesGroup):
    waiting_viewing_profile = State()
    waiting_edit_full_name = State()
    waiting_new_full_name = State()
    waiting_edit_phone_number = State()
    waiting_new_phone_number = State()
    waiting_editing_address = State()
    waiting_choose_address_field = State()
    waiting_region_edit = State()
    waiting_city_edit = State()
    waiting_street_address_edit = State()




@profile_router.message(F.text.in_(("👤 Profil ma'lumotlari", "📍 Manzilni yangilash", "📱 Qo'shimcha raqam kiritish", "📝 Ismni yangilash")))
async def profile_controls_handler(message: Message, state: FSMContext):
    actions = {
        "👤 Profil ma'lumotlari": (ProfileFSM.waiting_viewing_profile, show_profile),
        "📍 Manzilni yangilash": (ProfileFSM.waiting_editing_address, edit_address),
        "📱 Qo'shimcha raqam kiritish": (ProfileFSM.waiting_edit_phone_number, edit_phone),
        "📝 Ismni yangilash": (ProfileFSM.waiting_edit_full_name, edit_name),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)



#Profile update part start
@profile_router.message(ProfileFSM.waiting_viewing_profile)
async def show_profile(message: Message, state: FSMContext):
    """
    Displays the user's profile information.
    """
    user = await get_user_from_db(message.from_user.id)
    if user:
        profile_info = (
            f"<b>Ismingiz:</b> <b>{user.full_name}</b>\n"
            f"<b>Telefon raqamingiz:</b> <b>{user.phone_number}</b>\n"
            f"<b>Qo'shimcha telefon raqamingiz:</b> <b>{user.extra_phone_number or 'Yo\'q'}</b>\n"
            f"<b>Manzilingiz:</b>\n" 
            f"<b>1.Viloyat:</b> <b>{(user.region) or 'Yo\'q'}</b>\n"
            f"<b>2.Shahar:</b> <b>{(user.city) or 'Yo\'q'}</b>\n"
            f"<b>3.Ko'cha nomi va uy raqami:</b> <b>{(user.street_address) or 'Yo\'q'}</b>\n"
        )
        await message.answer(profile_info, parse_mode="HTML")
       
    else:
        await message.answer("Profil ma'lumotlari topilmadi.")
    await state.clear()

# Edit address
@profile_router.message(ProfileFSM.waiting_editing_address)
async def edit_address(message: Message, state: FSMContext):
    address_keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Viloyat"), KeyboardButton(text="Shahar")],
        [KeyboardButton(text="Ko'cha"), KeyboardButton(text="👤 Profil")],
    ],
    resize_keyboard=True)
  
    await message.answer(f"Qaysi maydonini tahrirlamoqchisiz 👇:", reply_markup=address_keyboard)
    await state.set_state(ProfileFSM.waiting_choose_address_field)

@profile_router.message(ProfileFSM.waiting_choose_address_field)
async def choose_address_field(message: Message, state: FSMContext):
    field_name = message.text.strip().capitalize()

    field_actions = {
        "Viloyat": (ProfileFSM.waiting_region_edit, "region"),
        "Shahar": (ProfileFSM.waiting_city_edit, "city"),
        "Ko'cha": (ProfileFSM.waiting_street_address_edit, "street_address"),
    }

    if field_name in field_actions:
        next_state, field = field_actions[field_name]
        await state.set_state(next_state)

        if field_name.lower() == "ko'cha":
            await message.answer(f"Yangi {field_name.lower()}ning nomini, uy va xonodon raqamini kiriting:")
        else:
            await message.answer(f"Yangi {field_name.lower()}ning nomini kiriting:")
    else:
        await message.answer("❌ Noto'g'ri maydon tanlandi. Iltimos, ro'yxatdan birini tanlang.")

@profile_router.message(ProfileFSM.waiting_region_edit)
async def edit_region(message: Message, state: FSMContext):
    await update_user_address_field(message, state, "region", message.text.strip().capitalize())

@profile_router.message(ProfileFSM.waiting_city_edit)  
async def edit_city(message: Message, state: FSMContext):
    await update_user_address_field(message, state, "city", message.text.strip().capitalize())

@profile_router.message(ProfileFSM.waiting_street_address_edit)
async def edit_street(message: Message, state: FSMContext):
    await update_user_address_field(message, state, "street_address", message.text.strip().capitalize())

async def update_user_address_field(message: Message, state: FSMContext, field: str, new_value: str):
    user = await get_user_from_db(message.from_user.id)
    if user:
        setattr(user, field, new_value)
        await message.answer(f"Yangi '{new_value.capitalize()}' {field}i muvaffaqqiyatli saqlandi.")
        await sync_to_async(user.save)()
    else:
        await message.answer("User topilmadi.")
    await state.set_state(ProfileFSM.waiting_editing_address)
    await edit_address(message, state)
#Phone
@profile_router.message(ProfileFSM.waiting_edit_phone_number)
async def edit_phone(message: Message, state: FSMContext):
    await message.answer("Qo'shimcha telefon raqamingizni kiriting:")
    await state.set_state(ProfileFSM.waiting_new_phone_number)

@profile_router.message(ProfileFSM.waiting_new_phone_number)
async def update_phone_number(message: Message, state: FSMContext):
    new_phone_number = message.text.strip()
    try:
        # Ensure the input contains only digits
        if not new_phone_number.isdigit():
            raise ValueError("Faqat raqamlardan iborat telefon raqam kiriting.")

        # Ensure the phone number has at least 9 digits
        if len(new_phone_number) != 9 and len(new_phone_number) != 12:
            raise ValueError("Telefon raqam kamida 9 yoki 12 ta raqamdan iborat bo‘lishi kerak.\n1-na'muna. 998991234567\n2-na'muna 991234567")

        # If the phone number is 9 digits, prepend '998'
        if len(new_phone_number) == 9:
            new_phone_number = f"998{new_phone_number}"

        user = await get_user_from_db(message.from_user.id)
        if user:
            user.extra_phone_number = new_phone_number
            await sync_to_async(user.save)()
            await message.answer(f"Yangi telefon raqamingiz '{new_phone_number}' muvaffaqiyatli saqlandi.")
        else:
            await message.answer("User topilmadi.")

        await state.clear()

    except ValueError as e:
        await message.answer(str(e))
#Name
@profile_router.message(ProfileFSM.waiting_edit_full_name)
async def edit_name(message: Message, state: FSMContext):
    await message.answer("Yangi ismingizni kiriting:")
    await state.set_state(ProfileFSM.waiting_new_full_name)

@profile_router.message(ProfileFSM.waiting_new_full_name)
async def update_full_name(message: Message, state: FSMContext):
    new_full_name = message.text.strip()
    user = await get_user_from_db(message.from_user.id)
    if user:
        user.full_name = new_full_name
        await sync_to_async(user.save)()
        await message.answer(f"Yangi ismingiz '{new_full_name}' muvaffaqqiyatli saqlandi.")
    else:
        await message.answer("User topilmadi.")
    await state.clear()
#Profile update part end