from datetime import datetime, timezone, timedelta
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.enums import ChatType
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaAudio, InputMediaVideo
from aiogram.fsm.context import FSMContext

from db import queries
from keyboards.keys import kb_collecting_ad, kb_confirm_ad, kb_main_menu, kb_admin_menu
from states.forms import AdStates
from config import settings

router = Router()

AD_COOLDOWN_HOURS = 4
ADMIN_ROLES = {"admin", "superadmin"}


def _menu_for(role: str):
    return kb_admin_menu() if role in ADMIN_ROLES else kb_main_menu()


async def _check_eligibility(user_id: int) -> Optional[str]:
    user = await queries.get_user(user_id)
    if user is None:
        return "⚠️ Siz ro'yxatdan o'tmaysiz. /start buyrug'ini kiriting."

    # Admins and superadmins bypass all restrictions
    if user["role"] in ADMIN_ROLES:
        return None

    now = datetime.now(timezone.utc)

    sub_until = user["subscription_until"]
    if sub_until is None or sub_until < now:
        return "❌ Sizda faol obuna yo'q. Administratorga murojaat qiling @jondor_admin1"

    blackout = await queries.get_active_blackout(now)
    if blackout:
        end_str = blackout["end_datetime"].strftime("%d.%m.%Y %H:%M UTC")
        return f"🚫 Hozir nashr qilish taqiqlangan. {end_str} dan keyin harakat qilib ko'ring."

    last_ad = user["last_ad_at"]
    if last_ad is not None:
        diff = now - last_ad
        if diff < timedelta(hours=AD_COOLDOWN_HOURS):
            remaining = timedelta(hours=AD_COOLDOWN_HOURS) - diff
            hours, rem = divmod(int(remaining.total_seconds()), 3600)
            minutes = rem // 60
            return (
                f"⏳ Reklama orasida {AD_COOLDOWN_HOURS} soat o'tishi kerak.\n"
                f"Keyingi nashr: {hours}soat {minutes}daqiqadan keyin."
            )

    return None


# ─── Entry point ────────────────────────────────────────────────────

@router.message(F.text == "📤 Reklama berish", F.chat.type == ChatType.PRIVATE)
async def start_ad(message: Message, state: FSMContext):
    user = await queries.get_user(message.from_user.id)
    if user is None:
        await message.answer("⚠️ Avval ro'yxatdan o'ting — /start buyrug'ini kiriting.")
        return

    error = await _check_eligibility(message.from_user.id)
    if error:
        await message.answer(error)
        return

    await state.set_state(AdStates.collecting)
    await state.update_data(photos=[], texts=[], audios=[], videos=[], message_ids=[])
    await message.answer(
        "📝 Reklama berish shartlari:\n"
        "• 1. Mahsulot surati\n"
        "• 2. Mahsulot nomi\n"
        "• 3. Manzil\n"
        "• 4. Narxi\n"
        "• 5. Telefon raqam\n\n"
        "Tugallaganingizdan so'ng — «📨 Reklamani yuborish» tugmasini bosing.",
        reply_markup=kb_collecting_ad(),
    )


# ─── Collecting content ──────────────────────────────────────────────

@router.message(AdStates.collecting, F.photo, F.chat.type == ChatType.PRIVATE)
async def collect_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos: list = data.get("photos", [])
    texts: list = data.get("texts", [])
    message_ids: list = data.get("message_ids", [])
    photos.append(message.photo[-1].file_id)
    if message.caption:
        texts.append(message.caption)
    message_ids.append(message.message_id)
    await state.update_data(photos=photos, texts=texts, message_ids=message_ids)


@router.message(AdStates.collecting, F.text & ~F.text.in_({"📨 Reklamani yuborish", "❌ Bekor qilish"}), F.chat.type == ChatType.PRIVATE)
async def collect_text(message: Message, state: FSMContext):
    data = await state.get_data()
    texts: list = data.get("texts", [])
    message_ids: list = data.get("message_ids", [])
    texts.append(message.text)
    message_ids.append(message.message_id)
    await state.update_data(texts=texts, message_ids=message_ids)


@router.message(AdStates.collecting, F.audio, F.chat.type == ChatType.PRIVATE)
async def collect_audio(message: Message, state: FSMContext):
    data = await state.get_data()
    audios: list = data.get("audios", [])
    texts: list = data.get("texts", [])
    message_ids: list = data.get("message_ids", [])
    audios.append(message.audio.file_id)
    if message.caption:
        texts.append(message.caption)
    message_ids.append(message.message_id)
    await state.update_data(audios=audios, texts=texts, message_ids=message_ids)


@router.message(AdStates.collecting, F.video, F.chat.type == ChatType.PRIVATE)
async def collect_video(message: Message, state: FSMContext):
    data = await state.get_data()
    videos: list = data.get("videos", [])
    texts: list = data.get("texts", [])
    message_ids: list = data.get("message_ids", [])
    videos.append(message.video.file_id)
    if message.caption:
        texts.append(message.caption)
    message_ids.append(message.message_id)
    await state.update_data(videos=videos, texts=texts, message_ids=message_ids)


# ─── Submit button ───────────────────────────────────────────────────

@router.message(AdStates.collecting, F.text == "📨 Reklamani yuborish", F.chat.type == ChatType.PRIVATE)
async def submit_ad(message: Message, state: FSMContext):
    data = await state.get_data()
    photos: list = data.get("photos", [])
    texts: list = data.get("texts", [])
    audios: list = data.get("audios", [])
    videos: list = data.get("videos", [])

    if not photos and not texts and not audios and not videos:
        await message.answer(
            "⚠️ Siz hech narsa qo'shmadingiz. Rasm, video, matn yoki audio yuboring.",
            reply_markup=kb_collecting_ad(),
        )
        return

    # Build preview text
    preview_parts = []
    if photos:
        preview_parts.append(f"🖼 Rasm: {len(photos)} ta")
    if videos:
        preview_parts.append(f"🎬 Video: {len(videos)} ta")
    if audios:
        preview_parts.append(f"🎵 Audio: {len(audios)} ta")
    if texts:
        preview_parts.append(f"📝 Matn:\n{chr(10).join(texts)}")

    await state.set_state(AdStates.confirm)
    await message.answer(
        f"📋 <b>Arizani oldindan ko'rish:</b>\n\n" + "\n".join(preview_parts) + "\n\nYuborishni tasdiqlang:",
        reply_markup=kb_confirm_ad(),
        parse_mode="HTML",
    )


# ─── Confirm & publish ───────────────────────────────────────────────

@router.callback_query(AdStates.confirm, F.data == "confirm_ad")
async def confirm_ad(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    user_id = callback.from_user.id

    error = await _check_eligibility(user_id)
    if error:
        user = await queries.get_user(user_id)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(error, reply_markup=_menu_for(user["role"] if user else "client"))
        await callback.answer()
        return

    photos: list = data.get("photos", [])
    videos: list = data.get("videos", [])
    audios: list = data.get("audios", [])
    texts: list = data.get("texts", [])

    now = datetime.now(timezone.utc)
    ad = await queries.create_ad(user_id, photos + videos + audios, "\n".join(texts) if texts else None)

    user = await queries.get_user(user_id)
    caption = "\n".join(texts) if texts else None

    try:
        # Prepare media group for photos and videos
        media_group = []
        for i, file_id in enumerate(photos):
            media_group.append(InputMediaPhoto(media=file_id))
        
        for i, file_id in enumerate(videos):
            media_group.append(InputMediaVideo(media=file_id))

        if media_group:
            # Attach caption to the first item in the media group
            media_group[0].caption = caption
            media_group[0].parse_mode = "HTML"

            if len(media_group) > 1:
                await bot.send_media_group(chat_id=settings.GROUP_ID, media=media_group)
            else:
                # Single photo or video
                item = media_group[0]
                if isinstance(item, InputMediaPhoto):
                    await bot.send_photo(chat_id=settings.GROUP_ID, photo=item.media, caption=caption, parse_mode="HTML")
                else:
                    await bot.send_video(chat_id=settings.GROUP_ID, video=item.media, caption=caption, parse_mode="HTML")
        elif caption:
            # Only text was sent
            await bot.send_message(chat_id=settings.GROUP_ID, text=caption, parse_mode="HTML")

        # Audios are sent separately or could be grouped if there are multiple (simplicity for now)
        for audio_file_id in audios:
            await bot.send_audio(chat_id=settings.GROUP_ID, audio=audio_file_id)

        await queries.mark_ad_sent(ad["id"], now)
        await queries.update_last_ad(user_id, now)

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "🎉 Reklamangiz muvaffaqiyatli nashr etildi!",
            reply_markup=_menu_for(user["role"]),
        )
    except Exception as e:
        await callback.message.answer(f"❌ Nashr qilishda xatolik: {e}\nAdministratorga murojaat qiling @jondor_admin1")

    await callback.answer()


# ─── Cancel ─────────────────────────────────────────────────────────

@router.message(AdStates.collecting, F.text == "❌ Bekor qilish", F.chat.type == ChatType.PRIVATE)
async def cancel_collecting(message: Message, state: FSMContext):
    user = await queries.get_user(message.from_user.id)
    await state.clear()
    await message.answer("❌ Ariza bekor qilindi.", reply_markup=_menu_for(user["role"] if user else "client"))


@router.callback_query(F.data == "cancel_ad")
async def cancel_ad(callback: CallbackQuery, state: FSMContext):
    user = await queries.get_user(callback.from_user.id)
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Ariza bekor qilindi.",
        reply_markup=_menu_for(user["role"] if user else "client"),
    )
    await callback.answer()