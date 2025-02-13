from aiogram import Router, F
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Reward
from telegram_bot.app.admin.utils import skip_inline_button, single_item_buttons, confirmation_keyboard, ACTIVITY_KEYBOARD
from telegram_bot.app.admin.main_controls import REWARD_CONTROLS_KEYBOARD

reward_router = Router()

#Reply keyboards




#Reward part start
class RewardFSM(StatesGroup):
    #get
    waiting_get_all_reward = State()

    #add
    waiting_reward_add = State()
    waiting_reward_type = State()
    waiting_reward_name = State()
    waiting_reward_points_required = State()
    waiting_reward_description = State()
    waiting_reward_activity = State()

    #edit
    waiting_edit_reward = State()
    waiting_search_reward_by_name = State()
    waiting_edit_reward_type = State() 
    waiting_edit_reward_name = State()
    waiting_edit_reward_points_required = State()
    waiting_edit_reward_description = State()
    waiting_edit_reward_activity = State()
    waiting_edit_reward_deletion = State()

#Utils
async def format_reward_info(reward):
    reward_info = (
        f"🎁 Sovg'a nomi: *{reward.name}*\n"
        f"📌 Sovg'a turi: *{dict(reward.REWARD_TYPES).get(reward.reward_type, 'Noma’lum')}*\n"
        f"🔢 Kerakli ball: *{reward.points_required}*\n"
        f"📄 Tavsif: *{"Yo'q" if not reward.description else reward.description}*\n"
        f"✅ Faollik: *{'Faol ✅' if reward.is_active else 'Nofaol ❌'}*\n"
    )
    return reward_info

async def reward_edit_keyboard(reward_id):
    fields = ['Sovg\'a nomi','Sovg\'a turi', 'Kerakli ballar', 'Tavsif', 'Faollik']
    keyboard = []
    for i in range(0, len(fields), 2):
        row = [
            InlineKeyboardButton(text=fields[i], callback_data=f"reward_field_{fields[i]}:{reward_id}")
        ]
        if i + 1 < len(fields):
            row.append(InlineKeyboardButton(text=fields[i + 1], callback_data=f"reward_field_{fields[i+1]}:{reward_id}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🗑 Sovg'ani o'chirish", callback_data=f"reward_delete:{reward_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Bosh menu", callback_data="◀️ Bosh menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def handle_reward_search_results(message: Message, rewards, state: FSMContext):
    if not rewards:
        await message.answer("❌ Hech qanday reward topilmadi.")
        return
    
    await state.update_data(search_results=rewards)
    
    rewards_with_numbers = [(index + 1, reward) for index, reward in enumerate(rewards)]
    total_pages = ((len(rewards_with_numbers) + 9) // 10)
    await display_rewards_page(1, message, rewards_with_numbers, total_pages, 10, "search_reward", state)

async def handle_reward_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    
    page_num = int(data_parts[1])
    state_data = await state.get_data()
    rewards = state_data.get("search_results", [])
   
    rewards_with_numbers = [(index + 1, reward) for index, reward in enumerate(rewards)]
    rewards_per_page = 10
    total_pages = (len(rewards_with_numbers) + rewards_per_page - 1) // rewards_per_page
    
    await display_rewards_page(page_num, callback_query, rewards_with_numbers, total_pages, rewards_per_page, callback_prefix, state)
    await callback_query.answer()

async def display_rewards_page(page_num, callback_query_or_message, rewards_with_numbers, total_pages, rewards_per_page, callback_prefix, state):
    start_index = (page_num - 1) * rewards_per_page
    end_index = min(start_index + rewards_per_page, len(rewards_with_numbers))
    page_rewards = rewards_with_numbers[start_index:end_index]

    getting_process = await state.get_state() == RewardFSM.waiting_get_all_reward
    
    message_text = (
        f"{ '✨ Sovg\'alarni ko\'rish bo\'limi:\n\n' if getting_process else '✒️ Sovg\'alarni tahrirlash bo\'limi: \n\n'} 🔍 Umumiy natija: {len(rewards_with_numbers)} ta sovg\'alar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, reward in page_rewards:
        message_text += f"{number}. {reward.name}\n"

    reward_buttons = []
    row = []
    for number, reward in page_rewards:
        if getting_process:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"reward:{reward.id}:get"))
        else:
            row.append(InlineKeyboardButton(text=str(number), callback_data=f"reward:{reward.id}:none"))
        if len(row) == 5:
            reward_buttons.append(row)
            row = []

    if row:
        reward_buttons.append(row)

    pagination_buttons = []

    if total_pages > 1:
        if page_num > 1:
            pagination_buttons.append(InlineKeyboardButton(
                text="⬅️", callback_data=f"{callback_prefix}_other_pages:{page_num - 1}"))

        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))

        if page_num < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="➡️", callback_data=f"{callback_prefix}_other_pages:{page_num + 1}"))
    else:
        pagination_buttons.append(InlineKeyboardButton(text="❌", callback_data="delete_message"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=reward_buttons + [pagination_buttons])
    
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text, reply_markup=keyboard, parse_mode="HTML"
        )
    
async def update_and_clean_messages_reward(message: Message, chat_id: int, message_id: int, text: str, reward_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=(await reward_edit_keyboard(reward_id))
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

def reward_type_buttons():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎁 Sovg'a"),KeyboardButton(text="🎟 Promokod"), KeyboardButton(text="🚚 Bepul yetkazib berish")],
                  [KeyboardButton(text="🎁 Sovg'alar bo'limi")]], 
        resize_keyboard=True,
    )
    return keyboard

@reward_router.message(F.text.in_(("➕ Sovg'a qo'shish", "✒️ Sovg'ani tahrirlash", "✨ Barcha sovg'alarni ko'rish")))
async def reward_controls_handler(message: Message, state: FSMContext):
    actions = {
        "➕ Sovg'a qo'shish": (RewardFSM.waiting_reward_add, add_reward),
        "✒️ Sovg'ani tahrirlash": (RewardFSM.waiting_edit_reward, edit_reward),
        "✨ Barcha sovg'alarni ko'rish": (RewardFSM.waiting_get_all_reward, get_all_rewards),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)

#search
@reward_router.message(RewardFSM.waiting_get_all_reward)
async def get_all_rewards(message: Message, state: FSMContext):
    rewards = await sync_to_async(list)(Reward.objects.all())
    await handle_reward_search_results(message, rewards, state)

@reward_router.callback_query(F.data.startswith('search_reward_other_pages:'))
async def get_search_reward_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await handle_reward_other_pages(callback_query, state, callback_prefix="search_reward")

@reward_router.callback_query(F.data.startswith('reward:'))
async def get_single_reward(callback_query: CallbackQuery):
    reward_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    reward = await sync_to_async(Reward.objects.filter(id=reward_id).first)()
    
    if not reward:
        await callback_query.message.answer("❌ Sovg'a topilmadi.")
        await callback_query.answer()
        return
    
    reward_info = await format_reward_info(reward)

    try:
        if action == "get":
            await callback_query.message.answer(text=reward_info, parse_mode='Markdown', reply_markup=await single_item_buttons())
        else:
            await callback_query.message.answer(text=reward_info, parse_mode='Markdown', reply_markup=await reward_edit_keyboard(reward_id))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Sovg'ani yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    await callback_query.answer()

# Add
@reward_router.message(RewardFSM.waiting_reward_add)
async def add_reward(message: Message, state: FSMContext):
    reward_template = (
    "🎁 *Yangi sovg'a yaratish quyidagi tartibda bo'ladi: 👇*\n\n"
    "📌 *Sovg'a turi:* \n"
    "   -  🚚 *Bepul yetkazib berish* \n"
    "   -  🎁 *Sovg'a* \n"
    "   -  🎟 *Promokod* \n\n"
    "🔢 *Kerakli ball:*  \n"
    "📄 *Tavsif:* \n"
    "✅ *Faollik:* \n\n"

    "📝 *Sovg'ani yaratish uchun yuqoridagi ma'lumotlarni to'ldiring!*"
)

    await message.answer(text=reward_template, parse_mode="Markdown")

    await message.answer("Sovg'a turini tanlang:\n- 🚚 Bepul yetkazib berish\n- 🎁 Sovg'a\n- 🎟 Promokod", reply_markup=reward_type_buttons())
    await state.set_state(RewardFSM.waiting_reward_type)

@reward_router.message(RewardFSM.waiting_reward_type)
async def set_reward_type(message: Message, state: FSMContext):
    reward_type = message.text.strip()

    if reward_type not in ["🚚 Bepul yetkazib berish", "🎁 Sovg'a", "🎟 Promokod"]:
        await message.answer("❌ Noto'g'ri sovg'a turi\n. Admin, quyidagilardan birini tanlang: 1. 🚚 Bepul yetkazib berish\n2. 🎁 Sovg'a\n3. 🎟 Promokod")
        return
    
    REWARD_TYPES = {
        "🚚 Bepul yetkazib berish":"free_shipping", 
        "🎁 Sovg'a": "gift",
        "🎟 Promokod": "promocode",
    }
    reward_type = REWARD_TYPES[reward_type]
    await state.update_data(reward_type=reward_type)
    await message.answer("Sovg'a nomini kiriting:")
    await state.set_state(RewardFSM.waiting_reward_name)

@reward_router.message(RewardFSM.waiting_reward_name)
async def set_reward_name(message: Message, state: FSMContext):
    reward_name = message.text.strip()
    await state.update_data(reward_name=reward_name)
    await message.answer("Sovg'ani olish uchun kerakli ballarni kiriting:")
    await state.set_state(RewardFSM.waiting_reward_points_required)

@reward_router.message(RewardFSM.waiting_reward_points_required)
async def set_reward_points_required(message: Message, state: FSMContext):
    try:
        points_required = int(message.text.strip())
        if points_required <= 0:
            await message.answer("❌ Ballar 0 dan katta bo'lishi kerak.")
            return
        await state.update_data(points_required=points_required)
        skip_keyboard = skip_inline_button("description")
        await message.answer("Sovg'ani tavsifini kiriting:", reply_markup=skip_keyboard)
        await state.set_state(RewardFSM.waiting_reward_description)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting.")

@reward_router.message(RewardFSM.waiting_reward_description)
async def set_reward_description(message: Message, state: FSMContext):
    description = message.text.strip()
    await state.update_data(description=description)
    await message.answer("Sovg'a faolligini tanlang (Faol/Nofaol):", reply_markup=ACTIVITY_KEYBOARD)
    await state.set_state(RewardFSM.waiting_reward_activity)

@reward_router.callback_query(F.data == "description_skip_step")
async def skip_description(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("✅ O‘tkazib yuborildi. Davom etamiz...")
    await state.update_data(description=None)
    await callback_query.message.answer("Sovg'a faolligini tanlang (Faol/Nofaol):", reply_markup=ACTIVITY_KEYBOARD)
    await state.set_state(RewardFSM.waiting_reward_activity)

@reward_router.message(RewardFSM.waiting_reward_activity)
async def set_reward_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        is_active = activity == "✅ Faol"
        await state.update_data(is_active=is_active)
        await save_reward(message, state)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")

async def save_reward(message, state):
    user = await get_user_from_db(message.from_user.id)

    data = await state.get_data()
    reward_type = data.get("reward_type")
    reward_name = data.get("reward_name")
    points_required = data.get("points_required")
    description = data.get("description")
    is_active = data.get("is_active")

    reward = await sync_to_async(Reward.objects.create)(
        owner=user,
        updated_by=user,
        reward_type=reward_type,
        name=reward_name,
        points_required=points_required,
        description=description,
        is_active=is_active,
    )

    await message.answer(f"✅ '{reward.name}' nomli sovg'a muvaffaqiyatli yaratildi.", reply_markup=REWARD_CONTROLS_KEYBOARD)
    await state.clear()



#Edit
@reward_router.message(RewardFSM.waiting_edit_reward)
async def edit_reward(message: Message, state: FSMContext):
    await message.answer("Tahrirlash uchun sovg'a nomini kiriting: 👇")
    await state.set_state(RewardFSM.waiting_search_reward_by_name)

@reward_router.message(RewardFSM.waiting_search_reward_by_name)
async def search_reward_by_name(message: Message, state: FSMContext):
    name = message.text.strip()
    rewards = await sync_to_async(list)(Reward.objects.filter(name__icontains=name))
    await handle_reward_search_results(message, rewards, state)

@reward_router.callback_query(F.data.startswith('reward_field_'))
async def reward_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[2]
    reward_id = int(callback_query.data.split(":")[1])

    user = await get_user_from_db(callback_query.from_user.id)
    reward = await sync_to_async(Reward.objects.filter(id=reward_id).first)()

    if not reward:
        await callback_query.answer("❌ Xatolik: Reward topilmadi.")
        return
    
    field_actions = {
        "Sovg'a turi": (RewardFSM.waiting_edit_reward_type),
        "Sovg'a nomi": (RewardFSM.waiting_edit_reward_name),
        "Kerakli ballar": (RewardFSM.waiting_edit_reward_points_required),
        "Tavsif": (RewardFSM.waiting_edit_reward_description),
        "Faollik": (RewardFSM.waiting_edit_reward_activity),
        "delete_reward": (RewardFSM.waiting_edit_reward_deletion),
    }   
        
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, rewardni asosiy bo‘limidan qaytadan tanlang.")
        return
    
    await state.update_data(message_id=message_id, chat_id=chat_id, reward=reward, user=user)

    next_state = field_actions[field]
    await state.set_state(next_state)

    if field == "delete_reward":
        await callback_query.message.answer(f"Ushbu sovg'ani o‘chirmoqchimisiz? 🗑", reply_markup=await confirmation_keyboard(reward, reward_id))
    elif field == "Faollik":
        await callback_query.message.answer(f"'{reward.name}'ning yangi {field.lower()}ni tanlang:", reply_markup=ACTIVITY_KEYBOARD)
    elif field == "Sovg'a turi":
        await callback_query.message.answer(f"'{reward.name}'ning yangi {field.lower()}ni tanlang:", reply_markup=reward_type_buttons())
    else:
        await callback_query.message.answer(f"'{reward.name}'ning yangi {field.lower()}ni kiriting:")
    await callback_query.answer()

@reward_router.message(RewardFSM.waiting_edit_reward_type)
async def edit_reward_type(message: Message, state: FSMContext):
    reward_type = message.text.strip()
    if reward_type not in ["🚚 Bepul yetkazib berish", "🎁 Sovg'a", "🎟 Promokod"]:
        await message.answer("❌ Noto'g'ri sovg'a turi\n. Admin, quyidagilardan birini tanlang:\n- 🚚 Bepul yetkazib berish\n- 🎁 Sovg'a\n- 🎟 Promokod")
        return
    
    REWARD_TYPES = {
        "🚚 Bepul yetkazib berish":"free_shipping", 
        "🎁 Sovg'a": "gift",
        "🎟 Promokod": "promocode",
    }
    reward_type = REWARD_TYPES[reward_type]
    
    data = await state.get_data()
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    user = data.get('user')
    reward = data.get("reward")

    if reward.reward_type == reward_type:
        await message.answer(f"❌ Reward turi allaqachon '{reward_type}' da turibdi. Boshqa tur kiriting: ")
        return
    
    if reward:
        reward.reward_type = reward_type
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Reward turi '{reward_type}' ga yangilandi👆")
        text = await format_reward_info(reward)
        await update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    else:
        await message.answer("❌ Reward topilmadi.")

@reward_router.message(RewardFSM.waiting_edit_reward_name)
async def edit_reward_name(message: Message, state: FSMContext):
    name = message.text.strip()
    
    data = await state.get_data()
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    user = data.get('user')
    reward = data.get("reward")

    if reward.name == name:
        await message.answer(f"❌ Sovg'a nomi allaqachon '{name}' da turibdi. Boshqa nom kiriting: ")
        return
    
    if reward:
        reward.name = name
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Sovg'a nomi '{name}' ga yangilandi👆")
        text = await format_reward_info(reward)
        await update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    else:
        await message.answer("❌ Sovg'a topilmadi.")

@reward_router.message(RewardFSM.waiting_edit_reward_points_required)
async def edit_reward_points_required(message: Message, state: FSMContext):
    try:
        points_required = int(message.text.strip())
        if points_required <= 0:
            await message.answer("❌ Ballar 0 dan katta bo'lishi kerak.")
            return
        
        data = await state.get_data()
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        reward = data.get("reward")

        if reward.points_required == points_required:
            await message.answer(f"❌ Kerakli ballar allaqachon '{points_required}' da turibdi. Boshqa son kiriting: ")
            return
        
        if reward:
            reward.points_required = points_required
            reward.updated_by = user
            await sync_to_async(reward.save)()
            await message.answer(f"✅ Kerakli ballar '{points_required}' ga yangilandi👆")
            text = await format_reward_info(reward)
            await update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
        else:
            await message.answer("❌ Reward topilmadi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting.")

@reward_router.message(RewardFSM.waiting_edit_reward_description)
async def edit_reward_description(message: Message, state: FSMContext):
    description = message.text.strip()
    
    data = await state.get_data()
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    user = data.get('user')
    reward = data.get("reward")

    if reward.description == description:
        await message.answer(f"❌ Tavsif allaqachon '{description}' da turibdi. Boshqa tavsif kiriting: ")
        return
    
    if reward:
        reward.description = description
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Tavsif '{description}' ga yangilandi👆")
        text = await format_reward_info(reward)
        await update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    else:
        await message.answer("❌ Reward topilmadi.")

@reward_router.message(RewardFSM.waiting_edit_reward_activity)
async def edit_reward_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        is_active = activity == "✅ Faol"
        
        data = await state.get_data()
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        user = data.get('user')
        reward = data.get("reward")
        
        if reward.is_active == is_active:
            await message.answer(f"❌ Reward faolligi allaqachon '{activity}' da turibdi. Boshqa holat kiriting: ")
            return
        
        if reward:
            reward.is_active = is_active
            reward.updated_by = user
            await sync_to_async(reward.save)()
            await message.answer(f"✅ Reward faolligi {'faol' if is_active else 'nofaol'} holatga yangilandi👆")
            text = await format_reward_info(reward)
            await update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
        else:
            await message.answer("❌ Reward topilmadi.")
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")

#Delete
@reward_router.callback_query(F.data.startswith("reward_delete"))
async def reward_delete_callback(callback_query: CallbackQuery, state: FSMContext):
    reward_id = int(callback_query.data.split(":")[1])
    reward = await sync_to_async(Reward.objects.filter(id=reward_id).first)()

    await state.update_data(reward_id=reward_id)
    await callback_query.message.edit_text(f"'{reward.name}' rewardni o‘chirmoqchimisiz?", reply_markup=await confirmation_keyboard("reward", reward_id))
    
@reward_router.callback_query(F.data.startswith("reward_confirm_delete:"))
async def reward_confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    reward_id = int(callback_query.data.split(":")[1])
    reward = await sync_to_async(Reward.objects.filter(id=reward_id).first)()

    if not reward:
        await callback_query.answer(f"⚠️ Reward topilmadi. Admin qaytadan urinib ko'ring.")
        return
    
    try:
        await sync_to_async(reward.delete)()  
        await callback_query.answer(f"✅ '{reward.name}' reward o‘chirildi.")
        await callback_query.bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Rewardni o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@reward_router.callback_query(F.data.startswith("reward_cancel_delete:"))
async def reward_cancel_delete(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id, message_id = data.get("chat_id"), data.get("message_id")
    reward_id = int(callback_query.data.split(":")[1])
    reward = await sync_to_async(Reward.objects.filter(id=reward_id).first)()
    text = await format_reward_info(reward)
    if not reward:
        await callback_query.answer(f"⚠️ Reward topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(text=text, parse_mode='Markdown', reply_markup=await reward_edit_keyboard(reward_id))

    if message_id and chat_id:
        text = f"Tanlangan reward: {reward.name}\nMaydonni tanlang:👇"
        await update_and_clean_messages_reward(callback_query.message, chat_id, message_id, text, reward_id )

#Reward part end
