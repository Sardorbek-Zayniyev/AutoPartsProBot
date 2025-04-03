from aiogram import Router, F
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder,  ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from django.db import IntegrityError
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_app.models import Category
from aiogram.exceptions import TelegramBadRequest
from telegram_bot.app.admin.product import admin_show_parent_categories
from telegram_bot.app.admin.utils import (
    admin_escape_markdown,
    admin_single_item_buttons,
    admin_delete_confirmation_keyboard,
    admin_keyboard_back_to_category,
    )

admin_category_router = Router()

class AdminCategoryFSM(StatesGroup):
    # Get
    admin_waiting_get_all_categories = State()
    # Add
    admin_waiting_get_category_name = State()
    admin_waiting_save_subcategory = State()
    admin_waiting_get_sub_category_name = State()
    #Edit
    admin_waiting_get_parent_categories_for_edition = State()
    # admin_waiting_update_category = State()
    admin_waiting_save_edited_category = State()

#Utils
async def admin_get_category_by_id(category_id):
    return await sync_to_async(lambda: Category.objects.select_related('owner', 'updated_by').filter(id=category_id).first())()

async def admin_format_category_info(category):
    owner_name = admin_escape_markdown(category.owner.full_name) 
    updated_by_name = admin_escape_markdown(category.updated_by.full_name)
    return (
        f"📂 *Nomi:* {category.name}\n"
        f"📝 *Tavsifi:* {category.description or 'Yo‘q'}\n"
        f"👤 Yaratgan: [{owner_name}](tg://user?id={category.owner.telegram_id})\n"
        f"✏️ Oxirgi tahrir: [{updated_by_name}](tg://user?id={category.updated_by.telegram_id})\n"
    )

def admin_category_edit_keyboard(category_id):
    builder = InlineKeyboardBuilder()

    builder.button(text="Nomi", callback_data=f"admin_edit_category_name:{category_id}")
    builder.button(text="Tavsifi", callback_data=f"admin_edit_category_description:{category_id}")

    builder.row(
        InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"admin_get_sub_categories:{category_id}"),
        InlineKeyboardButton(text="❌", callback_data="admin_delete_message"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_delete_category:{category_id}"))
    return builder.as_markup()

async def admin_get_categories_keyboard(callback_data_prefix: str, state: FSMContext) -> InlineKeyboardMarkup:
    data = await state.get_data()
    categories = data.get('categories') if data else None
    if categories is None:
        categories = await sync_to_async(lambda: list(Category.objects.filter(parent_category__isnull=True)))()
        if not categories:  
            categories = []  
        await state.update_data(categories=categories)

    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category.name,
            callback_data=f"{callback_data_prefix}:{category.id}"
        )
    builder.adjust(2, repeat=True)
    return InlineKeyboardMarkup(inline_keyboard=builder.export() + admin_keyboard_back_to_category().inline_keyboard)

async def admin_handle_category_search_results(message: Message, categories, state: FSMContext):
    if not categories:
        await message.answer("❌ Hech qanday kategoriya topilmadi.")
        return
    
    # Store the search results in the state
    await state.update_data(search_results=categories)
    
    categories_with_numbers = [(index + 1, category) for index, category in enumerate(categories)]
    total_pages = ((len(categories_with_numbers) + 9) // 10)
    await admin_display_categories_page(1, message, categories_with_numbers, total_pages, 10, "admin_search_category", state)

async def admin_handle_category_other_pages(callback_query: CallbackQuery, state: FSMContext, callback_prefix: str):
    data_parts = callback_query.data.split(':')

    page_num = int(data_parts[1])

    data = await state.get_data() or {}
    categories = data.get("search_results", [])
   
    categories_with_numbers = [(index + 1, category) for index, category in enumerate(categories)]
    categories_per_page = 10
    total_pages = (len(categories_with_numbers) + categories_per_page - 1) // categories_per_page
    
    await admin_display_categories_page(page_num, callback_query, categories_with_numbers, total_pages, categories_per_page, callback_prefix, state)
    await callback_query.answer()

async def admin_display_categories_page(
    page_num: int,
    callback_query_or_message: CallbackQuery | Message,
    categories_with_numbers: list[tuple[int, Category]],
    total_pages: int,
    categories_per_page: int,
    callback_prefix: str,
    state: FSMContext
) -> None:
    """
    Displays a paginated list of categories with inline buttons for navigation.
    """
    # Calculate the start and end indices for the current page
    start_index = (page_num - 1) * categories_per_page
    end_index = min(start_index + categories_per_page, len(categories_with_numbers))
    page_categories = categories_with_numbers[start_index:end_index]

    # Check if the current state is for getting all categories
    get_all_categories_state = await state.get_state() == AdminCategoryFSM.admin_waiting_get_all_categories

    # Build the message text
    message_text = (
        f"{'✨ Kategoriyani ko\'rish bo\'limi:\n\n' if get_all_categories_state else '✒️ Kategoriyani tahrirlash bo\'limi: \n\n'}"
        f"🔍 Umumiy natija: {len(categories_with_numbers)} ta kategoriyalar topildi.\n\n"
        f"Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
    )

    for number, category in page_categories:
        message_text += f"{number}. {category.name}\n"

    # Initialize the keyboard builder
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()

    # Add category buttons
    for number, category in page_categories:
        callback_data = (
            f"admin_category:{category.id}:get" if get_all_categories_state else
            f"admin_category:{category.id}:none"
        )
        builder.button(text=str(number), callback_data=callback_data)
       
    builder.adjust(5)

    if total_pages > 1:
        pagination_buttons = []
    
        if page_num > 1:
            prev_callback = f"{callback_prefix}_other_pages:{page_num - 1}" 
            pagination_buttons.append({"text": "⬅️", "callback_data": prev_callback})

        pagination_buttons.append({"text": "❌", "callback_data": "admin_delete_message"})

        if page_num < total_pages:
            next_callback = f"{callback_prefix}_other_pages:{page_num + 1}" 
            pagination_buttons.append({"text": "➡️", "callback_data": next_callback})

        for btn in pagination_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(pagination_buttons)) 

    else:
        pagination.button(text="❌", callback_data="admin_delete_message")
        pagination.adjust(5, 5, 1)  

    additional_buttons = admin_keyboard_back_to_category().inline_keyboard
    
    final_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export()+ pagination.export() + additional_buttons)

    # Send or edit the message
    if isinstance(callback_query_or_message, CallbackQuery):
        new_message = await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=final_keyboard, parse_mode="Markdown"
        )
    else:
        new_message = await callback_query_or_message.answer(
            text=message_text, reply_markup=final_keyboard, parse_mode="Markdown"
        )

    # Update the state with the new message ID
    await state.update_data(message_ids=[new_message.message_id])

async def admin_update_and_clean_message_category(message: Message, chat_id: int, message_id: int, text: str, category_id: int):
    """
    Xabarni yangilash va eski xabarlarni o'chirish.
    """
    await message.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode='Markdown',
        reply_markup=admin_category_edit_keyboard(category_id)
    )

    delete_tasks = []
    for msg_id in range(message.message_id, message_id, -1):
        delete_tasks.append(
            message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )

    # Bir vaqtning o'zida barcha xabarlarni o'chirish
    await asyncio.gather(*delete_tasks, return_exceptions=True)

#Get all categories
@admin_category_router.message(AdminCategoryFSM.admin_waiting_get_all_categories)
async def admin_get_all_categories(message: Message, state: FSMContext, order_by: str):
    products = await sync_to_async(list)(Category.objects.all().order_by(order_by))
    await admin_handle_category_search_results(message, products, state)

@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_category_other_pages:'))
async def admin_get_all_categories_other_pages(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_category_other_pages(callback_query, state, callback_prefix="admin_search_category")

# Get single category
@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith('admin_category:'))
async def admin_get_single_category(callback_query: CallbackQuery):
    category_id = int(callback_query.data.split(':')[1])
    action = callback_query.data.split(':')[2]
    category = await admin_get_category_by_id(category_id)
    
    if not category:
        await callback_query.message.answer("❌ Kategoriya topilmadi.", reply_markup=admin_keyboard_back_to_category())
        await callback_query.answer()
        return
    
    category_info = await admin_format_category_info(category)

    try:
        if action == "get":
            await callback_query.message.answer(text=category_info, parse_mode='Markdown', reply_markup=admin_single_item_buttons())
        else:
            await callback_query.message.answer(text=category_info, parse_mode='Markdown', reply_markup=admin_category_edit_keyboard(category_id))
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Kategoriyani yuklashda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

    await callback_query.answer()

# Adding part
@admin_category_router.message(AdminCategoryFSM.admin_waiting_get_category_name)
async def admin_get_category_name(message: Message, state: FSMContext):
    """
    Yangi kategoriya qo'shish jarayonini boshlaydi.
    """
    category_template = (
        "Kategoriyani yaratish uchun kerakli ma'lumotlarni kiriting!\n"
        "1.📂 *Nomi:*\n"
        "2.📝 *Tavsifi:*\n\n"
    )
    await message.answer(text=category_template, parse_mode='Markdown')
    await message.answer("Yangi kategoriya nomini kiriting yoki subkategoriya qo'shish uchun kategoriya tanlang 👇",
                         reply_markup=await admin_show_parent_categories(message))
    await state.set_state(AdminCategoryFSM.admin_waiting_get_sub_category_name)

@admin_category_router.message(AdminCategoryFSM.admin_waiting_get_sub_category_name)
async def admin_get_sub_category_name(message: Message, state: FSMContext):
    """
    Foydalanuvchi kiritgan yangi kategoriyani ma'lumotlar bazasiga qo'shadi.
    """
    user = await get_user_from_db(message.from_user.id) 
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Admin, qayta urinib ko‘ring.")
        return

    category_name = message.text.strip().title()

    existing_category = await sync_to_async(lambda: Category.objects.filter(name=category_name, parent_category__isnull=True).first())()
    
    if existing_category:
        await message.reply(f"✅ Ushbu kategoriya tanlandi. Endi yangi subkategoriya nomini yozing 👇")
        await state.update_data(parent_category_id=existing_category.id)
        await state.set_state(AdminCategoryFSM.admin_waiting_save_subcategory)
    else:
        try:
            category = await sync_to_async(Category.objects.create)(owner=user, updated_by=user, name=category_name)
            await message.reply(f"✅ Ushbu yangi kategoriya muvaffaqiyatli qo'shildi! Endi yangi subkategoriya nomini yozing 👇")
            await state.update_data(parent_category_id=category.id)
            await state.set_state(AdminCategoryFSM.admin_waiting_save_subcategory)
        except IntegrityError:
            await message.answer(f"⚠️ '{category_name}' nomli kategoriya allaqachon mavjud. Boshqa nom yozing.")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@admin_category_router.message(AdminCategoryFSM.admin_waiting_save_subcategory)
async def admin_save_new_subcategory(message: Message, state: FSMContext):
    """
    Subkategoriya qo'shish jarayoni.
    """
    user = await get_user_from_db(message.from_user.id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Admin, qayta urinib ko‘ring.")
        return
    
    data = await state.get_data() or {}

    parent_category_id = data.get("parent_category_id")
    subcategory_name = message.text.strip().title()
    
    existing_subcategory = await sync_to_async(Category.objects.filter(name=subcategory_name, parent_category_id=parent_category_id).first)()
    if existing_subcategory:
        await message.answer(f"⚠️ '{subcategory_name}' subkategoriya allaqachon mavjud. Boshqa nom kiriting.")
        return
    try:
        subcategory = await sync_to_async(Category.objects.create)(
            owner=user, updated_by=user, name=subcategory_name, parent_category_id=parent_category_id
        )
        from telegram_bot.app.admin.main_controls import ADMIN_CATEGORY_CONTROLS_KEYBOARD
        await message.reply(f"✅ Ushbu subkategoriya muvaffaqiyatli qo'shildi!", reply_markup=ADMIN_CATEGORY_CONTROLS_KEYBOARD)
        await state.clear()
    except IntegrityError:
            await message.answer(f"⚠️ '{subcategory_name}' nomli kategoriya allaqachon mavjud. Boshqa sub kategoriya nom yozing.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)} qayta urinib ko'ring. ")

# Editing part
@admin_category_router.message(AdminCategoryFSM.admin_waiting_get_parent_categories_for_edition)
async def admin_get_categories_for_edition(message: Message, state: FSMContext): 
    await message.answer("Bosh kategoriyalar:", reply_markup=await admin_get_categories_keyboard("admin_get_sub_categories", state))
    
@admin_category_router.callback_query(IsAdminFilter(), F.data == "admin_get_parent_categories")
async def admin_get_categories_menu_for_edition_callback(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(AdminCategoryFSM.admin_waiting_get_parent_categories_for_edition)
    await callback_query.message.edit_text("Bosh kategoriyalar:", reply_markup=await admin_get_categories_keyboard("admin_get_sub_categories", state))

@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith("admin_get_sub_categories:"))
async def admin_get_sub_categories(callback_query: CallbackQuery, state: FSMContext): 
    data = await state.get_data() or {}
    subcategories = data.get('subcategories')
    parent_category = data.get('parent_category')

    if not subcategories:
        category_id = int(callback_query.data.split(":")[1])
        parent_category = await sync_to_async(lambda: Category.objects.filter(id=category_id).select_related('owner', 'updated_by').first())()
        subcategories = await sync_to_async(lambda: list(Category.objects.filter(parent_category__id=category_id)))()

        if not subcategories:
            await callback_query.answer('❌ Ushbu kategoriyada sub kategoriya mavjud emas mavjud emas', show_alert=True)
            category_info = await admin_format_category_info(parent_category)
            await callback_query.message.answer(text=category_info, parse_mode='Markdown', reply_markup=admin_category_edit_keyboard(category_id))
            return
        category_info = await admin_format_category_info(parent_category)
        await callback_query.message.answer(text=category_info, parse_mode='Markdown', reply_markup=admin_category_edit_keyboard(category_id))
        await state.update_data(subcategories=subcategories, parent_category=parent_category)
        
    builder = InlineKeyboardBuilder()
    back_button = InlineKeyboardBuilder()
    builder.button(text=f"Bosh kategoriya: {parent_category.name}", callback_data=f"admin_category_edit:{parent_category.id}")
    back_button.button(text="↩️ Orqaga", callback_data=f"admin_get_parent_categories")
    for subcategory in subcategories:
        builder.button(
            text=subcategory.name,
            callback_data=f"admin_category_edit:{subcategory.id}"
        )
    builder.adjust(1, 2)
    keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export()+back_button.export() + admin_keyboard_back_to_category().inline_keyboard)
    await callback_query.message.edit_text("Tahrirlanadigan kategoriyani tanlang:", reply_markup=keyboard)

@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith("admin_category_edit:"))
async def admin_category_edit(callback_query: CallbackQuery, state: FSMContext): 
    category_id = int(callback_query.data.split(":")[1])
    category = await admin_get_category_by_id(category_id)

    if not category:
        await callback_query.answer('❌ Ushbu kategoriya mavjud emas')
        return

    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    text = await admin_format_category_info(category)
    await state.update_data(category_id=category_id, chat_id=chat_id, message_id=message_id)
    await callback_query.message.edit_text(text=text, parse_mode='Markdown', reply_markup=admin_category_edit_keyboard(category_id))
    await state.set_state(AdminCategoryFSM.admin_waiting_save_edited_category)

@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith("admin_edit_category_"))
async def admin_edit_category_field(callback_query: CallbackQuery, state: FSMContext):
    """
    Kategoriya nomi yoki tavsifini (description) tahrirlash uchun universal handler.
    """
    data_parts = callback_query.data.split(":")
    category_id = int(data_parts[1])
    field_type = data_parts[0].split("_")[-1]

    category = await admin_get_category_by_id(category_id)
    if not category:
        await callback_query.answer('❌ Ushbu kategoriya mavjud emas')
        return

    field_text = "nomini" if field_type == "name" else "tavsifini"
    await callback_query.message.answer(
        f"Yangi {field_text} kiriting: 👇"
    )
    
    await callback_query.answer()
    await state.update_data(category_id=category_id, field_type=field_type)
    await state.set_state(AdminCategoryFSM.admin_waiting_save_edited_category)

@admin_category_router.message(AdminCategoryFSM.admin_waiting_save_edited_category)
async def admin_save_updated_category(message: Message, state: FSMContext):
    """
    Kategoriya nomi yoki tavsifini yangilash.
    """
    user = await get_user_from_db(message.from_user.id) 
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Admin, qayta urinib ko‘ring.")
        return

    new_value = message.text.strip()
    data = await state.get_data() or {}
    category_id, field_type = data.get("category_id"), data.get("field_type")

    if not new_value:
        await message.answer("❌ Maydon bo‘sh bo‘lishi mumkin emas. Qayta kiriting! 👇")
        return

    if field_type == "name":
        if new_value.isdigit():
            await message.answer("❌ Kategoriya nomi faqat raqamlardan iborat bo‘lishi mumkin emas! 👇")
            return
        new_value = new_value.title()  

    category = await admin_get_category_by_id(category_id)
    if not category:
        await message.answer("❌ Kategoriya topilmadi, qayta urinib ko‘ring.")
        return

    old_value = getattr(category, field_type)
    if old_value == new_value:
        await message.answer(f"⚠️ '{new_value}' allaqachon mavjud, boshqa qiymat kiriting.")
        return

    try:
        setattr(category, field_type, new_value)
        category.updated_by = user
        await sync_to_async(category.save)()

        field_name = "nomi" if field_type == "name" else "tavsifi"
        await message.answer(f"✅ Kategoriya {field_name} '{new_value}' ga o‘zgartirildi 👆")

        text = await admin_format_category_info(category)
        chat_id, message_id = data.get("chat_id"), data.get("message_id")
        await admin_update_and_clean_message_category(message, chat_id, message_id, text, category_id)

    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await message.answer("❌ Yangilashda xatolik yuz berdi. Qayta urinib ko‘ring.")

# Deleting part
@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith("admin_delete_category"))
async def admin_delete_category_callback(callback_query: CallbackQuery, state: FSMContext):
    category_id = int(callback_query.data.split(":")[1])
    category = await admin_get_category_by_id(category_id)
    if not category:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
        return
    await state.update_data(category_id=category.id)
    await callback_query.message.answer(f"'{category.name}' kategoriyasini o‘chirmoqchimisiz?", reply_markup=admin_delete_confirmation_keyboard('admin_category' ,category_id))
    await callback_query.answer()

@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith("admin_category_confirm_delete:"))
async def admin_confirm_delete_category(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data() or {}
    chat_id, message_id = data.get("chat_id"), data.get("message_id")
    category_id = int(callback_query.data.split(":")[1])
    category = await admin_get_category_by_id(category_id)

    if not category:
        await callback_query.answer(f"⚠️ Kategoriya topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    try:
        await sync_to_async(category.delete)()  
        await callback_query.answer(f"✅ '{category.name}' kategoriyasi o‘chirildi.")
        if message_id and chat_id:
            try:
                await callback_query.bot.delete_message(chat_id=chat_id, message_id=callback_query.message.message_id)
                for msg_id in range(callback_query.message.message_id, message_id, -1):
                    await callback_query.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except TelegramBadRequest:  
                pass 
            await callback_query.message.answer("Kategoriyalar:", reply_markup=await admin_get_categories_keyboard("admin_category_edit", state))
        else:
            await callback_query.message.edit_text("Kategoriyalar:", reply_markup=await admin_get_categories_keyboard("admin_category_edit", state))
        await state.clear()
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        await callback_query.message.answer("❌ Kategoriya o'chirishda xatolik yuz berdi. Admin, qayta urinib ko'ring.")

@admin_category_router.callback_query(IsAdminFilter(), F.data.startswith("admin_category_cancel_delete:"))
async def admin_cancel_delete_category(callback_query: CallbackQuery, state: FSMContext):
    category_id = int(callback_query.data.split(":")[1])
    category = await admin_get_category_by_id(category_id)
    text = await admin_format_category_info(category)
    if not category:
        await callback_query.answer(f"⚠️ Kategoriya topilmadi. Admin qaytadan urinib ko'ring")
        return
    
    await callback_query.answer("O‘chirish bekor qilindi.")
    await callback_query.message.edit_text(text=text, parse_mode='Markdown', reply_markup=admin_category_edit_keyboard(category_id))

# Category part ended
