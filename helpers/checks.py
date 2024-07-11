from discord.ext import commands
import settings
import db.database


async def same_server_as_requester(ctx: commands.Context):
    return ctx.guild.id == settings.BASE_SERVER_ID.id


def is_guild_configured(ctx):
    server_settings = db.database.DatabaseManager.get_server_settings()
    return any(setting.get("serverid") == ctx.guild.id for setting in server_settings)


def is_guild_id_configured(guild_id: int):
    server_settings = db.database.DatabaseManager.get_server_settings()
    return any(setting.get("serverid") == guild_id for setting in server_settings)
