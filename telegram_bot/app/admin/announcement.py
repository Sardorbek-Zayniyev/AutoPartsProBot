from aiogram import Router, F
import asyncio, os
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton, CallbackQuery, Message, FSInputFile
from django.utils import timezone
from asgiref.sync import sync_to_async
from telegram_app.models import Product, User
from telegram_bot.app.utils import IsAdminFilter
from telegram_bot.app.admin.utils import (
    admin_get_cancel_reply_keyboard,
    admin_keyboard_back_to_announce
)
admin_announcement_router = Router()

# Define FSM states for announcement handling
class AdminAnnouncementFSM(StatesGroup):
    admin_waiting_select_new_product = State()
    admin_waiting_select_discounted_product = State() 
    admin_waiting_custom_text = State()  
    admin_process_custom_text_sent = State() 
    admin_waiting_confirm_announcement = State() 

# Utility functions
async def get_all_users():
    """Retrieve all users from the database."""
    return await sync_to_async(lambda: list(User.objects.filter(role="User").values_list('telegram_id', flat=True)))()

async def broadcast_message(bot, users, text=None, photo_path=None, caption=None):
    """Send text or photo message to all users."""
    tasks = []

    for user_id in users:
        if photo_path and os.path.exists(photo_path):
            try:
                input_file = FSInputFile(photo_path, filename=os.path.basename(photo_path))
                tasks.append(bot.send_photo(chat_id=user_id, photo=input_file, caption=caption or text, parse_mode="HTML"))
            except Exception as e:
                print(f"❌ Photo sending failed to {user_id}: {e}")
                # tasks.append(bot.send_message(chat_id=user_id, text=text, parse_mode="HTML"))
        else:
            tasks.append(bot.send_message(chat_id=user_id, text=text, parse_mode="HTML"))

    await asyncio.gather(*tasks, return_exceptions=True)

async def format_announcement_info(product, action):
    """Format product info for announcement, aligning with product.py style."""
    price_info = await sync_to_async(product.original_and_discounted_price)()
    price_text = (
        f"💰 <b>Asl narxi:</b> <s>{price_info['original_price']} so'm</s>\n"
        f"🤑 <b>Chegirmali narx:</b> {price_info['discounted_price']} so'm 🔥"
        if price_info["discounted_price"]
        else f"💵 <b>Narxi:</b> {price_info['original_price']} so'm"
    )

    return (
        f"{"\n✨ Yangi mahsulotlardan birinchilardan bo‘lib xabardor bo‘ling!\n\n\n" if action==True else "\n💥 Ajoyib chegirma! Bu imkoniyatni qo‘ldan boy bermang!\n\n\n"}"
        f"🛠 <b>Mahsulot nomi:</b> {product.name}\n"
        f"📂 <b>Kategoriya:</b> {product.category.name}\n"
        f"🏷 <b>Brend:</b> {product.car_brand.name}\n"
        f"🚘 <b>Model:</b> {product.car_model.name}\n"
        f"{price_text}\n"
    )

async def admin_handle_search_new_or_discounted_products_result(message: Message, products, state: FSMContext, action):
    if not products:
        text = ""
        if action == 'new':
           text = "❌ Hozircha 7 kun ichida kiritilgan yangi mahsulotlar yo'q."
        elif action == 'discounted':
           text = "❌ Hozircha chegirmali mahsulotlar yo'q."
        if isinstance(message, CallbackQuery):
           await message.message.answer(text)
        else:
           await message.answer(text)    
        return
    if action == 'new':
        await state.update_data(new_products=products)
    else:
        await state.update_data(discounted_products=products)

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    
    total_pages = ((len(products_with_numbers) + 9) // 10)
    await admin_display_fetched_new_or_discounted_products_list(1, message, products_with_numbers, total_pages, 10, f"admin_announce_{action}_product", state)

async def admin_display_fetched_new_or_discounted_products_list(page_num, callback_query_or_message, item_with_numbers, total_pages, item_per_page, callback_prefix, state):
    start_index = (page_num - 1) * item_per_page
    end_index = min(start_index + item_per_page, len(item_with_numbers))
    page_items = item_with_numbers[start_index:end_index]
    if callback_prefix == f"admin_announce_new_product":
        message_text = (
            f"✨ Yangi mahsulotlarni ko\'rish bo\'limi:\n\n 🔍 Umumiy natija: {len(item_with_numbers)} ta mahsulotlar topildi.\n\n"
            f"📜 Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
        )
    else:
         message_text = (
            f"🏷️ Chegirmali mahsulotlarni ko\'rish bo\'limi:\n\n 🔍 Umumiy natija: {len(item_with_numbers)} ta mahsulotlar topildi.\n\n"
            f"📜 Sahifa natijasi: {start_index + 1}-{end_index}:\n\n"
        )
    for number, product in page_items:
        message_text += f"{number}. _{product['car_brand__name']}_ : _{product['car_model__name']}_ — *{product['name']}*\n"
    
    # **Tugmalar yasash**
    builder = InlineKeyboardBuilder()
    pagination = InlineKeyboardBuilder()
    for number, item in page_items:
        callback_data = (
            f"{callback_prefix}:{item['id']}"
        )
        builder.button(text=str(number), callback_data=callback_data)

    builder.adjust(5)
    
    # Navigatsiya tugmalarini qo'shamiz
    if total_pages > 1:
       
        navigation_buttons = []
        
        if page_num > 1:
            prev_callback = f"{callback_prefix}_other_pages:{page_num - 1}" 
            navigation_buttons.append({"text": "⬅️", "callback_data": prev_callback})
        
        navigation_buttons.append({"text": "❌", "callback_data": "admin_delete_message"})
        
        if page_num < total_pages:
            next_callback = f"{callback_prefix}_other_pages:{page_num + 1}" 
            navigation_buttons.append({"text": "➡️", "callback_data": next_callback})
        
        # Navigatsiya tugmalarini qatorga joylashtiramiz
        for btn in navigation_buttons:
            pagination.button(text=btn["text"], callback_data=btn["callback_data"])
        pagination.adjust(5, 5, len(navigation_buttons))  # 5 tadan mahsulot tugmalari + navigatsiya qatori
    else:
        pagination.button(text="❌", callback_data="admin_delete_message")
        pagination.adjust(5, 5, 1)  # 5 tadan mahsulot tugmalari + faqat ❌ tugmasi

    
    additional_buttons = (
        admin_keyboard_back_to_announce().inline_keyboard
    )

    product_keyboard = InlineKeyboardMarkup(inline_keyboard=builder.export()+ pagination.export() + additional_buttons)

    # **Xabarni yangilash yoki yangi xabar jo‘natish**
    if isinstance(callback_query_or_message, CallbackQuery):
        new_message = await callback_query_or_message.message.edit_text(
            text=message_text, reply_markup=product_keyboard, parse_mode="Markdown"
        )
    else:
        new_message = await callback_query_or_message.answer(
            text=message_text, reply_markup=product_keyboard, parse_mode="Markdown"
        )

    await state.update_data(message_ids=[new_message.message_id])

#New Products announce
@admin_announcement_router.message(AdminAnnouncementFSM.admin_waiting_select_new_product)
async def admin_announce_new_product(message: Message, state: FSMContext):
    time_threshold = timezone.now() - timezone.timedelta(days=7)
    new_products = await sync_to_async(lambda: list(Product.objects.filter(created_at__gte=time_threshold, quality='new').select_related('car_brand', 'car_model').order_by('-created_at').values('id', 'name', 'car_brand__name', 'car_model__name')))()    
    await admin_handle_search_new_or_discounted_products_result(message, new_products, state, 'new')

#Discounted Products announce
@admin_announcement_router.message(AdminAnnouncementFSM.admin_waiting_select_discounted_product)
async def admin_announce_discounted_product(message: Message, state: FSMContext):
    discounted_products = await sync_to_async(lambda: list(Product.objects.filter(
        discounts__is_active=True,
        discounts__start_date__lte=timezone.now(),
        discounts__end_date__gte=timezone.now()
    ).select_related('car_brand', 'car_model').order_by('-created_at').values('id', 'name', 'car_brand__name', 'car_model__name')))()

    if not discounted_products:
        await message.answer("❌ Hozircha chegirmali mahsulotlar yo'q.")
        return

    await admin_handle_search_new_or_discounted_products_result(message, discounted_products, state, 'discounted')

@admin_announcement_router.callback_query(IsAdminFilter(), F.data.startswith(("admin_announce_new_product_other_pages:", "admin_announce_discounted_product_other_pages:")))
async def admin_new_or_discounted_product_other_pages(callback_query: CallbackQuery, state: FSMContext):
    """Handle pagination for new products."""
    page_num = int(callback_query.data.split(":")[1])
    action = callback_query.data.split(":")[0]
    data = await state.get_data()
    if not data:
        await callback_query.answer("❌ Xabar ma'lumotlari topilmadi, Sahifani qaytadan yuklang.", show_alert=True)
        return

    if action == "admin_announce_new_product_other_pages":
        products = data.get("new_products", [])
        text = "admin_announce_new_product"
    else:
        products = data.get("discounted_products", [])
        text = "admin_announce_discounted_product"

    products_with_numbers = [(index + 1, product) for index, product in enumerate(products)]
    total_pages = (len(products_with_numbers) + 9) // 10
    await admin_display_fetched_new_or_discounted_products_list(page_num, callback_query, products_with_numbers, total_pages , 10, text, state)
    await callback_query.answer()

@admin_announcement_router.callback_query(IsAdminFilter(), F.data.startswith(("admin_announce_new_product:", "admin_announce_discounted_product:")))
async def admin_get_selected_new_or_discounted_product(callback_query: CallbackQuery, state: FSMContext):
    """Process the selected new product and prepare for confirmation."""
    product_id = int(callback_query.data.split(":")[1])
    action = callback_query.data.split(":")[0]

    if action == "admin_announce_new_product":
        action = True

    product = await sync_to_async(lambda: Product.objects.select_related('car_brand', 'car_model', 'category').get(id=product_id))()
    await state.update_data(product=product)
    product_info = await format_announcement_info(product, action)

    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Ortga", callback_data=f"{'admin_back_to_new_product:' if action else 'admin_back_to_discounted_product:'}"), 
         InlineKeyboardButton(text="❌", callback_data="admin_delete_message"), 
         InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_confirm_announce:{product_id}:{'new' if action else 'discount'}")],
    ])
    if product.photo and os.path.exists(product.photo.path):
        try:
            input_file = FSInputFile(
                product.photo.path, filename=os.path.basename(product.photo.path))
            await callback_query.message.answer_photo(input_file, parse_mode='HTML', caption=product_info)
            await callback_query.message.answer(f"Yuboriladigan xabar 👆 \n\nUshbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
                    reply_markup=confirm_keyboard,
                    parse_mode="HTML"
                )        
        except Exception as e:
            await callback_query.message.answer(f"Mahsulot rasmi yuklanishda xatolik yuz berdi.\n\n{product_info}")
            print(f"Error loading photo: {e}")
    else:
        await callback_query.message.answer(f"Yuboriladigan xabar:\n\n{product_info}\n\nUshbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
        reply_markup=confirm_keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()

@admin_announcement_router.callback_query(IsAdminFilter(), F.data.startswith(('admin_back_to_new_product:' , 'admin_back_to_discounted_product:')))
async def admin_back_to_selection_new_or_discounted(callback_query: CallbackQuery, state: FSMContext):
    action = callback_query.data.split(":")[0]
    if action == "admin_back_to_new_product":
        await admin_announce_new_product(callback_query.message, state)
    else:
        await admin_announce_discounted_product(callback_query.message, state)
    await callback_query.answer()

#Text based announce
@admin_announcement_router.message(AdminAnnouncementFSM.admin_waiting_custom_text)
async def admin_announce_custom_text_message(message: Message, state: FSMContext):
    """Handle custom text message announcement."""
    await message.answer(
        "Barcha foydalanuvchilarga yuboriladigan matnni yozing 👇",
        reply_markup=admin_get_cancel_reply_keyboard().as_markup(resize_keyboard=True)
    )
    await state.set_state(AdminAnnouncementFSM.admin_process_custom_text_sent)

@admin_announcement_router.message(AdminAnnouncementFSM.admin_process_custom_text_sent)
async def process_custom_text_message(message: Message, state: FSMContext):
    """Process the custom text input and prepare for confirmation."""
    custom_text = message.text.strip()
    if not custom_text:
        await message.answer("❌ Matn bo'sh bo'lishi mumkin emas. Iltimos, qayta kiriting.")
        return

    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="admin_confirm_announce:custom:custom"), InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_main_menu")],
    ])
    await message.answer(
        f"Yuboriladigan xabar:\n\n<b>{custom_text}</b>\n\nUshbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
        reply_markup=confirm_keyboard,
        parse_mode="HTML"
    )
    await state.update_data(custom_text=custom_text)
    await state.set_state(AdminAnnouncementFSM.admin_waiting_confirm_announcement)

@admin_announcement_router.callback_query(IsAdminFilter(), F.data.startswith("admin_confirm_announce:"))
async def confirm_and_broadcast_announcement(callback_query: CallbackQuery, state: FSMContext):
    """Confirm and broadcast the announcement to all users."""

    data_parts = callback_query.data.split(":")
    announcement_type = data_parts[2]

    users = await get_all_users()
    if not users:
        await callback_query.message.edit_text("❌ Foydalanuvchilar topilmadi.")
        await callback_query.answer()
        return

    if announcement_type == "custom":
        data = await state.get_data()
        text = data.get("custom_text")
        await broadcast_message(callback_query.bot, users, text)
    else:
        data = await state.get_data()
        if not data:
            return
        product = data.get('product')
        if announcement_type == "new":
            product_info = await format_announcement_info(product, True)
        else:
            product_info = await format_announcement_info(product, False)
        photo_path = product.photo.path if product.photo and os.path.exists(product.photo.path) else None
        await broadcast_message(callback_query.bot, users, photo_path=photo_path, caption=product_info)

    from telegram_bot.app.admin.main_controls import ADMIN_ANNOUNCEMENT_CONTROLS_KEYBOARD
    await callback_query.message.edit_text(
        f"⏳ Xabar yuborilyapti!",
    )
    await asyncio.sleep(2)
    await callback_query.message.edit_text(
        f"✅ Xabar muvaffaqiyatli yuborildi!",
    )
    await asyncio.sleep(1)
    await callback_query.message.answer(
        f"👥 Jami: {len(users)} ta foydalanuvchi xabarni muvaffaqiyatli qabul qildi.",
        reply_markup=ADMIN_ANNOUNCEMENT_CONTROLS_KEYBOARD
    )
    await callback_query.answer()