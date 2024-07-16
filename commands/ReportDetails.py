import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from db.database import REPORT_TYPE_DISPLAY, DatabaseManager, ReportType
from helpers import checks
from helpers.pagination import Pagination
from helpers.utils import get_user_mention

logger = logging.getLogger("command")


@dataclass
class CheaterReport:
    report_type: ReportType
    total_reports: int
    last_reported_by: int
    last_report_time: int


@dataclass
class ServerReport:
    server_id: int
    server_name: str
    count: int


@dataclass
class CheaterNote:
    verifier_user_id: int
    timestamp: int
    content: str


@dataclass
class CheaterDetails:
    id: int
    name: str
    reports: Dict[ReportType, CheaterReport]
    top_reported_servers: List[ServerReport]
    notes: List[CheaterNote]
    last_report_type: Optional[ReportType] = None
    last_reported_time: int = 0
    last_reported_by: Optional[int] = None


class ReportDetails(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cheater_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        logger.debug(f"Cheater autocomplete called with current: {current}")
        cheaters = DatabaseManager.get_all_cheaters()
        logger.debug(f"Retrieved {len(cheaters)} cheaters from database")

        latest_cheaters = self.get_latest_cheaters(cheaters)
        logger.debug(f"Filtered to {len(latest_cheaters)} latest cheaters")

        choices = self.create_autocomplete_choices(latest_cheaters, current)
        logger.debug(f"Returning {len(choices)} autocomplete choices")
        return choices[:25]

    def get_latest_cheaters(self, cheaters: List[Dict]) -> Dict[int, Dict]:
        latest_cheaters = {}
        for cheater in cheaters:
            cheater_id = cheater["id"]
            if cheater_id not in latest_cheaters or cheater["report_time"] > latest_cheaters[cheater_id]["report_time"]:
                latest_cheaters[cheater_id] = cheater
        return latest_cheaters

    def create_autocomplete_choices(self, latest_cheaters: Dict[int, Dict], current: str) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=f"{cheater['name']} ({cheater['id']})", value=str(cheater["id"]))
            for cheater in latest_cheaters.values()
            if current.lower() in str(cheater["id"]).lower() or current.lower() in cheater["name"].lower()
        ]

    @app_commands.command(
        name="get_reported_details",
        description="Get detailed information about a suspected cheater",
    )
    @app_commands.autocomplete(cheater=cheater_autocomplete)
    async def get_cheater_details(self, interaction: discord.Interaction, cheater: str):
        logger.debug(f"get_reported_details called with cheater: {cheater}")

        if not await self.check_guild_configuration(interaction):
            return

        cheater_id = await self.parse_cheater_id(interaction, cheater)
        if not cheater_id:
            return

        cheater_details = await self.fetch_cheater_details(interaction, cheater_id)
        if not cheater_details:
            return

        embeds = await self.create_embeds(cheater_details)
        await self.display_pagination(interaction, embeds)

    async def check_guild_configuration(self, interaction: discord.Interaction) -> bool:
        if not checks.is_guild_id_configured(interaction.guild.id):
            logger.debug(f"Guild {interaction.guild.id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` first.",
                ephemeral=True,
            )
            return False
        return True

    async def parse_cheater_id(self, interaction: discord.Interaction, cheater: str) -> Optional[int]:
        try:
            return int(cheater)
        except ValueError:
            logger.debug(f"Invalid cheater ID format: {cheater}")
            await interaction.response.send_message("Invalid cheater ID format.", ephemeral=True)
            return None

    async def fetch_cheater_details(self, interaction: discord.Interaction, cheater_id: int) -> Optional[CheaterDetails]:
        logger.debug(f"Fetching comprehensive cheater details for ID: {cheater_id}")
        details = DatabaseManager.get_comprehensive_cheater_details(cheater_id)

        if not details:
            logger.debug(f"No details found for cheater ID: {cheater_id}")
            await interaction.response.send_message("Cheater not found.", ephemeral=True)
            return None

        reports = {}
        for report_type in ReportType:
            total_reports_key = f"total_{report_type.name.lower()}_reports"
            last_reported_by_key = f"last_{report_type.name.lower()}_reported_by"
            last_report_time_key = f"last_{report_type.name.lower()}_report_time"

            if details.get(total_reports_key, 0) > 0:
                reports[report_type] = CheaterReport(
                    report_type=report_type,
                    total_reports=details[total_reports_key],
                    last_reported_by=details[last_reported_by_key],
                    last_report_time=details[last_report_time_key],
                )

        top_reported_servers = [
            ServerReport(
                server_id=server_info["server_id"],
                server_name=(
                    self.bot.get_guild(server_info["server_id"]).name
                    if self.bot.get_guild(server_info["server_id"])
                    else f"Unknown Server ({server_info['server_id']})"
                ),
                count=server_info["count"],
            )
            for server_info in details.get("top_reported_servers", [])[:3]
        ]

        notes = [
            CheaterNote(verifier_user_id=note["verifier_user_id"], timestamp=note["timestamp"], content=note["content"])
            for note in details.get("notes", [])
        ]

        return CheaterDetails(
            id=details["id"], name=details["name"], reports=reports, top_reported_servers=top_reported_servers, notes=notes
        )

    async def create_embeds(self, cheater_details: CheaterDetails) -> List[discord.Embed]:
        embeds = []
        main_embed = await self.create_main_embed(cheater_details)
        embeds.append(main_embed)

        for note in cheater_details.notes:
            note_embed = await self.create_note_embed(note)
            embeds.append(note_embed)

        logger.debug(f"Created {len(embeds)} embeds")
        return embeds

    async def create_main_embed(self, details: CheaterDetails) -> discord.Embed:
        main_embed = discord.Embed(
            title="Cheater Details",
            color=discord.Color.red(),
        )

        main_embed.add_field(
            name="Last Known Name",
            value=f"[{details.name}](https://tarkov.dev/player/{details.id})",
            inline=True,
        )
        main_embed.add_field(
            name="Profile ID",
            value=f"[{details.id}](https://tarkov.dev/player/{details.id})",
            inline=True,
        )

        last_report = max(details.reports.values(), key=lambda r: r.last_report_time, default=None)
        if last_report:
            last_reported_mention = await get_user_mention(last_report.last_reported_by)
            main_embed.add_field(
                name=f"Last Report was '{REPORT_TYPE_DISPLAY[last_report.report_type]}'",
                value=f"{last_reported_mention} <t:{last_report.last_report_time}:R>",
                inline=True,
            )

        report_details = []
        for report in details.reports.values():
            last_reported_mention = await get_user_mention(report.last_reported_by)
            report_details.append(
                f"`{REPORT_TYPE_DISPLAY[report.report_type]}` has `{report.total_reports}` report(s). Last by {last_reported_mention} <t:{report.last_report_time}:R>"
            )

        if report_details:
            main_embed.add_field(
                name="Report Details",
                value="\n".join(report_details),
                inline=False,
            )

        if details.top_reported_servers:
            server_details = [f"`{server.server_name}`: `{server.count}` report(s)" for server in details.top_reported_servers]
            main_embed.add_field(
                name="Top Reporting Servers",
                value="\n".join(server_details),
                inline=False,
            )

        return main_embed

    async def create_note_embed(self, note: CheaterNote) -> discord.Embed:
        note_embed = discord.Embed(
            title="Report Note",
            color=discord.Color.blue(),
        )
        verifier_mention = await get_user_mention(note.verifier_user_id)
        note_embed.add_field(
            name="Added By",
            value=f"{verifier_mention} <t:{note.timestamp}:R>",
            inline=False,
        )
        note_embed.add_field(
            name="Note",
            value=f"```\n{note.content}\n```",
            inline=False,
        )
        return note_embed

    async def display_pagination(self, interaction: discord.Interaction, embeds: List[discord.Embed]):
        async def get_page(page):
            return embeds[page - 1], len(embeds)

        logger.debug("Creating pagination view")
        view = Pagination(interaction, get_page, timeout=120, delete_on_timeout=True, ephemeral=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(ReportDetails(bot))
