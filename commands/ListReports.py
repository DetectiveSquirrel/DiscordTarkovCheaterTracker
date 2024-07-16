import logging
import math
from typing import Dict, List, Tuple

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


class CheaterReport:
    def __init__(self, cheater_id: str, cheater_name: str, reporter_id: str, report_time: float):
        self.cheater_id = cheater_id
        self.cheater_name = cheater_name
        self.reporter_id = reporter_id
        self.report_time = report_time


class CheaterSummary:
    def __init__(self):
        self.count = 0
        self.latest_name = ""
        self.latest_time = 0
        self.reporters: Dict[str, int] = {}

    def update(self, report: CheaterReport):
        self.count += 1
        if report.report_time > self.latest_time:
            self.latest_time = report.report_time
            self.latest_name = report.cheater_name
        self.reporters[report.reporter_id] = self.reporters.get(report.reporter_id, 0) + 1

    @property
    def top_reporter(self):
        return max(self.reporters, key=self.reporters.get) if self.reporters else None


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

        if not await self.check_guild_configuration(ctx):
            return

        if report_type == "From User" and not user:
            logger.warning("From User selected but no user provided")
            await ctx.send("Please select a user when using 'From User' option.", ephemeral=True)
            return

        reports = await self.fetch_reports(report_type, user)
        if not reports:
            await ctx.send("No non-absolved reports found for the given criteria.", ephemeral=True)
            return

        cheater_summary = self.process_reports(reports)
        sorted_summary = self.sort_cheater_summary(cheater_summary)
        await self.display_pagination(ctx, sorted_summary, report_type)

    async def check_guild_configuration(self, ctx) -> bool:
        if not checks.is_guild_id_configured(ctx.guild.id):
            logger.warning(f"Guild {ctx.guild.id} not configured")
            await ctx.send(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return False
        return True

    async def fetch_reports(self, report_type: str, user: str = None) -> List[CheaterReport]:
        logger.debug(f"Fetching non-absolved cheater reports for type: {report_type}")
        try:
            if user:
                user_id = int(user)
                if report_type == "All":
                    db_reports = DatabaseManager.get_cheater_reports_by_user(user_id, absolved=False)
                else:
                    report_enum = ReportType[report_type]
                    db_reports = DatabaseManager.get_cheater_reports_by_type_and_user(report_enum, user_id, absolved=False)
            else:
                if report_type == "All":
                    db_reports = []
                    for rt in ReportType:
                        db_reports.extend(DatabaseManager.get_cheater_reports_by_type(rt, absolved=False))
                else:
                    report_enum = ReportType[report_type]
                    db_reports = DatabaseManager.get_cheater_reports_by_type(report_enum, absolved=False)

            return [
                CheaterReport(
                    report[CheaterReportFields.CHEATER_PROFILE_ID.value],
                    report[CheaterReportFields.CHEATER_GAME_NAME.value],
                    report[CheaterReportFields.REPORTER_USER_ID.value],
                    report[CheaterReportFields.REPORT_TIME.value],
                )
                for report in db_reports
            ]
        except Exception as e:
            logger.error(f"An error occurred while retrieving reports: {e}")
            return []

    def process_reports(self, reports: List[CheaterReport]) -> Dict[str, CheaterSummary]:
        logger.debug(f"Processing {len(reports)} reports")
        cheater_summary = {}
        for report in reports:
            if report.cheater_id not in cheater_summary:
                cheater_summary[report.cheater_id] = CheaterSummary()
            cheater_summary[report.cheater_id].update(report)
        return cheater_summary

    def sort_cheater_summary(self, cheater_summary: Dict[str, CheaterSummary]) -> List[Tuple[str, CheaterSummary]]:
        logger.debug("Sorting cheater summary")
        return sorted(cheater_summary.items(), key=lambda x: x[1].count, reverse=True)

    async def display_pagination(self, ctx, sorted_summary: List[Tuple[str, CheaterSummary]], report_type: str):
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
                latest_names.append(f"[{data.latest_name}](https://tarkov.dev/player/{cheater_id})")
                counts.append(f"` {data.count} `")
                reporter_mention = await utils.get_user_mention(data.top_reporter)
                reporters.append(reporter_mention)
                logger.debug(
                    f"Processed cheater: {cheater_id}, name: {data.latest_name}, count: {data.count}, reporter: {reporter_mention}"
                )

            embed.add_field(name="Last Reported Name", value="\n".join(latest_names), inline=True)
            embed.add_field(name="Times Reported", value="\n".join(counts), inline=True)
            embed.add_field(name="Reported Most By", value="\n".join(reporters), inline=True)
            logger.debug(f"Generated embed for page {page}")
            return embed, pages

        logger.info("Creating pagination view")
        view = Pagination(ctx.interaction, get_page, timeout=60, delete_on_timeout=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(ListReports(bot))
