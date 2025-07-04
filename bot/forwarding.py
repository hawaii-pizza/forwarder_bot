"""Per‑user forwarding engine. A single Telethon client instance per user, kept
alive as long as the user is authenticated and has at least one source + target."""
from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Tuple

from telethon import events, TelegramClient
from telethon.tl.custom import Message

from .db import Database, Source, Target
from .auth import AuthManager
from .utils import contains_token_related

log = logging.getLogger(__name__)


class ForwardManager:
    def __init__(self, db: Database, auth: AuthManager):
        self.db = db
        self.auth = auth
        # Keep track of the live TelegramClient and its run task per user
        self._clients: Dict[int, Tuple[TelegramClient, asyncio.Task]] = {}

    # ----------------------------- public API ---------------------------------
    async def refresh_user(self, tg_id: int):
        """(Re)start the forwarder task for a user if they have valid config."""
        if tg_id in self._clients:
            await self.stop_user(tg_id)

        sources = await self.db.list_sources(tg_id)
        target  = await self.db.get_target(tg_id)
        if not sources or not target:
            return  # nothing to do yet

        client = self.auth.client(tg_id)
        await client.start()

        filter_mode = await self.db.get_filter_mode(tg_id)
        filtered_ids = await self.db.list_filtered_users(tg_id)

        async def _handler(event: events.NewMessage.Event):
            msg: Message = event.message

            # 1️⃣ Optional user‑ID filter
            if filtered_ids and (msg.from_id is None or msg.from_id.user_id not in filtered_ids):
                return

            # 2️⃣ Content filter
            if filter_mode != "all" and not contains_token_related(msg.raw_text):
                return

            try:
                await client.forward_messages(
                    entity=(target.chat_id, target.topic_id) if target.topic_id else target.chat_id,
                    messages=msg,
                )
                log.info("Message forwarded for %s", tg_id)
            except Exception as e:
                log.warning("Forward failed for %s: %s", tg_id, e)

        for src in sources:
            chat = (src.chat_id, src.topic_id) if src.topic_id else src.chat_id
            client.add_event_handler(_handler, events.NewMessage(chats=chat))

        task = asyncio.create_task(client.run_until_disconnected())
        self._clients[tg_id] = (client, task)
        log.info("Forward loop started for %s", tg_id)

    async def stop_user(self, tg_id: int):
        entry = self._clients.pop(tg_id, None)
        if not entry:
            return
        client, task = entry
        if client.is_connected():
            await client.disconnect()
        if task and not task.done():
            task.cancel()
        log.info("Forward loop stopped for %s", tg_id)

    async def stop_all(self):
        for uid in list(self._clients.keys()):
            await self.stop_user(uid)
