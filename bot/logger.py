import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .config import settings

Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

handler = RotatingFileHandler(settings.LOG_FILE, maxBytes=2_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))

logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("bot")