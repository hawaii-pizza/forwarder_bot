import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .config import settings

Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

handler = RotatingFileHandler(settings.LOG_FILE, maxBytes=2_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))

logging.basicConfig(level=logging.INFO, handlers=[handler])
logging.getLogger("aiogram.dispatcher").setLevel(logging.DEBUG)
logging.getLogger("telethon").setLevel(logging.INFO)
logger = logging.getLogger("bot")
