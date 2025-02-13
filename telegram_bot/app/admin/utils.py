from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram_bot.app.admin.main_controls import ADMIN_MAIN_CONTROLS_KEYBOARD

router = Router()

#Reply keyboards
CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)

ACTIVITY_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Faol"), KeyboardButton(text="❌ Nofaol")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  
)




@router.callback_query(F.data.startswith("delete_message"))
async def callback_message_handlers(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == 'delete_message':
        await callback_query.message.delete()

@router.callback_query(F.data == "◀️ Bosh menu")
async def main_menu(callback_query: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.answer('Asosiy menuga xush kelibsiz!', reply_markup=ADMIN_MAIN_CONTROLS_KEYBOARD)
    await callback_query.answer()

async def single_item_buttons():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Bosh menu", callback_data="◀️ Bosh menu"), 
        InlineKeyboardButton(text="❌ Ushbu xabarni o'chirish", callback_data="delete_message")
    ]])
    return keyboard 

async def confirmation_keyboard(callback_prefix, model_id):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
              InlineKeyboardButton(text="✅ Ha", callback_data=f"{callback_prefix}_confirm_delete:{model_id}"),
              InlineKeyboardButton(text="❌ Yo‘q", callback_data=f"{callback_prefix}_cancel_delete:{model_id}")]])
    return keyboard

def skip_inline_button(callback_prefix):
    keyboard= InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O‘tkazib yuborish", callback_data=f"{callback_prefix}_skip_step")]])
    return keyboard


# async def delete_previous_messages(message: Message, count: int, delay: float = 0.3):
#     """
#     Oldingi xabarlarni o'chiradigan funksiya.
#     :param message: Aiogram Message obyekti
#     :param count: O'chiriladigan xabarlar soni
#     """
#     delete_tasks = []
#     for i in range(1, count + 1):
#         delete_tasks.append(
#             message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - i)
#         )
#     await asyncio.sleep(delay)
#     await asyncio.gather(*delete_tasks, return_exceptions=True)

# async def delete_message_after_delay(message: Message, delay: int):
#     """
#     Xabarni berilgan vaqtdan keyin o'chiradigan funksiya.
#     :param message: Aiogram Message obyekti
#     :param delay: Sekundlarda kutish vaqti
#     """
#     await asyncio.sleep(delay)  
#     await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id) 
