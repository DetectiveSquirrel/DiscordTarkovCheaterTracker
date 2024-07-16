import logging
import time
from dataclasses import dataclass
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


@dataclass
class ReportData:
    reporter_id: int
    server_id: int
    cheater_name: str
    cheater_profile_id: int
    report_time: int
    report_type: ReportType
    notes: str = None


class ContinueButton(discord.ui.View):
    def __init__(self, bot, report_type, report_enum, original_interaction):
        super().__init__()
        self.bot = bot
        self.report_type = report_type
        self.report_enum = report_enum
        self.original_interaction = original_interaction

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary, custom_id="continue_button")
    async def continue_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug(f"Continue button clicked by {button_interaction.user}")
        if button_interaction.user != self.original_interaction.user:
            logger.warning(f"Unauthorized button click by {button_interaction.user}")
            await button_interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        logger.debug("Sending report modal")
        await button_interaction.response.send_modal(ReportModal(self.bot, self.report_type, self.report_enum))


class ReportModal(discord.ui.Modal):
    def __init__(self, bot, report_type_display, report_enum):
        super().__init__(title=f"Submit {report_type_display} Report")
        self.bot = bot
        self.report_type_display = report_type_display
        self.report_enum = report_enum

    cheater_name = discord.ui.TextInput(
        label="Player's Game Name",
        placeholder="Enter the player's game name",
        min_length=3,
        max_length=17,
    )
    cheater_profile_id = discord.ui.TextInput(
        label="Player Profile ID",
        placeholder="Enter the player's profile ID",
    )
    notes = discord.ui.TextInput(
        label="Report Notes (Optional)",
        placeholder="Enter any additional notes about the cheater.",
        style=discord.TextStyle.paragraph,
        required=False,
    )

    async def on_submit(self, modal_interaction: discord.Interaction):
        logger.debug(f"Report modal submitted by {modal_interaction.user}")

        report_data = ReportData(
            reporter_id=modal_interaction.user.id,
            server_id=modal_interaction.guild_id,
            cheater_name=self.cheater_name.value.strip(),
            cheater_profile_id=int(self.cheater_profile_id.value),
            report_time=int(time.time()),
            report_type=self.report_enum,
            notes=self.notes.value.strip() if self.notes.value else None,
        )

        if not await self.validate_report(modal_interaction, report_data):
            return

        await self.submit_report(modal_interaction, report_data)

    async def validate_report(self, interaction: discord.Interaction, report_data: ReportData) -> bool:
        if not is_valid_game_name(report_data.cheater_name):
            logger.warning(f"Invalid cheater name provided: {report_data.cheater_name}")
            embed = discord.Embed(
                title="❌ Invalid Player Name",
                description="Please enter a name between 3 and 15 characters, using only letters, numbers (max 4), underscores '_', and hyphens '-'.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

        verified_status = DatabaseManager.check_verified_legit_status(report_data.cheater_profile_id)
        if verified_status["is_verified"]:
            logger.info(f"Attempt to report verified player {report_data.cheater_name} (ID: {report_data.cheater_profile_id})")
            embed = await self.create_verified_player_embed(interaction, verified_status, report_data)
            await interaction.response.send_message(
                "This player has been verified as legitimate and cannot be reported.",
                embed=embed,
                ephemeral=True,
            )
            return False

        return True

    async def submit_report(self, interaction: discord.Interaction, report_data: ReportData):
        logger.info(f"Adding cheater report for {report_data.cheater_name} (ID: {report_data.cheater_profile_id})")
        DatabaseManager.add_cheater_report(
            reporter_user_id=report_data.reporter_id,
            server_id=report_data.server_id,
            cheater_game_name=report_data.cheater_name,
            cheater_profile_id=report_data.cheater_profile_id,
            report_time=report_data.report_time,
            report_type=report_data.report_type,
            notes=report_data.notes,
            absolved=False,
        )

        embed = self.create_report_embed(interaction, report_data)
        server_settings = DatabaseManager.get_server_settings()
        await send_to_report_channels(self.bot, server_settings, embed)

        logger.info("Report submitted successfully")
        await interaction.response.send_message(
            f"{self.report_type_display} report has been submitted successfully.",
            ephemeral=True,
            silent=True,
        )

    async def create_verified_player_embed(
        self, interaction: discord.Interaction, verified_status: dict, report_data: ReportData
    ) -> discord.Embed:
        embed = await create_already_verified_embed(interaction, self.bot, verified_status)

        last_known_game_name = verified_status["tarkov_game_names"][-1] if verified_status["tarkov_game_names"] else "Unknown"
        twitch_name = verified_status["twitch_name"]

        verifier_mentions = await self.get_verifier_mentions(verified_status)

        embed.add_field(
            name="Latest Verified Player Name",
            value=f"[{last_known_game_name}](https://tarkov.dev/player/{report_data.cheater_profile_id})",
            inline=True,
        )
        embed.add_field(
            name="Account ID",
            value=f"[{report_data.cheater_profile_id}](https://tarkov.dev/player/{report_data.cheater_profile_id})",
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
            value="\n".join(verifier_mentions),
            inline=False,
        )

        return embed

    async def get_verifier_mentions(self, verified_status: dict) -> List[str]:
        verifier_info = {}
        for verifier_id, verification_time in zip(
            verified_status["verifier_ids"],
            verified_status["verification_times"],
        ):
            if verifier_id not in verifier_info or verification_time < verifier_info[verifier_id]:
                verifier_info[verifier_id] = verification_time

        verifier_mentions = []
        for verifier_id, verification_time in verifier_info.items():
            mention = await get_user_mention(verifier_id)
            verifier_mentions.append(f"{mention} <t:{verification_time}:R>")

        return verifier_mentions

    def create_report_embed(self, interaction: discord.Interaction, report_data: ReportData) -> discord.Embed:
        embed = discord.Embed(
            title=f"'{self.report_type_display}' report has been submitted.",
            color=discord.Color.red(),
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Reported By", value=f"<@{report_data.reporter_id}>", inline=True)
        embed.add_field(name="\u200B", value=f"\u200B", inline=True)
        embed.add_field(name="Time", value=f"<t:{report_data.report_time}>", inline=True)
        embed.add_field(
            name="Player Name",
            value=f"[{report_data.cheater_name}](https://tarkov.dev/player/{report_data.cheater_profile_id})",
            inline=True,
        )
        embed.add_field(name="\u200B", value=f"\u200B", inline=True)
        embed.add_field(
            name="Account Id",
            value=f"[{report_data.cheater_profile_id}](https://tarkov.dev/player/{report_data.cheater_profile_id})",
            inline=True,
        )
        if report_data.notes:
            embed.add_field(name="Notes", value=f"```\n{report_data.notes}\n```", inline=False)
        embed.add_field(
            name="From Discord Server",
            value=f"`{interaction.guild.name}`",
            inline=False,
        )

        return embed


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
    async def report_player(self, interaction: discord.Interaction, report_type: str):
        logger.info(f"Report command called by {interaction.user} with report_type: {report_type}")

        if not await self.check_guild_configuration(interaction):
            return

        try:
            report_enum = ReportType[report_type]
            logger.debug(f"Parsed report type: {report_enum}")
        except KeyError:
            logger.warning(f"Invalid report type provided: {report_type}")
            await interaction.response.send_message("Invalid report type. Please try again.", ephemeral=True)
            return

        await self.send_instructions(interaction, report_enum)

    async def check_guild_configuration(self, interaction: discord.Interaction) -> bool:
        if not checks.is_guild_id_configured(interaction.guild_id):
            logger.warning(f"Server {interaction.guild_id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` first.",
                ephemeral=True,
            )
            return False
        return True

    async def send_instructions(self, interaction: discord.Interaction, report_enum: ReportType):
        logger.debug("Sending initial response with continue button")
        embed = discord.Embed(
            title="Instructions to Get Profile ID and Name",
            description=(
                "1. Go to [Tarkov.dev/players Page](https://tarkov.dev/players).\n"
                "2. Find the profile and copy the Profile ID from the URL (the number at the end).\n"
                "3. Copy the details into the fields and click Submit.\n\n"
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Click the button below to continue.")
        await interaction.response.send_message(
            embed=embed,
            view=ContinueButton(self.bot, REPORT_TYPE_DISPLAY[report_enum], report_enum, interaction),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(ReportAPlayer(bot))
