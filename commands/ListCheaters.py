import discord
import logging
import math
from typing import List
from discord import app_commands
from discord.ext import commands
from db.database import (
    DatabaseManager,
    ReportType,
    CheaterReportFields,
    REPORT_TYPE_DISPLAY,
)
from helpers.pagination import Pagination
from helpers import utils, checks

logger = logging.getLogger("command")


class ListCheaters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def report_type_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        logger.debug(f"Report type autocomplete called with current: {current}")
        choices = [
            app_commands.Choice(name=REPORT_TYPE_DISPLAY[rt], value=rt.name)
            for rt in ReportType
            if current.lower() in REPORT_TYPE_DISPLAY[rt].lower()
        ]
        logger.debug(f"Returning {len(choices)} autocomplete choices")
        return choices

    @commands.hybrid_command(
        name="list_cheaters",
        description="List all cheaters reported.",
    )
    @app_commands.autocomplete(report_type=report_type_autocomplete)
    async def list_cheaters(self, ctx, report_type: str):
        logger.info(
            f"list_cheaters command called by {ctx.author} with report_type: {report_type}"
        )

        try:
            report_enum = ReportType[report_type]
            logger.debug(f"Parsed report type: {report_enum}")
        except KeyError:
            logger.warning(f"Invalid report type provided: {report_type}")
            await ctx.send("Invalid report type. Please try again.", ephemeral=True)
            return

        if not checks.is_guild_configured(ctx):
            logger.warning(f"Guild {ctx.guild.id} not configured")
            await ctx.send(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return

        logger.debug(f"Fetching cheater reports for type: {report_enum}")
        reports = DatabaseManager.get_cheater_reports_by_type(report_enum)

        if not reports:
            logger.info(f"No {REPORT_TYPE_DISPLAY[report_enum]} reports found")
            await ctx.send(
                f"No {REPORT_TYPE_DISPLAY[report_enum]} reports found.", ephemeral=True
            )
            return

        logger.debug(f"Processing {len(reports)} reports")
        cheater_summary = {}
        reporter_summary = {}
        for report in reports:
            cheater_id = report[CheaterReportFields.CHEATER_PROFILE_ID.value]
            from_user_id = report[CheaterReportFields.REPORTER_USER_ID.value]

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
                report[CheaterReportFields.REPORT_TIME.value]
                > cheater_summary[cheater_id]["latest_time"]
            ):
                cheater_summary[cheater_id]["latest_time"] = report[
                    CheaterReportFields.REPORT_TIME.value
                ]
                cheater_summary[cheater_id]["latest_name"] = report[
                    CheaterReportFields.CHEATER_GAME_NAME.value
                ]

            # Find the user who reported the most for this cheater
            cheater_summary[cheater_id]["reporter"] = max(
                reporter_summary[cheater_id], key=reporter_summary[cheater_id].get
            )

        logger.debug("Sorting cheater summary")
        sorted_summary = sorted(
            cheater_summary.items(), key=lambda x: x[1]["count"], reverse=True
        )

        items_per_page = 10
        pages = math.ceil(len(sorted_summary) / items_per_page)
        logger.debug(f"Calculated {pages} pages for pagination")

        async def get_page(page):
            logger.debug(f"Generating page {page} of {pages}")
            start = (page - 1) * items_per_page
            end = start + items_per_page
            current_page = sorted_summary[start:end]

            embed = discord.Embed(
                title=f"'{REPORT_TYPE_DISPLAY[report_enum]}' Reports",
                color=discord.Color.red(),
            )

            latest_names = []
            counts = []
            reporters = []

            for cheater_id, data in current_page:
                latest_names.append(
                    f"[{data['latest_name']}](https://tarkov.dev/player/{cheater_id})"
                )
                counts.append(f"({data['count']})")
                reporter_mention = await utils.get_user_mention(
                    ctx.guild, ctx.bot, data["reporter"]
                )
                reporters.append(reporter_mention)
                logger.debug(
                    f"Processed cheater: {cheater_id}, name: {data['latest_name']}, count: {data['count']}, reporter: {reporter_mention}"
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
                name="Reported Most By", value="\n".join(reporters), inline=True
            )

            embed.set_footer(text=f"Page {page} of {pages}")
            logger.debug(f"Generated embed for page {page}")
            return embed, pages

        logger.info("Creating pagination view")
        view = Pagination(ctx.interaction, get_page)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(ListCheaters(bot))
