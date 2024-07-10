from discord.ext import commands
import discord
import logging
import db.database as database
import time

logger = logging.getLogger("bot")


class ShiftDonators(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="set_channel")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_id: str):
        guild = ctx.guild
        channel_id_int = int(channel_id)
        channel = guild.get_channel(channel_id_int)

        # Use DatabaseManager to add or update the server settings
        existing_settings = database.DatabaseManager.get_server_settings(
            serverid=guild.id
        )
        if existing_settings:
            database.DatabaseManager.update_server_settings(
                serverid=guild.id, channelid=channel_id_int
            )
            await ctx.send(
                f"Channel for server `{guild.name}` set to <#{channel.id}>",
                ephemeral=True,
            )
        else:
            database.DatabaseManager.add_server_settings(
                serverid=guild.id, channelid=channel_id_int
            )
            await ctx.send(
                f"Channel for server `{guild.name}` changed to <#{channel.id}>",
                ephemeral=True,
            )

    @commands.hybrid_command(name="add_cheater_kill")
    async def add_cheater_kill(self, ctx):
        class ContinueButton(discord.ui.View):
            @discord.ui.button(
                label="Continue",
                style=discord.ButtonStyle.primary,
                custom_id="continue_button",
            )
            async def continue_button(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    await interaction.response.send_message(
                        "This button is not for you.", ephemeral=True
                    )
                    return

                class CheaterIDModal(
                    discord.ui.Modal, title="Submit Cheater Information"
                ):
                    cheater_name = discord.ui.TextInput(
                        label="Cheater's Game Name",
                        placeholder="Enter the cheater's game name",
                    )
                    cheater_profile_id = discord.ui.TextInput(
                        label="Cheater Profile ID",
                        placeholder="Enter the cheater's profile ID (get it from tarkov.dev/players)",
                    )

                    async def on_submit(self, interaction: discord.Interaction):
                        cheater_name_value = self.cheater_name.value.strip().lower()
                        cheater_profile_id_value = self.cheater_profile_id.value
                        from_user_id_int = interaction.user.id
                        server_id_logged_in_int = interaction.guild.id
                        cheater_profile_id_int = int(cheater_profile_id_value)
                        time_reported = int(time.time())

                        database.DatabaseManager.add_cheater_killed(
                            fromUserid=from_user_id_int,
                            serverIdLoggedIn=server_id_logged_in_int,
                            cheatersgamename=cheater_name_value,
                            cheaterprofileid=cheater_profile_id_int,
                            timereported=time_reported,
                        )
                        await interaction.response.send_message(
                            f"Reporting a cheater was killed:\nUser <@{from_user_id_int}>\nReported cheater ['{cheater_name_value}' ({cheater_profile_id_int})](<https://tarkov.dev/{cheater_profile_id_int}>)\nOn server '{interaction.guild.name}'\nAt time <t:{time_reported}>"
                        )

                modal = CheaterIDModal()
                await interaction.response.send_modal(modal)

        await ctx.send(
            "Please go to [tarkov.dev/players](<https://tarkov.dev/players>) to get the profile ID and name, then click the button below to continue.",
            view=ContinueButton(),
        )

    @commands.hybrid_command(name="add_killed_by_cheater")
    async def add_killed_by_cheater(self, ctx):
        class ContinueButton(discord.ui.View):
            @discord.ui.button(
                label="Continue",
                style=discord.ButtonStyle.primary,
                custom_id="continue_button",
            )
            async def continue_button(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    await interaction.response.send_message(
                        "This button is not for you.", ephemeral=True
                    )
                    return

                class CheaterIDModal(
                    discord.ui.Modal, title="Submit Cheater Information"
                ):
                    cheater_name = discord.ui.TextInput(
                        label="Cheater's Game Name",
                        placeholder="Enter the cheater's game name",
                    )
                    cheater_profile_id = discord.ui.TextInput(
                        label="Cheater Profile ID",
                        placeholder="Enter the cheater's profile ID (get it from tarkov.dev/players)",
                    )

                    async def on_submit(self, interaction: discord.Interaction):
                        cheater_name_value = self.cheater_name.value.strip().lower()
                        cheater_profile_id_value = self.cheater_profile_id.value
                        from_user_id_int = interaction.user.id
                        server_id_logged_in_int = interaction.guild.id
                        cheater_profile_id_int = int(cheater_profile_id_value)
                        time_reported = int(time.time())

                        database.DatabaseManager.add_killed_by_cheater(
                            fromUserid=from_user_id_int,
                            serverIdLoggedIn=server_id_logged_in_int,
                            cheatersgamename=cheater_name_value,
                            cheaterprofileid=cheater_profile_id_int,
                            timereported=time_reported,
                        )
                        await interaction.response.send_message(
                            f"Reporting someone was killed by a cheater:\nUser <@{from_user_id_int}>\nReported cheater ['{cheater_name_value}' ({cheater_profile_id_int})](<https://tarkov.dev/{cheater_profile_id_int}>)\nOn server '{interaction.guild.name}'\nAt time <t:{time_reported}>"
                        )

                modal = CheaterIDModal()
                await interaction.response.send_modal(modal)

        await ctx.send(
            "Please go to [tarkov.dev/players](<https://tarkov.dev/players>) to get the profile ID and name, then click the button below to continue.",
            view=ContinueButton(),
        )

    @commands.hybrid_command(name="list_cheaters_kills")
    async def list_cheaters_kills(self, ctx):
        # Fetch raw data from the table
        reports = database.DatabaseManager.get_cheater_reports(
            table=database.DatabaseEnum.TABLE_CHEATER_DEATHS.value
        )

        if not reports:
            await ctx.send("No cheater reports found.", ephemeral=True)
            return

        # Debug: Print the first report to see its structure
        if reports:
            await ctx.send(f"Debug - First report: {reports[0]}", ephemeral=True)

        # Process the data to create a summary
        cheater_summary = {}
        for report in reports:
            cheater_id = report[database.DatabaseEnum.CHEATER_PROFILE_ID.value]
            if cheater_id not in cheater_summary:
                cheater_summary[cheater_id] = {
                    "count": 0,
                    "latest_name": "",
                    "latest_time": 0,
                }
            cheater_summary[cheater_id]["count"] += 1
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

        # Create the summary string
        summary_string = ""
        for cheater_id, data in cheater_summary.items():
            summary_string += f"Cheater ID: {cheater_id}, Report Count: {data['count']}, Latest Name: {data['latest_name']}\n"

        # Send the summary
        if summary_string:
            await ctx.send(summary_string, ephemeral=False)
        else:
            await ctx.send("No cheater reports processed.", ephemeral=True)

    @commands.hybrid_command(name="list_cheater_deaths")
    async def list_cheater_deaths(self, ctx):
        # Fetch raw data from the table
        reports = database.DatabaseManager.get_cheater_reports(
            table=database.DatabaseEnum.TABLE_CHEATERS_KILLED
        )

        if not reports:
            await ctx.send("No cheater death reports found.", ephemeral=True)
            return

        # Process the data to create a summary
        cheater_summary = {}
        for report in reports:
            cheater_id = report[database.DatabaseEnum.CHEATER_PROFILE_ID.value]
            if cheater_id not in cheater_summary:
                cheater_summary[cheater_id] = {
                    "count": 0,
                    "latest_name": "",
                    "latest_time": 0,
                }
            cheater_summary[cheater_id]["count"] += 1
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

        # Create the summary string
        summary_string = ""
        for cheater_id, data in cheater_summary.items():
            summary_string += f"Cheater ID: {cheater_id}, Report Count: {data['count']}, Latest Name: {data['latest_name']}\n"

        # Send the summary
        if summary_string:
            await ctx.send(summary_string, ephemeral=False)
        else:
            await ctx.send("No cheater death reports processed.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ShiftDonators(bot))
