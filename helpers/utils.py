import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


async def get_user_mention(guild_or_interaction, bot, user_id: int) -> str:
    logger.debug(f"Attempting to get user mention for user_id: {user_id}")

    # Determine if we're dealing with an Interaction or a Context
    if isinstance(guild_or_interaction, discord.Interaction):
        guild = guild_or_interaction.guild
    else:  # Assume it's a Guild object
        guild = guild_or_interaction

    logger.debug(f"Guild ID: {guild.id}")

    # First, try to get the member from the guild cache
    member = guild.get_member(user_id)
    if member:
        logger.debug(f"Found member {member.name} (ID: {user_id}) in guild cache")
        return member.mention

    logger.debug(
        f"Member {user_id} not found in guild cache, attempting to fetch from guild"
    )
    try:
        # If not in cache, try to fetch the member from the guild
        member = await guild.fetch_member(user_id)
        logger.debug(
            f"Successfully fetched member {member.name} (ID: {user_id}) from guild"
        )
        return member.mention
    except discord.errors.NotFound:
        logger.debug(
            f"Member {user_id} not found in guild, attempting to fetch user globally"
        )
        try:
            # If not in the guild, try to fetch the user globally
            user = await bot.fetch_user(user_id)
            logger.debug(
                f"Successfully fetched user {user.name} (ID: {user_id}) globally"
            )
            return f"`@{user.name}`"
        except discord.errors.NotFound:
            logger.debug(f"User {user_id} not found globally")
            return f"`@Unknown User ({user_id})`"
    except discord.errors.HTTPException as e:
        # Handle potential API errors
        logger.error(f"HTTP exception when fetching user {user_id}: {str(e)}")
        return f"`@Unresolved User ({user_id})`"
    except Exception as e:
        # Catch any other unexpected exceptions
        logger.error(f"Unexpected error when fetching user {user_id}: {str(e)}")
        return f"`@Error User ({user_id})`"
