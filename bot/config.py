import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.environ["BOT_TOKEN"]
    API_ID: int = int(os.environ["API_ID"])
    API_HASH: str = os.environ["API_HASH"]

    DB_PATH: str = os.getenv("DB_PATH", "bot.db")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/bot.log")
    SESSION_DIR: str = os.getenv("SESSION_DIR", "sessions")

    # Runtime sanity‑checks
    def validate(self):
        missing = [k for k, v in self.__dict__.items() if v in (None, "")]
        if missing:
            raise RuntimeError(f"Missing required settings: {missing}")

settings = Settings()
settings.validate()