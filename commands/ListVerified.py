import logging
import math

import discord
from discord.ext import commands

from db.database import DatabaseManager
from helpers import checks, utils
from helpers.pagination import Pagination

logger = logging.getLogger("command")


class ListVerified(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="list_verified",
        description="List all verified users.",
    )
    async def list_verified(self, ctx):
        logger.info(f"list_verified command called by {ctx.author}")

        if not checks.is_guild_configured(ctx):
            logger.warning(f"Guild {ctx.guild.id} not configured")
            await ctx.send(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return

        logger.debug("Fetching verified users")
        try:
            verified_users = DatabaseManager.get_all_verified_users()
            logger.debug(f"Retrieved {len(verified_users)} verified users")
        except Exception as e:
            logger.error(f"Error fetching verified users: {e}")
            await ctx.send(
                "An error occurred while fetching verified users. Please try again later.",
                ephemeral=True,
            )
            return

        if not verified_users:
            logger.info("No verified users found")
            await ctx.send("No verified users found.", ephemeral=True)
            return

        logger.debug("Processing verified users")
        sorted_users = sorted(verified_users, key=lambda x: x["verified_time"], reverse=True)

        items_per_page = 10
        pages = math.ceil(len(sorted_users) / items_per_page)
        logger.debug(f"Calculated {pages} pages for pagination")

        async def get_page(page):
            logger.debug(f"Generating page {page} of {pages}")
            start = (page - 1) * items_per_page
            end = start + items_per_page
            current_page = sorted_users[start:end]

            embed = discord.Embed(
                title="Verified Users",
                color=discord.Color.green(),
            )

            tarkov_names = []
            twitch_names = []
            verifiers = []

            for user in current_page:
                tarkov_names.append(f"[{user['tarkov_game_name']}](https://tarkov.dev/player/{user['tarkov_profile_id']})")
                twitch_names.append(f"[{user['twitch_name']}](https://twitch.tv/{user['twitch_name']})" if user["twitch_name"] else "N/A")
                verifier_mention = await utils.get_user_mention(ctx.guild, ctx.bot, user["verifier_user_id"])
                verifiers.append(f"{verifier_mention} <t:{user['verified_time']}:R>")
                logger.debug(f"Processed user: {user['tarkov_game_name']}, twitch: {user['twitch_name']}, verifier: {verifier_mention}")

            embed.add_field(name="Tarkov Name", value="\n".join(tarkov_names), inline=True)
            embed.add_field(name="Twitch Name", value="\n".join(twitch_names), inline=True)
            embed.add_field(name="Verified By", value="\n".join(verifiers), inline=True)

            logger.debug(f"Generated embed for page {page}")
            return embed, pages

        logger.info("Creating pagination view")
        view = Pagination(ctx.interaction, get_page, timeout=60, delete_on_timeout=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(ListVerified(bot))
