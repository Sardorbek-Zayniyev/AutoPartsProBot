from telegram_app.models import User
from asgiref.sync import sync_to_async


@sync_to_async
def get_user_from_db(telegram_id):
    """
    Retrieves a user from the database based on their Telegram ID.
    """
    user = User.objects.filter(telegram_id=telegram_id).first()
    return user


@sync_to_async
def set_as_admin(telegram_id):
    user = User.objects.get(telegram_id=telegram_id)
    user.role = User.ADMIN
    user.save()
    return user


@sync_to_async
def set_as_user(telegram_id):
    user = User.objects.get(telegram_id=telegram_id)
    user.role = User.USER
    user.save()
    return user
