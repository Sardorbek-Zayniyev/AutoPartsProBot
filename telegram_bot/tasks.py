from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from telegram_app.models import Cart, CartItem, Product, User, RewardHistory
import requests

from .config import BOT_TOKEN

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_telegram_request(method: str, params: dict) -> dict:
    """Telegram API’ga sinxron so‘rov yuborish"""
    url = f"{TELEGRAM_API_URL}/{method}"
    try:
        response = requests.post(url, json=params)
        response.raise_for_status()  
        return response.json()
    except requests.RequestException as e:
        print(f"Telegram so‘rovida xatolik: {e}")
        return {}

def edit_telegram_message(chat_id: str, message_id: int, text: str) -> dict:
    """Telegram xabarini tahrirlash uchun funksiya"""
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    return send_telegram_request("editMessageText", params)

# @shared_task(ignore_result=True)
# def clear_expired_reservations():
#     now = timezone.now()
#     expired_carts = Cart.objects.filter(reserved_until__lte=now, is_active=True)
    
#     for cart in expired_carts:
#         cart_items = CartItem.objects.filter(cart=cart)
#         for item in cart_items:
#             product = item.product
#             product.reserved_stock -= item.quantity
#             item.delete()
#             product.available = product.available_stock > 0
#             product.save()
        
#         if cart.user and cart.user.telegram_id and cart.last_message_id:
#             if not cart.items.exists():
#                 params = {
#                     "chat_id": cart.user.telegram_id,
#                     "message_id": cart.last_message_id,
#                     "text": "Savatingizdan mahsulotlar o'chirildi."
#                 }
#                 edit_telegram_message(cart.user.telegram_id, cart.last_message_id, "Savatingizdan mahsulotlar o'chirildi.")
#                 cart.warning_sent = False
#                 cart.save()

#         if not CartItem.objects.filter(cart=cart).exists():
#             cart.reserved_until = None
#         cart.save()

def restore_cart_promocodes_and_rewards(cart):
    """
    Savatcha muddati tugaganda promokod va rewardlarni foydalanuvchiga qaytarish.
    """
    user = cart.user
    if not user:
        return

    # 🔹 1️⃣ Promokodlarni qaytarish
    promocodes = list(cart.promocodes.all())
    for promo in promocodes:
        promo.used_count = max(promo.used_count - 1, 0)
        if promo.used_count < promo.usage_limit:
            promo.is_active = True  
        promo.save()

        # ✅ Agar bu promokod reward orqali qo‘shilgan bo‘lsa, rewardni qaytarish
        reward_history = RewardHistory.objects.filter(user=user, reward__promocode=promo, is_used=True).first()
        if reward_history:
            reward_history.is_used = False
            reward_history.save()

    # 🔹 2️⃣ Sovg‘alarni qaytarish
    rewards = list(cart.rewards.all())
    for reward in rewards:
        reward_history = RewardHistory.objects.filter(user=user, reward=reward, is_used=True).first()
        if reward_history:
            reward_history.is_used = False
            reward_history.save()

@shared_task(ignore_result=True)
def clear_expired_reservations():
    now = timezone.now()
    expired_carts = Cart.objects.filter(reserved_until__lte=now, is_active=True)
    
    for cart in expired_carts:
        # 1️⃣ Foydalanuvchining promokod va rewardlarini qaytarish
        restore_cart_promocodes_and_rewards(cart)

        # 2️⃣ Savatdagi mahsulotlarni tiklash
        cart_items = CartItem.objects.filter(cart=cart)
        for item in cart_items:
            product = item.product
            product.reserved_stock -= item.quantity
            item.delete()
            product.available = product.available_stock > 0
            product.save()
        
        # 3️⃣ Telegram orqali foydalanuvchiga xabar berish
        if cart.user and cart.user.telegram_id and cart.last_message_id:
            if not cart.items.exists():
                edit_telegram_message(cart.user.telegram_id, cart.last_message_id, "Savatingizdan mahsulotlar o‘chirildi.")
                cart.warning_sent = False

        # 4️⃣ Cartni deaktiv qilish
        if not CartItem.objects.filter(cart=cart).exists():
            cart.reserved_until = None
        cart.save()

@shared_task(ignore_result=True)
def warn_cart_expiration():
    now = timezone.now()
    two_minutes_later = now + timedelta(minutes=2)
    carts_to_warn = Cart.objects.filter(
        reserved_until__gte=now + timedelta(seconds=110),
        reserved_until__lte=now + timedelta(seconds=130),
        is_active=True
    )
    for cart in carts_to_warn:
        user = cart.user
        if user and user.telegram_id and cart.items.exists():
            if not cart.warning_sent:
                keyboard = {
                    "inline_keyboard": [[
                        {"text": "Vaqtni uzaytirish (15 daqiqaga)", "callback_data": f"user_extend_cart_time:{cart.id}"}
                    ]]
                }
                
                params = {
                    "chat_id": user.telegram_id,
                    "text": "Diqqat! 2 minutdan keyin savatingizdagi mahsulotlar o'chiriladi.",
                    "reply_markup": keyboard
                }
                response = send_telegram_request("sendMessage", params)
                if response.get("ok"):
                    cart.last_message_id = response["result"]["message_id"]
                    cart.warning_sent = True
                    cart.save()

@shared_task(ignore_result=True)
def notify_admins_pending_products():
    now = timezone.now()
    admins = User.objects.filter(role=User.ADMIN)
    pending_count = Product.objects.filter(status=Product.STATUS_PENDING, owner__role=User.USER).count()

    if pending_count == 0:
        return  # No pending products, no notification

    for admin in admins:
        if not admin.telegram_id:
            continue  # Skip admins without Telegram ID

        # Prepare the message text
        message_text = (
            f"⏳ Tasdiqlanishi kutilayotgan mahsulotlar soni: {pending_count} ta\n"
        )
        # Prepare the inline keyboard
        params = {
            "chat_id": admin.telegram_id,
            "text": message_text,
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "Kutilayotgan mahsulotlarni ko‘rish", "callback_data": "admin_view_pending_products"}
                ]]
            }
        }

        # Delete the previous message if it exists
        if hasattr(admin, 'last_pending_message_id') and admin.last_pending_message_id:
            delete_params = {
                "chat_id": admin.telegram_id,
                "message_id": admin.last_pending_message_id
            }
            send_telegram_request("deleteMessage", delete_params)  # Delete old message

        # Send a new message
        response = send_telegram_request("sendMessage", params)
        if response.get("ok"):
            admin.last_pending_message_id = response["result"]["message_id"]
            admin.save()