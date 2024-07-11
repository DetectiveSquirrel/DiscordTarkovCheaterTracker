import discord
from discord import app_commands
from discord.ext import commands
import db.database as database
import logging
from helpers.utils import get_user_mention
import helpers.checks

logger = logging.getLogger("bot")


class CheaterDetails(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cheater_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        cheaters = database.DatabaseManager.get_all_cheaters()

        latest_cheaters = {}
        for cheater in cheaters:
            cheater_id = cheater["id"]
            if (
                cheater_id not in latest_cheaters
                or cheater["timereported"] > latest_cheaters[cheater_id]["timereported"]
            ):
                latest_cheaters[cheater_id] = cheater

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

        return choices[:25]

    @app_commands.command(
        name="get_cheater_details",
        description="Get detailed information about a suspected cheater",
    )
    @app_commands.autocomplete(cheater=cheater_autocomplete)
    async def get_cheater_details(self, interaction: discord.Interaction, cheater: str):
        if not helpers.checks.is_guild_id_configured(interaction.guild.id):
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return

        try:
            logger.debug(f"Parsing cheater ID: {cheater}")
            cheater_id = int(cheater)
        except ValueError:
            logger.debug("Invalid cheater ID format.")
            await interaction.response.send_message(
                "Invalid cheater ID format.", ephemeral=True
            )
            return

        logger.debug(f"Fetching comprehensive cheater details for ID: {cheater_id}")
        cheater_details = database.DatabaseManager.get_comprehensive_cheater_details(
            cheater_id
        )
        logger.debug(f"Cheater details: {cheater_details}")

        if not cheater_details:
            logger.debug("Cheater not found or an error occurred.")
            await interaction.response.send_message(
                "Cheater not found or an error occurred.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"Cheater Details",
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

        # Determine last report type and details
        if (
            cheater_details.get("last_kill_report_time")
            and not cheater_details.get("last_death_report_time")
        ) or (
            cheater_details.get("last_kill_report_time")
            and cheater_details.get("last_kill_report_time")
            >= cheater_details.get("last_death_report_time")
        ):
            last_report_type = "Murder Report"
            last_reported_time = cheater_details.get("last_kill_report_time")
            last_reported_by = cheater_details.get("last_kill_reported_by")
        else:
            last_report_type = "Death Report"
            last_reported_time = cheater_details.get("last_death_report_time")
            last_reported_by = cheater_details.get("last_death_reported_by")

        last_reported_mention = await get_user_mention(
            interaction.guild, self.bot, last_reported_by
        )
        embed.add_field(
            name=f"Last Reported as a {last_report_type}",
            value=f"{last_reported_mention}\n<t:{last_reported_time}:R>",
            inline=True,
        )

        # Add most reported server
        if cheater_details.get("most_reported_server"):
            server = self.bot.get_guild(
                cheater_details["most_reported_server"]["server_id"]
            )
            server_name = (
                server.name
                if server
                else f"Unknown Server ({cheater_details['most_reported_server']['server_id']})"
            )
            embed.add_field(
                name="Most Reports From Server",
                value=f"'{server_name}' ({cheater_details['most_reported_server']['count']})",
                inline=False,
            )

        # Add kill report details if available
        if cheater_details["total_kill_reports"] > 0:
            most_killed_by_mention = await get_user_mention(
                interaction.guild,
                self.bot,
                cheater_details["most_killed_by"]["user_id"],
            )
            embed.add_field(
                name="Total Times Murdered",
                value=f"({cheater_details['total_kill_reports']})",
                inline=True,
            )
            embed.add_field(
                name="Most Killed By",
                value=f"{most_killed_by_mention}\n({cheater_details['most_killed_by']['count']})",
                inline=True,
            )
            last_kill_reported_mention = await get_user_mention(
                interaction.guild, self.bot, cheater_details["last_kill_reported_by"]
            )
            embed.add_field(
                name="Last Reported",
                value=f"{last_kill_reported_mention}\n<t:{cheater_details['last_kill_report_time']}:R>",
                inline=True,
            )

        # Add death report details if available
        if cheater_details["total_death_reports"] > 0:
            if cheater_details["most_deaths_to"]:
                most_deaths_to_mention = await get_user_mention(
                    interaction.guild,
                    self.bot,
                    cheater_details["most_deaths_to"]["user_id"],
                )
                embed.add_field(
                    name="Total Deaths From",
                    value=f"({cheater_details['total_death_reports']})",
                    inline=True,
                )
                embed.add_field(
                    name="Most Deaths From",
                    value=f"{most_deaths_to_mention}\n({cheater_details['most_deaths_to']['count']})",
                    inline=True,
                )
                last_death_reported_mention = await get_user_mention(
                    interaction.guild,
                    self.bot,
                    cheater_details["last_death_reported_by"],
                )
                embed.add_field(
                    name="Last Reported",
                    value=f"{last_death_reported_mention}\n<t:{cheater_details['last_death_report_time']}:R>",
                    inline=True,
                )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(CheaterDetails(bot))
