import logging
import time
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from db.database import REPORT_TYPE_DISPLAY, DatabaseManager, ReportType
from helpers import checks
from helpers.utils import (
    create_already_verified_embed,
    get_user_mention,
    is_valid_game_name,
    send_to_report_channels,
)

logger = logging.getLogger("command")


class ReportAPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def report_type_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        logger.debug(f"Report type autocomplete called with current: {current}")
        choices = [
            app_commands.Choice(name=REPORT_TYPE_DISPLAY[rt], value=rt.name)
            for rt in ReportType
            if current.lower() in REPORT_TYPE_DISPLAY[rt].lower()
        ]
        logger.debug(f"Returning {len(choices)} autocomplete choices")
        return choices

    @app_commands.command(name="report_player", description="Submit a report about a player.")
    @app_commands.autocomplete(report_type=report_type_autocomplete)
    async def report_player(
        self,
        interaction: discord.Interaction,
        report_type: str,
    ):
        logger.info(f"Report command called by {interaction.user} with report_type: {report_type}")
        if not checks.is_guild_configured(interaction.guild_id):
            logger.warning(f"Server {interaction.guild_id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` first.",
                ephemeral=True,
            )
            return

        try:
            report_enum = ReportType[report_type]
            logger.debug(f"Parsed report type: {report_enum}")
        except KeyError:
            logger.warning(f"Invalid report type provided: {report_type}")
            await interaction.response.send_message("Invalid report type. Please try again.", ephemeral=True)
            return

        class ContinueButton(discord.ui.View):
            def __init__(self, bot):
                super().__init__()
                self.bot = bot

            @discord.ui.button(
                label="Continue",
                style=discord.ButtonStyle.primary,
                custom_id="continue_button",
            )
            async def continue_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                logger.debug(f"Continue button clicked by {button_interaction.user}")
                if button_interaction.user != interaction.user:
                    logger.warning(f"Unauthorized button click by {button_interaction.user}")
                    await button_interaction.response.send_message("This button is not for you.", ephemeral=True)
                    return

                logger.debug("Sending report modal")
                await button_interaction.response.send_modal(ReportModal(self.bot, REPORT_TYPE_DISPLAY[report_enum], report_enum))

        class ReportModal(discord.ui.Modal, title=f"Submit {REPORT_TYPE_DISPLAY[report_enum]} Report"):
            def __init__(self, bot, report_type_display, report_enum):
                super().__init__()
                self.bot = bot
                self.report_type_display = report_type_display
                self.report_enum = report_enum

            cheater_name = discord.ui.TextInput(
                label="Player's Game Name",
                placeholder="Enter the player's game name",
                min_length=3,
                max_length=15,
            )
            cheater_profile_id = discord.ui.TextInput(
                label="Player Profile ID",
                placeholder="Enter the player's profile ID",
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                logger.debug(f"Report modal submitted by {modal_interaction.user}")

                cheater_name_value = self.cheater_name.value.strip()
                cheater_profile_id_int = int(self.cheater_profile_id.value)
                report_time = int(time.time())

                logger.debug(f"Validating cheater name: {cheater_name_value}")
                if not is_valid_game_name(cheater_name_value):
                    logger.warning(f"Invalid cheater name provided: {cheater_name_value}")
                    embed = discord.Embed(
                        title="❌ Invalid Player Name",
                        description="Please enter a name between 3 and 15 characters, using only letters, numbers (max 4), underscores '_', and hyphens '-'.",
                        color=discord.Color.red(),
                    )
                    await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                verified_status = DatabaseManager.check_verified_legit_status(cheater_profile_id_int)
                if verified_status["is_verified"]:
                    logger.info(f"Attempt to report verified player {cheater_name_value} (ID: {cheater_profile_id_int})")

                    embed = await create_already_verified_embed(modal_interaction, self.bot, verified_status)

                    last_known_game_name = verified_status["tarkov_game_names"][-1] if verified_status["tarkov_game_names"] else "Unknown"
                    twitch_name = verified_status["twitch_name"]

                    verifier_info = {}
                    for verifier_id, verification_time in zip(
                        verified_status["verifier_ids"],
                        verified_status["verification_times"],
                    ):
                        if verifier_id not in verifier_info or verification_time < verifier_info[verifier_id]:
                            verifier_info[verifier_id] = verification_time

                    verifier_mentions = []
                    for verifier_id, verification_time in verifier_info.items():
                        mention = await get_user_mention(modal_interaction.guild, self.bot, verifier_id)
                        verifier_mentions.append(f"{mention} <t:{verification_time}:R>")

                    verifier_mentions_str = "\n".join(verifier_mentions)

                    embed.add_field(
                        name="Latest Verified Player Name",
                        value=f"[{last_known_game_name}](https://tarkov.dev/player/{cheater_profile_id_int})",
                        inline=True,
                    )
                    embed.add_field(
                        name="Account ID",
                        value=f"[{cheater_profile_id_int}](https://tarkov.dev/player/{cheater_profile_id_int})",
                        inline=True,
                    )
                    if twitch_name:
                        embed.add_field(
                            name="Twitch Name",
                            value=f"[{twitch_name}](https://www.twitch.tv/{twitch_name})",
                            inline=True,
                        )
                    embed.add_field(
                        name="Verified By Users",
                        value=verifier_mentions_str,
                        inline=False,
                    )

                    await modal_interaction.response.send_message(
                        "This player has been verified as legitimate and cannot be reported.",
                        embed=embed,
                        ephemeral=True,
                    )
                    return

                logger.info(f"Adding cheater report for {cheater_name_value} (ID: {cheater_profile_id_int})")
                DatabaseManager.add_cheater_report(
                    reporter_user_id=interaction.user.id,
                    server_id=interaction.guild_id,
                    cheater_game_name=cheater_name_value,
                    cheater_profile_id=cheater_profile_id_int,
                    report_time=report_time,
                    report_type=self.report_enum,
                    absolved=False,
                )

                logger.debug("Creating report embed")
                embed = discord.Embed(
                    title=f"'{self.report_type_display}' report has been submitted.",
                    color=discord.Color.red(),
                )

                embed.set_thumbnail(url=interaction.user.display_avatar.url)

                embed.add_field(name="Reported By", value=f"<@{interaction.user.id}>", inline=True)

                embed.add_field(name="\u200B", value=f"\u200B", inline=True)

                embed.add_field(name="Time", value=f"<t:{report_time}>", inline=True)

                embed.add_field(
                    name="Player Name",
                    value=f"[{cheater_name_value}](https://tarkov.dev/player/{cheater_profile_id_int})",
                    inline=True,
                )

                embed.add_field(name="\u200B", value=f"\u200B", inline=True)

                embed.add_field(
                    name="Account Id",
                    value=f"[{cheater_profile_id_int}](https://tarkov.dev/player/{cheater_profile_id_int})",
                    inline=True,
                )
                embed.add_field(
                    name="From Discord Server",
                    value=f"`{interaction.guild.name}`",
                    inline=False,
                )

                logger.debug("Fetching server settings for report channel")
                server_settings = DatabaseManager.get_server_settings()
                await send_to_report_channels(self.bot, server_settings, embed)

                logger.info("Report submitted successfully")
                await modal_interaction.response.send_message(
                    f"{self.report_type_display} report has been submitted successfully.",
                    ephemeral=True,
                    silent=True,
                )

        logger.debug("Sending initial response with continue button")
        await interaction.response.send_message(
            "Please go to [tarkov.dev/players](https://tarkov.dev/players) to get the profile ID and name (id is the URL # at the end), then click the button below to continue.",
            view=ContinueButton(self.bot),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(ReportAPlayer(bot))
