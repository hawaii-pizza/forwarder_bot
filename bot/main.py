from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import qrcode
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from bot.config import settings
from bot.logger import logger


class AuthManager:
    """One Telethon client per user; manages QR login & 2FA."""

    _active_qr: Dict[int, asyncio.Event] = {}

    # ---------------------------------------------------------------------
    # Low‑level helpers
    # ---------------------------------------------------------------------

    def _session_path(self, uid: int) -> str:
        Path(settings.SESSION_DIR).mkdir(exist_ok=True)
        return f"{settings.SESSION_DIR}/{uid}"

    def client(self, uid: int) -> TelegramClient:
        return TelegramClient(self._session_path(uid), settings.API_ID, settings.API_HASH)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    async def start_login(self, uid: int) -> Tuple[TelegramClient, io.BytesIO]:
        """Begin QR login and return (client, qr.png BytesIO)."""
        client = self.client(uid)
        await client.connect()
        qr_login = await client.qr_login()

        img = qrcode.make(qr_login.url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        # Event to unblock handler once QR is scanned or password needed
        ev = asyncio.Event()
        self._active_qr[uid] = ev

        async def _waiter():
            try:
                await qr_login.wait()
                # Reached either authorized state or 2FA password prompt
            except SessionPasswordNeededError:
                # Expected path when 2‑step verification is enabled
                logger.info("User %s requires 2FA password", uid)
            except Exception as exc:
                logger.error("QR wait error for %s: %s", uid, exc)
            finally:
                # Always release waiter so router can continue
                ev.set()

        asyncio.create_task(_waiter())
        return client, buf

    async def wait_complete(self, uid: int):
        ev = self._active_qr.get(uid)
        if ev:
            await ev.wait()
            self._active_qr.pop(uid, None)

    async def finish_with_password(self, uid: int, client: TelegramClient, pwd: str) -> bool:
        try:
            await client.sign_in(password=pwd)
            logger.info("User %s passed 2FA", uid)
            return True
        except Exception as exc:
            logger.warning("2FA login failed for %s: %s", uid, exc)
            return False
