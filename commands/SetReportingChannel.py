from discord import app_commands
from discord.ext import commands
import discord
import logging
import db.database as database

logger = logging.getLogger("bot")


class SetReportingChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="set_reporting_channel",
        description="Set the channel for reporting cheater activities.",
    )
    async def set_channel(self, interaction: discord.Interaction, channel: str):
        guild = interaction.guild

        # Check if the user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You do not have the necessary permissions to use this command.",
                ephemeral=True,
            )
            return

        # Convert the channel ID string back to an integer
        channel_id = int(channel)
        selected_channel = guild.get_channel(channel_id)

        if selected_channel is None:
            await interaction.response.send_message(
                "Channel not found. Please ensure you select a valid channel.",
                ephemeral=True,
            )
            return

        # Use DatabaseManager to add or update the server settings
        existing_settings = database.DatabaseManager.get_server_settings(
            serverid=guild.id
        )
        if existing_settings:
            database.DatabaseManager.update_server_settings(
                serverid=guild.id, channelid=channel_id
            )
            await interaction.response.send_message(
                f"Channel for server `{guild.name}` set to <#{selected_channel.id}>",
                ephemeral=True,
            )
        else:
            database.DatabaseManager.add_server_settings(
                serverid=guild.id, channelid=channel_id
            )
            await interaction.response.send_message(
                f"Channel for server `{guild.name}` changed to <#{selected_channel.id}>",
                ephemeral=True,
            )

    @set_channel.autocomplete("channel")
    async def channel_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        guild = interaction.guild
        channels = [
            app_commands.Choice(name=f"#{channel.name}", value=str(channel.id))
            for channel in guild.text_channels
            if current.lower() in channel.name.lower()
        ]
        return channels[:25]  # Discord only supports up to 25 choices


async def setup(bot):
    await bot.add_cog(SetReportingChannel(bot))
