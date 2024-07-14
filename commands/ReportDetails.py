import discord
from discord import app_commands
from discord.ext import commands
from db.database import DatabaseManager, ReportType, REPORT_TYPE_DISPLAY
import logging
from helpers.utils import get_user_mention
from helpers import checks

logger = logging.getLogger("command")


class ReportDetails(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cheater_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        logger.debug(f"Cheater autocomplete called with current: {current}")
        cheaters = DatabaseManager.get_all_cheaters()
        logger.debug(f"Retrieved {len(cheaters)} cheaters from database")

        latest_cheaters = {}
        for cheater in cheaters:
            cheater_id = cheater["id"]
            if (
                cheater_id not in latest_cheaters
                or cheater["report_time"] > latest_cheaters[cheater_id]["report_time"]
            ):
                latest_cheaters[cheater_id] = cheater

        logger.debug(f"Filtered to {len(latest_cheaters)} latest cheaters")

        choices = []
        for cheater in latest_cheaters.values():
            if (
                current.lower() in str(cheater["id"]).lower()
                or current.lower() in cheater["name"].lower()
            ):
                choice_name = f"{cheater['name']} ({cheater['id']})"
                choices.append(
                    app_commands.Choice(name=choice_name, value=str(cheater["id"]))
                )

        logger.debug(f"Returning {len(choices)} autocomplete choices")
        return choices[:25]

    @app_commands.command(
        name="get_reported_details",
        description="Get detailed information about a suspected cheater",
    )
    @app_commands.autocomplete(cheater=cheater_autocomplete)
    async def get_cheaterget_reported_details_details(
        self, interaction: discord.Interaction, cheater: str
    ):
        logger.debug(f"get_reported_details called with cheater: {cheater}")

        if not checks.is_guild_id_configured(interaction.guild.id):
            logger.debug(f"Guild {interaction.guild.id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return

        try:
            logger.debug(f"Parsing cheater ID: {cheater}")
            cheater_id = int(cheater)
        except ValueError:
            logger.debug(f"Invalid cheater ID format: {cheater}")
            await interaction.response.send_message(
                "Invalid cheater ID format.", ephemeral=True
            )
            return

        logger.debug(f"Fetching comprehensive cheater details for ID: {cheater_id}")
        cheater_details = DatabaseManager.get_comprehensive_cheater_details(cheater_id)

        if not cheater_details:
            logger.debug(f"No details found for cheater ID: {cheater_id}")
            await interaction.response.send_message(
                "Cheater not found.", ephemeral=True
            )
            return

        logger.debug("Creating embed")
        embed = discord.Embed(
            color=discord.Color.red(),
        )

        embed.add_field(
            name="Profile ID",
            value=f"[{cheater_details['id']}](https://tarkov.dev/player/{cheater_details['id']})",
            inline=True,
        )
        embed.add_field(
            name="Last Known Name",
            value=f"[{cheater_details['name']}](https://tarkov.dev/player/{cheater_details['id']})",
            inline=True,
        )

        logger.debug("Determining last report type and details")
        last_report_type = None
        last_reported_time = 0
        last_reported_by = None

        try:
            for report_type in ReportType:
                report_time_key = f"last_{report_type.name.lower()}_report_time"
                reported_by_key = f"last_{report_type.name.lower()}_reported_by"

                logger.debug(f"Checking report type: {report_type}")
                logger.debug(
                    f"report_time_key: {report_time_key}, value: {cheater_details.get(report_time_key)}"
                )
                logger.debug(
                    f"reported_by_key: {reported_by_key}, value: {cheater_details.get(reported_by_key)}"
                )

                current_report_time = cheater_details.get(report_time_key, 0)
                if current_report_time > last_reported_time:
                    last_report_type = report_type
                    last_reported_time = current_report_time
                    last_reported_by = cheater_details.get(reported_by_key)
                    logger.debug(
                        f"Updated last report: type={last_report_type}, time={last_reported_time}, by={last_reported_by}"
                    )

            logger.debug(
                f"Final last report type: {last_report_type}, time: {last_reported_time}, by: {last_reported_by}"
            )
        except Exception as e:
            logger.error(f"Error determining last report type: {e}")
            last_report_type = None
            last_reported_time = 0
            last_reported_by = None

        if last_report_type:
            logger.debug(f"Getting user mention for last reporter: {last_reported_by}")
            try:
                last_reported_mention = await get_user_mention(
                    interaction.guild, self.bot, last_reported_by
                )
                logger.debug(f"User mention retrieved: {last_reported_mention}")
                embed.add_field(
                    name=f"Last Reported was '{REPORT_TYPE_DISPLAY[last_report_type]}'",
                    value=f"{last_reported_mention} <t:{last_reported_time}:R>",
                    inline=True,
                )
            except Exception as e:
                logger.error(f"Error getting user mention: {e}")
                embed.add_field(
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
                logger.debug(f"Processing report type: {report_type}")
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
                    logger.error(
                        f"Error getting user mention for report type {report_type}: {e}"
                    )
                    report_details.append(
                        f"`{REPORT_TYPE_DISPLAY[report_type]}` has `{cheater_details[total_reports_key]}` report(s). Last by `Unknown User` <t:{cheater_details[last_report_time_key]}:R>"
                    )

        logger.debug("Adding report details to embed")
        if report_details:
            embed.add_field(
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
                server_name = (
                    server.name
                    if server
                    else f"Unknown Server ({server_info['server_id']})"
                )
                server_details.append(
                    f"`{server_name}`: `{server_info['count']}` report(s)"
                )

            embed.add_field(
                name="Top Reporting Servers",
                value="\n".join(server_details),
                inline=False,
            )

        logger.debug("Sending response")
        try:
            await interaction.response.send_message(
                embed=embed, ephemeral=True, silent=True
            )
            logger.debug("Response sent successfully")
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            await interaction.response.send_message(
                "An error occurred while sending the response.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ReportDetails(bot))
