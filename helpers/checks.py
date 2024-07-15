from discord.ext import commands

import db.database
import settings


async def same_server_as_requester(ctx: commands.Context):
    return ctx.guild.id == settings.BASE_SERVER_ID.id


def is_guild_configured(ctx):
    server_settings = db.database.DatabaseManager.get_server_settings(ctx.guild.id)
    return server_settings is not None


def is_guild_configured(interaction):
    server_settings = bool(db.database.DatabaseManager.get_server_settings(interaction.guild.id))
    return server_settings is not None


def is_guild_configured(guild_id):
    server_settings = bool(db.database.DatabaseManager.get_server_settings(guild_id))
    return server_settings is not None


def is_guild_id_configured(guild_id: int):
    server_settings = db.database.DatabaseManager.get_server_settings(guild_id)
    return server_settings is not None
