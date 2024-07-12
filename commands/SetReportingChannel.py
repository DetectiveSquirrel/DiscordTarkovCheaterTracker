from discord import app_commands
from discord.ext import commands
import discord
import logging
from db.database import DatabaseManager, ServerSettingsFields

logger = logging.getLogger("command")


class SetReportingChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="set_reporting_channel",
        description="Set the channel for reporting cheater activities.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        guild = interaction.guild

        # Use DatabaseManager to add or update the server settings
        existing_settings = DatabaseManager.get_server_settings(server_id=guild.id)
        if existing_settings:
            DatabaseManager.update_server_settings(
                server_id=guild.id, channel_id=channel.id
            )
            await interaction.response.send_message(
                f"Reporting channel for server `{guild.name}` updated to {channel.mention}",
                ephemeral=True,
            )
        else:
            DatabaseManager.add_server_settings(
                server_id=guild.id, channel_id=channel.id
            )
            await interaction.response.send_message(
                f"Reporting channel for server `{guild.name}` set to {channel.mention}",
                ephemeral=True,
            )

    @set_channel.error
    async def set_channel_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
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
