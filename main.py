import asyncio
import logging
import sys
from typing import List

import discord
from discord.ext import commands

import settings
import db.database as database

logger = logging.getLogger(__name__)


EXTENSIONS = [
    "commands.ReportAPlayer",
    "commands.CheaterDetails",
    "commands.SetReportingChannel",
    "commands.ListCheaters",
]


class TarkovCheaterBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for extension in EXTENSIONS:
            await self.load_extension_safe(extension)

    async def on_ready(self):
        logger.info(f"Connected as {self.user} (ID: {self.user.id})")
        guilds = [guild.name for guild in self.guilds]
        logger.info(f"Guilds ({len(self.guilds)}): {', '.join(guilds)}")
        await self.sync_commands()

    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        await self.sync_commands(guilds=[guild])

    async def on_guild_remove(self, guild: discord.Guild):
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")

    async def load_extension_safe(self, extension: str):
        try:
            await self.load_extension(extension)
            logger.info(f"Loaded extension '{extension}'")
        except Exception as e:
            logger.error(f"Failed to load extension '{extension}': {e}")

    async def sync_commands(self, guilds: List[discord.Guild] = None):
        if guilds is None:
            guilds = self.guilds
        for guild in guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commands synced for guild: {guild.name}")


def init_database():
    if database.engine is not None:
        database.Base.metadata.create_all(database.engine)
        logger.info("Database initialized successfully")
    else:
        logger.error("Failed to initialize database: engine is None")
        sys.exit(1)


async def main():
    logger.info(f"Starting up bot '{settings.BOT_NAME} v{settings.BOT_VERSION}'")

    # Initialize the database
    init_database()

    # Create and run the bot
    bot = TarkovCheaterBot()

    try:
        await bot.start(settings.DISCORD_API_SECRET)
    except Exception as e:
        logger.error(f"An error occurred while running the bot: {e}")
        if not bot.is_closed():
            await bot.close()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot was stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
