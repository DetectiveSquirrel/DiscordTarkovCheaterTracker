from discord.ext import commands
import discord
import logging
import db.database
import time

logger = logging.getLogger("bot")


class ReportKilledByCheater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="report_killed_by_cheater",
        description="Report that you were killed by a cheater.",
    )
    async def report_killed_by_cheater(self, ctx):
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
                    cheater_name = discord.ui.TextInput(
                        label="Cheater's Game Name",
                        placeholder="Enter the cheater's game name",
                    )
                    cheater_profile_id = discord.ui.TextInput(
                        label="Cheater Profile ID",
                        placeholder="Enter the cheater's profile ID",
                    )

                    async def on_submit(self, interaction: discord.Interaction):
                        cheater_name_value = self.cheater_name.value.strip().lower()
                        cheater_profile_id_value = self.cheater_profile_id.value
                        from_user_id_int = interaction.user.id
                        server_id_logged_in_int = interaction.guild.id
                        cheater_profile_id_int = int(cheater_profile_id_value)
                        time_reported = int(time.time())

                        db.database.DatabaseManager.add_killed_by_cheater(
                            fromUserid=from_user_id_int,
                            serverIdLoggedIn=server_id_logged_in_int,
                            cheatersgamename=cheater_name_value,
                            cheaterprofileid=cheater_profile_id_int,
                            timereported=time_reported,
                        )
                        embed = discord.Embed(
                            title="Killed by Cheater Report",
                            description="A user has reported being killed by a cheater.",
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
                            value=f"```\n{interaction.guild.name}```",
                            inline=False,
                        )

                        await interaction.response.send_message(embed=embed)

                modal = CheaterIDModal()
                await interaction.response.send_modal(modal)

        await ctx.send(
            "Please go to [tarkov.dev/players](https://tarkov.dev/players) to get the profile ID and name (id is the URL # at the end), then click the button below to continue.",
            view=ContinueButton(ctx),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(ReportKilledByCheater(bot))
