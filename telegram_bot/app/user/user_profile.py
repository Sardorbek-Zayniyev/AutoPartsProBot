from aiogram import Router, F
import asyncio, re
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsUserFilter
from telegram_bot.app.user.utils import user_keyboard_back_to_profile


user_profile_router = Router()

class UserProfileFSM(StatesGroup):
    user_waiting_viewing_profile = State()

    user_waiting_choose_address_field = State()
    user_waiting_region_edit = State()
    user_waiting_city_edit = State()

    user_waiting_new_street_address_edit = State()
    user_waiting_new_full_name = State()
    user_waiting_new_phone_number = State()

def user_format_profile_info(user):
    return (
            f"1.<b>Ismingiz:</b> <b>{user.full_name}</b>\n"
            f"2.<b>Telefon raqamingiz:</b> <b>{user.phone_number}</b>\n"
            f"3.<b>Qo'shimcha telefon raqamingiz:</b> <b>{user.extra_phone_number or 'Yo\'q'}</b>\n"
            f"4.<b>Manzilingiz:</b>\n" 
            f"— <b>1.Viloyat:</b> <b>{(user.region) or 'Yo\'q'}</b>\n"
            f"— <b>2.Shahar:</b> <b>{(user.city) or 'Yo\'q'}</b>\n"
            f"— <b>3.Ko'cha nomi va uy raqami:</b> <b>{(user.street_address) or 'Yo\'q'}</b>\n"
    ) 

def user_format_address_info(user):
    return (
        f"<b>Manzilingiz:</b>\n" 
            f"— <b>1.Viloyat:</b> <b>{(user.region) or 'Yo\'q'}</b>\n"
            f"— <b>2.Shahar:</b> <b>{(user.city) or 'Yo\'q'}</b>\n"
            f"— <b>3.Ko'cha nomi va uy raqami:</b> <b>{(user.street_address) or 'Yo\'q'}</b>\n"
    )

def user_profile_edit_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📍 Manzilni yangilash", callback_data="user_edit_address"), 
        InlineKeyboardButton(text="📱 Qo'shimcha raqam kiritish", callback_data="user_edit_phone"),
        InlineKeyboardButton(text="📝 Ismni yangilash", callback_data="user_edit_name"),
        InlineKeyboardButton(text="⬅️ Bosh menu", callback_data="user_main_menu"), 
    )
    builder.adjust(2)
    return builder.as_markup()

def user_address_edit_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="Viloyat", callback_data="user_region"), 
        InlineKeyboardButton(text="Shahar", callback_data="user_city"),
        InlineKeyboardButton(text="Ko'cha", callback_data="user_street_address")
    )
    builder.adjust(3)
    builder.attach(InlineKeyboardBuilder.from_markup(user_keyboard_back_to_profile()))
    return builder.as_markup()

async def user_update_and_clean_message_profile(message: Message, chat_id: int, message_id: int, info: str, keyboard):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=info,
        parse_mode='HTML',
        reply_markup=keyboard()
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

async def user_update_user_address_field(message: Message, state: FSMContext, field: str, new_value: str):
    user = await get_user_from_db(message.from_user.id)
    data = await state.get_data()
    message_id, chat_id = data.get("message_id"), data.get("chat_id")
    if user:
        setattr(user, field, new_value)
        field = data.get('field')
        sent_message = await message.answer(f"✅ Manzil '{new_value.capitalize()}' {field} muvaffaqqiyatli yangilandi. 👆")
        await sync_to_async(user.save)()
        address_info = user_format_address_info(user)
        if message_id and chat_id:
            await user_update_and_clean_message_profile(message, chat_id, message_id, address_info, user_address_edit_keyboard)
        await asyncio.sleep(3)
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)
        except Exception as e:
            print({e})
    else:
        await message.answer("User topilmadi.")

# Profile update part start
@user_profile_router.message(UserProfileFSM.user_waiting_viewing_profile)
async def user_show_profile(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
   
    if user:
        profile_info = user_format_profile_info(user)
        sent_message = await message.answer(profile_info, parse_mode="HTML", reply_markup=user_profile_edit_keyboard())
        await state.update_data(message_id=sent_message.message_id, chat_id=message.chat.id)
    else:
        await message.answer("Profil ma'lumotlari topilmadi.", reply_markup=user_keyboard_back_to_profile())
        await state.clear()


@user_profile_router.callback_query(IsUserFilter(), F.data.startswith("user_profile_informations"))
async def user_handler_back_to_profile_informations_keyboard(callback_query: CallbackQuery, state: FSMContext):
    callback_query.answer()
    user = await get_user_from_db(callback_query.from_user.id)
    if user:
        profile_info = user_format_profile_info(user)
        sent_message = await callback_query.message.edit_text(profile_info, parse_mode="HTML", reply_markup=user_profile_edit_keyboard())
        await state.update_data(message_id=sent_message.message_id, chat_id=callback_query.message.chat.id)
    else:
        await callback_query.answer("Profil ma'lumotlari topilmadi.", reply_markup=user_keyboard_back_to_profile())
        await state.clear()

# Edit address
@user_profile_router.callback_query(IsUserFilter(), F.data.startswith('user_edit_address'))
async def user_handler_edit_address(callback_query: CallbackQuery, state: FSMContext):
    user = await get_user_from_db(callback_query.from_user.id)
    address = (
            f"<b>Manzilingiz:</b>\n" 
            f"|— <b>1.Viloyat:</b> <b>{(user.region) or 'Yo\'q'}</b>\n"
            f"|— <b>2.Shahar:</b> <b>{(user.city) or 'Yo\'q'}</b>\n"
            f"|— <b>3.Ko'cha nomi va uy raqami:</b> <b>{(user.street_address) or 'Yo\'q'}</b>\n"
    ) 
    await callback_query.message.edit_text(address, parse_mode='HTML', reply_markup=user_address_edit_keyboard())

@user_profile_router.callback_query(IsUserFilter(), F.data.startswith("user_region"))
async def user_handler_edit_state_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(f"Yangi viloyat nomini kiriting:")
    await callback_query.answer()
    await state.set_state(UserProfileFSM.user_waiting_region_edit)
    await state.update_data(field='viloyati')

@user_profile_router.callback_query(IsUserFilter(), F.data.startswith("user_city"))
async def user_handler_edit_city_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(f"Yangi shahar nomini kiriting:")
    await callback_query.answer()
    await state.set_state(UserProfileFSM.user_waiting_city_edit)
    await state.update_data(field='shahri')

@user_profile_router.callback_query(IsUserFilter(), F.data.startswith("user_street_address"))
async def user_handler_edit_street_keyboard(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(f"Yangi ko'chaning nomini, uy va xonodon raqamini kiriting:")
    await callback_query.answer()
    await state.set_state(UserProfileFSM.user_waiting_new_street_address_edit)
    await state.update_data(field='ko\'chasi')

@user_profile_router.message(UserProfileFSM.user_waiting_region_edit)
async def user_edit_region(message: Message, state: FSMContext):
    await user_update_user_address_field(message, state, "region", message.text.strip().capitalize())

@user_profile_router.message(UserProfileFSM.user_waiting_city_edit)  
async def user_edit_city(message: Message, state: FSMContext):
    await user_update_user_address_field(message, state, "city", message.text.strip().capitalize())

@user_profile_router.message(UserProfileFSM.user_waiting_new_street_address_edit)
async def user_edit_street(message: Message, state: FSMContext):
    if message.text.strip().isdigit():
        await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\n"
                            "Kiritilgan ko'cha nomi faqat raqamdan iborat bo'lishi mumkin emas.\n"
                            "Na'muna 1: Barhayot ko'chasi 52-uy\n"
                            "Na'muna 2: Chilonzor 5-mavze 40-uy 81-xonadon\n\n"
                            "Ko'cha nomi va raqamini kiriting 👇")
        return
    elif re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ\'\- ]+", message.text.strip()):  
        await message.reply("~~~~~~~~~~~~~~~~~~~~~~❌ Xatolik~~~~~~~~~~~~~~~~~~~~~~\n"
                        "Kiritilgan ko'cha nomi faqat matndan iborat bo'lishi mumkin emas.\n"
                        "Na'muna 1: Barhayot ko'chasi 52-uy\n"
                        "Na'muna 2: Chilonzor 5-mavze 40-uy 81-xonadon\n\n"
                        "Ko'cha nomi va raqamini kiriting 👇")
        return
    await user_update_user_address_field(message, state, "street_address", message.text.strip().capitalize())


# Phone
@user_profile_router.callback_query(IsUserFilter(), F.data.startswith('user_edit_phone'))
async def user_handler_edit_phone(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Qo'shimcha telefon raqamingizni kiriting\nnamuna: 998991234567 yoki 991234567")
    await state.set_state(UserProfileFSM.user_waiting_new_phone_number)

@user_profile_router.message(UserProfileFSM.user_waiting_new_phone_number)
async def user_update_phone_number(message: Message, state: FSMContext):
    new_phone_number = message.text.strip()
    data = await state.get_data()
    message_id, chat_id = data.get("message_id"), data.get("chat_id")
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
            sent_message = await message.answer(f"✅Qo'shimcha telefon raqam '{new_phone_number}' muvaffaqiyatli saqlandi.👆")
            profile_info = user_format_profile_info(user)
            if message_id and chat_id:
                await user_update_and_clean_message_profile(message, chat_id, message_id, profile_info, user_profile_edit_keyboard)
            await asyncio.sleep(3)
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)
            except Exception as e:
                print({e})
        else:
            await message.answer("User topilmadi.")
    except ValueError as e:
        await message.answer(str(e))

# Name
@user_profile_router.callback_query(IsUserFilter(), F.data.startswith('user_edit_name'))
async def user_handler_edit_name(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Yangi ismingizni kiriting:")
    await state.set_state(UserProfileFSM.user_waiting_new_full_name)

@user_profile_router.message(UserProfileFSM.user_waiting_new_full_name)
async def user_update_full_name(message: Message, state: FSMContext):
    new_full_name = message.text.strip()
    user = await get_user_from_db(message.from_user.id)
    data = await state.get_data()
    message_id, chat_id = data.get("message_id"), data.get("chat_id")
    if user:
        user.full_name = new_full_name
        await sync_to_async(user.save)()
        sent_message = await message.answer(f"✅Ismingiz '{new_full_name}' muvaffaqqiyatli saqlandi.👆")
        profile_info = user_format_profile_info(user)

        if message_id and chat_id:
            await user_update_and_clean_message_profile(message, chat_id, message_id, profile_info, user_profile_edit_keyboard)

        await asyncio.sleep(3)
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent_message.message_id)
        except Exception as e:
            print({e})
    else:
        await message.answer("User topilmadi.")
    await state.clear()

# Profile update part end