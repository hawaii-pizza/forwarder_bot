"""Handles QR-code + (optional) 2FA login for an individual user."""
from __future__ import annotations

import asyncio
import io
from pathlib import Path
from typing import Dict, Tuple

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from bot.config import settings
from bot.logger import logger


class AuthManager:
    """
    One live Telethon client per user; manages QR login & 2FA.

    _pending  – client waiting for the user to enter 2-FA password
    _active   – fully authorised client you can reuse any time
    _qr_event – asyncio.Event we set when QR is scanned / 2-FA required
    """

    _pending: Dict[int, TelegramClient] = {}
    _active: Dict[int, TelegramClient] = {}
    _qr_event: Dict[int, asyncio.Event] = {}

    # ------------------------------------------------------------------ #
    # helpers                                                            #
    # ------------------------------------------------------------------ #

    def _session_path(self, uid: int) -> str:
        Path(settings.SESSION_DIR).mkdir(exist_ok=True)
        return f"{settings.SESSION_DIR}/{uid}"

    def _new_client(self, uid: int) -> TelegramClient:
        """Create a *disconnected* Telethon client for this user."""
        return TelegramClient(
            self._session_path(uid), settings.API_ID, settings.API_HASH
        )

    # ------------------------------------------------------------------ #
    # public API                                                         #
    # ------------------------------------------------------------------ #

    async def start_login(self, uid: int) -> Tuple[TelegramClient, io.BytesIO]:
        """
        Begin QR login and return (connected client, qr.png BytesIO).

        The connected client is cached in _pending until the user
        finishes 2-factor verification.
        """
        client = self._new_client(uid)
        await client.connect()
        qr_login = await client.qr_login()

        # Render QR
        img = qrcode.make(qr_login.url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        # Event to unblock aiogram handler once the QR is scanned
        ev = asyncio.Event()
        self._qr_event[uid] = ev
        self._pending[uid] = client

        async def _waiter() -> None:
            try:
                await qr_login.wait()                      # blocks here
            except SessionPasswordNeededError:
                logger.info("User %s requires 2FA password", uid)
            except Exception as exc:
                logger.error("QR wait error for %s: %s", uid, exc)
            finally:
                ev.set()

        asyncio.create_task(_waiter())
        return client, buf

    async def wait_complete(self, uid: int) -> None:
        ev = self._qr_event.get(uid)
        if ev:
            await ev.wait()
            self._qr_event.pop(uid, None)

    async def finish_with_password(
        self, uid: int, pwd: str
    ) -> Tuple[bool, TelegramClient]:
        """
        Complete 2-factor verification.

        Returns:
            (ok, client) – ok=True if password was accepted,
            client is the live authorised TelegramClient.
        """
        client = self._pending.pop(uid, None) or self._active.get(uid) or self._new_client(uid)

        if not client.is_connected():
            await client.connect()

        try:
            await client.sign_in(password=pwd)
            logger.info("User %s passed 2FA", uid)
            self._active[uid] = client          # promote to active cache
            return True, client
        except Exception as exc:
            logger.warning("2FA login failed for %s: %s", uid, exc)
            return False, client

    async def session_is_authorized(self, uid: int) -> bool:
        """
        Tell if the saved session on disk is already logged in.

        Reuses the in-memory client if we have one; otherwise opens
        the session *once* (read-only) and keeps it open in _active
        so we never fight over the SQLite lock.
        """
        client = self._active.get(uid) or self._new_client(uid)

        if not client.is_connected():
            # *Once* per process – afterwards we leave it connected
            try:
                await client.connect()
            except Exception as exc:
                logger.warning("Could not connect session for %s: %s", uid, exc)
                return False

        self._active[uid] = client
        return await client.is_user_authorized()
