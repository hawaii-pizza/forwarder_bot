# Telegram Forwarder Bot

This project runs a Telegram message forwarding bot.

The `docker-compose.yml` file mounts a local `data/` directory inside the
container at `/app/data` and sets `DB_PATH=/app/data/bot.db` so the SQLite
database persists across restarts.

