from discord.ext import commands
import discord
import logging
import db.database as database
from helpers.pagination import Pagination
import helpers.utils
import math

logger = logging.getLogger("bot")


class ListCheatersKilled(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="list_cheaters_killed",
        description="List all cheaters reported MURDERED!.",
    )
    # @commands.cooldown(3, 30, commands.BucketType.guild)
    async def list_cheaters_killed(self, ctx):
        reports = database.DatabaseManager.get_cheater_reports(
            table=database.DatabaseEnum.TABLE_CHEATERS_KILLED
        )

        if not reports:
            await ctx.send("No cheater death reports found.", ephemeral=True)
            return

        cheater_summary = {}
        reporter_summary = {}
        for report in reports:
            cheater_id = report[database.DatabaseEnum.CHEATER_PROFILE_ID.value]
            from_user_id = report[database.DatabaseEnum.FROM_USER_ID.value]

            if cheater_id not in cheater_summary:
                cheater_summary[cheater_id] = {
                    "count": 0,
                    "latest_name": "",
                    "latest_time": 0,
                    "reporter": "",
                }
                reporter_summary[cheater_id] = {}

            cheater_summary[cheater_id]["count"] += 1

            if from_user_id not in reporter_summary[cheater_id]:
                reporter_summary[cheater_id][from_user_id] = 0
            reporter_summary[cheater_id][from_user_id] += 1

            if (
                report[database.DatabaseEnum.TIME_REPORTED.value]
                > cheater_summary[cheater_id]["latest_time"]
            ):
                cheater_summary[cheater_id]["latest_time"] = report[
                    database.DatabaseEnum.TIME_REPORTED.value
                ]
                cheater_summary[cheater_id]["latest_name"] = report[
                    database.DatabaseEnum.CHEATERS_GAME_NAME.value
                ]

            # Find the user who reported the most for this cheater
            cheater_summary[cheater_id]["reporter"] = max(
                reporter_summary[cheater_id], key=reporter_summary[cheater_id].get
            )

        sorted_summary = sorted(
            cheater_summary.items(), key=lambda x: x[1]["count"], reverse=True
        )

        items_per_page = 10
        pages = math.ceil(len(sorted_summary) / items_per_page)

        async def get_page(page):
            start = (page - 1) * items_per_page
            end = start + items_per_page
            current_page = sorted_summary[start:end]

            embed = discord.Embed(
                title="Murdered Cheater Reports", color=discord.Color.red()
            )

            latest_names = []
            counts = []
            reporters = []

            for cheater_id, data in current_page:
                latest_names.append(
                    f"[{data['latest_name']}](https://tarkov.dev/player/{cheater_id})"
                )
                counts.append(f"({data['count']})")
                reporters.append(
                    await helpers.utils.get_user_mention(
                        ctx.guild, ctx.bot, data["reporter"]
                    )
                )

            embed.add_field(
                name="Last Reported Name", value="\n".join(latest_names), inline=True
            )
            embed.add_field(
                name="Times Reported",
                value="\n".join(counts),
                inline=True,
            )
            embed.add_field(
                name="Killed Most By", value="\n".join(reporters), inline=True
            )

            embed.set_footer(text=f"Page {page} of {pages}")
            return embed, pages

        view = Pagination(ctx.interaction, get_page)
        await view.navigate()


async def setup(bot):
    await bot.add_cog(ListCheatersKilled(bot))
