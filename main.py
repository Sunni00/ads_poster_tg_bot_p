import asyncio
import asyncpg
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db import queries
from db.models import ALL_TABLES
from handlers import start, ads, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def create_tables(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        for sql in ALL_TABLES:
            await conn.execute(sql)
    logger.info("Database tables ensured.")


async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    await queries.set_pool(pool)
    await create_tables(pool)

    dp = Dispatcher(storage=MemoryStorage())

    # Register routers (order matters — more specific first)
    dp.include_router(start.router)
    dp.include_router(ads.router)
    dp.include_router(admin.router)

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await pool.close()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())

