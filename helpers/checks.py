from discord.ext import commands
import settings


async def same_server_as_requester(ctx: commands.Context):
    return ctx.guild.id == settings.BASE_SERVER_ID.id
