import logging

from discord_bot.db import Database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

class Repository:
    def __init__(self, db: Database):
        self._db = db

    async def log_sekai(self, user_id: int, display_name: str) -> int:
        sekai_idx = await self._db.pool.fetchval(
            "INSERT INTO sekai_log (discord_user_id, discord_user_display_name) VALUES ($1, $2) RETURNING id",
            user_id, display_name
        )
        return sekai_idx

