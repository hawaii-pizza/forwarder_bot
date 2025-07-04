"""
bot/routers/targets.py
----------------------
Target‑chat configuration:
• "set_tgt" – prompt for chat_id[:topic_id]
• Accepts user reply, validates access, stores in DB

After a target is set we restart the forwarding loop for that user.
"""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
)
from aiogram.enums import ParseMode

router = Router()
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Shared singletons via lazy import
# -----------------------------------------------------------------------------

def services():
    from bot import runtime as r
    from bot.keyboards import main_menu
    return r.db, r.auth, r.forwarder, main_menu

def parse_chat_topic_id(raw: str):
    if ":" in raw:
        cid, tid = raw.split(":", 1)
        return int(cid), int(tid)
    return int(raw), None


async def ensure_user(entry: Message | CallbackQuery):
    db, *_ = services()
    uid = entry.from_user.id
    await db.add_user_if_missing(uid)
    return uid

# In‑memory awaiting map specific to this router
AWAITING_TGT: dict[int, bool] = {}

# -----------------------------------------------------------------------------
# Set / change target flow
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "set_tgt")
async def set_target_start(call: CallbackQuery):
    uid = await ensure_user(call)
    AWAITING_TGT[uid] = True
    await call.message.answer(
        "Send the <code>chat_id</code> or <code>chat_id:topic_id</code> of the <b>target</b> chat where messages should be forwarded.",
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text, lambda m: AWAITING_TGT.get(m.from_user.id))
async def set_target_finish(message: Message):
    db, auth, forwarder, main_menu = services()
    uid = message.from_user.id
    try:
        chat_id, topic_id = parse_chat_topic_id(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid format – try again.")
        return

    client = auth.client(uid)
    try:
        await client.start()
        await client.get_entity(chat_id)  # access check
    except Exception as e:
        await message.answer(f"❌ Cannot access chat: {e}")
        return

    await db.set_target(uid, chat_id, topic_id)
    logger.info("User %s set target %s:%s", uid, chat_id, topic_id)
    if forwarder:
        await forwarder.refresh_user(uid)

    await message.answer("✅ Target updated!", reply_markup=main_menu().as_markup())
    AWAITING_TGT.pop(uid, None)
