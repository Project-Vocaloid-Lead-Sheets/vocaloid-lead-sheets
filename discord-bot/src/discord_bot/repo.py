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

    async def get_active_workflows(self) -> list[GitHubWorkflow]:
        rows = await self._db.pool.fetch(
            """
            SELECT
                github_run_id, github_run_url, discord_channel_id
            FROM github_workflow_runs
            WHERE conclusion IS NULL
            ORDER BY requested_at
            """
        )

        return [
            GitHubWorkflow(
                run_id=row["github_run_id"],
                html_url=row["github_run_url"],
                channel_id=row["discord_channel_id"],
                status=None,
                conclusion=None,
            )
            for row in rows
        ]



    async def mark_run_completed(self, github_run_id: int, conclusion: str):
        await self._db.pool.execute(
            """
            UPDATE github_workflow_runs
            SET
                conclusion = $2,
                completed_at = now()
            WHERE github_run_id = $1
            """,
            github_run_id, conclusion,
        )
