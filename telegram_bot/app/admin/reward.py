from aiogram import Router, F
import asyncio
from django.utils import timezone
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_app.models import Reward
from telegram_bot.app.admin.promocode import admin_get_all_promocodes, admin_get_promocode_by_id, admin_edit_or_set_promocode
from telegram_bot.app.admin.utils import (
    admin_skip_inline_button,
    admin_single_item_buttons,
    admin_delete_confirmation_keyboard, 
    admin_escape_markdown,
    admin_keyboard_back_to_reward,
    admin_check_state_data,
    admin_invalid_command_message,
    ADMIN_ACTIVITY_KEYBOARD,
    )

admin_reward_router = Router()

class AdminRewardFSM(StatesGroup):
    # Get
    admin_waiting_get_all_reward = State()

    # Add
    admin_waiting_reward_add = State()
    admin_waiting_reward_type = State()
    admin_waiting_to_set_promocode_to_reward_type = State()
    admin_waiting_reward_name = State()
    admin_waiting_reward_points_required = State()
    admin_waiting_reward_description = State()
    admin_waiting_reward_activity = State()

    # Edit
    admin_waiting_edit_reward = State()
    admin_waiting_search_reward_by_name = State()
    admin_waiting_edit_reward_type = State() 
    admin_waiting_for_promocode = State() 
    admin_waiting_edit_reward_name = State()
    admin_waiting_edit_reward_points_required = State()
    admin_waiting_edit_reward_description = State()
    admin_waiting_edit_reward_activity = State()

    # Deleting
    admin_waiting_edit_reward_deletion = State()

# Utils
async def admin_get_reward_by_id(reward_id):
    return await sync_to_async(lambda: Reward.objects.select_related('owner', 'updated_by').filter(id=reward_id).first())()

async def admin_format_reward_info(reward):
    REWARD_TYPES = {
        "free_shipping": "🚚 Bepul yetkazib berish",
        "gift": "🎁 Sovg'a",
        "promocode": "🎟 Promokod",
    }
    owner_name = admin_escape_markdown(reward.owner.full_name)
    updated_by_name = admin_escape_markdown(reward.updated_by.full_name)
    return (
        f"🎁 Sovg'a nomi: *{reward.name}*\n"
        f"📌 Sovg'a turi: *{REWARD_TYPES.get(reward.reward_type, 'Noma’lum')}*\n"
        f"🔢 Kerakli ball: *{reward.points_required}*\n"
        f"📄 Tavsif: *{'Yo‘q' if not reward.description else admin_escape_markdown(reward.description)}*\n"
        f"✅ Faollik: *{'Faol ✅' if reward.is_active else 'Nofaol ❌'}*\n"
        f"👤 Yaratgan: [{owner_name}](tg://user?id={reward.owner.telegram_id})\n"
        f"✏️ Oxirgi tahrir: [{updated_by_name}](tg://user?id={reward.updated_by.telegram_id})\n"
    )

def admin_reward_edit_keyboard(reward_id):
    fields = ['Sovg\'a nomi', 'Sovg\'a turi', 'Kerakli ballar', 'Tavsif', 'Faollik']
    builder = InlineKeyboardBuilder()
    for i in range(0, len(fields), 2):
        builder.button(text=fields[i], callback_data=f"admin_reward_field_{fields[i]}:{reward_id}")
        if i + 1 < len(fields):
            builder.button(text=fields[i + 1], callback_data=f"admin_reward_field_{fields[i+1]}:{reward_id}")
    builder.button(text="🗑 Sovg'ani o'chirish", callback_data=f"admin_reward_field_delete_reward:{reward_id}")
    builder.adjust(2, 2, 1, 1)
    return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_single_item_buttons().inline_keyboard)

def admin_reward_type_buttons():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="◀️ Bosh menu"), KeyboardButton(text="🚫 Jarayonni bekor qilish"))
    builder.row(
        KeyboardButton(text="🎁 Sovg'a"),
        KeyboardButton(text="🎟 Promokod"),
        KeyboardButton(text="🚚 Bepul yetkazib berish")
    )
    return builder.as_markup(resize_keyboard=True)

async def admin_handle_reward_search_results(message: Message, rewards, state: FSMContext):
    if not rewards:
        await message.answer("❌ Hech qanday sovg'a topilmadi.")
        return
    await state.update_data(search_results=rewards)
    rewards_with_numbers = [(index + 1, reward) for index, reward in enumerate(rewards)]
    total_pages = ((len(rewards_with_numbers) + 9) // 10)
    await admin_display_rewards_page(1, message, rewards_with_numbers, total_pages, 10, "admin_search_reward", state)

async def admin_handle_reward_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    page_num = int(data_parts[1])
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    rewards = data.get("search_results", [])
    rewards_with_numbers = [(index + 1, reward) for index, reward in enumerate(rewards)]
    rewards_per_page = 10
    total_pages = (len(rewards_with_numbers) + rewards_per_page - 1) // rewards_per_page
    await admin_display_rewards_page(page_num, callback_query, rewards_with_numbers, total_pages, rewards_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_display_rewards_page(page_num, callback_query_or_message, rewards_with_numbers, total_pages, rewards_per_page, callback_prefix, state):
    start_index = (page_num - 1) * rewards_per_page
    end_index = min(start_index + rewards_per_page, len(rewards_with_numbers))
    page_rewards = rewards_with_numbers[start_index:end_index]
    getting_process = await state.get_state() == AdminRewardFSM.admin_waiting_get_all_reward
    message_text = (
        f"{'✨ Sovg\'alarni ko\'rish bo\'limi:\n\n' if getting_process else '✒️ Sovg\'alarni tahrirlash bo\'limi:\n\n'}"
        f"🔍 Umumiy natija: {len(rewards_with_numbers)} ta sovg\'alar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )
    for number, reward in page_rewards:
        message_text += f"{number}. {reward.name}\n"
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()
    for number, reward in page_rewards:
        callback_data = f"admin_reward:{reward.id}:get" if getting_process else f"admin_reward:{reward.id}:none"
        builder.button(text=str(number), callback_data=callback_data)
    builder.adjust(5)
    if total_pages > 1:
        pagination_buttons = []
        if page_num > 1:
            pagination_buttons.append({"text": "⬅️", "callback_data": f"{callback_prefix}_other_pages:{page_num - 1}"})
        pagination_buttons.append({"text": "❌", "callback_data": "admin_delete_message"})
        if page_num < total_pages:
            pagination_buttons.append({"text": "➡️", "callback_data": f"{callback_prefix}_other_pages:{page_num + 1}"})
        for btn in pagination_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(pagination_buttons))
    else:
        pagination.button(text="❌", callback_data="admin_delete_message")
        pagination.adjust(5, 5, 1)
    additional_buttons = admin_keyboard_back_to_reward().inline_keyboard
    final_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + pagination.export() + additional_buttons)
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")
    else:
        await callback_query_or_message.answer(text=message_text, reply_markup=final_keyboard, parse_mode="HTML")

async def admin_update_and_clean_messages_reward(message: Message, chat_id: int, message_id: int, text: str, reward_id: int):
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=admin_reward_edit_keyboard(reward_id)
    )
    delete_tasks = [message.bot.delete_message(chat_id, msg_id) for msg_id in range(message.message_id, message_id, -1)]
    await asyncio.gather(*delete_tasks, return_exceptions=True)

# Get all rewards
@admin_reward_router.message(AdminRewardFSM.admin_waiting_get_all_reward)
async def admin_get_all_rewards(message: Message, state: FSMContext):
    rewards = await sync_to_async(lambda: list(Reward.objects.select_related('owner', 'updated_by').all().order_by('-created_at')))()
    await admin_handle_reward_search_results(message, rewards, state)

@admin_reward_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_reward_other_pages:'))
async def admin_get_all_rewards_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_reward_other_pages(callback_query, state, callback_prefix="admin_search_reward")

# Get single reward
@admin_reward_router.callback_query(IsAdminFilter(), F.data.startswith('admin_reward:'))
async def admin_get_single_reward(callback_query: CallbackQuery):
    reward_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    reward = await admin_get_reward_by_id(reward_id)
    if not reward:
        await callback_query.message.answer("❌ Sovg'a topilmadi.")
        await callback_query.answer()
        return
    reward_info = await admin_format_reward_info(reward)
    try:
        # if action == "get":
        #     await callback_query.message.answer(text=reward_info, parse_mode='Markdown', reply_markup=admin_single_item_buttons())
        # else:
        await callback_query.message.answer(text=reward_info, parse_mode='Markdown', reply_markup=admin_reward_edit_keyboard(reward_id))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Sovg'ani yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")
    await callback_query.answer()

# Adding part
@admin_reward_router.message(AdminRewardFSM.admin_waiting_reward_add)
async def admin_add_reward(message: Message, state: FSMContext):
    reward_template = (
        "🎁 *Yangi sovg'a yaratish quyidagi tartibda bo'ladi: 👇*\n\n"
        "📌 *Sovg'a turi:*\n"
        "   -  🚚 *Bepul yetkazib berish*\n"
        "   -  🎁 *Sovg'a*\n"
        "   -  🎟 *Promokod*\n\n"
        "🔢 *Kerakli ball:*\n"
        "📄 *Tavsif:*\n"
        "✅ *Faollik:*\n\n"
        "📝 *Sovg'ani yaratish uchun yuqoridagi ma'lumotlarni to'ldiring!*"
    )
    await message.answer(text=reward_template, parse_mode="Markdown")
    await message.answer("Sovg'a turini tanlang:\n- 🚚 Bepul yetkazib berish\n- 🎁 Sovg'a\n- 🎟 Promokod",  reply_markup=admin_reward_type_buttons())
    await state.set_state(AdminRewardFSM.admin_waiting_reward_type)

@admin_reward_router.message(AdminRewardFSM.admin_waiting_reward_type)
async def admin_set_reward_type(message: Message, state: FSMContext):
    reward_type = message.text.strip()
    if reward_type not in ["🚚 Bepul yetkazib berish", "🎁 Sovg'a", "🎟 Promokod"]:
        await message.answer("❌ Noto'g'ri sovg'a turi.\n Admin, quyidagilardan birini tanlang:\n- 🚚 Bepul yetkazib berish\n- 🎁 Sovg'a\n- 🎟 Promokod")
        return
    REWARD_TYPES = {
        "🚚 Bepul yetkazib berish": "free_shipping",
        "🎁 Sovg'a": "gift",
        "🎟 Promokod": "promocode",
    }
    reward_type = REWARD_TYPES[reward_type]
    await state.update_data(reward_type=reward_type)
    if reward_type == "promocode":
        await state.update_data(reward_true=True)
        await admin_get_all_promocodes(message, state, "admin_set_promocode_to_reward")
        await message.answer("Promokodni tanlang 👆")
        await admin_edit_or_set_promocode(message, state, 'admin_set_promocode_to_reward')
        await state.update_data(reward='admin_set_promocode_to_reward')
    else:
        await message.answer("Sovg'a nomini kiriting:")
        await state.set_state(AdminRewardFSM.admin_waiting_reward_name)

@admin_reward_router.callback_query(IsAdminFilter(), F.data.startswith('admin_set_promocode_to_reward:'))
async def admin_set_promocode(callback_query: CallbackQuery, state: FSMContext):
    promocode_id = int(callback_query.data.split(':')[1])
    promocode = await admin_get_promocode_by_id(promocode_id)
    data = await state.get_data() or {}
    reward_type = data.get('reward_type')
    reward = data.get('reward_obj')
    if not reward_type:
        await callback_query.message.answer(admin_invalid_command_message, reply_markup=admin_keyboard_back_to_reward())
        await callback_query.answer()
        await state.clear()
        return
    if promocode:
        await state.update_data(promocode=promocode)
        await callback_query.answer(f"Promokod {promocode} tanlandi ✅")
        if reward:
            await state.set_state(AdminRewardFSM.admin_waiting_for_promocode)
            await admin_edit_reward_type_to_promocode(callback_query.message, state)
            return
    else:
        await state.update_data(promocode=None)
    await callback_query.message.answer("Sovg'a nomini kiriting:")
    await state.set_state(AdminRewardFSM.admin_waiting_reward_name)
    await callback_query.answer()

@admin_reward_router.message(AdminRewardFSM.admin_waiting_reward_name)
async def admin_set_reward_name(message: Message, state: FSMContext):
    reward_name = message.text.strip()
    await state.update_data(reward_name=reward_name)
    await message.answer("Sovg'ani olish uchun kerakli ballarni kiriting:")
    await state.set_state(AdminRewardFSM.admin_waiting_reward_points_required)

@admin_reward_router.message(AdminRewardFSM.admin_waiting_reward_points_required)
async def admin_set_reward_points_required(message: Message, state: FSMContext):
    try:
        points_required = int(message.text.strip())
        if points_required <= 0:
            await message.answer("❌ Ballar 0 dan katta bo'lishi kerak.")
            return
        await state.update_data(points_required=points_required)
        await message.answer("Sovg'ani tavsifini kiriting:", reply_markup=admin_skip_inline_button("admin_description"))
        await state.set_state(AdminRewardFSM.admin_waiting_reward_description)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Admin, raqam kiriting.")

@admin_reward_router.message(AdminRewardFSM.admin_waiting_reward_description)
async def admin_set_reward_description(message: Message, state: FSMContext):
    description = message.text.strip()
    await state.update_data(description=description)
    await message.answer("Sovg'a faolligini tanlang (Faol/Nofaol):", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    await state.set_state(AdminRewardFSM.admin_waiting_reward_activity)

@admin_reward_router.callback_query(IsAdminFilter(), F.data == "admin_description_skip_step")
async def admin_skip_description(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("✅ O‘tkazib yuborildi. Davom etamiz...")
    await state.update_data(description=None)
    await callback_query.message.answer("Sovg'a faolligini tanlang (Faol/Nofaol):", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    await state.set_state(AdminRewardFSM.admin_waiting_reward_activity)

@admin_reward_router.message(AdminRewardFSM.admin_waiting_reward_activity)
async def admin_set_reward_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        is_active = activity == "✅ Faol"
        await state.update_data(is_active=is_active)
        await admin_save_reward(message, state)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")

async def admin_save_reward(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    user = await get_user_from_db(message.from_user.id)
    required_fields = ["reward_type", "reward_name", "points_required"]
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        missing_fields_str = ", ".join(missing_fields)
        await message.answer(f"❌ Quyidagi maydonlar yetishmayapti: {missing_fields_str}. Admin qaytadan to'g'ri ma'lumotlarni kiriting.", reply_markup=admin_keyboard_back_to_reward())
        await state.clear()
        return
    reward_type = data.get("reward_type")
    promocode = data.get("promocode")
    reward_name = data.get("reward_name")
    points_required = data.get("points_required")
    description = data.get("description")
    is_active = data.get("is_active", False)
    reward = await sync_to_async(Reward.objects.create)(
        owner=user,
        updated_by=user,
        reward_type=reward_type,
        promocode=promocode,
        name=reward_name,
        points_required=points_required,
        description=description,
        is_active=is_active,
    )
    from telegram_bot.app.admin.main_controls import ADMIN_REWARD_CONTROLS_KEYBOARD
    await message.answer(f"✅ '{reward.name}' nomli sovg'a muvaffaqiyatli yaratildi.", reply_markup=ADMIN_REWARD_CONTROLS_KEYBOARD)
    await state.clear()

# Editing part
@admin_reward_router.message(AdminRewardFSM.admin_waiting_edit_reward)
async def admin_edit_reward(message: Message, state: FSMContext):
    await message.answer("Tahrirlash uchun sovg'a nomini kiriting: 👇")
    await state.set_state(AdminRewardFSM.admin_waiting_search_reward_by_name)

@admin_reward_router.message(AdminRewardFSM.admin_waiting_search_reward_by_name)
async def admin_search_reward_by_name(message: Message, state: FSMContext):
    name = message.text.strip()
    rewards = await sync_to_async(lambda: list(Reward.objects.select_related('owner', 'updated_by').filter(name__icontains=name)))()
    await admin_handle_reward_search_results(message, rewards, state)

@admin_reward_router.callback_query(IsAdminFilter(), F.data.startswith('admin_reward_field_'))
async def admin_reward_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[3]
    reward_id = int(callback_query.data.split(":")[1])
    user = await get_user_from_db(callback_query.from_user.id)
    reward = await admin_get_reward_by_id(reward_id)
    if not reward:
        await callback_query.answer("❌ Xatolik: Reward topilmadi.")
        return
    field_actions = {
        "Sovg'a turi": (AdminRewardFSM.admin_waiting_edit_reward_type),
        "Sovg'a nomi": (AdminRewardFSM.admin_waiting_edit_reward_name),
        "Kerakli ballar": (AdminRewardFSM.admin_waiting_edit_reward_points_required),
        "Tavsif": (AdminRewardFSM.admin_waiting_edit_reward_description),
        "Faollik": (AdminRewardFSM.admin_waiting_edit_reward_activity),
        "delete": (AdminRewardFSM.admin_waiting_edit_reward_deletion),
    }
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, rewardni asosiy bo‘limidan qaytadan tanlang.")
        return
    await state.update_data(message_id=message_id, chat_id=chat_id, reward=reward, user=user)
    next_state = field_actions[field]
    await state.set_state(next_state)
    if field == "delete":
        await callback_query.message.edit_text(f"Ushbu sovg'ani o‘chirmoqchimisiz? 🗑", reply_markup=admin_delete_confirmation_keyboard("admin_reward", reward_id))
    elif field == "Faollik":
        await callback_query.message.answer(f"'{reward.name}'ning yangi {field.lower()}ni tanlang:", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    elif field == "Sovg'a turi":
        await callback_query.message.answer(f"'{reward.name}'ning yangi {field.lower()}ni tanlang:", reply_markup=admin_reward_type_buttons())
    else:
        await callback_query.message.answer(f"'{reward.name}'ning yangi {field.lower()}ni kiriting:")
    await callback_query.answer()

@admin_reward_router.message(AdminRewardFSM.admin_waiting_edit_reward_type)
async def admin_edit_reward_type(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    reward, chat_id, message_id, user = (data.get(k) for k in ("reward", "chat_id", "message_id", "user"))
    if not reward:
        await message.answer("❌ Sovg'a topilmadi. Admin qayta urinib ko'ring")
        return
    
    reward_type_input = message.text.strip()
    if reward_type_input not in ["🚚 Bepul yetkazib berish", "🎁 Sovg'a", "🎟 Promokod"]:
        await message.answer("❌ Noto'g'ri sovg'a turi\n. Admin, quyidagilardan birini tanlang:\n- 🚚 Bepul yetkazib berish\n- 🎁 Sovg'a\n- 🎟 Promokod")
        return
    REWARD_TYPES = {
        "🚚 Bepul yetkazib berish": "free_shipping",
        "🎁 Sovg'a": "gift",
        "🎟 Promokod": "promocode",
    }
    reward_type = REWARD_TYPES[reward_type_input]
    try:
        if reward.reward_type == reward_type:
            await message.answer(f"❌ Reward turi allaqachon '{reward_type}' da turibdi. Boshqa tur kiriting: ")
            return
        if reward_type == "promocode":
            reward.reward_type = reward_type
            await sync_to_async(reward.save)()
            await state.update_data(reward_true=True)
            await admin_get_all_promocodes(message, state, "admin_set_promocode_to_reward")
            await message.answer("Promokodni tanlang 👆")
            await admin_edit_or_set_promocode(message, state, 'admin_set_promocode_to_reward')
            await state.update_data(reward='admin_set_promocode_to_reward', reward_type=reward_type_input, reward_obj=reward)
            return
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Sovg'a turi '{reward_type_input}' ga yangilandi👆")
        text = await admin_format_reward_info(reward)
        await admin_update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Sovg'a turini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_reward_router.message(AdminRewardFSM.admin_waiting_for_promocode)
async def admin_edit_reward_type_to_promocode(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    reward, promocode, reward_type, chat_id, message_id, user = (data.get(k) for k in ("reward_obj","promocode", "reward_type","chat_id", "message_id", "user"))
    if not promocode:
        await message.answer("❌ Promokod topilmadi. Admin qayta urinib ko'ring")
        return
    try:
        reward.promocode = promocode
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Sovg'a turi '{reward_type}' ga yangilandi👆")
        text = await admin_format_reward_info(reward)
        await admin_update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Sovg'a turi yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_reward_router.message(AdminRewardFSM.admin_waiting_edit_reward_name)
async def admin_edit_reward_name(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    reward, chat_id, message_id, user = (data.get(k) for k in ("reward", "chat_id", "message_id", "user"))
    if not reward:
        await message.answer("❌ Sovg'a topilmadi. Admin qayta urinib ko'ring")
        return
    name = message.text.strip()
    try:
        if reward.name == name:
            await message.answer(f"❌ Sovg'a nomi allaqachon '{name}' da turibdi. Boshqa nom kiriting: ")
            return
        reward.name = name
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Sovg'a nomi '{name}' ga yangilandi👆")
        text = await admin_format_reward_info(reward)
        await admin_update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Sovg'a nomini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_reward_router.message(AdminRewardFSM.admin_waiting_edit_reward_points_required)
async def admin_edit_reward_points_required(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    reward, chat_id, message_id, user = (data.get(k) for k in ("reward", "chat_id", "message_id", "user"))
    if not reward:
        await message.answer("❌ Sovg'a topilmadi. Admin qayta urinib ko'ring")
        return
    try:
        points_required = int(message.text.strip())
        if points_required <= 0:
            await message.answer("❌ Ballar 0 dan katta bo'lishi kerak.")
            return
        if reward.points_required == points_required:
            await message.answer(f"❌ Kerakli ballar allaqachon '{points_required}' da turibdi. Boshqa son kiriting: ")
            return
        reward.points_required = points_required
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Kerakli ballar '{points_required}' ga yangilandi👆")
        text = await admin_format_reward_info(reward)
        await admin_update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Sovg'a kerakli ballarini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_reward_router.message(AdminRewardFSM.admin_waiting_edit_reward_description)
async def admin_edit_reward_description(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    reward, chat_id, message_id, user = (data.get(k) for k in ("reward", "chat_id", "message_id", "user"))
    if not reward:
        await message.answer("❌ Sovg'a topilmadi. Admin qayta urinib ko'ring")
        return
    description = message.text.strip()
    try:
        if reward.description == description:
            await message.answer(f"❌ Tavsif allaqachon '{description}' da turibdi. Boshqa tavsif kiriting: ")
            return
        reward.description = description
        reward.updated_by = user
        await sync_to_async(reward.save)()
        await message.answer(f"✅ Tavsif '{description}' ga yangilandi👆")
        text = await admin_format_reward_info(reward)
        await admin_update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Sovg'a tavsifini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_reward_router.message(AdminRewardFSM.admin_waiting_edit_reward_activity)
async def admin_edit_reward_activity(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    reward, chat_id, message_id, user = (data.get(k) for k in ("reward", "chat_id", "message_id", "user"))
    if not reward:
        await message.answer("❌ Sovg'a topilmadi. Admin qayta urinib ko'ring")
        return
    activity = message.text.strip()
    try:
        if activity in ["✅ Faol", "❌ Nofaol"]:
            is_active = activity == "✅ Faol"
            if is_active and reward.end_date < timezone.now():
                    await message.answer("❌ Sovg'a muddati tugagan. Faollashtirish uchun tugash sanasini o'zgartiring.")
                    return
            if reward.is_active == is_active:
                await message.answer(f"❌ Reward faolligi allaqachon '{activity}' da turibdi. Boshqa holat kiriting: ",
                                     reply_markup=ADMIN_ACTIVITY_KEYBOARD)
                return
            reward.is_active = is_active
            reward.updated_by = user
            await sync_to_async(reward.save)()
            await message.answer(f"✅ Reward faolligi {'faol' if is_active else 'nofaol'} holatga yangilandi👆")
            text = await admin_format_reward_info(reward)
            await admin_update_and_clean_messages_reward(message, chat_id, message_id, text, reward.id)
        else:
            await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Sovg'a faolligini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

# Deleting part
@admin_reward_router.callback_query(IsAdminFilter(), F.data.startswith("admin_reward_confirm_delete:"))
async def admin_reward_confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    reward_id = int(callback_query.data.split(":")[1])
    reward = await admin_get_reward_by_id(reward_id)
    if not reward:
        await callback_query.answer(f"⚠️ Sovg'a topilmadi. Admin qaytadan urinib ko'ring.")
        return
    try:
        await sync_to_async(reward.delete)()
        await callback_query.answer(f"✅ '{reward.name}' sovg'a o‘chirildi.")
        await callback_query.bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Sovg'ani o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_reward_router.callback_query(IsAdminFilter(), F.data.startswith("admin_reward_cancel_delete:"))
async def admin_reward_cancel_delete(callback_query: CallbackQuery, state: FSMContext):
    reward_id = int(callback_query.data.split(":")[1])
    reward = await admin_get_reward_by_id(reward_id)
    text = await admin_format_reward_info(reward)
    if not reward:
        await callback_query.answer(f"⚠️ Sovg'a topilmadi. Admin qaytadan urinib ko'ring")
        return
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(text=text, parse_mode='Markdown', reply_markup=admin_reward_edit_keyboard(reward_id))








