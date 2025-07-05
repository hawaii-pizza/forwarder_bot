"""Logging utilities for the bot package."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import settings


def configure_logging() -> None:
    """Configure root logging with both file and console handlers."""
    root = logging.getLogger()
    if root.handlers:
        return  # already configured

    Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=2_000_000,
        backupCount=5,
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


logger = logging.getLogger("bot")
