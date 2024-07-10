import logging
import discord
from discord.ext import commands
import settings
import db.database_management as database_management

logger = logging.getLogger(__name__)

name = "Overlay Management"
version = "1.0"

extensions = [
    "cogs.slashcommands"
]

def init_database():
    if database_management.engine is not None:
        database_management.Base.metadata.create_all(database_management.engine)
        logger.info("Database initialized successfully")
    else:
        logger.error("Failed to initialize database: engine is None")

def run():
    logger.info(f"Starting up bot '{name} v{version}'")
    init_database()  # Initialize the database
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        guilds = [guild.name for guild in bot.guilds]
        logger.info(f"Connected as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Guilds ({len(bot.guilds)}). {guilds}")

        for extension in extensions:
            try:
                await bot.load_extension(extension)
                logger.info(f"Loaded extension '{extension}'")
            except commands.ExtensionAlreadyLoaded:
                logger.warning(f"Extension '{extension}' is already loaded")
            except commands.ExtensionNotFound:
                logger.error(f"Extension '{extension}' not found")
            except commands.NoEntryPointError:
                logger.error(f"Extension '{extension}' does not have a setup function")
            except commands.ExtensionFailed as e:
                logger.error(f"Extension '{extension}' failed to load: {e}")

        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)

    bot.run(settings.DISCORD_API_SECRET, reconnect=True, root_logger=True)

if __name__ == "__main__":
    run()