import logging
import re

import discord

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

    logger.debug(f"Member {user_id} not found in guild cache, attempting to fetch from guild")
    try:
        # If not in cache, try to fetch the member from the guild
        member = await guild.fetch_member(user_id)
        logger.debug(f"Successfully fetched member {member.name} (ID: {user_id}) from guild")
        return member.mention
    except discord.errors.NotFound:
        logger.debug(f"Member {user_id} not found in guild, attempting to fetch user globally")
        try:
            # If not in the guild, try to fetch the user globally
            user = await bot.fetch_user(user_id)
            logger.debug(f"Successfully fetched user {user.name} (ID: {user_id}) globally")
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


async def send_to_report_channels(bot, server_settings, embed):
    for setting in server_settings:
        channel_id = setting.get("channel_id")
        if channel_id:
            report_channel = bot.get_channel(channel_id)
            if report_channel:
                try:
                    await report_channel.send(embed=embed, silent=True)
                    logger.info(f"Message sent to channel {channel_id}")
                except Exception as e:
                    logger.error(f"Failed to send message to channel {channel_id}: {e}")
            else:
                logger.warning(f"Could not find report channel with ID {channel_id}")
        else:
            logger.warning(f"No report channel configured for server settings: {setting}")


def is_valid_game_name(game_name):
    return re.match(r"^(?!.*\d{5})[a-zA-Z0-9_-]{3,15}$", game_name)


async def create_already_verified_embed(interaction, bot, verified_status):
    embed = discord.Embed(
        title="Player Already Verified as Legitimate",
        color=discord.Color.blue(),
    )

    first_verifier_id = verified_status["verifier_ids"][0]
    first_verification_time = verified_status["verification_times"][0]

    first_verifier_mention = await get_user_mention(interaction.guild, bot, first_verifier_id)

    embed.add_field(
        name="First Verified By",
        value=first_verifier_mention,
        inline=True,
    )
    embed.add_field(
        name="Total Verifications",
        value=f"` {str(verified_status['count'])} `",
        inline=True,
    )
    embed.add_field(
        name="First Verified Time",
        value=f"<t:{first_verification_time}>",
        inline=True,
    )

    return embed
