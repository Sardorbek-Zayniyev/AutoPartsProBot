from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import  Reward
from telegram_bot.app.user.main_controls import REWARD_CONTROLS_KEYBOARD

reward_router = Router()


class RewardFSM(StatesGroup):
    waiting_show_my_points = State()
    waiting_show_my_aimed_rewards = State()
    waiting_viewing_available_rewards = State()











@reward_router.message(F.text.in_(("🏆 Mening ballarim","⭐ Mening erishgan yutuqlarim", "🎀 Mavjud sovg'alar")))
async def gamification_controls_handler(message: Message, state: FSMContext):
    """
    Handle gamification control actions (My scores, See rewards)
    """

    actions = {
        "🏆 Mening ballarim": (RewardFSM.waiting_show_my_points, show_points),
        # "⭐ Mening erishgan yutuqlarim": (RewardFSM.waiting_show_my_aimed_rewards, show_my_rewards),
        "🎀 Mavjud sovg'alar": (RewardFSM.waiting_viewing_available_rewards, show_rewards),
    }
    next_state, handler_function = actions[message.text]
    if next_state:
        await state.set_state(next_state)
    await handler_function(message, state)




@reward_router.message(RewardFSM.waiting_show_my_points)
async def show_points(message: Message, state: FSMContext):
    user = await get_user_from_db(message.from_user.id)
    await message.answer(f"Sizda {user.points} ball to'plangan.")

@reward_router.message(RewardFSM.waiting_viewing_available_rewards)
async def show_rewards(message: Message, state: FSMContext):
    rewards = await sync_to_async(list)(Reward.objects.filter(is_active=True))
    if rewards:
        rewards_text = "Mavjud sovg'alar:\n\n"
        for reward in rewards:
            rewards_text += f"🎁 {reward.name} - {reward.points_required} ball\n"
        await message.answer(rewards_text, reply_markup=None)
    else:
        await message.answer("Hozircha mavjud sovg'alar yo'q.")

