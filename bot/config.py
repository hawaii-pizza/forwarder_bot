import os
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
        required = ["BOT_TOKEN", "API_ID", "API_HASH"]
        missing = [k for k in required if not getattr(self, k)]
        if missing:
            raise RuntimeError(f"Missing required settings: {missing}")

settings = Settings()
settings.validate()
