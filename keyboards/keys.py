from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)

PAGE_SIZE = 10  # Max user buttons per page


# ─── Reply keyboards ────────────────────────────────────────────────

def kb_request_contact() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kb_main_menu() -> ReplyKeyboardRemove:
    """Clients use the group directly — no private-chat action buttons needed."""
    return ReplyKeyboardRemove()


def kb_admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👥 Obunalar"),
                KeyboardButton(text="➕ Uzaytirish"),
            ],
            [
                KeyboardButton(text="🚫 Blackout"),
                KeyboardButton(text="🔑 Rollar"),
            ],
            [
                KeyboardButton(text="🗑 Obunani bekor qilish"),
            ],
        ],
        resize_keyboard=True,
    )


def kb_remove() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ─── Inline keyboards ───────────────────────────────────────────────


def kb_extend_months() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 oy", callback_data="extend_1"),
                InlineKeyboardButton(text="2 oy", callback_data="extend_2"),
                InlineKeyboardButton(text="3 oy", callback_data="extend_3"),
            ],
            [InlineKeyboardButton(text="📅 Sanani qo'lda kiritish", callback_data="extend_custom")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel")],
        ]
    )


def kb_admin_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel")]
        ]
    )


def kb_users_list(users: list, now, page: int = 0) -> InlineKeyboardMarkup:
    """Paginated list of users for subscription extension.
    callback prefix: ul_p_{page}
    """
    total_pages = max(1, (len(users) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    page_users = users[start : start + PAGE_SIZE]

    buttons = []
    for u in page_users:
        name = u["full_name"] or u["username"] or f"ID{u['telegram_id']}"
        sub = u["subscription_until"]
        status = f"✅ {sub.strftime('%d.%m')} gacha" if sub and sub > now else "❌ yo'q"
        role_badge = " 👮" if u["role"] == "admin" else ""
        phone = u["phone"] or "—"
        buttons.append([
            InlineKeyboardButton(
                text=f"{name}{role_badge} | {phone} — {status}",
                callback_data=f"extend_user_{u['telegram_id']}",
            )
        ])

    # Navigation row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅ Orqaga", callback_data=f"ul_p_{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Oldinga ➡", callback_data=f"ul_p_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_view_users_list(users: list, now, page: int = 0) -> InlineKeyboardMarkup:
    """Paginated list of users with active subscriptions.
    callback prefix: vul_p_{page}
    """
    total_pages = max(1, (len(users) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    page_users = users[start : start + PAGE_SIZE]

    buttons = []
    for u in page_users:
        name = u["full_name"] or u["username"] or f"ID{u['telegram_id']}"
        sub = u["subscription_until"]
        status = f"✅ {sub.strftime('%d.%m')} gacha" if sub and sub > now else "❌ yo'q"
        role_badge = " 👮" if u["role"] == "admin" else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{name}{role_badge} — {status}",
                callback_data=f"view_user_{u['telegram_id']}",
            )
        ])

    # Navigation row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅ Orqaga", callback_data=f"vul_p_{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Oldinga ➡", callback_data=f"vul_p_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_blackout_list(blackouts: list) -> InlineKeyboardMarkup:
    buttons = []
    for b in blackouts:
        label = f"🗑 #{b['id']} {b['start_datetime'].strftime('%d.%m %H:%M')} – {b['end_datetime'].strftime('%d.%m %H:%M')}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"del_blackout_{b['id']}")])
    buttons.append([InlineKeyboardButton(text="➕ Qo'shish", callback_data="add_blackout")])
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_remove_sub_list(users: list, now, page: int = 0) -> InlineKeyboardMarkup:
    """Paginated list of active subscribers for subscription removal.
    callback prefix: rs_p_{page}
    """
    total_pages = max(1, (len(users) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    page_users = users[start : start + PAGE_SIZE]

    buttons = []
    for u in page_users:
        name = u["full_name"] or u["username"] or f"ID{u['telegram_id']}"
        sub = u["subscription_until"]
        until_str = sub.strftime('%d.%m.%Y') if sub else "—"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {name} — {until_str} gacha",
                callback_data=f"remove_sub_{u['telegram_id']}",
            )
        ])

    # Navigation row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅ Orqaga", callback_data=f"rs_p_{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Oldinga ➡", callback_data=f"rs_p_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)