from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.types import Message

from config import settings
from db import queries

router = Router()

ADMIN_ROLES = {"admin", "superadmin"}


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.chat.id == settings.GROUP_ID,
)
async def group_message_guard(message: Message, bot: Bot):
    """Delete posts from users without an active subscription."""

    # Ignore service/system messages and other bots
    if message.from_user is None or message.from_user.is_bot:
        return

    user_id = message.from_user.id
    user = await queries.get_user(user_id)
    now = datetime.now(timezone.utc)

    # Admins and superadmins can always post freely
    if user and user["role"] in ADMIN_ROLES:
        return

    # Subscribed user — check blackout
    if user and user["subscription_until"] and user["subscription_until"] > now:
        blackout = await queries.get_active_blackout(now)
        if not blackout:
            return  # All good — subscribed, no blackout active
        end_str = blackout["end_datetime"].strftime("%d.%m.%Y %H:%M")
        reason = (
            f"🚫 Hozir nashr qilish vaqtincha taqiqlangan.\n"
            f"⏰ {end_str} (UTC) dan keyin harakat qilib ko'ring."
        )
    # elif user is None:
    #     reason = (
    #         "⚠️ Siz hali ro'yxatdan o'tmagansiz.\n"
    #         "Ro'yxatdan o'tish uchun botga yozing va /start buyrug'ini kiriting."
    #     )
    else:
        # Registered but no active subscription
        reason = (
            f"❌ Hurmatli {user['full_name']}\n"
            "Guruhga yozish uchun admin tomonidan ruxsat olishingiz kerak!\n"
            "@jondor_admin1 ga yozing!✅"
        )

    # Delete the unauthorized post
    try:
        await message.delete()
    except Exception:
        pass  # Bot must have 'Delete messages' permission in the group

    # Notify in the group, mention the user by clickable name
    user_mention = f'<a href="tg://user?id={user_id}">{message.from_user.full_name}</a>'
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"👤 {user_mention}\n\n{reason}",
        parse_mode="HTML",
    )
