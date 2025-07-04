"""
bot/routers/filters.py
----------------------
User-filtering & message-filter mode toggle:
• "add_filter" – prompt for numeric Telegram user_id to allow
• accepts reply, stores display name
• "mgr_filter" – list filtered IDs with ❌ delete buttons
• "del_filter:<user_id>" – remove filter
• "toggle_mode" – switch between 'all' and 'token' content filter
"""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.enums import ParseMode

router = Router()
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Lazy singletons to avoid circulars
# -----------------------------------------------------------------------------

def services():
    from bot import runtime as r
    from bot.keyboards import main_menu
    return r.db, r.auth, r.forwarder, main_menu


async def ensure_user(entry: Message | CallbackQuery):
    db, *_ = services()
    uid = entry.from_user.id
    await db.add_user_if_missing(uid)
    return uid

# -----------------------------------------------------------------------------
# In-memory awaiting map for add-filter flow
# -----------------------------------------------------------------------------

AWAITING_FILTER: dict[int, bool] = {}

# -----------------------------------------------------------------------------
# Keyboards
# -----------------------------------------------------------------------------

async def filters_kb(uid: int):
    db, *_ = services()
    ids = await db.list_filtered_users(uid)
    rows = [
        [InlineKeyboardButton(text=f"• {u} ❌", callback_data=f"del_filter:{u}")]
        for u in ids
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# -----------------------------------------------------------------------------
# Add filtered user flow
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "add_filter")
async def add_filter_start(call: CallbackQuery):
    uid = await ensure_user(call)
    AWAITING_FILTER[uid] = True
    await call.message.answer("Send the <code>user_id</code> you want to <b>allow</b>. Leave blank to cancel.", parse_mode=ParseMode.HTML)


@router.message(F.text, lambda m: AWAITING_FILTER.get(m.from_user.id))
async def add_filter_finish(message: Message):
    db, auth, forwarder, main_menu = services()
    uid = message.from_user.id
    raw = message.text.strip()
    if not raw:
        await message.answer("⏹️ Cancelled.", reply_markup=main_menu().as_markup())
        AWAITING_FILTER.pop(uid, None)
        return

    try:
        user_id = int(raw)
    except ValueError:
        await message.answer("❌ Please send a valid numeric user_id.")
        return

    client = auth.client(uid)
    try:
        await client.start()
        entity = await client.get_entity(user_id)
        display_name = getattr(entity, "first_name", "user")
    except Exception:
        display_name = "user"

    await db.add_filtered_user(uid, user_id, display_name)
    logger.info("User %s added filter user %s", uid, user_id)
    if forwarder:
        await forwarder.refresh_user(uid)

    await message.answer("✅ Filtered user added!", reply_markup=main_menu().as_markup())
    AWAITING_FILTER.pop(uid, None)

# -----------------------------------------------------------------------------
# Manage filtered users
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "mgr_filter")
async def manage_filtered(call: CallbackQuery):
    uid = await ensure_user(call)
    await call.message.answer("Your filtered users:", reply_markup=await filters_kb(uid))


@router.callback_query(lambda c: c.data.startswith("del_filter:"))
async def delete_filter(call: CallbackQuery):
    db, _, forwarder, _ = services()
    uid = await ensure_user(call)
    _, user_id_str = call.data.split(":", 1)
    user_id = int(user_id_str)

    await db.remove_filtered_user(uid, user_id)
    logger.info("User %s removed filter user %s", uid, user_id)
    if forwarder:
        await forwarder.refresh_user(uid)

    await call.message.edit_reply_markup(reply_markup=await filters_kb(uid))

# -----------------------------------------------------------------------------
# Toggle content filter mode
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "toggle_mode")
async def toggle_mode(call: CallbackQuery):
    db, _, forwarder, _ = services()
    uid = await ensure_user(call)
    current = await db.get_filter_mode(uid)
    new_mode = "token" if current == "all" else "all"
    await db.set_filter_mode(uid, new_mode)
    if forwarder:
        await forwarder.refresh_user(uid)
    await call.answer("Switched!")
