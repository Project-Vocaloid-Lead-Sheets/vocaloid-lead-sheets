import os
import logging
import discord
import pathlib

from discord_bot.github_client import GitHubClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

SCRIPT_DIR = pathlib.Path(__file__).parent
SEKAI_TEXT = (SCRIPT_DIR / "sekai.txt").read_text(encoding="utf-8").splitlines()
BOT_CHANNEL_NAME = "bot-terminal"


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

        # Since the GitHub client relies on aiohttp, you have to wait for the async loop to start to initialize one
        self._github: GitHubClient = None

        self._sekai_counter = 0

    def _register_events(self):
        @self._client.event
        async def on_ready():
            _logger.info(f"Logged in as {self._client.user}")
            await self._tree.sync()
            _logger.info("Slash commands synced")
            self._github = GitHubClient("Project-Vocaloid-Lead-Sheets", "vocaloid-lead-sheets", os.environ["GITHUB_TOKEN"])
            _logger.info("GitHub client initialized!")

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
            calling_user = interaction.user
            _logger.info(f"User {calling_user.display_name} ({calling_user.id}) really wants to listen to World is Mine")
            line = SEKAI_TEXT[self._sekai_counter % len(SEKAI_TEXT)]
            self._sekai_counter += 1
            await interaction.response.send_message(line)

        @group.command(name="sync", description="Sync and deploy website with updated Google Drive contents")
        async def sync(interaction: discord.Interaction):
            calling_user = interaction.user
            _logger.info(f"User {calling_user.display_name} ({calling_user.id}) started a site sync and deploy")
            await self._github.dispatch_workflow("content-sync-and-deploy.yml")
            await interaction.response.send_message("Content sync started!")


        self._tree.add_command(group)

    def run(self, token: str):
        self._client.run(token)
