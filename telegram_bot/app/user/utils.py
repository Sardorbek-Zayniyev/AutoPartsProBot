from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message



utils_router = Router()

@utils_router.callback_query(F.data == 'delete_message')
async def delete_message_handler(callback_query: CallbackQuery):
    await callback_query.message.delete()
