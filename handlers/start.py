from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.enums import ChatType
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from db import queries
from keyboards.keys import kb_request_contact, kb_main_menu, kb_admin_menu
from states.forms import RegistrationStates
from config import settings

router = Router()

ADMIN_ROLES = {"admin", "superadmin"}


def _menu_for(role: str):
    return kb_admin_menu() if role in ADMIN_ROLES else kb_main_menu()


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await queries.get_user(message.from_user.id)

    # Superadmin auto-setup
    if message.from_user.id == settings.SUPERADMIN_ID and (
        user is None or user["role"] != "superadmin"
    ):
        if user is None:
            await queries.create_user(
                telegram_id=message.from_user.id,
                phone="",
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                full_name=message.from_user.full_name,
                language_code=message.from_user.language_code,
                is_bot=message.from_user.is_bot,
                role="superadmin",
            )
        else:
            await queries.set_role(message.from_user.id, "superadmin")
        await message.answer("👑 Siz superadmin bo'lib kirdingiz.", reply_markup=kb_admin_menu())
        return

    if user is None:
        await message.answer(
            "Ro'yxatdan o'tish uchun telefon raqamingizni yuboring:",
            reply_markup=kb_request_contact(),
        )
        await state.set_state(RegistrationStates.waiting_contact)
        return

    await message.answer(
        f"👋 Xush kelibsiz, {message.from_user.first_name}!",
        reply_markup=_menu_for(user["role"]),
    )


@router.message(RegistrationStates.waiting_contact, F.contact, F.chat.type == ChatType.PRIVATE)
async def handle_contact(message: Message, state: FSMContext):
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer("⚠️ Iltimos, o'z raqamingizni yuboring.")
        return

    await queries.create_user(
        telegram_id=message.from_user.id,
        phone=contact.phone_number,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        full_name=message.from_user.full_name,
        language_code=message.from_user.language_code,
        is_bot=message.from_user.is_bot,
    )
    await state.clear()
    await message.answer(
        "✅ Ro'yxatdan o'tish yakunlandi! Jondor olxga reklama berish uchun 10 ming so'm to'lov qilishingiz kerak. @jondor_admin1",
        reply_markup=kb_main_menu(),
    )


@router.message(RegistrationStates.waiting_contact, F.chat.type == ChatType.PRIVATE)
async def handle_no_contact(message: Message):
    await message.answer(
        "⚠️ Iltimos, kontaktni yuborish uchun tugmani bosing.",
        reply_markup=kb_request_contact(),
    )