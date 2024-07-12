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
        logger.info("ListCheaters cog initialized")

    async def report_type_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        logger.debug(f"Report type autocomplete called with current: {current}")
        choices = [app_commands.Choice(name="All", value="All")]
        choices.extend(
            [
                app_commands.Choice(name=REPORT_TYPE_DISPLAY[rt], value=rt.name)
                for rt in ReportType
            ]
        )
        choices.append(app_commands.Choice(name="From User", value="From User"))

        filtered_choices = [
            choice for choice in choices if current.lower() in choice.name.lower()
        ]
        logger.debug(f"Returning {len(filtered_choices)} autocomplete choices")
        return filtered_choices[:25]

    async def user_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        logger.debug(f"User autocomplete called with current: {current}")
        members = interaction.guild.members
        choices = [
            app_commands.Choice(name=member.name, value=member.mention)
            for member in members
            if current.lower() in member.name.lower()
            or current.lower() in member.mention
        ]
        logger.debug(f"Returning {len(choices)} user autocomplete choices")
        return choices[:25]

    @commands.hybrid_command(
        name="list_cheaters",
        description="List all cheaters reported.",
    )
    @app_commands.autocomplete(
        report_type=report_type_autocomplete, user=user_autocomplete
    )
    async def list_cheaters(self, ctx, report_type: str, user: str = None):
        logger.info(
            f"list_cheaters command called by {ctx.author} with report_type: {report_type}, user: {user}"
        )

        if not checks.is_guild_configured(ctx):
            logger.warning(f"Guild {ctx.guild.id} not configured")
            await ctx.send(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return

        if report_type == "From User" and not user:
            logger.warning("From User selected but no user provided")
            await ctx.send(
                "Please select a user when using 'From User' option.", ephemeral=True
            )
            return

        logger.debug(f"Fetching cheater reports for type: {report_type}")
        if report_type == "All":
            reports = []
            for rt in ReportType:
                reports.extend(DatabaseManager.get_cheater_reports_by_type(rt))
        elif report_type == "From User":
            user_id = (
                int(user[2:-1])
                if user.startswith("<@") and user.endswith(">")
                else None
            )
            if user_id:
                reports = DatabaseManager.get_cheater_reports_by_user(user_id)
            else:
                logger.warning(f"Invalid user mention: {user}")
                await ctx.send(
                    "Invalid user mention. Please try again.", ephemeral=True
                )
                return
        else:
            try:
                report_enum = ReportType[report_type]
                reports = DatabaseManager.get_cheater_reports_by_type(report_enum)
            except KeyError:
                logger.warning(f"Invalid report type provided: {report_type}")
                await ctx.send("Invalid report type. Please try again.", ephemeral=True)
                return

        if not reports:
            logger.info(f"No reports found for the given criteria")
            await ctx.send("No reports found for the given criteria.", ephemeral=True)
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
                title=f"Cheater Reports - {report_type}",
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
