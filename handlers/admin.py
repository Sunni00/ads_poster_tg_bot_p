from datetime import datetime, timezone, timedelta
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import settings
from db import queries
from keyboards.keys import (
    kb_extend_months,
    kb_admin_cancel,
    kb_blackout_list,
    kb_admin_menu,
    kb_users_list,
    kb_view_users_list,
    kb_remove_sub_list,
)
from states.forms import AdminExtendStates, AdminBlackoutStates

router = Router()

ADMIN_ROLES = {"admin", "superadmin"}


async def check_admin(source) -> Optional[str]:
    user_id = source.from_user.id
    # .env superadmin always has access, even without a DB record
    if user_id == settings.SUPERADMIN_ID:
        return "superadmin"
    user = await queries.get_user(user_id)
    if user and user["role"] in ADMIN_ROLES:
        return user["role"]
    return None


# ─────────────────────────── Subscriptions ──────────────────────────

@router.message(F.text == "👥 Obunalar", F.chat.type == ChatType.PRIVATE)
async def cmd_subscriptions(message: Message):
    if not await check_admin(message):
        return

    users = await queries.get_all_users()
    now = datetime.now(timezone.utc)
    # Filter: only show users with an active subscription
    active_users = [u for u in users if u["subscription_until"] and u["subscription_until"] > now]

    if not active_users:
        return await message.answer("📋 Faol obunaga ega foydalanuvchilar topilmadi.")

    await message.answer(
        "📋 <b>Mijozlar ro'yxati:</b>\nBatafsil ma'lumot uchun tanlang:",
        reply_markup=kb_view_users_list(active_users, now),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_user_"))
async def view_user_details(callback: CallbackQuery):
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    target_id = int(callback.data.split("_")[-1])
    user = await queries.get_user(target_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi.", show_alert=True)
        return

    now = datetime.now(timezone.utc)
    sub = user["subscription_until"]
    status = f"✅ {sub.strftime('%d.%m.%Y %H:%M')} gacha" if sub and sub > now else "❌ obuna yo'q"
    last_ad = user["last_ad_at"].strftime('%d.%m.%Y %H:%M') if user["last_ad_at"] else "yo'q"

    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
        f"👤 Ism: {user['full_name'] or '—'}\n"
        f"📞 Tel: {user['phone'] or '—'}\n"
        f"🌐 Username: @{user['username'] or '—'}\n"
        f"👮 Rol: {user['role']}\n"
        f"📅 Obuna: {status}\n"
        f"🚀 Oxirgi reklama: {last_ad}\n"
        f"🆕 Ro'yxatdan o'tdi: {user['created_at'].strftime('%d.%m.%Y')}"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb_admin_cancel())
    await callback.answer()


# ─────────────────────────── Extend ─────────────────────────────────

@router.message(F.text == "➕ Uzaytirish", F.chat.type == ChatType.PRIVATE)
async def cmd_extend(message: Message, state: FSMContext):
    if not await check_admin(message):
        return

    await state.clear()
    users = await queries.get_all_users()
    
    now = datetime.now(timezone.utc)
    # Filter: only show users without active subscription
    users = [u for u in users if u["subscription_until"] is None or u["subscription_until"] < now]

    if not users:
        return await message.answer("📋 Obunasi yo'q foydalanuvchilar topilmadi.")

    await message.answer(
        "👤 Obunani uzaytirish uchun foydalanuvchini tanlang:",
        reply_markup=kb_users_list(users, now),
    )


@router.callback_query(F.data.startswith("extend_user_"))
async def extend_pick_user(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    target_id = int(callback.data.split("extend_user_")[1])
    user = await queries.get_user(target_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi.", show_alert=True)
        return

    await state.update_data(target_id=target_id)
    await state.set_state(AdminExtendStates.waiting_months_or_date)

    now = datetime.now(timezone.utc)
    name = user["full_name"] or user["username"] or f"ID{target_id}"
    sub = user["subscription_until"]
    current = f"{sub.strftime('%d.%m.%Y')} gacha" if sub and sub > now else "obuna yo'q"

    await callback.message.edit_text(
        f"👤 <b>{name}</b>\nJoriy obuna: {current}\n\nUzaytirish muddatini tanlang:",
        reply_markup=kb_extend_months(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AdminExtendStates.waiting_months_or_date, F.data.startswith("extend_"))
async def extend_choose_period(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_id = data["target_id"]
    choice = callback.data

    if choice == "extend_custom":
        await state.set_state(AdminExtendStates.waiting_custom_date)
        await callback.message.edit_text(
            "📅 Obuna tugash sanasini <b>KK.OO.YYYY</b> formatida kiriting:",
            reply_markup=kb_admin_cancel(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    months = int(choice.split("_")[1])
    await _apply_extension(callback.message, state, target_id, bot=callback.bot, months=months)
    await callback.answer()


@router.message(AdminExtendStates.waiting_custom_date, F.text, F.chat.type == ChatType.PRIVATE)
async def extend_custom_date(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data["target_id"]
    try:
        until = datetime.strptime(message.text.strip(), "%d.%m.%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return await message.answer("⚠️ Noto'g'ri format. Sanani KK.OO.YYYY ko'rinishida kiriting:", reply_markup=kb_admin_cancel())

    if until <= datetime.now(timezone.utc):
        return await message.answer("⚠️ Sana kelajakda bo'lishi kerak.", reply_markup=kb_admin_cancel())
    
    # Get bot instance from the message
    await _apply_extension(message, state, target_id, bot=message.bot, until=until)


async def _apply_extension(msg, state, target_id, bot=None, months=0, until=None):
    user = await queries.get_user(target_id)
    now = datetime.now(timezone.utc)

    if until is None:
        base = user["subscription_until"]
        base = base if base and base > now else now
        until = base + timedelta(days=30 * months)

    await queries.extend_subscription(target_id, until)
    await state.clear()

    # Notify the user
    if bot:
        try:
            await bot.send_message(
                chat_id=target_id,
                text=f"✅ Sizning obunangiz <b>{until.strftime('%d.%m.%Y')}</b> gacha uzaytirildi.\nEndi reklama berishingiz mumkin! 🚀",
                parse_mode="HTML"
            )
        except Exception:
            pass # User might have blocked the bot

    name = user["full_name"] or user["username"] or f"ID{target_id}"
    await msg.answer(
        f"✅ <b>{name}</b> obunasi <b>{until.strftime('%d.%m.%Y')}</b> gacha uzaytirildi.",
        reply_markup=kb_admin_menu(),
        parse_mode="HTML",
    )


# ─────────────────────────── Blackout ───────────────────────────────

@router.message(F.text == "🚫 Blackout", F.chat.type == ChatType.PRIVATE)
async def cmd_blackout(message: Message, state: FSMContext):
    if not await check_admin(message):
        return

    await state.clear()
    blackouts = await queries.get_all_blackouts()
    text = (
        "🚫 <b>Nashr qilish taqiqlangan davrlar:</b>\nO'chirish uchun davrni bosing.\n"
        if blackouts else
        "🚫 <b>Faol taqiqlangan davrlar yo'q.</b>\n"
    )
    await message.answer(text, reply_markup=kb_blackout_list(blackouts), parse_mode="HTML")


@router.callback_query(F.data == "add_blackout")
async def add_blackout_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    await state.set_state(AdminBlackoutStates.waiting_start)
    await callback.message.edit_text(
        "📅 Taqiq <b>boshlanish sanasi va vaqtini</b> kiriting:\n<code>KK.OO.YYYY SS:DA</code> (UTC)",
        reply_markup=kb_admin_cancel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminBlackoutStates.waiting_start, F.text, F.chat.type == ChatType.PRIVATE)
async def blackout_get_start(message: Message, state: FSMContext):
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return await message.answer("⚠️ Noto'g'ri format. Foydalaning: KK.OO.YYYY SS:DA", reply_markup=kb_admin_cancel())

    await state.update_data(blackout_start=start.isoformat())
    await state.set_state(AdminBlackoutStates.waiting_end)
    await message.answer(
        "📅 Endi <b>tugash sanasi va vaqtini</b> kiriting:\n<code>KK.OO.YYYY SS:DA</code> (UTC)",
        reply_markup=kb_admin_cancel(),
        parse_mode="HTML",
    )


@router.message(AdminBlackoutStates.waiting_end, F.text, F.chat.type == ChatType.PRIVATE)
async def blackout_get_end(message: Message, state: FSMContext):
    data = await state.get_data()
    start = datetime.fromisoformat(data["blackout_start"])
    try:
        end = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return await message.answer("⚠️ Noto'g'ri format. Foydalaning: KK.OO.YYYY SS:DA", reply_markup=kb_admin_cancel())

    if end <= start:
        return await message.answer("⚠️ Tugash vaqti boshlanishidan kechroq bo'lishi kerak.", reply_markup=kb_admin_cancel())

    await queries.add_blackout(start, end, message.from_user.id)
    await state.clear()
    await message.answer(
        f"✅ Taqiq o'rnatildi:\n🕐 {start.strftime('%d.%m.%Y %H:%M')} — {end.strftime('%d.%m.%Y %H:%M')} UTC",
        reply_markup=kb_admin_menu(),
    )


@router.callback_query(F.data.startswith("del_blackout_"))
async def delete_blackout(callback: CallbackQuery):
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    blackout_id = int(callback.data.split("_")[-1])
    await queries.delete_blackout(blackout_id)

    blackouts = await queries.get_all_blackouts()
    text = "🚫 <b>Nashr qilish taqiqlangan davrlar:</b>\n" if blackouts else "🚫 <b>Faol taqiqlangan davrlar yo'q.</b>\n"
    await callback.message.edit_text(text, reply_markup=kb_blackout_list(blackouts), parse_mode="HTML")
    await callback.answer("🗑 O'chirildi")


# ─────────────────────────── Roles ──────────────────────────────────

@router.message(F.text == "🔑 Rollar", F.chat.type == ChatType.PRIVATE)
async def cmd_roles_help(message: Message):
    is_superadmin = message.from_user.id == settings.SUPERADMIN_ID
    if not is_superadmin:
        user = await queries.get_user(message.from_user.id)
        if not user or user["role"] != "superadmin":
            return await message.answer("⛔ Faqat superadmin uchun.")

    await message.answer(
        "🔑 <b>Rollarni boshqarish</b>\n\n"
        "Buyruqdan foydalaning:\n"
        "<code>/setrole &lt;telegram_id&gt; &lt;rol&gt;</code>\n\n"
        "Mavjud rollar: <code>client</code>, <code>admin</code>, <code>superadmin</code>\n\n"
        "Misol: <code>/setrole 123456789 admin</code>",
        parse_mode="HTML",
    )


@router.message(Command("setrole"), F.chat.type == ChatType.PRIVATE)
async def cmd_setrole(message: Message):
    is_superadmin = message.from_user.id == settings.SUPERADMIN_ID
    if not is_superadmin:
        user = await queries.get_user(message.from_user.id)
        if not user or user["role"] != "superadmin":
            return await message.answer("⛔ Faqat superadmin uchun.")

    parts = message.text.strip().split()
    if len(parts) != 3:
        return await message.answer("Foydalanish: /setrole <telegram_id> <client|admin|superadmin>")

    try:
        target_id = int(parts[1])
        role = parts[2]
    except ValueError:
        return await message.answer("⚠️ Noto'g'ri format.")

    if role not in ("client", "admin", "superadmin"):
        return await message.answer("⚠️ Rol: client, admin yoki superadmin.")

    target = await queries.get_user(target_id)
    if not target:
        return await message.answer("❌ Foydalanuvchi topilmadi.")

    await queries.set_role(target_id, role)
    await message.answer(f"✅ {target_id} foydalanuvchi roli <b>{role}</b> ga o'zgartirildi.", parse_mode="HTML")


# ─────────────────────────── Pagination ────────────────────────────

@router.callback_query(F.data.startswith("ul_p_"))
async def extend_list_page(callback: CallbackQuery, state: FSMContext):
    """Navigate pages in the 'Uzaytirish' user list."""
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    page = int(callback.data.split("ul_p_")[1])
    now = datetime.now(timezone.utc)
    users = await queries.get_all_users()
    users = [u for u in users if u["subscription_until"] is None or u["subscription_until"] < now]

    if not users:
        await callback.answer("📋 Obunasi yo'q foydalanuvchilar topilmadi.", show_alert=True)
        return

    await callback.message.edit_reply_markup(
        reply_markup=kb_users_list(users, now, page=page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vul_p_"))
async def view_list_page(callback: CallbackQuery):
    """Navigate pages in the 'Obunalar' view list."""
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    page = int(callback.data.split("vul_p_")[1])
    now = datetime.now(timezone.utc)
    users = await queries.get_all_users()
    active_users = [u for u in users if u["subscription_until"] and u["subscription_until"] > now]

    if not active_users:
        await callback.answer("📋 Faol obunaga ega foydalanuvchilar topilmadi.", show_alert=True)
        return

    await callback.message.edit_reply_markup(
        reply_markup=kb_view_users_list(active_users, now, page=page)
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Silently acknowledge the page-counter button (no action)."""
    await callback.answer()


# ─────────────────────────── Remove Subscription ────────────────────

@router.message(F.text == "🗑 Obunani bekor qilish", F.chat.type == ChatType.PRIVATE)
async def cmd_remove_sub(message: Message):
    if not await check_admin(message):
        return

    now = datetime.now(timezone.utc)
    users = await queries.get_all_users()
    active_users = [u for u in users if u["subscription_until"] and u["subscription_until"] > now]

    if not active_users:
        return await message.answer("📋 Faol obunaga ega foydalanuvchilar topilmadi.")

    await message.answer(
        "🗑 <b>Obunani bekor qilish:</b>\nFoydalanuvchini tanlang:",
        reply_markup=kb_remove_sub_list(active_users, now),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("remove_sub_"))
async def confirm_remove_sub(callback: CallbackQuery, bot: Bot):
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    target_id = int(callback.data.split("remove_sub_")[1])
    user = await queries.get_user(target_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi.", show_alert=True)
        return

    await queries.remove_subscription(target_id)

    name = user["full_name"] or user["username"] or f"ID{target_id}"

    # Notify the user
    try:
        await bot.send_message(
            chat_id=target_id,
            text="❌ Sizning obunangiz admin tomonidan bekor qilindi.\n"
                 "Obunani qayta faollashtirish uchun @jondor_admin1 ga murojaat qiling.",
        )
    except Exception:
        pass  # User may have blocked the bot

    # Refresh the list
    now = datetime.now(timezone.utc)
    users = await queries.get_all_users()
    active_users = [u for u in users if u["subscription_until"] and u["subscription_until"] > now]

    if active_users:
        await callback.message.edit_text(
            f"✅ <b>{name}</b> obunasi bekor qilindi.\n\n"
            "🗑 <b>Obunani bekor qilish:</b>\nFoydalanuvchini tanlang:",
            reply_markup=kb_remove_sub_list(active_users, now),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"✅ <b>{name}</b> obunasi bekor qilindi.\n"
            "📋 Boshqa faol obunalar yo'q.",
            parse_mode="HTML",
        )
        await callback.message.answer("👀", reply_markup=kb_admin_menu())

    await callback.answer(f"✅ {name} obunasi o'chirildi")


@router.callback_query(F.data.startswith("rs_p_"))
async def remove_sub_list_page(callback: CallbackQuery):
    """Navigate pages in the remove-subscription list."""
    if not await check_admin(callback):
        await callback.answer("⛔ Kirish taqiqlangan.", show_alert=True)
        return

    page = int(callback.data.split("rs_p_")[1])
    now = datetime.now(timezone.utc)
    users = await queries.get_all_users()
    active_users = [u for u in users if u["subscription_until"] and u["subscription_until"] > now]

    if not active_users:
        await callback.answer("📋 Faol obunaga ega foydalanuvchilar topilmadi.", show_alert=True)
        return

    await callback.message.edit_reply_markup(
        reply_markup=kb_remove_sub_list(active_users, now, page=page)
    )
    await callback.answer()


# ─────────────────────────── Universal cancel ───────────────────────

@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ Harakat bekor qilindi.", reply_markup=kb_admin_menu())
    await callback.answer()