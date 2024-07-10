from discord.ext import commands
import logging
import db.database as database

logger = logging.getLogger("bot")


class SetReportingChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="set_reporting_channel",
        description="Set the channel for reporting cheater activities.",
    )
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_id: str):
        guild = ctx.guild
        channel_id_int = int(channel_id)
        channel = guild.get_channel(channel_id_int)

        # Use DatabaseManager to add or update the server settings
        existing_settings = database.DatabaseManager.get_server_settings(
            serverid=guild.id
        )
        if existing_settings:
            database.DatabaseManager.update_server_settings(
                serverid=guild.id, channelid=channel_id_int
            )
            await ctx.send(
                f"Channel for server `{guild.name}` set to <#{channel.id}>",
                ephemeral=True,
            )
        else:
            database.DatabaseManager.add_server_settings(
                serverid=guild.id, channelid=channel_id_int
            )
            await ctx.send(
                f"Channel for server `{guild.name}` changed to <#{channel.id}>",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(SetReportingChannel(bot))
