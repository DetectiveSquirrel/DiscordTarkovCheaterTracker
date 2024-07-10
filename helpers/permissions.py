from discord.ext import commands


async def check_permissions_and_hierarchy(ctx: commands.Context, role_ids: list):
    guild = ctx.guild
    bot_member = guild.get_member(ctx.bot.user.id)

    # Check if bot has manage roles permission
    if not bot_member.guild_permissions.manage_roles:
        await ctx.send("I do not have permission to manage roles.", ephemeral=True)
        return False

    # Check role hierarchy
    bot_highest_role = bot_member.top_role
    for role_id in role_ids:
        role = guild.get_role(role_id)
        if role and bot_highest_role <= role:
            await ctx.send(
                "I cannot manage roles that are higher or equal to my highest role.",
                ephemeral=True,
            )
            return False

    return True
