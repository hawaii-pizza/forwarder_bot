from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from bot.db import Database
from bot.auth import AuthManager

if TYPE_CHECKING:  # Only for type hints – avoids heavy import at runtime
    from bot.forwarding import ForwardManager

# Shared instances -----------------------------------------------------------

db: Database = Database()
auth: AuthManager = AuthManager()

# Will be created on startup in bot.entry
forwarder: Optional["ForwardManager"] = None