from aiogram import Router, F
import asyncio
from django.utils import timezone
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_app.models import Promocode 
from telegram_bot.app.admin.utils import (
    admin_single_item_buttons, 
    admin_keyboard_back_to_promocode,
    admin_keyboard_back_to_reward,
    admin_delete_confirmation_keyboard, 
    admin_escape_markdown,
    admin_check_state_data,
    admin_get_cancel_reply_keyboard,
    ADMIN_ACTIVITY_KEYBOARD,
    )

admin_promocode_router = Router()

class AdminPromocodeFSM(StatesGroup):
    # Get
    admin_waiting_get_all_promocode = State()

    # Add
    admin_waiting_promocode_add = State()
    admin_waiting_promocode_discount_percentage = State()
    admin_waiting_promocode_start_date = State()
    admin_waiting_promocode_end_date = State()
    admin_waiting_promocode_usage_limit = State()
    admin_waiting_promocode_activity = State()

    # Edit
    admin_waiting_edit_promocode = State()
    admin_waiting_edit_promocode_by_code = State()
    admin_waiting_edit_promocode_field = State()
    admin_waiting_edit_promocode_discount_percentage = State()
    admin_waiting_edit_promocode_start_date = State()
    admin_waiting_edit_promocode_end_date = State()
    admin_waiting_edit_promocode_usage_limit = State()
    admin_waiting_edit_promocode_activity = State()

    # Deleting
    admin_waiting_promocode_deletion = State()

# Utils
async def admin_get_promocode_by_id(promocode_id):
    return await sync_to_async(lambda: Promocode.objects.select_related('owner', 'updated_by').filter(id=promocode_id).first())()

async def admin_format_promocode_info(promocode):
    owner_name = admin_escape_markdown(promocode.owner.full_name)
    updated_by_name = admin_escape_markdown(promocode.updated_by.full_name)
    return (
        f"📝 Promokod: *{promocode.code}*\n"
        f"📉 Chegirma foizi: *{int(promocode.discount_percentage) if promocode.discount_percentage % 1 == 0 else promocode.discount_percentage} %*\n"
        f"📅🕙 Boshlanish sanasi: *{promocode.valid_from.strftime('%Y-%m-%d %H:%M')}*\n"
        f"📅🕛 Tugash sanasi: *{promocode.valid_until.strftime('%Y-%m-%d %H:%M')}*\n"
        f"✅ Faollik: *{'Faol ✅' if promocode.is_active else 'Nofaol ❌'}*\n"
        f"🔢 Foydalanish chegarasi: *{promocode.usage_limit}*\n"
        f"🔢 Foydalanilgan soni: *{promocode.used_count}*\n"
        f"👤 Yaratgan: [{owner_name}](tg://user?id={promocode.owner.telegram_id})\n"
        f"✏️ Oxirgi tahrir: [{updated_by_name}](tg://user?id={promocode.updated_by.telegram_id})\n"
    )

def admin_promocode_edit_keyboard(promocode_id):
    fields = ['Chegirma foizi', 'Boshlanish sanasi', 'Foydalanish chegarasi', 'Tugash sanasi', 'Faollik']
    builder = InlineKeyboardBuilder()
    for i in range(0, len(fields), 2):
        row = [
            InlineKeyboardButton(text=fields[i], callback_data=f"admin_promocode_field_{fields[i]}:{promocode_id}")
        ]
        if i + 1 < len(fields):
            row.append(InlineKeyboardButton(text=fields[i + 1], callback_data=f"admin_promocode_field_{fields[i+1]}:{promocode_id}"))
        builder.row(*row)
    builder.button(text="🗑 Promokodni o'chirish", callback_data=f"admin_promocode_field_deletepromocode:{promocode_id}")
    builder.adjust(2, 2, 1, 1)
    return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_single_item_buttons().inline_keyboard)

async def admin_handle_promocode_search_results(message: Message, promocodes, state: FSMContext, prefix: str = None):
    if not promocodes:
        await message.answer("❌ Hech qanday promokod topilmadi.")
        return
    await state.update_data(search_results=promocodes)
    prefix = prefix or "admin_search_promocode"
    promocodes_with_numbers = [(index + 1, promocode) for index, promocode in enumerate(promocodes)]
    total_pages = ((len(promocodes_with_numbers) + 9) // 10)
    await admin_display_promocodes_page(1, message, promocodes_with_numbers, total_pages, 10, prefix, state)

async def admin_handle_promocode_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    page_num = int(data_parts[1])
    if not (data := await admin_check_state_data(state, callback_query)):
        return 
    promocodes = data.get("search_results", [])
    promocodes_with_numbers = [(index + 1, promocode) for index, promocode in enumerate(promocodes)]
    promocodes_per_page = 10
    total_pages = (len(promocodes_with_numbers) + promocodes_per_page - 1) // promocodes_per_page
    await admin_display_promocodes_page(page_num, callback_query, promocodes_with_numbers, total_pages, promocodes_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_display_promocodes_page(page_num, callback_query_or_message, promocodes_with_numbers, total_pages, promocodes_per_page, callback_prefix, state):
    start_index = (page_num - 1) * promocodes_per_page
    end_index = min(start_index + promocodes_per_page, len(promocodes_with_numbers))
    page_promocodes = promocodes_with_numbers[start_index:end_index]
    getting_process = await state.get_state() == AdminPromocodeFSM.admin_waiting_get_all_promocode
    message_text = (
        f"{'✨ Promokodni ko\'rish bo\'limi:\n\n' if getting_process or callback_prefix == 'admin_set_promocode_to_reward' else '✒️ Promokodni tahrirlash bo\'limi:\n\n'}"
        f"🔍 Umumiy natija: {len(promocodes_with_numbers)} ta promokodlar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )
    for number, promocode in page_promocodes:
        message_text += f"{number}. {promocode.code}\n"
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()
    for number, promocode in page_promocodes:
        if callback_prefix == "admin_set_promocode_to_reward":
            callback_data = f"admin_set_promocode_to_reward:{promocode.id}"
        elif getting_process:
            callback_data = f"admin_promocode:{promocode.id}:get"
        else:
            callback_data = f"admin_promocode:{promocode.id}:none"
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
    additional_buttons = admin_keyboard_back_to_reward().inline_keyboard if callback_prefix == "admin_set_promocode_to_reward" else admin_keyboard_back_to_promocode().inline_keyboard
    final_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + pagination.export() + additional_buttons)
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(text=message_text, reply_markup=final_keyboard, parse_mode="Markdown")
    else:
        await callback_query_or_message.reply(text=message_text, reply_markup=final_keyboard, parse_mode="Markdown")

async def admin_update_and_clean_messages_promocode(message: Message, chat_id: int, message_id: int, text: str, promocode_id: int):
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=admin_promocode_edit_keyboard(promocode_id)
    )
    delete_tasks = [message.bot.delete_message(chat_id, msg_id) for msg_id in range(message.message_id, message_id, -1)]
    await asyncio.gather(*delete_tasks, return_exceptions=True)


# Get all promocodes
@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_get_all_promocode)
async def admin_get_all_promocodes(message: Message, state: FSMContext, prefix=None):
    data = await state.get_data() or {}
    reward = data.get('reward_true')
    if reward:
        promocodes = await sync_to_async(lambda: list(Promocode.objects.filter(reward__isnull=True).select_related('owner', 'updated_by')))()
    else:
        promocodes = await sync_to_async(lambda: list(Promocode.objects.select_related('owner', 'updated_by').all()))()
    await admin_handle_promocode_search_results(message, promocodes, state, prefix)

@admin_promocode_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_promocode_other_pages:'))
async def admin_get_all_promocodes_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_promocode_other_pages(callback_query, state, callback_prefix="admin_search_promocode")

@admin_promocode_router.callback_query(IsAdminFilter(), F.data.startswith('admin_set_promocode_to_reward_other_pages:'))
async def admin_get_all_promocodes_other_pages_set_to_reward(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_promocode_other_pages(callback_query, state, callback_prefix="admin_set_promocode_to_reward")

# Get single promocode
@admin_promocode_router.callback_query(IsAdminFilter(), F.data.startswith('admin_promocode:'))
async def admin_get_single_promocode(callback_query: CallbackQuery, state: FSMContext):
    promocode_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    promocode = await admin_get_promocode_by_id(promocode_id)
    if not promocode:
        await callback_query.message.answer("❌ Promokod topilmadi.")
        await callback_query.answer()
        return
    promocode_info = await admin_format_promocode_info(promocode)
    try:
        # if action == "get":
        #     await callback_query.message.answer(text=promocode_info, parse_mode='Markdown', reply_markup=admin_single_item_buttons())
        # else:
        await callback_query.message.answer(text=promocode_info, parse_mode='Markdown', reply_markup=admin_promocode_edit_keyboard(promocode_id))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Promokodni yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")
    await callback_query.answer()

# Adding part
@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_promocode_add)
async def admin_add_promocode(message: Message, state: FSMContext):
    promocode_template = (
        "📝 *Promokod yaratish quyidagi tartibda bo'ladi: 👇*\n\n"
        "📉 *Chegirma foizi:*\n"
        "📅🕙 *Boshlanish sanasi va soati:*\n"
        "📅🕛 *Tugash sanasi va soati:*\n"
        "🔢 *Foydalanish chegarasi:*\n"
        "✅ *Faollik:*\n\n"
        "Promokod yaratish uchun kerakli ma'lumotlarni kiriting!"
    )
    await message.answer(text=promocode_template, parse_mode="Markdown")

    await message.answer("Promokod uchun chegirma foizini kiriting (masalan, 10 yoki 15.5):", reply_markup=admin_get_cancel_reply_keyboard().as_markup(resize_keyboard=True))
    await state.set_state(AdminPromocodeFSM.admin_waiting_promocode_discount_percentage)

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_promocode_discount_percentage)
async def admin_set_promocode_discount_percentage(message: Message, state: FSMContext):
    try:
        discount_percentage = float(message.text.strip())
        if not (0 < discount_percentage <= 100):
            await message.answer("❌ Chegirma foizi 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        await state.update_data(discount_percentage=discount_percentage)
        await message.answer("Promokod boshlanish sanasini kiriting (masalan, 2025-05-15 10:00):")
        await state.set_state(AdminPromocodeFSM.admin_waiting_promocode_start_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_promocode_start_date)
async def admin_set_promocode_start_date(message: Message, state: FSMContext):
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        await state.update_data(start_date=start_date)
        await message.answer("Promokod tugash sanasini kiriting (masalan, 2025-05-25 23:59):")
        await state.set_state(AdminPromocodeFSM.admin_waiting_promocode_end_date)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_promocode_end_date)
async def admin_set_promocode_end_date(message: Message, state: FSMContext):
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)
        await state.update_data(end_date=end_date)
        await message.answer("Promokod foydalanish chegarasini kiriting (masalan, 100):")
        await state.set_state(AdminPromocodeFSM.admin_waiting_promocode_usage_limit)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_promocode_usage_limit)
async def admin_set_promocode_usage_limit(message: Message, state: FSMContext):
    try:
        usage_limit = int(message.text.strip())
        if usage_limit <= 0:
            await message.answer("❌ Foydalanish chegarasi 0 dan katta bo'lishi kerak.")
            return
        await state.update_data(usage_limit=usage_limit)
        await message.answer("Promokod faolligini tanlang (Faol/Nofaol):", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
        await state.set_state(AdminPromocodeFSM.admin_waiting_promocode_activity)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 100).")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_promocode_activity)
async def admin_set_promocode_activity(message: Message, state: FSMContext):
    activity = message.text.strip()
    if activity in ["✅ Faol", "❌ Nofaol"]:
        is_active = activity == "✅ Faol"
        await state.update_data(is_active=is_active)
        await admin_save_promocode(message, state)
    else:
        await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")

async def admin_save_promocode(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    user = await get_user_from_db(message.from_user.id)
    discount_percentage = data.get("discount_percentage")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    usage_limit = data.get("usage_limit")
    is_active = data.get("is_active")
    promocode = await sync_to_async(Promocode.objects.create)(
        owner=user,
        updated_by=user,
        discount_percentage=discount_percentage,
        valid_from=start_date,
        valid_until=end_date,
        usage_limit=usage_limit,
        is_active=is_active,
    )
    from telegram_bot.app.admin.main_controls import ADMIN_PROMOCODE_CONTROLS_KEYBOARD
    await message.answer(f"✅ Promokod '{promocode.code}' muvaffaqiyatli yaratildi.", reply_markup=ADMIN_PROMOCODE_CONTROLS_KEYBOARD)
    await state.clear()

# Editing part
@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_edit_promocode)
async def admin_edit_or_set_promocode(message: Message, state: FSMContext, prefix=None):
    if prefix:
        await message.answer("Yoki izlash uchun promokod kodini kiriting: 👇")
    else:
        await message.answer("Tahrirlash uchun promokod kodini kiriting: 👇")
    await state.set_state(AdminPromocodeFSM.admin_waiting_edit_promocode_by_code)

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_edit_promocode_by_code)
async def admin_search_promocode_by_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    data = await state.get_data() or {}
    prefix = data.get('reward')
    reward = data.get('reward_true')
    if reward:
        promocodes = await sync_to_async(lambda: list(Promocode.objects.filter(reward__isnull=True).select_related('owner', 'updated_by')))()
    else:       
        promocodes = await sync_to_async(lambda: list(Promocode.objects.select_related('owner', 'updated_by').filter(code__icontains=code)))()
    await admin_handle_promocode_search_results(message, promocodes, state, prefix)

@admin_promocode_router.callback_query(IsAdminFilter(), F.data.startswith('admin_promocode_field_'))
async def admin_promocode_field_selection(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":")[0].split("_")[3]
    promocode_id = int(callback_query.data.split(":")[1])
    user = await get_user_from_db(callback_query.from_user.id)
    promocode = await admin_get_promocode_by_id(promocode_id)
    if not promocode:
        await callback_query.answer("❌ Xatolik: Promokod topilmadi.")
        return
    field_actions = {
        "Chegirma foizi": (AdminPromocodeFSM.admin_waiting_edit_promocode_discount_percentage),
        "Boshlanish sanasi": (AdminPromocodeFSM.admin_waiting_edit_promocode_start_date),
        "Tugash sanasi": (AdminPromocodeFSM.admin_waiting_edit_promocode_end_date),
        "Faollik": (AdminPromocodeFSM.admin_waiting_edit_promocode_activity),
        "Foydalanish chegarasi": (AdminPromocodeFSM.admin_waiting_edit_promocode_usage_limit),
        "deletepromocode": (AdminPromocodeFSM.admin_waiting_promocode_deletion),
    }
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    if not message_id or not chat_id:
        await callback_query.message.answer("❌ Xatolik: Eski xabar ma'lumotlari topilmadi. Admin, promokodni asosiy bo‘limidan qaytadan tanlang.")
        return
    await state.update_data(message_id=message_id, chat_id=chat_id, promocode=promocode, user=user)
    next_state = field_actions[field]
    await state.set_state(next_state)
    if field == "deletepromocode":
        await callback_query.message.edit_text(f"Ushbu chegirmani o‘chirmoqchimisiz? 🗑", reply_markup=admin_delete_confirmation_keyboard("admin_promocode", promocode_id))
    elif field == "Faollik":
        await callback_query.message.answer(f"'{promocode}' chegirmasining yangi {field.lower()}ni tanlang:", reply_markup=ADMIN_ACTIVITY_KEYBOARD)
    else:
        await callback_query.message.answer(f"'{promocode}' chegirmasining yangi {field.lower()}ni kiriting:", reply_markup=ReplyKeyboardRemove())
    await callback_query.answer()

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_edit_promocode_discount_percentage)
async def admin_edit_promocode_discount_percentage(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    promocode, chat_id, message_id, user = (data.get(k) for k in ("promocode", "chat_id", "message_id", "user"))
    if not promocode:
        await message.answer("❌ Promokod topilmadi.")
        return
    try:
        discount_percentage = float(message.text.strip())
        if not (0 < discount_percentage <= 100):
            await message.answer("❌ Chegirma foizi 0 dan katta va 100 dan kichik bo'lishi kerak.")
            return
        if promocode.discount_percentage == discount_percentage:
            await message.answer(f"❌ Chegirma foizi allaqachon '{discount_percentage}'% da turibdi. Boshqa son kiriting: ")
            return
        promocode.discount_percentage = discount_percentage
        promocode.updated_by = user
        await sync_to_async(promocode.save)()
        await message.answer(f"✅ Promokod chegirma foizi '{discount_percentage}'% ga yangilandi👆")
        text = await admin_format_promocode_info(promocode)
        await admin_update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 10 yoki 15.5).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Promokod foizini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_edit_promocode_start_date)
async def admin_edit_promocode_start_date(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    promocode, chat_id, message_id, user = (data.get(k) for k in ("promocode", "chat_id", "message_id", "user"))
    if not promocode:
        await message.answer("❌ Promokod topilmadi. Admin qayta urinib ko'ring.")
        return
    try:
        start_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        start_date = timezone.make_aware(start_date)
        if promocode.valid_from == start_date:
            await message.answer(f"❌ Promokod boshlanish sanasi allaqachon '{start_date.strftime('%Y-%m-%d %H:%M')}'da turibdi. Boshqa sana kiriting: ")
            return
        promocode.valid_from = start_date
        promocode.updated_by = user
        await sync_to_async(promocode.save)()
        await message.answer(f"✅ Promokod boshlanish sanasi '{start_date.strftime('%Y-%m-%d %H:%M')}'ga yangilandi👆")
        text = await admin_format_promocode_info(promocode)
        await admin_update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-15 10:00).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Promokod boshlanish sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_edit_promocode_end_date)
async def admin_edit_promocode_end_date(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    promocode, chat_id, message_id, user = (data.get(k) for k in ("promocode", "chat_id", "message_id", "user"))
    if not promocode:
        await message.answer("❌ Promokod topilmadi.")
        return
    try:
        end_date = timezone.datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        end_date = timezone.make_aware(end_date)
        if promocode.valid_until == end_date:
            await message.answer(f"❌ Promokod tugash sanasi allaqachon '{end_date.strftime('%Y-%m-%d %H:%M')}'da turibdi. Boshqa sana kiriting: ")
            return
        promocode.valid_until = end_date
        promocode.updated_by = user
        await sync_to_async(promocode.save)()
        await message.answer(f"✅ Promokod tugash sanasi '{end_date.strftime('%Y-%m-%d %H:%M')}' ga yangilandi👆")
        text = await admin_format_promocode_info(promocode)
        await admin_update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, sana va vaqtni to'g'ri kiriting (masalan, 2025-05-25 23:59).")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Promokod tugash sanasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_edit_promocode_usage_limit)
async def admin_edit_promocode_usage_limit(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    promocode, chat_id, message_id, user = (data.get(k) for k in ("promocode", "chat_id", "message_id", "user"))
    if not promocode:
        await message.answer("❌ Promokod topilmadi.")
        return
    try:
        usage_limit = int(message.text.strip())
        if usage_limit <= 0:
            await message.answer("❌ Foydalanish chegarasi 0 dan katta bo'lishi kerak.")
            return
        if promocode.usage_limit == usage_limit:
            await message.answer(f"❌ Promokod foydalanish chegarasi allaqachon '{usage_limit}' ta turibdi. Boshqa son kiriting: ")
            return
        promocode.usage_limit = usage_limit
        promocode.updated_by = user
        await sync_to_async(promocode.save)()
        await message.answer(f"✅ Promokod foydalanish chegarasi {usage_limit} ta ga yangilandi👆")
        text = await admin_format_promocode_info(promocode)
        await admin_update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, raqam kiriting (masalan, 100). ")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Promokod foydalanish chegarasini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_promocode_router.message(AdminPromocodeFSM.admin_waiting_edit_promocode_activity)
async def admin_edit_promocode_activity(message: Message, state: FSMContext):
    if not (data := await admin_check_state_data(state, message)):
        return 
    promocode, chat_id, message_id, user = (data.get(k) for k in ("promocode", "chat_id", "message_id", "user"))
    if not promocode:
        await message.answer("❌ Promokod topilmadi. Admin qayta urinib ko'ring.")
        return
    activity = message.text.strip()
    try:
        if activity in ["✅ Faol", "❌ Nofaol"]:
            is_active = activity == "✅ Faol"
            if is_active and promocode.end_date < timezone.now():
                    await message.answer("❌ Promokod muddati tugagan. Faollashtirish uchun tugash sanasini o'zgartiring.")
                    return
            if promocode.is_active == is_active:
                await message.answer(f"❌ Promokod faolligi allaqachon '{activity}'da turibdi. Boshqa holat kiriting: ",
                                     reply_markup=ADMIN_ACTIVITY_KEYBOARD)
                return
            promocode.is_active = is_active
            promocode.updated_by = user
            await sync_to_async(promocode.save)()
            await message.answer(f"✅ Promokod faolligi {'faol' if is_active else 'nofaol'} holatga yangilandi👆")
            text = await admin_format_promocode_info(promocode)
            await admin_update_and_clean_messages_promocode(message, chat_id, message_id, text, promocode.id)
        else:
            await message.answer("Admin, faqat '✅ Faol' yoki '❌ Nofaol' deb javob bering.")
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Promokod faollogini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

# Deleting part
@admin_promocode_router.callback_query(IsAdminFilter(), F.data.startswith("admin_promocode_field_delete_promocode"))
async def admin_promocode_delete_callback(callback_query: CallbackQuery, state: FSMContext):
    promocode_id = int(callback_query.data.split(":")[1])
    promocode = await admin_get_promocode_by_id(promocode_id)
    await state.update_data(category_id=promocode_id)
    await callback_query.message.edit_text(f"'{promocode.code}' promokodini o‘chirmoqchimisiz?", reply_markup=admin_delete_confirmation_keyboard("admin_promocode", promocode_id))

@admin_promocode_router.callback_query(IsAdminFilter(), F.data.startswith("admin_promocode_confirm_delete:"))
async def admin_promocode_confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    promocode_id = int(callback_query.data.split(":")[1])
    promocode = await admin_get_promocode_by_id(promocode_id)
    if not promocode:
        await callback_query.answer(f"⚠️ Promokod topilmadi. Admin qaytadan urinib ko'ring.")
        return
    try:
        await sync_to_async(promocode.delete)()
        await callback_query.answer(f"✅ '{promocode.code}' promokodi o‘chirildi.")
        await callback_query.bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Promokodni o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_promocode_router.callback_query(IsAdminFilter(), F.data.startswith("admin_promocode_cancel_delete:"))
async def admin_promocode_cancel_delete(callback_query: CallbackQuery, state: FSMContext):
    promocode_id = int(callback_query.data.split(":")[1])
    promocode = await admin_get_promocode_by_id(promocode_id)
    text = await admin_format_promocode_info(promocode)
    if not promocode:
        await callback_query.answer(f"⚠️ Promokod topilmadi. Admin qaytadan urinib ko'ring")
        return
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(text=text, parse_mode='Markdown', reply_markup=admin_promocode_edit_keyboard(promocode_id))