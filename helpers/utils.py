from discord.ext import commands
import discord


async def get_user_mention(guild, bot, user_id):
    user = guild.get_member(user_id)
    if user:
        return f"<@{user_id}>"
    else:
        try:
            user = await guild.fetch_member(user_id)
            return f"<@{user_id}>"
        except discord.NotFound:
            try:
                user = await bot.fetch_user(user_id)
                return f"@{user.name}"
            except discord.NotFound:
                return f"@Unknown User"
