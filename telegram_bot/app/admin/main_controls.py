from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

main_controls_router = Router()
# Buttons
ADMIN_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya"), KeyboardButton(text="📦 Mahsulot bo'limi")],
        [KeyboardButton(text="🏷️ Chegirmalar bo'limi"), KeyboardButton(text="🔖 Promokodlar bo'limi"), KeyboardButton(text="🎁 Sovg'alar bo'limi") ],

    ],
    resize_keyboard=True,
)

CATEGORY_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Kategoriya qo'shish"), KeyboardButton(text="✒️ Kategoriyani tahrirlash")],
        [KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    # one_time_keyboard=True
)

PRODUCT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="✒️ Mahsulotni tahrirlash")],
        [KeyboardButton(text="✨ Barcha mahsulotlarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True
)

DISCOUNT_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Chegirma qo'shish"), KeyboardButton(text="✒️ Chegirmalarni tahrirlash")],
        [KeyboardButton(text="✨ Barcha chegirmalarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
PROMOCODE_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Promocode qo'shish"), KeyboardButton(text="✒️ Promocodeni tahrirlash")],
        [KeyboardButton(text="✨ Barcha promocodelarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
REWARD_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Sovg'a qo'shish"), KeyboardButton(text="✒️ Sovg'ani tahrirlash")],
        [KeyboardButton(text="✨ Barcha sovg'alarni ko'rish"), KeyboardButton(text="◀️ Bosh menu")],
        
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
# Main control handlers
MAIN_CONTROLS_RESPONSES = {
    "📂 Kategoriya": {
        "text": "Kategoriya boshqaruvi uchun tugmalar:",
        "keyboard": CATEGORY_CONTROLS_KEYBOARD
    },
    "📦 Mahsulot bo'limi": {
        "text": "Mahsulot boshqaruvi uchun tugmalar:",
        "keyboard": PRODUCT_CONTROLS_KEYBOARD
    },
    "🏷️ Chegirmalar bo'limi": {
        "text": "Chegirmalarni boshqaruvi uchun tugmalar:",
        "keyboard": DISCOUNT_CONTROLS_KEYBOARD
    },
    "🔖 Promokodlar bo'limi": {
        "text": "Pomokodlarni boshqaruvi uchun tugmalar:",
        "keyboard": PROMOCODE_CONTROLS_KEYBOARD
    },
    "🎁 Sovg'alar bo'limi": {
        "text": "Sovg'alar boshqaruvi uchun tugmalar:",
        "keyboard": REWARD_CONTROLS_KEYBOARD
    },
    "◀️ Bosh menu": {
        "text": "Asosiy menuga xush kelibsiz!",
        "keyboard": ADMIN_MAIN_CONTROLS_KEYBOARD,
        "clear_state": True 
    }
}


@main_controls_router.message(F.text.in_(MAIN_CONTROLS_RESPONSES))
async def main_controls_handler(message: Message, state: FSMContext):
    response = MAIN_CONTROLS_RESPONSES[message.text]
    await message.answer(response["text"], reply_markup=response["keyboard"])
    if response.get("clear_state"):
        await state.clear()
