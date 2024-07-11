import discord
from discord.ext import commands
import time
import db.database
import logging

logger = logging.getLogger("bot")


class ReportCheaterKill(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="report_cheater_kill", description="Report a cheater that has been killed."
    )
    async def add_cheater_kill(self, ctx):
        class ContinueButton(discord.ui.View):
            def __init__(self, ctx):
                super().__init__()
                self.ctx = ctx
                self.interaction = None

            @discord.ui.button(
                label="Continue",
                style=discord.ButtonStyle.primary,
                custom_id="continue_button",
            )
            async def continue_button(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                self.interaction = interaction
                if interaction.user != self.ctx.author:
                    await interaction.response.send_message(
                        "This button is not for you.", ephemeral=True
                    )
                    return

                class CheaterIDModal(
                    discord.ui.Modal, title="Submit Cheater Information"
                ):
                    def __init__(self, ctx):
                        super().__init__()
                        self.ctx = ctx

                    cheater_name = discord.ui.TextInput(
                        label="Cheater's Game Name",
                        placeholder="Enter the cheater's game name",
                    )
                    cheater_profile_id = discord.ui.TextInput(
                        label="Cheater Profile ID",
                        placeholder="Enter the cheater's profile ID",
                    )

                    async def on_submit(self, interaction: discord.Interaction):
                        logger.debug("on_submit called")
                        cheater_name_value = self.cheater_name.value.strip().lower()
                        cheater_profile_id_value = self.cheater_profile_id.value
                        from_user_id_int = interaction.user.id
                        server_id_logged_in_int = interaction.guild.id
                        cheater_profile_id_int = int(cheater_profile_id_value)
                        time_reported = int(time.time())

                        logger.debug(f"Cheater Name: {cheater_name_value}")
                        logger.debug(f"Cheater Profile ID: {cheater_profile_id_int}")
                        logger.debug(f"Reported by User ID: {from_user_id_int}")
                        logger.debug(f"Server ID: {server_id_logged_in_int}")
                        logger.debug(f"Time Reported: {time_reported}")

                        db.database.DatabaseManager.add_cheater_killed(
                            fromUserid=from_user_id_int,
                            serverIdLoggedIn=server_id_logged_in_int,
                            cheatersgamename=cheater_name_value,
                            cheaterprofileid=cheater_profile_id_int,
                            timereported=time_reported,
                        )

                        logger.debug("Database entry added")

                        embed = discord.Embed(
                            title="Cheater Kill Report",
                            description="A cheater has been reported killed.",
                            color=discord.Color.red(),
                        )

                        embed.add_field(
                            name="By User", value=f"<@{from_user_id_int}>", inline=True
                        )
                        embed.add_field(
                            name="Time", value=f"<t:{time_reported}>", inline=True
                        )
                        embed.add_field(
                            name="Cheater",
                            value=f"[{cheater_name_value} ({cheater_profile_id_int})](https://tarkov.dev/player/{cheater_profile_id_int})",
                            inline=False,
                        )
                        embed.add_field(
                            name="Server",
                            value=f"'{interaction.guild.name}'",
                            inline=False,
                        )

                        # Send report to all configured report channels
                        logger.debug("Fetching server settings")
                        server_settings = (
                            db.database.DatabaseManager.get_server_settings()
                        )
                        for setting in server_settings:
                            report_channel_id = setting.get("channelid")
                            if report_channel_id:
                                report_channel = self.ctx.bot.get_channel(
                                    report_channel_id
                                )
                                if report_channel:
                                    logger.debug(
                                        f"Sending report to channel ID: {report_channel_id}"
                                    )
                                    await report_channel.send(embed=embed)

                        await interaction.response.send_message(
                            "Report sent to all configured channels.", ephemeral=True
                        )

                modal = CheaterIDModal(ctx)
                await interaction.response.send_modal(modal)

        await ctx.send(
            "Please go to [tarkov.dev/players](https://tarkov.dev/players) to get the profile ID and name (id is the URL # at the end), then click the button below to continue.",
            view=ContinueButton(ctx),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(ReportCheaterKill(bot))
