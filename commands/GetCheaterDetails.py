import discord
from discord import app_commands
from discord.ext import commands
import db.database as database
import logging

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

        # Add required fields
        embed.add_field(
            name="Last Known Name", value=cheater_details["name"], inline=True
        )
        embed.add_field(
            name="ID",
            value=f"[{cheater_details['id']}](https://tarkov.dev/player/{cheater_details['id']})",
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
            last_report_type = "Kill Report"
            last_reported_time = cheater_details.get("last_kill_report_time")
            last_reported_by = cheater_details.get("last_kill_reported_by")
        else:
            last_report_type = "Death Report"
            last_reported_time = cheater_details.get("last_death_report_time")
            last_reported_by = cheater_details.get("last_death_reported_by")

        last_reported_user = await self.bot.fetch_user(last_reported_by)
        last_reported_mention = (
            last_reported_user.mention
            if last_reported_user
            else f"Unknown User ({last_reported_by})"
        )
        embed.add_field(
            name=f"Last Reported ({last_report_type})",
            value=f"{last_reported_mention} at <t:{last_reported_time}:f>",
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
                name="Most Reported Server",
                value=f"{server_name} ({cheater_details['most_reported_server']['count']} times)",
                inline=False,
            )

        # Add kill report details if available
        if cheater_details["total_kill_reports"] > 0:
            most_killed_by_user = await self.bot.fetch_user(
                cheater_details["most_killed_by"]["user_id"]
            )
            most_killed_by_mention = (
                most_killed_by_user.mention
                if most_killed_by_user
                else f"Unknown User ({cheater_details['most_killed_by']['user_id']})"
            )
            embed.add_field(
                name="Total Killed",
                value=f"{cheater_details['total_kill_reports']}",
                inline=True,
            )
            embed.add_field(
                name="Most Killed By",
                value=f"{most_killed_by_mention} ({cheater_details['most_killed_by']['count']} times)",
                inline=True,
            )
            last_kill_reported_user = await self.bot.fetch_user(
                cheater_details["last_kill_reported_by"]
            )
            last_kill_reported_mention = (
                last_kill_reported_user.mention
                if last_kill_reported_user
                else f"Unknown User ({cheater_details['last_kill_reported_by']})"
            )
            embed.add_field(
                name="Last Reported By (Kill)",
                value=f"{last_kill_reported_mention} at <t:{cheater_details['last_kill_report_time']}:f>",
                inline=True,
            )

        # Add death report details if available
        if cheater_details["total_death_reports"] > 0:
            if cheater_details["most_deaths_to"]:
                most_deaths_to_user = await self.bot.fetch_user(
                    cheater_details["most_deaths_to"]["user_id"]
                )
                most_deaths_to_mention = (
                    most_deaths_to_user.mention
                    if most_deaths_to_user
                    else f"Unknown User ({cheater_details['most_deaths_to']['user_id']})"
                )
                embed.add_field(
                    name="Total Deaths From",
                    value=f"{cheater_details['total_death_reports']}",
                    inline=True,
                )
                embed.add_field(
                    name="Most Deaths To",
                    value=f"{most_deaths_to_mention} ({cheater_details['most_deaths_to']['count']} times)",
                    inline=True,
                )
                last_death_reported_user = await self.bot.fetch_user(
                    cheater_details["last_death_reported_by"]
                )
                last_death_reported_mention = (
                    last_death_reported_user.mention
                    if last_death_reported_user
                    else f"Unknown User ({cheater_details['last_death_reported_by']})"
                )
                embed.add_field(
                    name="Last Reported By (Death)",
                    value=f"{last_death_reported_mention} at <t:{cheater_details['last_death_report_time']}:f>",
                    inline=True,
                )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(CheaterDetails(bot))
