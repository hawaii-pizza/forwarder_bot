import aiosqlite
from dataclasses import dataclass
from typing import List, Optional
from .config import settings

@dataclass
class Source:
    chat_id: int
    topic_id: Optional[int]
    title: str

@dataclass
class Target:
    chat_id: int
    topic_id: Optional[int]

class Database:
    def __init__(self):
        self._path = settings.DB_PATH
        self.conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        self.conn = await aiosqlite.connect(self._path, isolation_level=None)
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA synchronous=NORMAL")
        await self.conn.execute("PRAGMA busy_timeout=5000")  # Wait if locked
        await self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                tg_id      INTEGER PRIMARY KEY,
                filter_mode TEXT  NOT NULL DEFAULT 'all'
            );

            CREATE TABLE IF NOT EXISTS sources (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id     INTEGER NOT NULL,
                chat_id   INTEGER NOT NULL,
                topic_id  INTEGER,
                title     TEXT,
                UNIQUE(tg_id, chat_id, topic_id),
                FOREIGN KEY (tg_id) REFERENCES users(tg_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS targets (
                tg_id     INTEGER PRIMARY KEY,
                chat_id   INTEGER NOT NULL,
                topic_id  INTEGER
            );

            CREATE TABLE IF NOT EXISTS filtered_users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id       INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                display_name TEXT,
                UNIQUE(tg_id, user_id),
                FOREIGN KEY (tg_id) REFERENCES users(tg_id) ON DELETE CASCADE
            );
            """
        )
        await self.conn.commit()

    # User helpers ------------------------------------------------------------------
    async def add_user_if_missing(self, tg_id: int):
        await self.conn.execute("INSERT OR IGNORE INTO users(tg_id) VALUES (?)", (tg_id,))
        await self.conn.commit()

    async def set_filter_mode(self, tg_id: int, mode: str):
        await self.conn.execute("UPDATE users SET filter_mode=? WHERE tg_id=?", (mode, tg_id))
        await self.conn.commit()

    async def get_filter_mode(self, tg_id: int) -> str:
        cur = await self.conn.execute("SELECT filter_mode FROM users WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
        return row[0] if row else "all"

    # Source helpers ----------------------------------------------------------------
    async def add_source(self, tg_id: int, chat_id: int, topic_id: Optional[int], title: str):
        await self.conn.execute(
            """INSERT INTO sources(tg_id, chat_id, topic_id, title)
                   VALUES(?, ?, ?, ?)
                   ON CONFLICT(tg_id, chat_id, topic_id)
                   DO UPDATE SET title=excluded.title""",
            (tg_id, chat_id, topic_id, title),
        )
        await self.conn.commit()

    async def remove_source(self, tg_id: int, chat_id: int, topic_id: Optional[int]):
        await self.conn.execute(
            "DELETE FROM sources WHERE tg_id=? AND chat_id=? AND (topic_id IS ? OR topic_id=?)",
            (tg_id, chat_id, topic_id, topic_id),
        )
        await self.conn.commit()

    async def list_sources(self, tg_id: int) -> List[Source]:
        cur = await self.conn.execute(
            "SELECT chat_id, topic_id, title FROM sources WHERE tg_id=?", (tg_id,)
        )
        return [Source(*row) async for row in cur]

    # Target helpers ----------------------------------------------------------------
    async def set_target(self, tg_id: int, chat_id: int, topic_id: Optional[int]):
        await self.conn.execute(
            "INSERT INTO targets(tg_id, chat_id, topic_id) VALUES(?, ?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET chat_id=excluded.chat_id, topic_id=excluded.topic_id",
            (tg_id, chat_id, topic_id),
        )
        await self.conn.commit()

    async def get_target(self, tg_id: int) -> Optional[Target]:
        cur = await self.conn.execute(
            "SELECT chat_id, topic_id FROM targets WHERE tg_id=?", (tg_id,)
        )
        row = await cur.fetchone()
        return Target(*row) if row else None

    # Filtered users helpers ---------------------------------------------------------
    async def add_filtered_user(self, tg_id: int, user_id: int, display_name: str):
        await self.conn.execute(
            """INSERT INTO filtered_users(tg_id, user_id, display_name)
                   VALUES(?, ?, ?)
                   ON CONFLICT(tg_id, user_id)
                   DO UPDATE SET display_name=excluded.display_name""",
            (tg_id, user_id, display_name),
        )
        await self.conn.commit()

    async def remove_filtered_user(self, tg_id: int, user_id: int):
        await self.conn.execute(
            "DELETE FROM filtered_users WHERE tg_id=? AND user_id=?", (tg_id, user_id)
        )
        await self.conn.commit()

    async def list_filtered_users(self, tg_id: int) -> List[int]:
        cur = await self.conn.execute(
            "SELECT user_id FROM filtered_users WHERE tg_id=?", (tg_id,)
        )
        return [row[0] async for row in cur]