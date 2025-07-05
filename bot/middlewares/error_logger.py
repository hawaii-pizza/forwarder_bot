import logging
from aiogram import BaseMiddleware
logger = logging.getLogger(__name__)

class ErrorLogger(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as exc:      # noqa: BLE001
            logger.exception("Unhandled error: %s", exc)
            raise
