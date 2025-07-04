"""
bot/routers/auth.py
Handles login / logout and automatic menu display.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router()
log = logging.getLogger(__name__)

from bot.routers.sources import AWAITING_SRC
from bot.routers.targets import AWAITING_TGT
from bot.routers.filters import AWAITING_FILTER

# --------------------------------------------------------------------------- #
# Shared singletons (avoids circular-import re-execution)                     #
# --------------------------------------------------------------------------- #
def services():
    from bot import runtime as r          # runtime.db / auth / forwarder
    from bot.keyboards import main_menu
    return r.db, r.auth, r.forwarder, main_menu


async def ensure_user(event: Message | CallbackQuery):
    db, *_ = services()
    uid = event.from_user.id
    await db.add_user_if_missing(uid)
    return uid


# per-user flag while waiting for password
AWAIT_PWD: dict[int, bool] = {}


# --------------------------------------------------------------------------- #
# /start  – decide which menu to show                                         #
# --------------------------------------------------------------------------- #
@router.message(CommandStart())
async def cmd_start(msg: Message):
    db, auth, _, menu = services()
    uid = await ensure_user(msg)

    session_ok = await auth.session_is_authorized(uid)

    if session_ok:
        await msg.answer("Welcome back!", reply_markup=menu().as_markup())
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔑 Log in",callback_data="login")]]
        )
        await msg.answer("Welcome! Please authenticate.", reply_markup=kb)


# --------------------------------------------------------------------------- #
#  QR login                                                                   #
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "login")
async def login_qr(call: CallbackQuery):
    db, auth, fwd, menu = services()
    uid = await ensure_user(call)

    client, qr_png = await auth.start_login(uid)
    qr_file = BufferedInputFile(qr_png.getvalue(), filename="qr.png")

    # send QR (retry 3× if Telegram connection hiccups)
    for attempt in range(3):
        try:
            await call.message.answer_photo(
                qr_file,
                caption=(
                    "Scan this QR-code in Telegram. "
                    "If you use 2-Step Verification, send the password next."
                ),
            )
            break
        except TelegramNetworkError as e:
            log.warning("QR send failed (%s) retry %s/3", e, attempt + 1)
            await asyncio.sleep(2)
    else:
        await call.message.answer("❌ Could not send QR. Try again later.")
        return

    await auth.wait_complete(uid)

    if await client.is_user_authorized():
        await call.message.answer("✅ Logged in!", reply_markup=menu().as_markup())
        if fwd:
            await fwd.refresh_user(uid)
    else:
        AWAIT_PWD[uid] = True
        await call.message.answer("🔐 Send your 2-step password.")


# --------------------------------------------------------------------------- #
# 2-step Verification password                                                #
# --------------------------------------------------------------------------- #
@router.message(F.text, lambda m: AWAIT_PWD.get(m.from_user.id))
async def receive_password(msg: Message):
    db, auth, fwd, menu = services()
    uid = msg.from_user.id

    ok, client = await auth.finish_with_password(uid, msg.text.strip())
    if ok and await client.is_user_authorized():
        await msg.answer("✅ Logged in!", reply_markup=menu().as_markup())
        if fwd:
            await fwd.refresh_user(uid)
    else:
        await msg.answer("❌ Incorrect password.")

    AWAIT_PWD.pop(uid, None)


# --------------------------------------------------------------------------- #
# Logout                                                                      #
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "logout")
async def logout(call: CallbackQuery):
    db, auth, fwd, _ = services()
    uid = await ensure_user(call)

    if fwd:
        await fwd.stop_user(uid)

    try:
        Path(auth._session_path(uid) + ".session").unlink()
    except FileNotFoundError:
        pass

    await call.message.answer("🔒 Logged out.")


# --------------------------------------------------------------------------- #
# Automatic menu on any DM                                                    #
# --------------------------------------------------------------------------- #
@router.message(F.chat.type == "private", flags={"block": False})
async def auto_menu(msg: Message):
    uid = msg.from_user.id
    if any((
        AWAITING_SRC.get(uid),
        AWAITING_TGT.get(uid),
        AWAITING_FILTER.get(uid),
        AWAIT_PWD.get(uid),
    )):
        return
    db, auth, _, menu = services()
    await db.add_user_if_missing(uid)

    if Path(auth._session_path(uid) + ".session").exists() and auth.client(uid).is_user_authorized():
        await msg.answer("Main menu:", reply_markup=menu().as_markup())
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔑 Log in", callback_data="login")]]
        )
        await msg.answer("Please authenticate to continue.", reply_markup=kb)
