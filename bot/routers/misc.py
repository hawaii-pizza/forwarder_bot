"""
bot/routers/misc.py
-------------------
Odds-and-ends interactions that don't modify config:
• "view_cfg" – show full config summary
• "donate"   – display donation addresses
• "back_main" – bring user back to main menu
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

router = Router()

# -----------------------------------------------------------------------------

def services():
    from bot import runtime as r
    from bot.keyboards import main_menu
    return r.db, r.auth, r.forwarder, main_menu


async def ensure_user(entry):
    db, *_ = services()
    uid = entry.from_user.id
    await db.add_user_if_missing(uid)
    return uid

# -----------------------------------------------------------------------------
# View configuration
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "view_cfg")
async def view_config(call: CallbackQuery):
    db, _, _, main_menu = services()
    uid = await ensure_user(call)

    srcs = await db.list_sources(uid)
    tgt = await db.get_target(uid)
    mode = await db.get_filter_mode(uid)
    flt = await db.list_filtered_users(uid)

    lines = ["<b>Your current configuration</b>", "<b>Sources:</b>"]
    for s in srcs or []:
        lines.append(f"• {s.chat_id}{f':{s.topic_id}' if s.topic_id else ''} — {s.title}")
    if not srcs:
        lines.append("  None ✅")

    lines.append("\n<b>Target:</b>")
    if tgt:
        lines.append(f"• {tgt.chat_id}{f':{tgt.topic_id}' if tgt.topic_id else ''}")
    else:
        lines.append("  None ❌")

    lines.append(f"\n<b>Filter mode:</b> {'All messages' if mode=='all' else 'Token-related only'}")

    lines.append("\n<b>Filtered users:</b>")
    if flt:
        lines.extend(f"• {u}" for u in flt)
    else:
        lines.append("  None")

    await call.message.answer("\n".join(lines), reply_markup=main_menu().as_markup())

# -----------------------------------------------------------------------------
# Donate
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "donate")
async def donate(call: CallbackQuery):
    _, _, _, main_menu = services()
    txt = (
        "<b>You can send your donations to:</b>\n"
        "• SOL: <code>So11111111111111111111111111111111111111112</code>\n"
        "• ETH: <code>0x0123456789abcdef0123456789abcdef01234567</code>"
    )
    await call.message.answer(txt, parse_mode=ParseMode.HTML, reply_markup=main_menu().as_markup())

# -----------------------------------------------------------------------------
# Back navigation
# -----------------------------------------------------------------------------

@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    _, _, _, main_menu = services()
    await call.message.answer("Main menu:", reply_markup=main_menu().as_markup())
