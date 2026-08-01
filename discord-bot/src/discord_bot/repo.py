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
        cursor = await self._db.connection.execute(
            """
            INSERT INTO sekai_log
                (discord_user_id, discord_user_display_name)
            VALUES (?, ?)
            RETURNING id
            """,
            (user_id, display_name)
        )

        row = await cursor.fetchone()
        await cursor.close()
        await self._db.connection.commit()
        if row is None:
            raise RuntimeError("INSERT did not return a sekai_log ID")

        return row["id"]

    async def add_workflow(self, workflow: GitHubWorkflow, interaction: discord.Interaction):
        if interaction.channel_id is None:
            raise ValueError("Interaction did not originate in a channel")

        await self._db.connection.execute(
            """
            INSERT INTO github_workflow_runs
                (github_run_id, github_run_url, git_sha, discord_user_id, discord_channel_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (workflow.run_id, workflow.html_url, workflow.git_sha, interaction.user.id, interaction.channel_id),
        )
        await self._db.connection.commit()

    async def get_active_workflows(self) -> list[GitHubWorkflow]:
        async with self._db.connection.execute(
            """
            SELECT
                github_run_id, github_run_url, git_sha, discord_channel_id
            FROM github_workflow_runs
            WHERE conclusion IS NULL
            ORDER BY requested_at
            """
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            GitHubWorkflow(
                run_id=row["github_run_id"],
                html_url=row["github_run_url"],
                git_sha=row["git_sha"],
                channel_id=row["discord_channel_id"],
                status=None,
                conclusion=None,
            )
            for row in rows
        ]

    async def mark_run_completed(self, github_run_id: int, conclusion: str):
        cursor = await self._db.connection.execute(
            """
            UPDATE github_workflow_runs
            SET conclusion = ?, completed_at = CURRENT_TIMESTAMP
            WHERE github_run_id = ?
            AND conclusion IS NULL
            """,
            (conclusion, github_run_id),
        )
        await cursor.close()
        await self._db.connection.commit()

        if cursor.rowcount == 0:
            raise LookupError(f"No active workflow found for GitHub run {github_run_id}")
