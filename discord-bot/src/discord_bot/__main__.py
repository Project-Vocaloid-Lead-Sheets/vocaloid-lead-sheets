import os
from discord_bot.bot_core import PvlsBotCore

def main():
    discord_bot = PvlsBotCore()
    discord_bot.run(os.environ["DISCORD_TOKEN"])

if __name__ == "__main__":
    main()
