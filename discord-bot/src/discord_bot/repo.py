import logging

import discord

from discord_bot.db import Database
from discord_bot.github_client import GitHubWorkflow

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

class Repository:
    def __init__(self, db: Database):
        self._db = db

    async def log_sekai(self, user_id: int, display_name: str) -> int:
        sekai_idx = await self._db.pool.fetchval(
            """
            INSERT INTO sekai_log
                (discord_user_id, discord_user_display_name)
            VALUES ($1, $2)
            RETURNING id
            """,
            user_id, display_name
        )
        return sekai_idx

    async def add_workflow(self, workflow: GitHubWorkflow, interaction: discord.Interaction):
        await self._db.pool.execute(
            """
            INSERT INTO github_workflow_runs
                (github_run_id, github_run_url, discord_user_id, discord_channel_id)
            VALUES ($1, $2, $3, $4)
            """,
            workflow.run_id, workflow.html_url, interaction.user.id, interaction.channel_id
        )

