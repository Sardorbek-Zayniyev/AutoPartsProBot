from config import *
import asyncio
from aiogram import Bot, Dispatcher
from handlers import start
from handlers import superadmin
from handlers import admin
from handlers import auth

# Set up logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(auth.auth_router)
dp.include_router(start.start_router)
dp.include_router(superadmin.superadmin_router)
dp.include_router(admin.admin_router)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
