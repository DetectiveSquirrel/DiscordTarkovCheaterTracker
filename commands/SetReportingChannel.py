import logging
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands

from db.database import DatabaseManager

logger = logging.getLogger("command")


@dataclass
class ServerSettings:
    server_id: int
    channel_id: int


class SetReportingChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="set_reporting_channel",
        description="Set the channel for reporting cheater activities.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild = interaction.guild
        settings = ServerSettings(server_id=guild.id, channel_id=channel.id)

        await self.update_server_settings(interaction, settings)

    async def update_server_settings(self, interaction: discord.Interaction, settings: ServerSettings):
        existing_settings = DatabaseManager.get_server_settings(server_id=settings.server_id)

        if existing_settings:
            DatabaseManager.update_guild_server_settings(server_id=settings.server_id, channel_id=settings.channel_id)
            message = f"Reporting channel for server `{interaction.guild.name}` updated to {interaction.guild.get_channel(settings.channel_id).mention}"
        else:
            DatabaseManager.add_guild_server_settings(server_id=settings.server_id, channel_id=settings.channel_id)
            message = f"Reporting channel for server `{interaction.guild.name}` set to {interaction.guild.get_channel(settings.channel_id).mention}"

        await interaction.response.send_message(message, ephemeral=True)

    @set_channel.error
    async def set_channel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You do not have the necessary permissions to use this command.",
                ephemeral=True,
            )
        else:
            logger.error(f"Error in set_channel command: {error}")
            await interaction.response.send_message(
                "An error occurred while processing the command. Please try again later.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(SetReportingChannel(bot))
