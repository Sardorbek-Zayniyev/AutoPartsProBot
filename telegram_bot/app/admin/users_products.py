import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from asgiref.sync import sync_to_async
from telegram_bot.app.utils import get_user_from_db, IsAdminFilter
from telegram_app.models import Product, User
from telegram_bot.app.admin.product import admin_format_product_info, admin_handle_search_products_result, admin_handle_get_all_products_other_pages, admin_get_product_by_id
from django.db.models import Count, Q

admin_user_products_router = Router()

# State klassi
class AdminUserProductsFSM(StatesGroup):
    admin_waiting_get_approved_products = State()
    admin_waiting_get_rejected_products = State()
    admin_waiting_get_pending_products = State()
    admin_waiting_show_statistics = State()
    admin_waiting_product_action = State()
    admin_waiting_rejection_reason = State()  

# Utils
def admin_user_product_action_keyboard(product_id: int, status: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if status == "approved":
        builder.button(text="🚫 Rad etish", callback_data=f"admin_user_product_reject:{product_id}")
    elif status == "rejected":
        builder.button(text="✅ Tasdiqlash", callback_data=f"admin_user_product_approve:{product_id}")
    elif status == "pending":
        builder.button(text="✅ Tasdiqlash", callback_data=f"admin_user_product_approve:{product_id}")
        builder.button(text="🚫 Rad etish", callback_data=f"admin_user_product_reject:{product_id}")
    
    builder.button(text="❌", callback_data="admin_delete_message")
    # builder.button(text="↩️ Orqaga", callback_data="admin_user_products_back")
    builder.adjust(2 if status in ("approved", "rejected") else 2, 2)
    
    return builder.as_markup()


# Get products added by users
async def admin_get_user_products_by_status(message, state: FSMContext, status: str):
    """
    Foydalanuvchi mahsulotlarini status bo'yicha filtrlab oladi va pagination bilan ko'rsatadi.
    """
    products = await sync_to_async(lambda: list(
        Product.objects.filter(status=status, owner__role=User.USER)
        .select_related('car_brand', 'car_model')
        .order_by('created_at')
        .values('id', 'name', 'car_brand__name', 'car_model__name')
    ))()
    products = [{
        "id": product["id"],
        "name": product["name"],
        "car_brand": product["car_brand__name"],
        "car_model": product["car_model__name"]
    } for product in products]
    await admin_handle_search_products_result(message, products, state)

@admin_user_products_router.callback_query(IsAdminFilter(), F.data.startswith('admin_search_product_other_pages:'))
async def admin_get_user_products_other_pages_callback(callback_query: CallbackQuery, state: FSMContext):
    await admin_handle_get_all_products_other_pages(callback_query, state, callback_prefix="admin_search_product")

# Get pending products added by users
@admin_user_products_router.callback_query(IsAdminFilter(), F.data == "admin_view_pending_products")
async def admin_view_pending_products_callback(callback_query: CallbackQuery, state: FSMContext):
    """Handle the 'View Pending Products' button press."""
    await callback_query.answer()
    await state.set_state(AdminUserProductsFSM.admin_waiting_get_pending_products)
    await admin_get_user_products_by_status(callback_query, state, status=Product.STATUS_PENDING)

# Approve product
@admin_user_products_router.callback_query(IsAdminFilter(), F.data.startswith('admin_user_product_approve:'))
async def admin_approve_user_product(callback_query: CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split(':')[1])
    user = await get_user_from_db(callback_query.from_user.id)
    product = await admin_get_product_by_id(product_id)

    if product.status == Product.STATUS_APPROVED:
        await callback_query.answer("⚠️ Bu mahsulot allaqachon tasdiqlangan!")
        return

    product.status = Product.STATUS_APPROVED
    product.is_active = True
    product.updated_by = user
    await sync_to_async(product.save)()

    product_info = await admin_format_product_info(product, True)
    if callback_query.message.content_type == "photo":
        await callback_query.message.edit_caption(
            caption=product_info,
            parse_mode='HTML',
            reply_markup=admin_user_product_action_keyboard(product_id, product.status)
        )
    else:
        await callback_query.message.edit_text(
            text=product_info,
            parse_mode='HTML',
            reply_markup=admin_user_product_action_keyboard(product_id, product.status)
        )
    await callback_query.answer("✅ Mahsulot muvaffaqqiyatli tasdiqlandi!")

# Reject product
@admin_user_products_router.callback_query(IsAdminFilter(), F.data.startswith('admin_user_product_reject:'))
async def admin_reject_user_product(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    product_id = int(callback_query.data.split(':')[1])
    await state.update_data(product_id=product_id)
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭️ Sababsiz rad etish", callback_data="admin_reject_users_product_without_reason")
    builder.adjust(1)
    keyboard = builder.as_markup()
    if callback_query.message.photo:
        try:
            await callback_query.message.edit_caption(caption="Mahsulotni rad etilish sababini yozing 👇", reply_markup=keyboard)
        except Exception as e:
            print(f"Xatolik: {e}")
    else:
        try:
            await callback_query.message.edit_text(text="Mahsulotni rad etilish sababini yozing 👇", reply_markup=keyboard)
        except Exception as e:
            print(f"Xatolik: {e}")
    await state.set_state(AdminUserProductsFSM.admin_waiting_rejection_reason)

@admin_user_products_router.message(AdminUserProductsFSM.admin_waiting_rejection_reason)
async def admin_reject_users_product_with_reason(message: Message, state: FSMContext):
    data = await state.get_data() or {}
    product_id = data.get('product_id')
    message_id = data.get('message_id')
    
    user = await get_user_from_db(message.from_user.id)
    product = await admin_get_product_by_id(product_id)

    product.rejection_reason = message.text.strip()
    product.status = Product.STATUS_REJECTED
    product.is_active = False

    product.updated_by = user
    await sync_to_async(product.save)()

    product_info = await admin_format_product_info(product, True)
    keyboard = admin_user_product_action_keyboard(product_id, status=product.status)
    if message_id:
        try:
            # Agar avvalgi xabar photo bo'lsa, captionni yangilash
            await message.bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message_id,
                caption=product_info,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            # Agar caption tahrirlash ishlamasa, text sifatida tahrirlashga urinamiz
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    text=product_info,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            except Exception as e2:
                print(f"Xatolik: {e2}")
                await message.answer("Xabarni tahrirlashda xatolik yuz berdi!")
    else:
        await message.answer(product_info, parse_mode='HTML', reply_markup=keyboard)

    confirmation_message = await message.answer("Mahsulot rad etildi! 🚫")

    await asyncio.sleep(1.5)
    try:
        await message.delete()
        await confirmation_message.delete()  #
    except Exception as e:
        print(f"Xabarni o'chirishda xatolik: {e}")

    await state.clear()

@admin_user_products_router.callback_query(IsAdminFilter(), F.data.startswith('admin_reject_users_product_without_reason'))
async def admin_reject_users_product_without_reason_callback(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data() or {}
    product_id = data.get('product_id')
    message_id = data.get('message_id')

    user = await get_user_from_db(callback_query.from_user.id)
    product = await admin_get_product_by_id(product_id)

    if not product:
        await callback_query.answer("❌ Mahsulot topilmadi! Sahifani qayta yuklang", show_alert=True)
        return
    
    product.rejection_reason = None
    product.status = Product.STATUS_REJECTED
    product.is_active = False

    product.updated_by = user
    await sync_to_async(product.save)()

    product_info = await admin_format_product_info(product, True)
    keyboard = admin_user_product_action_keyboard(product_id, status=product.status)

    chat_id = callback_query.message.chat.id
    if message_id:
        try:
            await callback_query.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=product_info,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            try:
                await callback_query.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=product_info,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            except Exception as e2:
                await callback_query.answer(f"❌ Xabarni tahrirlashda xato: {str(e2)}", show_alert=True)
    else:
        await callback_query.message.answer(product_info, parse_mode='HTML', reply_markup=keyboard)

    await callback_query.answer("Mahsulot muvaffaqqiyatli rad etildi 🚫")

# Statistika ko'rsatish
async def admin_show_user_products_statistics(message: Message, state: FSMContext):
    products = await sync_to_async(lambda: Product.objects.aggregate(
        total=Count('id', filter=Q(owner__role=User.USER)),
        approved=Count('id', filter=Q(status=Product.STATUS_APPROVED, owner__role=User.USER)),
        rejected=Count('id', filter=Q(status=Product.STATUS_REJECTED, owner__role=User.USER)),
        pending=Count('id', filter=Q(status=Product.STATUS_PENDING, owner__role=User.USER))
    ))()

    products_text = (
        "📊 *Foydalanuvchilar mahsulotlarining statistikasi:*\n\n"
        f"🔢 Umumiy mahsulotlar: {products['total']} ta\n"
        f"✅ Tasdiqlangan: {products['approved']} ta\n"
        f"❌ Rad etilgan: {products['rejected']} ta\n"
        f"⏳ Kutilayotgan: {products['pending']} ta"
    )
    await message.answer(products_text, parse_mode='Markdown')


