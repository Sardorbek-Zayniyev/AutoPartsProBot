from aiogram import Router, F
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from django.db import IntegrityError
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db
from telegram_app.models import Category
from telegram_bot.app.admin.utils import skip_inline_button, single_item_buttons, confirmation_keyboard, ACTIVITY_KEYBOARD
from telegram_bot.app.admin.main_controls import CATEGORY_CONTROLS_KEYBOARD



category_router = Router()


class CategoryFSM(StatesGroup):
    waiting_get_category = State()
    waiting_save_get_category = State()
    waiting_show_categories_for_edition = State()
    waiting_update_category = State()
    waiting_save_updated_category = State()
    waiting_show_categories_for_deletion = State()
    waiting_category_delete_confirm = State()
    waiting_delete_category = State()




@category_router.callback_query(F.data == "category_buttons")
async def category_buttons_callback(callback_query: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.answer('Kategoriya boshqaruvi uchun tugmalar:', reply_markup=CATEGORY_CONTROLS_KEYBOARD)
    await callback_query.answer()

@category_router.message(F.text.in_(("➕ Kategoriya qo'shish", "✒️ Kategoriyani tahrirlash")))
async def category_controls_handler(message: Message, state: FSMContext):
    """
    Handle category management actions (add, edit, delete).
    """
    actions = {
        "➕ Kategoriya qo'shish": (CategoryFSM.waiting_get_category, get_category),
        "✒️ Kategoriyani tahrirlash": (CategoryFSM.waiting_show_categories_for_edition, show_categories_for_edition),
    }
    next_state, handler_function = actions[message.text]
    await state.set_state(next_state)
    await handler_function(message, state)


async def show_category_list(message: Message):
    """
    Kategoriyalar ro'yxatini qayta yangilaydi va foydalanuvchiga ko'rsatadi.
    """
    categories = await sync_to_async(lambda: list(Category.objects.all()))()
    if not categories:
        await message.answer("Hozircha kategoriyalar mavjud emas.")
        return

    category_names = [category.name for category in categories]
    buttons = [KeyboardButton(text=name) for name in category_names]
    back_button = KeyboardButton(text="◀️ Bosh menu")

    # Yangi kategoriya tugmalarini yaratish
    category_keyboard = ReplyKeyboardMarkup(
        keyboard=[buttons[i:i + 2]
                  for i in range(0, len(buttons), 2)] + [[back_button]],
        resize_keyboard=True
    )
    return category_keyboard

async def get_categories_keyboard(callback_data_prefix: str, state: FSMContext) -> InlineKeyboardMarkup:

    categories = await sync_to_async(list)(Category.objects.all())
    category_buttons = []
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                row.append(InlineKeyboardButton(
                    text=categories[i + j].name, callback_data=f"{callback_data_prefix}:{categories[i + j].id}"))
        category_buttons.append(row)
    # if await state.get_state() == CategoryFSM.waiting_show_categories_for_edition:
    #     category_buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"category_buttons"),
    #                              InlineKeyboardButton(text="◀️ Bosh menu", callback_data=f"◀️ Bosh menu")])
    return InlineKeyboardMarkup(inline_keyboard=category_buttons)

async def category_edit_keyboard(category_id):
    edit_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✒️ Nomini tahrirlash", callback_data=f"edit_category:{category_id}"),
         InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_category:{category_id}")],
        [InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"show_categories")]
         ]) 
    return edit_button

async def update_and_clean_messages_category(message: Message, chat_id: int, message_id: int, text: str, category_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=(await category_edit_keyboard(category_id))
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)




# Adding part
@category_router.message(CategoryFSM.waiting_get_category)
async def get_category(message: Message, state: FSMContext):
    """
    Yangi kategoriya qo'shish jarayonini boshlaydi.
    """
    await message.answer("Yangi kategoriya nomini kiriting:")
    await state.set_state(CategoryFSM.waiting_save_get_category)

@category_router.message(CategoryFSM.waiting_save_get_category)
async def save_get_category(message: Message, state: FSMContext):
    """
    Foydalanuvchi kiritgan yangi kategoriyani ma'lumotlar bazasiga qo'shadi.
    """
    category_name = message.text.strip()
    if not category_name:
        await message.answer("Kategoriya nomi bo'sh bo'lishi mumkin emas. Admin, qayta kiriting.")
        return

    try:
        category = await sync_to_async(Category.objects.create)(name=category_name)
        await message.answer(f"✅ '{category.name}' kategoriyasi muvaffaqiyatli qo'shildi!")
        await message.answer("Kategoriya ro'yxati yangilandi 👇", reply_markup=(await show_category_list(message)))
    except IntegrityError:
        await message.answer(f"⚠️ '{category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom kiriting.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()

# Upadating part
@category_router.message(CategoryFSM.waiting_show_categories_for_edition)
async def show_categories_for_edition(message: Message, state: FSMContext): 
    await message.answer("Tahrirlanadigan kategoriyani tanlang:", reply_markup=await get_categories_keyboard("category_edit", state))
    
@category_router.callback_query(F.data == "show_categories")
async def show_categories_menu_for_edition_callback(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(CategoryFSM.waiting_show_categories_for_edition)
    await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))

@category_router.callback_query(F.data.startswith("category_edit:"))
async def category_edit(callback_query: CallbackQuery, state: FSMContext):
  
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if not category:
        await callback_query.answer('❌ Ushbu kategoriya mavjud emas')
        return

    
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id

    await state.update_data(category_id=category_id, chat_id=chat_id, message_id=message_id)
    await callback_query.message.edit_text(f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇", reply_markup=await category_edit_keyboard(category_id))
    await state.set_state(CategoryFSM.waiting_save_updated_category)

@category_router.callback_query(F.data.startswith("edit_category:"))
async def edit_category_callback(callback_query: CallbackQuery, state: FSMContext):
 
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if not category:
        await callback_query.answer('❌ Ushbu kategoriya mavjud emas')
        return

    await callback_query.message.edit_text(f"Tanlangan kategoriya: {category.name}\n\nYangi nomni kiriting: 👇")
    await callback_query.answer()
    await state.update_data(category_id=category_id)
    await state.set_state(CategoryFSM.waiting_save_updated_category)

@category_router.message(CategoryFSM.waiting_save_updated_category)
async def save_updated_category(message: Message, state: FSMContext):
  
    new_category_name = message.text.strip().title()

    if not new_category_name:
        await message.answer("Kategoriya nomi bo'sh bo'lishi mumkin emas. Admin, qayta kiriting.👇")
        return
    
    if new_category_name.isdigit():
        await message.answer("❌ Kategoriya nomifaqat raqamlardan iborat bo‘lishi mumkin emas. Admin, boshqa nom kiriting!👇")
        return

    data = await state.get_data()
    chat_id, message_id, category_id = data.get("chat_id"), data.get("message_id"), data.get("category_id")


    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if category.name == new_category_name:
        await message.answer(f"⚠️ '{new_category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom kiriting.")
        return
    
    try:
        category.name = new_category_name
        await sync_to_async(category.save)()
        await message.answer(f"✅ Kategoriya '{new_category_name}' nomiga o'zgartirildi 👆")
        
        text = f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇"
        await update_and_clean_messages_category(message, chat_id, message_id, text, category_id )
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Kategoriya nomini yangilashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@category_router.callback_query(F.data.startswith("delete_category"))
async def delete_category_callback(callback_query: CallbackQuery, state: FSMContext):
 
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    await state.update_data(category_id=category.id)
    await callback_query.message.edit_text(f"'{category.name}' kategoriyasini o‘chirmoqchimisiz?", reply_markup=await confirmation_keyboard(category ,category_id))

@category_router.callback_query(F.data.startswith("category_confirm_delete:"))
async def confirm_delete_category(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id, message_id = data.get("chat_id"), data.get("message_id")
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()

    if not category:
        await callback_query.answer(f"⚠️ Kategoriya topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    try:
        await sync_to_async(category.delete)()  
        await callback_query.answer(f"✅ '{category.name}' kategoriyasi o‘chirildi.")

        if message_id and chat_id:
            await callback_query.bot.delete_message(chat_id=chat_id, message_id=callback_query.message.message_id)
            for msg_id in range(callback_query.message.message_id, message_id, -1):
                await callback_query.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            await callback_query.message.answer("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))
        else:
            await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await get_categories_keyboard("category_edit", state))
        await state.clear()
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Kategoriya o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@category_router.callback_query(F.data.startswith("category_cancel_delete:"))
async def cancel_delete_category(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id, message_id = data.get("chat_id"), data.get("message_id")
    category_id = int(callback_query.data.split(":")[1])
    category = await sync_to_async(Category.objects.filter(id=category_id).first)()
    
    if not category:
        await callback_query.answer(f"⚠️ Kategoriya topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇", reply_markup=await category_edit_keyboard(category_id))

    if message_id and chat_id:
        text = f"Tanlangan kategoriya: {category.name}\nMaydonni tanlang:👇"
        await update_and_clean_messages_category(callback_query.message, chat_id, message_id, text, category_id )

# Category part ended