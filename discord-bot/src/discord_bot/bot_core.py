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

# For some crazy reason, Discord caps the autofill count to 25 and will just reject the command if you try to supply
# anything more than that
DISCORD_AUTOFILL_COUNT_MAX = 25


def asyncio_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, any]) -> None:
    exception = context.get("exception")
    _logger.critical("Unhandled asyncio error: %s", context.get("message", "unknown asyncio error"), exc_info=exception)


class PvlsBotCore:
    def __init__(self):
        self._client = discord.Client(intents=discord.Intents.default())
        self._tree = discord.app_commands.CommandTree(self._client)
        self._register_events()
        self._register_commands()

        self._db = Database(pathlib.Path(os.environ.get("DATABASE_PATH", "/data/discord-bot.sqlite3")))
        self._repo = Repository(self._db)

        self._sync_autofill_choices: list[str] = []

        # These resources require allocation from an async context so we can't initialize them here
        self._github: GitHubClient = None
        self._workflow_poll_task: asyncio.Task[None] | None = None
        self._sync_autocomplete_poll_task: asyncio.Task[None] | None = None

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
        await self._poll_sync_autofill_once();
        _logger.info("Autofill populated.")

        self._workflow_poll_task = asyncio.create_task(self._poll_workflows(), name="workflow-poller")
        self._sync_autofill_poll_task = asyncio.create_task(self._poll_sync_autofill(), name="sync-autofill-poller")
        _logger.info("Autofill task started!")

    def _register_events(self):
        @self._client.event
        async def on_ready():
            await self.setup_hook()

    def _register_commands(self):
        group = discord.app_commands.Group(name="pvlsbot", description="PVLS bot commands")

        @group.command(name="sekai", description="Print the lyrics to World is Mine")
        async def sekai(interaction: discord.Interaction):
            await self._do_sekai(interaction)

        @group.command(name="sync", description="Sync and deploy website with updated Google Drive contents")
        @discord.app_commands.describe(song="If specified, syncs only the song specified.")
        @discord.app_commands.autocomplete(song=self._do_sync_autocomplete)
        async def sync(interaction: discord.Interaction, song: str | None = None):
            await self._do_sync(interaction, song)

        self._tree.add_command(group)


    async def _do_sekai(self, interaction: discord.Interaction):
        user = interaction.user
        sekai_id = await self._repo.log_sekai(user.id, user.display_name)
        _logger.info(f"User {user.display_name} ({user.id}) really wants to listen to World is Mine ({sekai_id})")
        line = SEKAI_TEXT[max(0, sekai_id - 1) % len(SEKAI_TEXT)]
        await interaction.response.send_message(line)


    async def _do_sync(self, interaction: discord.Interaction, song_slug: str | None):
        user = interaction.user
        _logger.info(f"User {user.display_name} ({user.id}) started a site sync and deploy")

        inputs = {}
        if song_slug:
            if song_slug not in self._sync_autofill_choices:
                await self.send_sync_reject(interaction, song_slug)
                return

            inputs["song_slug"] = song_slug
            _logger.info(f"Targeted sync for '{song_slug}' selected.")

        workflow = await self._github.post_workflow("content-sync-and-deploy.yml", inputs=inputs)
        await self._repo.add_workflow(workflow, interaction)

        response_message = f"{user.mention} started a site content sync"
        if song_slug:
            response_message += f" for the song `{song_slug}`"
        else:
            response_message += " for ***all songs***"
        await interaction.response.send_message(response_message + f".\nGitHub Link: <{workflow.html_url}>")


    async def _do_sync_autocomplete(
        self, interaction: discord.Interaction, current_str: str
    ) -> list[discord.app_commands.Choice[str]]:
        return [
            discord.app_commands.Choice(name=song, value=song)
            for song in self._sync_autofill_choices if current_str.casefold() in song.casefold()
        ][:DISCORD_AUTOFILL_COUNT_MAX]


    async def send_sync_reject(self, interaction: discord.Interaction, song_slug: str):
        await interaction.response.send_message(f"***The song '{song_slug}' does not exist on PVLS.***", ephemeral=True)


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

    async def _poll_sync_autofill_once(self):
        generated_manifest = await self._github.download_json_at("frontend/src/data/generated-manifest.json")
        self._sync_autofill_choices = [pathlib.Path(song).stem for song in generated_manifest["songs"]]

    async def _poll_sync_autofill(self):
        while True:
            _logger.debug("Poll sync autofill options!")
            try:
                await self._poll_sync_autofill_once()
                await asyncio.sleep(30)
            except Exception as e:
                _logger.error(f"Poll failed - {e}")

    def run(self, token: str):
        self._client.run(token)
