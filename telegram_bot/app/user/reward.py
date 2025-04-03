import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsUserFilter
from telegram_app.models import Reward, RewardHistory
from telegram_bot.app.user.utils import user_keyboard_back_to_rewards

user_reward_router = Router()

class UserRewardFSM(StatesGroup):
    user_waiting_get_my_points = State()
    user_waiting_get_all_rewards = State()
    user_waiting_get_all_my_rewards = State()

REWARD_TYPES = {
        "free_shipping": "🚚 Bepul yetkazib berish",
        "gift": "🎁 Sovg'a",
        "promocode": "🎟 Promokod",
    }

# Reward ma'lumotlarini faqat kerakli qiymatlarni olish
async def user_get_reward_by_id(reward_id):
    return await sync_to_async(lambda: Reward.objects.filter(id=reward_id).values('id', 'name', 'reward_type', 'points_required', 'description').first())()

# Reward ma'lumotlarini formatlash
async def user_format_reward_info(reward_dict):
    return (
        f"🎁 Sovg'a nomi: *{reward_dict['name']}*\n"
        f"📌 Sovg'a turi: *{REWARD_TYPES.get(reward_dict['reward_type'], 'Noma’lum')}*\n"
        f"🔢 Kerakli ball: *{reward_dict['points_required']}*\n"
        f"📄 Tavsif: *{'Yo‘q' if not reward_dict['description'] else reward_dict['description']}*\n"
    )

# Reward uchun inline klaviatura
def user_reward_keyboard(reward_id, add_to_cart_state=None):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"user_add_single_reward_to_cart:{reward_id}") if add_to_cart_state else  InlineKeyboardButton(text="Sotib olish", callback_data=f"user_purchase_reward:{reward_id}"),
        InlineKeyboardButton(text="❌", callback_data="user_delete_message"),
        InlineKeyboardButton(text="⬅️ Bosh menu", callback_data="user_main_menu"),
    )
    builder.adjust(1, 2)  
    
    return builder.as_markup()

# Rewardlarni qidirish natijalarini ko‘rsatish
async def user_handle_reward_search_results(message: Message, rewards, state: FSMContext):
    if not rewards:
        await message.answer("❌ Hech qanday sovg'a topilmadi.")
        return
    
    await state.update_data(user_search_results=rewards)
    
    rewards_with_numbers = [(index + 1, reward) for index, reward in enumerate(rewards)]
    total_pages = ((len(rewards_with_numbers) + 9) // 10)
    await user_display_fetched_rewards_page(1, message, rewards_with_numbers, total_pages, 10, "user_search_reward", state)

# Boshqa sahifalarni ko‘rsatish
async def user_handle_reward_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')
    
    page_num = int(data_parts[1])
    state_data = await state.get_data()
    rewards = state_data.get("user_search_results", [])
   
    rewards_with_numbers = [(index + 1, reward) for index, reward in enumerate(rewards)]
    rewards_per_page = 10
    total_pages = (len(rewards_with_numbers) + rewards_per_page - 1) // rewards_per_page
    
    await user_display_fetched_rewards_page(page_num, callback_query, rewards_with_numbers, total_pages, rewards_per_page, callback_prefix, state)
    await callback_query.answer()

# Reward sahifasini ko‘rsatish
async def user_display_fetched_rewards_page(page_num, callback_query_or_message, rewards_with_numbers, total_pages, rewards_per_page, callback_prefix, state):
    start_index = (page_num - 1) * rewards_per_page
    end_index = min(start_index + rewards_per_page, len(rewards_with_numbers))
    page_rewards = rewards_with_numbers[start_index:end_index]
    current_state = await state.get_state()

    if not current_state:
        text = "❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang."
        if isinstance(callback_query_or_message, CallbackQuery):
            await callback_query_or_message.answer(text, show_alert=True)
        else:
            await callback_query_or_message.answer(text)  
        return
    
    add_reward_to_cart_state = False
    
    if current_state.startswith('UserCartFSM'):
        add_reward_to_cart_state = True

    message_text = (
        f"🎟 Promokod qo'shish bo'limi:\n\n" if add_reward_to_cart_state else f"✨ Sovg'alarni ko'rish bo'limi:\n\n" 
        f"🔍 Umumiy natija: {len(rewards_with_numbers)} ta sovg'a topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )
    
    for number, reward in page_rewards:
        message_text += f"{number}. {reward['name'] + '  ——  ' + REWARD_TYPES.get(reward['reward_type'], 'Noma’lum')}\n"
    
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()
    
    for number, reward in page_rewards:
        if add_reward_to_cart_state:
            callback_data = f"user_reward:{reward['reward_fk']}:add_to_cart" 
        else:
            callback_data = f"user_reward:{reward['id']}:get" 
        builder.button(text=str(number), callback_data=callback_data)
    
    builder.adjust(5)
    
    if total_pages > 1:
        pagination_buttons = []
        if page_num > 1:
            pagination_buttons.append({"text": "⬅️", "callback_data": f"{callback_prefix}_other_pages:{page_num - 1}"})

        pagination_buttons.append({"text": "❌", "callback_data": "user_delete_message"})

        if page_num < total_pages:
            pagination_buttons.append({"text": "➡️", "callback_data": f"{callback_prefix}_other_pages:{page_num + 1}"})

        for btn in pagination_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(pagination_buttons)) 
    
    else:
        pagination.button(text="❌", callback_data="user_delete_message")
        pagination.adjust(5, 5, 1)  

    additional_buttons = user_keyboard_back_to_rewards().inline_keyboard

    final_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export() + pagination.export() + additional_buttons)
    
    if isinstance(callback_query_or_message, CallbackQuery):
        await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=final_keyboard, parse_mode="HTML"
        )
    else:
        await callback_query_or_message.answer(
            text=message_text, reply_markup=final_keyboard, parse_mode="HTML"
        )

# Foydalanuvchi ballarini ko‘rsatish
@user_reward_router.message(UserRewardFSM.user_waiting_get_my_points)
async def user_get_points(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    await message.answer(f"Sizda {user.points} ball to'plangan.")
    await state.clear()

# Sovg'ani sotib olish
@user_reward_router.callback_query(IsUserFilter(), F.data.startswith("user_purchase_reward:"))
async def user_purchase_reward(callback_query: CallbackQuery, state: FSMContext):
    try:
        reward_id = int(callback_query.data.split(':')[1])  
        reward = await user_get_reward_by_id(reward_id)  

        if not reward:
            await callback_query.answer("❌ Sovg'a topilmadi!", show_alert=True)
            return

        user = await get_user_from_db(callback_query.from_user.id) 

        if not user:
            await callback_query.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return

        # Reward obyektini qayta yaratish (redeem uchun)
        reward_obj = await sync_to_async(Reward.objects.get)(id=reward_id)
        result = await sync_to_async(reward_obj.redeem)(user)  

        if result:
            sent_message = await callback_query.message.edit_text(f"🎉 Tabriklaymiz! '{reward['name']}' sovg'asi endi sizniki!", show_alert=True)
            await asyncio.sleep(2)
            await callback_query.bot.delete_message(chat_id = callback_query.message.chat.id, message_id=sent_message.message_id)
        else:
            await callback_query.answer("❌ Ushbu sovg'ani olish uchun sizning ballaringiz yetarli emas!", show_alert=True)
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer("❌ Xatolik yuz berdi!")
        print(f"Error in user_purchase_reward: {e}")

# Foydalanuvchi sotib olgan sovg'alarni ko‘rsatish
@user_reward_router.message(UserRewardFSM.user_waiting_get_all_my_rewards)
async def user_get_all_my_rewards(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)

    reward_history = await sync_to_async(list)(
        RewardHistory.objects.filter(is_successful=True, user=user).values('reward__name', 'points_used', 'redeemed_at', 'is_used', 'reward__description').order_by('-redeemed_at')
    )

    if reward_history:
        rewards_text = "🎁 Sotib olingan sovg'alar:\n\n"
        for number, history in enumerate(reward_history, 1):
            rewards_text += f"⭐ {number}. -Nomi: {history['reward__name']}\n           -{history['points_used']} ball, {"Faol ✅" if not history['is_used'] else "Ishlatilgan ❌"}\n           -Tavsifi: {history['reward__description'] if history['reward__description'] else "Yo'q"}\n           -Sotib olingan vaqti: {history['redeemed_at'].strftime('%d-%m-%Y %H:%M')}\n"
        await message.answer(rewards_text)
    else:
        await message.answer("📭 Hozircha siz sotib olgan sovg'alar yo'q.")

    await state.clear()

# Barcha sovg'alarni ko‘rsatish
@user_reward_router.message(UserRewardFSM.user_waiting_get_all_rewards)
async def user_get_all_rewards(message: Message, state: FSMContext):
    rewards = await sync_to_async(list)(
        Reward.objects.filter(is_active=True).order_by('-created_at').values('id', 'name', 'reward_type')
    )
    await user_handle_reward_search_results(message, rewards, state)

# Boshqa sahifalarni ko‘rsatish uchun callback
@user_reward_router.callback_query(IsUserFilter(), F.data.startswith('user_search_reward_other_pages:'))
async def user_get_all_rewards_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await user_handle_reward_other_pages(callback_query, state, callback_prefix="user_search_reward")

# Bitta sovg'ani ko‘rsatish
@user_reward_router.callback_query(IsUserFilter(), F.data.startswith('user_reward:'))
async def user_get_single_reward(callback_query: CallbackQuery):
    await callback_query.answer()
    reward_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2] == "add_to_cart"
    reward = await user_get_reward_by_id(reward_id)
    
    if not reward:
        await callback_query.message.answer("❌ Sovg'a topilmadi.")
        await callback_query.answer()
        return

    reward_info = await user_format_reward_info(reward)

    try:
        if action:
            await callback_query.message.edit_text(
            text=reward_info, 
            parse_mode='Markdown', 
            reply_markup=user_reward_keyboard(reward['id'], action)
        ) 
        else:
            await callback_query.message.answer(
            text=reward_info, 
            parse_mode='Markdown', 
            reply_markup=user_reward_keyboard(reward['id'], action)
        ) 

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Sovg'ani yuklashda xatolik yuz berdi. Qayta urinib ko'ring.")

    await callback_query.answer()































