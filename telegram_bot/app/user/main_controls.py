from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message


main_controls_router = Router ()

USER_MAIN_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗂 Katalog"), KeyboardButton(text="🔎 Qidiruv")],
        [KeyboardButton(text="📜 Mening buyurtmalarim"), KeyboardButton(text="🛒 Savat")],
        [KeyboardButton(text="🏆 Mening ballarim"), KeyboardButton(text="🎁 Sovg'alar")],
        [KeyboardButton(text="👤 Profil"),  KeyboardButton(text="❓ Yordam")],
    ],
    resize_keyboard=True,
)

CART_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👁️ Savatni ko'rish"), KeyboardButton(
            text="♥️ Saqlangan mahsulotlar")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

CATALOG_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Aksiyalar")],
        [KeyboardButton(text="🆕 Yangi"), KeyboardButton(text="🔄 B/U")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

ORDERS_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏳ Joriy buyurtmalar"),
         KeyboardButton(text="📜 Buyurtma tarixi")],
        [KeyboardButton(text="🚫 Buyurtmani bekor qilish")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

PRODUCT_SEARCH_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Kategoriya"), KeyboardButton(
            text="🔤 Ehtiyot qism nomi")],
        [KeyboardButton(text="🚘 Mashina brendi"),
         KeyboardButton(text="🚗 Mashina modeli")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)

REWARD_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Mening erishgan yutuqlarim"), KeyboardButton(text="🎀 Mavjud sovg'alar")],
        [KeyboardButton(text="⬅ Bosh menu")],

    ],
    resize_keyboard=True,
)

PROFILE_CONTROLS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Profil ma'lumotlari"), KeyboardButton(text="📍 Manzilni yangilash")],
        [KeyboardButton(text="📝 Ismni yangilash"), KeyboardButton(text="📱 Qo'shimcha raqam kiritish")],
        [KeyboardButton(text="⬅ Bosh menu")],
    ],
    resize_keyboard=True,
)


MAIN_CONTROLS_RESPONSES = {
    "🗂 Katalog": {
        "text": "Katalog boshqaruvi uchun tugmalar:",
        "keyboard": CATALOG_CONTROLS_KEYBOARD,
    },
    "🔎 Qidiruv": {
        "text": "Mahsulot qidiruvi uchun tugmalar:",
        "keyboard": PRODUCT_SEARCH_CONTROLS_KEYBOARD
    },
    "📜 Mening buyurtmalarim": {
        "text": "Buyurtmalar boshqaruvi uchun tugmalar:",
        "keyboard": ORDERS_CONTROLS_KEYBOARD
    },
    "🛒 Savat": {
        "text": "Savat boshqaruvi uchun tugmalar:",
        "keyboard": CART_CONTROLS_KEYBOARD
    },
    "👤 Profil": {
        "text": "Profil sozlamalari uchun tugmalar:",
        "keyboard": PROFILE_CONTROLS_KEYBOARD
    },
    "🏆 Mening ballarim": {
        "text": "",
        "keyboard": None
    },
    "🎁 Sovg'alar": {
        "text": "Sovg'alar uchun tugmalar:",
        "keyboard": REWARD_CONTROLS_KEYBOARD,
    },
    "⬅ Bosh menu": {
        "text": "Asosiy menuga xush kelibsiz!",
        "keyboard": USER_MAIN_CONTROLS_KEYBOARD,
        "clear_state": True
    }
}



@main_controls_router.message(F.text.in_(MAIN_CONTROLS_RESPONSES))
async def main_controls_handler(message: Message, state: FSMContext):
    response = MAIN_CONTROLS_RESPONSES[message.text]
    await message.answer(response["text"], reply_markup=response["keyboard"])
    if response.get("clear_state"):
        await state.clear()
