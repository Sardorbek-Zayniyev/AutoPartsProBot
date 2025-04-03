from telegram_app.models import User
from asgiref.sync import sync_to_async
from aiogram.filters import BaseFilter
from aiogram.types import Message
@sync_to_async
def get_user_from_db(telegram_id):
    """
    Retrieves a user from the database based on their Telegram ID.
    """
    user = User.objects.filter(telegram_id=telegram_id).first()
    return user

@sync_to_async
def get_admins():
    return list(User.objects.filter(role__in=["Admin"]))


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = await get_user_from_db(message.from_user.id)
        return user and user.role == 'Admin'
    
class IsUserFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = await get_user_from_db(message.from_user.id)
        return user and user.role == 'User'

class IsSuperAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = await get_user_from_db(message.from_user.id)
        return user and user.role == 'Superadmin'
