from discord.ext import commands
import discord
import logging
import settings
import db.database_management as database_management
import asyncio
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
        existing_settings = database_management.DatabaseManager.get_server_settings(serverid=guild.id)
        if existing_settings:
            database_management.DatabaseManager.update_server_settings(serverid=guild.id, channelid=channel_id_int)
            await ctx.send(f"Channel for server `{guild.name}` set to <#{channel.id}>", ephemeral=True)
        else:
            database_management.DatabaseManager.add_server_settings(serverid=guild.id, channelid=channel_id_int)
            await ctx.send(f"Channel for server `{guild.name}` changed to <#{channel.id}>", ephemeral=True)

    @commands.hybrid_command(name="add_cheater_kill")
    async def add_cheater_kill(self, ctx):
        class ContinueButton(discord.ui.View):
            @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary, custom_id="continue_button")
            async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("This button is not for you.", ephemeral=True)
                    return

                class CheaterIDModal(discord.ui.Modal, title="Submit Cheater Information"):
                    cheater_name = discord.ui.TextInput(
                        label="Cheater's Game Name",
                        placeholder="Enter the cheater's game name"
                    )
                    cheater_profile_id = discord.ui.TextInput(
                        label="Cheater Profile ID",
                        placeholder="Enter the cheater's profile ID (get it from tarkov.dev/players)"
                    )

                    async def on_submit(self, interaction: discord.Interaction):
                        cheater_name_value = self.cheater_name.value.strip().lower()
                        cheater_profile_id_value = self.cheater_profile_id.value
                        from_user_id_int = interaction.user.id
                        server_id_logged_in_int = interaction.guild.id
                        cheater_profile_id_int = int(cheater_profile_id_value)
                        time_reported = int(time.time())

                        database_management.DatabaseManager.add_cheater_killed(
                            fromUserid=from_user_id_int,
                            serverIdLoggedIn=server_id_logged_in_int,
                            cheatersgamename=cheater_name_value,
                            cheaterprofileid=cheater_profile_id_int,
                            timereported=time_reported
                        )
                        await interaction.response.send_message(f"Reporting a cheater was killed:\nUser <@{from_user_id_int}>\nReported cheater ['{cheater_name_value}' ({cheater_profile_id_int})](<https://tarkov.dev/{cheater_profile_id_int}>)\nOn server '{interaction.guild.name}'\nAt time <t:{time_reported}>")

                modal = CheaterIDModal()
                await interaction.response.send_modal(modal)

        await ctx.send(
            "Please go to [tarkov.dev/players](<https://tarkov.dev/players>) to get the profile ID and name, then click the button below to continue.",
            view=ContinueButton()
        )

    @commands.hybrid_command(name="add_killed_by_cheater")
    async def add_killed_by_cheater(self, ctx):
        class ContinueButton(discord.ui.View):
            @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary, custom_id="continue_button")
            async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("This button is not for you.", ephemeral=True)
                    return

                class CheaterIDModal(discord.ui.Modal, title="Submit Cheater Information"):
                    cheater_name = discord.ui.TextInput(
                        label="Cheater's Game Name",
                        placeholder="Enter the cheater's game name"
                    )
                    cheater_profile_id = discord.ui.TextInput(
                        label="Cheater Profile ID",
                        placeholder="Enter the cheater's profile ID (get it from tarkov.dev/players)"
                    )

                    async def on_submit(self, interaction: discord.Interaction):
                        cheater_name_value = self.cheater_name.value.strip().lower()
                        cheater_profile_id_value = self.cheater_profile_id.value
                        from_user_id_int = interaction.user.id
                        server_id_logged_in_int = interaction.guild.id
                        cheater_profile_id_int = int(cheater_profile_id_value)
                        time_reported = int(time.time())

                        database_management.DatabaseManager.add_killed_by_cheater(
                            fromUserid=from_user_id_int,
                            serverIdLoggedIn=server_id_logged_in_int,
                            cheatersgamename=cheater_name_value,
                            cheaterprofileid=cheater_profile_id_int,
                            timereported=time_reported
                        )
                        await interaction.response.send_message(f"Reporting someone was killed by a cheater:\nUser <@{from_user_id_int}>\nReported cheater ['{cheater_name_value}' ({cheater_profile_id_int})](<https://tarkov.dev/{cheater_profile_id_int}>)\nOn server '{interaction.guild.name}'\nAt time <t:{time_reported}>")

                modal = CheaterIDModal()
                await interaction.response.send_modal(modal)

        await ctx.send(
            "Please go to [tarkov.dev/players](<https://tarkov.dev/players>) to get the profile ID and name, then click the button below to continue.",
            view=ContinueButton()
        )

    @commands.hybrid_command(name="list_cheaters_killed")
    async def set_channel(self, ctx):
        # Use DatabaseManager to add or update the server settings
        summary = database_management.DatabaseManager.get_cheaters_killed_report_summary()
        # Initialize an empty string
        summary_string = ""

        # Append each cheater report to the string
        for report in summary:
            summary_string += f"Cheater ID: {report['cheater_id']}, Report Count: {report['count']}, Latest Name: {report['latest_name']}\n"

        if summary:
            await ctx.send(summary_string, ephemeral=False)
        else:
            await ctx.send(f"something happened, unsure.", ephemeral=True)

    @commands.hybrid_command(name="list_killed_by_cheaters")
    async def set_channel(self, ctx):
        # Use DatabaseManager to add or update the server settings
        summary = database_management.DatabaseManager.get_killed_by_cheaters_report_summary()
        # Initialize an empty string
        summary_string = ""

        # Append each cheater report to the string
        for report in summary:
            summary_string += f"Cheater ID: {report['cheater_id']}, Report Count: {report['count']}, Latest Name: {report['latest_name']}\n"

        if summary:
            await ctx.send(summary_string, ephemeral=False)
        else:
            await ctx.send(f"something happened, unsure.", ephemeral=True)

    @commands.hybrid_command(name="list_kills_by_cheater_for_me")
    async def list_kills_by_cheater_for_me(self, ctx, user_id: int):
        summary = database_management.DatabaseManager.get_kills_by_cheater_report_for_user(user_id)
        
        # Initialize an empty string
        summary_string = ""

        # Append each cheater report to the string
        for report in summary:
            summary_string += f"Cheater ID: {report['cheater_id']}, Report Count: {report['count']}, Latest Name: {report['latest_name']}\n"

        if summary:
            await ctx.send(summary_string, ephemeral=False)
        else:
            await ctx.send("You have no reports.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ShiftDonators(bot))
