import logging
import math
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from db.database import (
    REPORT_TYPE_DISPLAY,
    CheaterReportFields,
    DatabaseManager,
    ReportType,
)
from helpers import checks, utils
from helpers.pagination import Pagination

logger = logging.getLogger("command")


class ListReports(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def report_type_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        logger.debug(f"Report type autocomplete called with current: {current}")
        choices = [app_commands.Choice(name="All", value="All")]
        choices.extend([app_commands.Choice(name=REPORT_TYPE_DISPLAY[rt], value=rt.name) for rt in ReportType])

        filtered_choices = [choice for choice in choices if current.lower() in choice.name.lower()]
        logger.debug(f"Returning {len(filtered_choices)} autocomplete choices")
        return filtered_choices[:25]

    async def user_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        logger.debug(f"User autocomplete called with current: {current}")
        members = interaction.guild.members
        choices = [
            app_commands.Choice(name=f"@{member.display_name}", value=str(member.id))
            for member in members
            if current.lower() in member.display_name.lower()
        ]
        logger.debug(f"Returning {len(choices)} user autocomplete choices")
        return choices[:8]

    @commands.hybrid_command(
        name="list_reports",
        description="List all users reported.",
    )
    @app_commands.autocomplete(report_type=report_type_autocomplete, user=user_autocomplete)
    async def list_reports(self, ctx, report_type: str, user: str = None):
        logger.info(f"list_reports command called by {ctx.author} with report_type: {report_type}, user: {user}")

        if not checks.is_guild_configured(ctx):
            logger.warning(f"Guild {ctx.guild.id} not configured")
            await ctx.send(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return

        if report_type == "From User" and not user:
            logger.warning("From User selected but no user provided")
            await ctx.send("Please select a user when using 'From User' option.", ephemeral=True)
            return

        logger.debug(f"Fetching non-absolved cheater reports for type: {report_type}")
        try:
            if user:
                user_id = int(user)
                if report_type == "All":
                    reports = DatabaseManager.get_cheater_reports_by_user(user_id, absolved=False)
                    logger.debug(f"Retrieved {len(reports)} non-absolved reports for user: {user}")
                else:
                    report_enum = ReportType[report_type]
                    reports = DatabaseManager.get_cheater_reports_by_type_and_user(report_enum, user_id, absolved=False)
                    logger.debug(f"Retrieved {len(reports)} non-absolved reports for ReportType: {report_enum} and user: {user}")
            else:
                if report_type == "All":
                    reports = []
                    for rt in ReportType:
                        type_reports = DatabaseManager.get_cheater_reports_by_type(rt, absolved=False)
                        logger.debug(f"Retrieved {len(type_reports)} non-absolved reports for ReportType: {rt}")
                        reports.extend(type_reports)
                else:
                    report_enum = ReportType[report_type]
                    reports = DatabaseManager.get_cheater_reports_by_type(report_enum, absolved=False)
                    logger.debug(f"Retrieved {len(reports)} non-absolved reports for ReportType: {report_enum}")
        except Exception as e:
            logger.error(f"An error occurred while retrieving reports: {e}")
            reports = []

        if not reports:
            logger.info(f"No non-absolved reports found for the given criteria")
            await ctx.send("No non-absolved reports found for the given criteria.", ephemeral=True)
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

            if report[CheaterReportFields.REPORT_TIME.value] > cheater_summary[cheater_id]["latest_time"]:
                cheater_summary[cheater_id]["latest_time"] = report[CheaterReportFields.REPORT_TIME.value]
                cheater_summary[cheater_id]["latest_name"] = report[CheaterReportFields.CHEATER_GAME_NAME.value]

            # Find the user who reported the most for this cheater
            cheater_summary[cheater_id]["reporter"] = max(reporter_summary[cheater_id], key=reporter_summary[cheater_id].get)

        logger.debug("Sorting cheater summary")
        sorted_summary = sorted(cheater_summary.items(), key=lambda x: x[1]["count"], reverse=True)

        items_per_page = 10
        pages = math.ceil(len(sorted_summary) / items_per_page)
        logger.debug(f"Calculated {pages} pages for pagination")

        async def get_page(page):
            logger.debug(f"Generating page {page} of {pages}")
            start = (page - 1) * items_per_page
            end = start + items_per_page
            current_page = sorted_summary[start:end]

            try:
                report_type_display = REPORT_TYPE_DISPLAY[ReportType[report_type]] if report_type != "All" else "All Types"
            except KeyError:
                report_type_display = report_type

            embed = discord.Embed(
                title=f"Reports for '{report_type_display}'",
                color=discord.Color.red(),
            )

            latest_names = []
            counts = []
            reporters = []

            for cheater_id, data in current_page:
                latest_names.append(f"[{data['latest_name']}](https://tarkov.dev/player/{cheater_id})")
                counts.append(f"` {data['count']} `")
                reporter_mention = await utils.get_user_mention(ctx.guild, ctx.bot, data["reporter"])
                reporters.append(reporter_mention)
                logger.debug(
                    f"Processed cheater: {cheater_id}, name: {data['latest_name']}, count: {data['count']}, reporter: {reporter_mention}"
                )

            embed.add_field(name="Last Reported Name", value="\n".join(latest_names), inline=True)
            embed.add_field(name="Times Reported", value="\n".join(counts), inline=True)
            embed.add_field(name="Reported Most By", value="\n".join(reporters), inline=True)
            logger.debug(f"Generated embed for page {page}")
            return embed, pages

        logger.info("Creating pagination view")
        view = Pagination(ctx.interaction, get_page, timeout=60, delete_on_timeout=True, ephemeral=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(ListReports(bot))
