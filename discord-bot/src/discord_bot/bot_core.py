import os
import logging
import discord
import pathlib
import asyncio
import aiohttp

from discord_bot.github_client import GitHubClient, GitHubWorkflow
from discord_bot.db import Database
from discord_bot.repo import Repository

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

SCRIPT_DIR = pathlib.Path(__file__).parent
SEKAI_TEXT = (SCRIPT_DIR / "sekai.txt").read_text(encoding="utf-8").splitlines()
BOT_CHANNEL_NAME = "bot-terminal"


def asyncio_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, any]) -> None:
    exception = context.get("exception")
    _logger.critical("Unhandled asyncio error: %s", context.get("message", "unknown asyncio error"), exc_info=exception)


def find_bot_channel(interaction: discord.Interaction) -> discord.TextChannel | None:
    if interaction.guild is None:
        return None
    return discord.utils.get(interaction.guild.text_channels, name=BOT_CHANNEL_NAME)


class WrongChannel(discord.app_commands.CheckFailure):
    pass


class PVLSGroup(discord.app_commands.Group):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        channel_ok = interaction.channel is not None and interaction.channel.id == find_bot_channel(interaction).id
        if not channel_ok:
            raise WrongChannel()
        return channel_ok

class PvlsBotCore:
    def __init__(self):
        self._client = discord.Client(intents=discord.Intents.default())
        self._tree = discord.app_commands.CommandTree(self._client)
        self._register_events()
        self._register_commands()

        self._db = Database(pathlib.Path(os.environ.get("DATABASE_PATH", "/data/discord-bot.sqlite3")))
        self._repo = Repository(self._db)

        # These resources require allocation from an async context so we can't initialize them here
        self._github: GitHubClient = None
        self._workflow_poll_task: asyncio.Task[None] | None = None

    async def setup_hook(self):
        # I hate how asyncio fails silently. Asyncio is the scourge of modern computing but unironically a good option
        asyncio.get_running_loop().set_exception_handler(asyncio_exception_handler)

        _logger.info(f"Logged in as {self._client.user}")
        await self._tree.sync()
        _logger.info("Slash commands synced!")

        self._github = GitHubClient("Project-Vocaloid-Lead-Sheets", "vocaloid-lead-sheets", os.environ["GITHUB_TOKEN"])
        repo_hash = await self._github.get_branch_sha()
        _logger.info(f"GitHub client initialized - main hash: {repo_hash}")

        await self._db.start()

        self._workflow_poll_task = asyncio.create_task(self._poll_workflows(), name="workflow-poller")
        _logger.info("Polling task started!")


    def _register_events(self):
        @self._client.event
        async def on_ready():
            await self.setup_hook()

        @self._tree.error
        async def on_error(interaction, error):
            if isinstance(error, WrongChannel):
                bot_channel = find_bot_channel(interaction)
                await interaction.response.send_message(f"Please run bot commands in {bot_channel.mention}.", ephemeral=True)
            return

    def _register_commands(self):
        group = PVLSGroup(name="pvlsbot", description="PVLS bot commands")

        @group.command(name="sekai", description="Print the lyrics to World is Mine")
        async def sekai(interaction: discord.Interaction):
            await self._do_sekai(interaction)

        @group.command(name="sync", description="Sync and deploy website with updated Google Drive contents")
        async def sync(interaction: discord.Interaction):
            await self._do_sync(interaction)

        self._tree.add_command(group)


    async def _do_sekai(self, interaction: discord.Interaction):
        user = interaction.user
        sekai_id = await self._repo.log_sekai(user.id, user.display_name)
        _logger.info(f"User {user.display_name} ({user.id}) really wants to listen to World is Mine ({sekai_id})")
        line = SEKAI_TEXT[max(0, sekai_id - 1) % len(SEKAI_TEXT)]
        await interaction.response.send_message(line)


    async def _do_sync(self, interaction: discord.Interaction):
        user = interaction.user
        _logger.info(f"User {user.display_name} ({user.id}) started a site sync and deploy")
        workflow = await self._github.post_workflow("content-sync-and-deploy.yml")
        await self._repo.add_workflow(workflow, interaction)

        await interaction.response.send_message(
            f"{user.mention} started a site content sync.\n"
            f"GitHub Link: <{workflow.html_url}>"
        )

    async def send_sync_response_message(self, workflow: GitHubWorkflow):
        channel = await self._client.fetch_channel(workflow.channel_id)
        after_sync_hash = await self._github.get_branch_sha()
        before_sync_hash = workflow.git_sha
        _logger.info("Compare hashes:")
        _logger.info(f"    Before: {before_sync_hash}")
        _logger.info(f"     After: {after_sync_hash}")

        message_header = f"Sync status: **{workflow.status}**. "
        message = ""
        diff_discovered = False
        if before_sync_hash != after_sync_hash:
            changed_files = await self._github.get_diff_file_list(before_sync_hash, after_sync_hash)
            changed_songs_meta_paths = [
                path for path in changed_files
                if (p := pathlib.PurePosixPath(path)).suffix == ".json"
                and p.parent == pathlib.PurePosixPath("frontend/src/data")
                and p.name != "generated-manifest.json"
            ]

            for song_meta_path in changed_songs_meta_paths:
                keys = ["Vocals", "Bb", "C", "Eb", "F", "G", "Alto", "Bass"]

                old_checksums = { key: "" for key in keys }
                try:
                    old_meta = await self._github.download_json_at(song_meta_path, before_sync_hash)
                    old_pdf_checksums = old_meta.get("pdfChecksums", {})
                except aiohttp.ClientResponseError as e:
                    if e.status != 404:
                        raise e
                    _logger.info(f"{song_meta_path} - Old JSON doesn't exist, assuming it was newly created")

                new_meta = await self._github.download_json_at(song_meta_path, after_sync_hash)
                new_checksums = new_meta.get("pdfChecksums", {})

                changed_transpositions = []
                for key in keys:
                    if new_checksums.get(key, "") != old_checksums.get(key, ""):
                        changed_transpositions.append(key)

                update_line = f"- {new_meta['title']}: ({', '.join(changed_transpositions)})\n"
                message += update_line
                _logger.info(update_line)
                diff_discovered = True

        if diff_discovered:
            message_header += "The following songs were updated:\n"
        else:
            message_header += "All songs up to date!\n"

        await channel.send(message_header + message)


    async def _poll_workflows_once(self) -> None:
        workflows = await self._repo.get_active_workflows()
        for workflow in workflows:
            status = await self._github.get_workflow_status(workflow.run_id)
            if status.status == "completed":
                _logger.info(f"Job {workflow.run_id} finished with status {status.conclusion}")
                await self._repo.mark_run_completed(workflow.run_id, conclusion=status.conclusion or "unknown")
                workflow.status = status.status
                await self.send_sync_response_message(workflow)

            else:
                _logger.info(f"Job {workflow.run_id} still running...")

    async def _poll_workflows(self):
        while True:
            _logger.debug("Poll all workflows!")
            try:
                await self._poll_workflows_once()
                await asyncio.sleep(3)
            except Exception as e:
                _logger.error(f"Poll failed - {e}")


    def run(self, token: str):
        self._client.run(token)
