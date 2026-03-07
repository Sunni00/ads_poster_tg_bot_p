from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.types import Message
from cachetools import TTLCache

from config import settings
from db import queries

router = Router()

ADMIN_ROLES = {"admin", "superadmin"}

# Tracks media_group_ids we've already notified about.
# Holds up to 256 entries, each expires after 10 seconds.
_notified_groups: TTLCache = TTLCache(maxsize=256, ttl=10)


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

    # ── .env superadmin always passes through ────────────────────────
    if user_id == settings.SUPERADMIN_ID:
        return

    # ── Telegram-native admin check (most reliable) ──────────────────
    # If Telegram itself says the user is a group creator or admin, let them post.
    try:
        member = await bot.get_chat_member(chat_id=message.chat.id, user_id=user_id)
        if member.status in {"creator", "administrator"}:
            return
    except Exception:
        pass  # If we can't check, fall through to DB check

    user = await queries.get_user(user_id)
    now = datetime.now(timezone.utc)

    # DB role check as a secondary safeguard
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
    elif user is None:
        reason = (
            f"❌ Hurmatli {message.from_user.full_name}\n"
            "Guruhga yozish uchun admin tomonidan ruxsat olishingiz kerak!\n"
            "@jondor_admin1 ga yozing!✅"
        )
    else:
        # Registered but no active subscription
        reason = (
            f"❌ Hurmatli {user['full_name']}\n"
            "Guruhga yozish uchun admin tomonidan ruxsat olishingiz kerak!\n"
            "@jondor_admin1 ga yozing!✅"
        )

    # Delete the unauthorized post (every photo/video in the album)
    try:
        await message.delete()
    except Exception:
        pass  # Bot must have 'Delete messages' permission in the group

    # For media groups (albums), only send ONE notification for the whole album.
    media_group_id = message.media_group_id
    if media_group_id:
        if media_group_id in _notified_groups:
            return  # Already notified for this album — skip
        _notified_groups[media_group_id] = True

    # Notify in the group, mention the user by clickable name
    user_mention = f'<a href="tg://user?id={user_id}">{message.from_user.full_name}</a>'
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"👤 {user_mention}\n\n{reason}",
        parse_mode="HTML",
    )
