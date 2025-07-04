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

__all__ = ["user_state"]
