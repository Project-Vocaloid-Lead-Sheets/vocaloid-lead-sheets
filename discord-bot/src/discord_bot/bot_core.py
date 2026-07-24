import logging
import discord
import pathlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

SCRIPT_DIR = pathlib.Path(__file__).parent
SEKAI_TEXT = (SCRIPT_DIR / "sekai.txt").read_text(encoding="utf-8")
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
        self.client = discord.Client(intents=discord.Intents.default())
        self.tree = discord.app_commands.CommandTree(self.client)
        self._register_events()
        self._register_commands()

    def _register_events(self):
        @self.client.event
        async def on_ready():
            _logger.info(f"Logged in as {self.client.user}")
            await self.tree.sync()
            _logger.info("Slash commands synced")

        @self.tree.error
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
            await interaction.response.send_message(SEKAI_TEXT)

        self.tree.add_command(group)

    def run(self, token: str):
        self.client.run(token)
