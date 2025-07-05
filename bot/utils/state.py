"""
bot/utils/state.py
------------------
Tiny helper for per‑user in‑memory state machines shared across routers.
Routers can do:

    from bot.utils.state import user_state
    user_state[user_id] = "awaiting_something"

This avoids each router having its own dict if you prefer a single map.
"""
from __future__ import annotations

from typing import Dict

# Global mutable map (uid → state‑str)
user_state: Dict[int, str] = {}

WAITING_SRC    = "waiting_for_source"
WAITING_TGT    = "waiting_for_target"
WAITING_FILTER = "waiting_for_filter"

__all__ = [
    "user_state",
    "WAITING_SRC",
    "WAITING_TGT",
    "WAITING_FILTER",
]