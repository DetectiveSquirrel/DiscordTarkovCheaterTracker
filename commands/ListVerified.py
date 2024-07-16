import logging
import math
from typing import Dict, List, Tuple

import discord
from discord.ext import commands

from db.database import DatabaseManager, VerifiedLegitFields
from helpers import checks, utils
from helpers.pagination import Pagination

logger = logging.getLogger("command")


class VerifiedUser:
    def __init__(self, user_id: str, game_name: str, verified_by: str, verified_time: float):
        self.user_id = user_id
        self.game_name = game_name
        self.verified_by = verified_by
        self.verified_time = verified_time


class UserSummary:
    def __init__(self):
        self.latest_name = ""
        self.verified_count = 0
        self.first_verified_by = ""
        self.first_verified_time = float("inf")
        self.latest_verified_time = 0

    def update(self, user: VerifiedUser):
        self.verified_count += 1
        if user.verified_time < self.first_verified_time:
            self.first_verified_time = user.verified_time
            self.first_verified_by = user.verified_by
        if user.verified_time > self.latest_verified_time:
            self.latest_name = user.game_name
            self.latest_verified_time = user.verified_time


class ListVerified(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="list_verified",
        description="List all verified users.",
    )
    async def list_verified(self, ctx):
        logger.info(f"list_verified command called by {ctx.author}")

        if not await self.check_guild_configuration(ctx):
            return

        verified_users = await self.fetch_verified_users()
        if not verified_users:
            await ctx.send("No verified users found.", ephemeral=True)
            return

        user_summary = self.process_verified_users(verified_users)
        sorted_summary = self.sort_user_summary(user_summary)
        await self.display_pagination(ctx, sorted_summary)

    async def check_guild_configuration(self, ctx) -> bool:
        if not checks.is_guild_id_configured(ctx.guild.id):
            logger.warning(f"Guild {ctx.guild.id} not configured")
            await ctx.send(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return False
        return True

    async def fetch_verified_users(self) -> List[VerifiedUser]:
        logger.debug("Fetching verified users")
        try:
            db_users = DatabaseManager.get_all_verified_users()
            logger.debug(f"Retrieved {len(db_users)} verified users")
            return [
                VerifiedUser(
                    user[VerifiedLegitFields.TARKOV_PROFILE_ID.value],
                    user[VerifiedLegitFields.TARKOV_GAME_NAME.value],
                    user[VerifiedLegitFields.VERIFIER_USER_ID.value],
                    user[VerifiedLegitFields.VERIFIED_TIME.value],
                )
                for user in db_users
            ]
        except Exception as e:
            logger.error(f"An error occurred while retrieving verified users: {e}")
            return []

    def process_verified_users(self, verified_users: List[VerifiedUser]) -> Dict[str, UserSummary]:
        logger.debug(f"Processing {len(verified_users)} verified users")
        user_summary = {}
        for user in verified_users:
            if user.user_id not in user_summary:
                user_summary[user.user_id] = UserSummary()
            user_summary[user.user_id].update(user)
        return user_summary

    def sort_user_summary(self, user_summary: Dict[str, UserSummary]) -> List[Tuple[str, UserSummary]]:
        logger.debug("Sorting user summary")
        return sorted(user_summary.items(), key=lambda x: x[1].verified_count, reverse=True)

    async def display_pagination(self, ctx, sorted_summary: List[Tuple[str, UserSummary]]):
        items_per_page = 10
        pages = math.ceil(len(sorted_summary) / items_per_page)
        logger.debug(f"Calculated {pages} pages for pagination")

        async def get_page(page):
            logger.debug(f"Generating page {page} of {pages}")
            start = (page - 1) * items_per_page
            end = start + items_per_page
            current_page = sorted_summary[start:end]

            embed = discord.Embed(title="Verified Users", color=discord.Color.green())
            latest_names, verified_counts, first_verified_by = [], [], []

            for user_id, data in current_page:
                latest_names.append(f"[{data.latest_name}](https://tarkov.dev/player/{user_id})")
                verified_counts.append(f"` {data.verified_count} `")
                verifier_mention = await utils.get_user_mention(data.first_verified_by)
                first_verified_by.append(f"{verifier_mention} <t:{int(data.first_verified_time)}:R>")

            embed.add_field(name="Latest Game Name", value="\n".join(latest_names), inline=True)
            embed.add_field(name="Times Verified", value="\n".join(verified_counts), inline=True)
            embed.add_field(name="First Verified By", value="\n".join(first_verified_by), inline=True)
            logger.debug(f"Generated embed for page {page}")
            return embed, pages

        logger.info("Creating pagination view")
        view = Pagination(ctx.interaction, get_page, timeout=60, delete_on_timeout=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(ListVerified(bot))
