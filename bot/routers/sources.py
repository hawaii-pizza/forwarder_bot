"""
bot/routers/sources.py
----------------------
Source‑chat management:
• "add_src" – prompt user for <chat_id[:topic_id]>
• receives the chat_id message, validates access, stores in DB
• "mgr_src" – list existing sources with ❌ delete buttons
• "del_src:<chat_id>:<topic_id>" – remove source, refresh forwarder

Relies on singletons in `bot.entry` (db, auth, forwarder) and
`bot.keyboards.main_menu`.
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
# Utility accessors to avoid circular imports
# -----------------------------------------------------------------------------

def services():
    from bot import runtime as r
    from bot.keyboards import main_menu
    return r.db, r.auth, r.forwarder, main_menu

def parse_chat_topic_id(raw: str) -> tuple[int, int | None]:
    """Convert "-100123" or "-100123:55" → (chat_id, topic_id|None)."""
    if ":" in raw:
        cid, tid = raw.split(":", 1)
        return int(cid), int(tid)
    return int(raw), None


async def ensure_user(entry: Message | CallbackQuery):
    db, *_ = services()
    uid = entry.from_user.id
    await db.add_user_if_missing(uid)
    return uid

# -----------------------------------------------------------------------------
# In‑memory FSM for this router only
# -----------------------------------------------------------------------------

AWAITING_SRC: dict[int, bool] = {}

# -----------------------------------------------------------------------------
# Keyboards
# -----------------------------------------------------------------------------

async def sources_kb(uid: int):
    db, *_ = services()
    rows = [
        [
            InlineKeyboardButton(
                text=f"• {s.chat_id}{f':{s.topic_id}' if s.topic_id else ''} — {s.title} ❌",
                callback_data=f"del_src:{s.chat_id}:{s.topic_id or 0}",
            )
        ]
        for s in await db.list_sources(uid)
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# -----------------------------------------------------------------------------
# Add Source flow
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "add_src")
async def add_src_start(call: CallbackQuery):
    uid = await ensure_user(call)
    AWAITING_SRC[uid] = True
    await call.message.answer(
        "Send the <code>chat_id</code> or <code>chat_id:topic_id</code> of the <b>source</b> chat you want me to monitor.",
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text, lambda m: AWAITING_SRC.get(m.from_user.id))
async def add_src_finish(message: Message):
    db, auth, forwarder, main_menu = services()
    uid = message.from_user.id

    # Parse
    try:
        chat_id, topic_id = parse_chat_topic_id(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid format – try again.")
        return

    # Validate access via Telethon
    client = auth.client(uid)
    try:
        await client.start()
        entity = await client.get_entity(chat_id)
        title = getattr(entity, "title", str(entity)) + (f" (topic {topic_id})" if topic_id else "")
    except Exception as e:
        await message.answer(f"❌ Cannot access chat: {e}")
        return

    await db.add_source(uid, chat_id, topic_id, title)
    logger.info("User %s added source %s:%s", uid, chat_id, topic_id)
    if forwarder:
        await forwarder.refresh_user(uid)

    await message.answer("✅ Source added!", reply_markup=main_menu().as_markup())
    AWAITING_SRC.pop(uid, None)

# -----------------------------------------------------------------------------
# Manage / delete sources
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "mgr_src")
async def manage_sources(call: CallbackQuery):
    uid = await ensure_user(call)
    await call.message.answer("Your sources:", reply_markup=await sources_kb(uid))


@router.callback_query(lambda c: c.data.startswith("del_src:"))
async def delete_source(call: CallbackQuery):
    db, _, forwarder, _ = services()
    uid = await ensure_user(call)

    _, cid_str, tid_str = call.data.split(":", 2)
    chat_id, topic_id = int(cid_str), int(tid_str) or None

    await db.remove_source(uid, chat_id, topic_id)
    logger.info("User %s removed source %s:%s", uid, chat_id, topic_id)
    if forwarder:
        await forwarder.refresh_user(uid)

    await call.message.edit_reply_markup(reply_markup=await sources_kb(uid))
