import logging

import discord
from discord import app_commands
from discord.ext import commands

from db.database import REPORT_TYPE_DISPLAY, DatabaseManager, ReportType
from helpers import checks
from helpers.pagination import Pagination
from helpers.utils import get_user_mention

logger = logging.getLogger("command")


class ReportDetails(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cheater_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        logger.debug(f"Cheater autocomplete called with current: {current}")
        cheaters = DatabaseManager.get_all_cheaters()
        logger.debug(f"Retrieved {len(cheaters)} cheaters from database")

        latest_cheaters = {}
        for cheater in cheaters:
            cheater_id = cheater["id"]
            if cheater_id not in latest_cheaters or cheater["report_time"] > latest_cheaters[cheater_id]["report_time"]:
                latest_cheaters[cheater_id] = cheater

        logger.debug(f"Filtered to {len(latest_cheaters)} latest cheaters")

        choices = []
        for cheater in latest_cheaters.values():
            if current.lower() in str(cheater["id"]).lower() or current.lower() in cheater["name"].lower():
                choice_name = f"{cheater['name']} ({cheater['id']})"
                choices.append(app_commands.Choice(name=choice_name, value=str(cheater["id"])))

        logger.debug(f"Returning {len(choices)} autocomplete choices")
        return choices[:25]

    @app_commands.command(
        name="get_reported_details",
        description="Get detailed information about a suspected cheater",
    )
    @app_commands.autocomplete(cheater=cheater_autocomplete)
    async def get_cheater_details(self, interaction: discord.Interaction, cheater: str):
        logger.debug(f"get_reported_details called with cheater: {cheater}")

        if not checks.is_guild_id_configured(interaction.guild.id):
            logger.debug(f"Guild {interaction.guild.id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` first.",
                ephemeral=True,
            )
            return

        try:
            cheater_id = int(cheater)
            logger.debug(f"Parsed cheater ID: {cheater_id}")
        except ValueError:
            logger.debug(f"Invalid cheater ID format: {cheater}")
            await interaction.response.send_message("Invalid cheater ID format.", ephemeral=True)
            return

        logger.debug(f"Fetching comprehensive cheater details for ID: {cheater_id}")
        cheater_details = DatabaseManager.get_comprehensive_cheater_details(cheater_id)

        if not cheater_details:
            logger.debug(f"No details found for cheater ID: {cheater_id}")
            await interaction.response.send_message("Cheater not found.", ephemeral=True)
            return

        embeds = []

        # Main embed
        main_embed = discord.Embed(
            title="Cheater Details",
            color=discord.Color.red(),
        )

        main_embed.add_field(
            name="Profile ID",
            value=f"[{cheater_details['id']}](https://tarkov.dev/player/{cheater_details['id']})",
            inline=True,
        )
        main_embed.add_field(
            name="Last Known Name",
            value=f"[{cheater_details['name']}](https://tarkov.dev/player/{cheater_details['id']})",
            inline=True,
        )

        last_report_type = None
        last_reported_time = 0
        last_reported_by = None

        logger.debug("Determining last report type and details")
        for report_type in ReportType:
            report_time_key = f"last_{report_type.name.lower()}_report_time"
            reported_by_key = f"last_{report_type.name.lower()}_reported_by"

            current_report_time = cheater_details.get(report_time_key, 0)
            if current_report_time is not None and current_report_time > last_reported_time:
                last_report_type = report_type
                last_reported_time = current_report_time
                last_reported_by = cheater_details.get(reported_by_key)

        if last_report_type is not None:
            logger.debug(f"Getting user mention for last reporter: {last_reported_by}")
            try:
                last_reported_mention = await get_user_mention(interaction.guild, self.bot, last_reported_by)
                logger.debug(f"User mention retrieved: {last_reported_mention}")
                main_embed.add_field(
                    name=f"Last Report was '{REPORT_TYPE_DISPLAY[last_report_type]}'",
                    value=f"{last_reported_mention} <t:{last_reported_time}:R>",
                    inline=True,
                )
            except Exception as e:
                logger.error(f"Error getting user mention: {e}")
                main_embed.add_field(
                    name=f"Last Reported was '{REPORT_TYPE_DISPLAY[last_report_type]}'",
                    value=f"Unknown User <t:{last_reported_time}:R>",
                    inline=True,
                )

        logger.debug("Adding dynamic report type details")
        report_details = []
        for report_type in ReportType:
            total_reports_key = f"total_{report_type.name.lower()}_reports"
            last_reported_by_key = f"last_{report_type.name.lower()}_reported_by"
            last_report_time_key = f"last_{report_type.name.lower()}_report_time"

            if cheater_details.get(total_reports_key, 0) > 0:
                try:
                    last_reported_mention = await get_user_mention(
                        interaction.guild,
                        self.bot,
                        cheater_details[last_reported_by_key],
                    )
                    logger.debug(f"User mention retrieved: {last_reported_mention}")
                    report_details.append(
                        f"`{REPORT_TYPE_DISPLAY[report_type]}` has `{cheater_details[total_reports_key]}` report(s). Last by {last_reported_mention} <t:{cheater_details[last_report_time_key]}:R>"
                    )
                except Exception as e:
                    logger.error(f"Error getting user mention for report type {report_type}: {e}")
                    report_details.append(
                        f"`{REPORT_TYPE_DISPLAY[report_type]}` has `{cheater_details[total_reports_key]}` report(s). Last by `Unknown User` <t:{cheater_details[last_report_time_key]}:R>"
                    )

        logger.debug("Adding report details to embed")
        if report_details:
            main_embed.add_field(
                name="Report Details",
                value="\n".join(report_details),
                inline=False,
            )

        logger.debug("Adding top reported servers")
        if cheater_details.get("top_reported_servers"):
            top_servers = cheater_details["top_reported_servers"]
            server_details = []
            for server_info in top_servers[:3]:
                server = self.bot.get_guild(server_info["server_id"])
                server_name = server.name if server else f"Unknown Server ({server_info['server_id']})"
                server_details.append(f"`{server_name}`: `{server_info['count']}` report(s)")

            main_embed.add_field(
                name="Top Reporting Servers",
                value="\n".join(server_details),
                inline=False,
            )

        embeds.append(main_embed)

        # Create embeds for each note
        if "notes" in cheater_details:
            for note in cheater_details["notes"]:
                note_embed = discord.Embed(
                    title="Report Note",
                    color=discord.Color.blue(),
                )
                verifier_mention = await get_user_mention(interaction.guild, self.bot, note["verifier_user_id"])
                note_embed.add_field(
                    name="Added By",
                    value=f"{verifier_mention} <t:{note['timestamp']}:R>",
                    inline=False,
                )
                note_embed.add_field(
                    name="Note",
                    value=f"```\n{note['content']}\n```",
                    inline=False,
                )
                embeds.append(note_embed)

        logger.debug(f"Created {len(embeds)} embeds")

        async def get_page(page):
            return embeds[page - 1], len(embeds)

        logger.debug("Creating pagination view")
        view = Pagination(interaction, get_page, timeout=120, delete_on_timeout=True, ephemeral=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(ReportDetails(bot))
