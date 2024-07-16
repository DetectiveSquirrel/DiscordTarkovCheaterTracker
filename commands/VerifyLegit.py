import logging
import time
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands

from db.database import DatabaseManager
from helpers.utils import (
    create_already_verified_embed,
    is_valid_game_name,
    send_to_report_channels,
)

logger = logging.getLogger("command")


@dataclass
class VerificationData:
    verifier_id: int
    server_id: int
    tarkov_game_name: str
    tarkov_profile_id: int
    verified_time: int
    twitch_name: str = None
    notes: str = None


class VerifyLegitButton(discord.ui.View):
    def __init__(self, bot, original_interaction):
        super().__init__()
        self.bot = bot
        self.original_interaction = original_interaction

    @discord.ui.button(
        label="Verify Player",
        style=discord.ButtonStyle.primary,
        custom_id="verify_legit_button",
    )
    async def verify_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug(f"Verify legit button clicked by {button_interaction.user}")
        if button_interaction.user != self.original_interaction.user:
            logger.warning(f"Unauthorized button click by {button_interaction.user}")
            await button_interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        logger.debug("Sending verify legit modal")
        await button_interaction.response.send_modal(VerifyLegitModal(self.bot))


class VerifyLegitModal(discord.ui.Modal, title="Verify Player as Legitimate"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    tarkov_game_name = discord.ui.TextInput(
        label="Player's Tarkov Game Name",
        placeholder="Enter the player's Tarkov game name",
        min_length=3,
        max_length=15,
    )
    tarkov_profile_id = discord.ui.TextInput(
        label="Player's Tarkov Profile ID",
        placeholder="Enter the player's Tarkov profile ID",
    )
    twitch_name = discord.ui.TextInput(
        label="Player's Twitch Name (Optional)",
        placeholder="Enter the player's Twitch name (optional)",
        required=False,
    )
    notes = discord.ui.TextInput(
        label="Verification Notes (Optional)",
        placeholder="Enter any additional notes about the verification.",
        style=discord.TextStyle.paragraph,
        required=False,
    )

    async def on_submit(self, modal_interaction: discord.Interaction):
        logger.debug(f"Verify legit modal submitted by {modal_interaction.user}")

        verification_data = VerificationData(
            verifier_id=modal_interaction.user.id,
            server_id=modal_interaction.guild_id,
            tarkov_game_name=self.tarkov_game_name.value.strip(),
            tarkov_profile_id=int(self.tarkov_profile_id.value),
            verified_time=int(time.time()),
            twitch_name=self.twitch_name.value.strip() if self.twitch_name.value else None,
            notes=self.notes.value.strip() if self.notes.value else None,
        )

        if not await self.validate_verification(modal_interaction, verification_data):
            return

        await self.process_verification(modal_interaction, verification_data)

    async def validate_verification(self, interaction: discord.Interaction, verification_data: VerificationData) -> bool:
        logger.debug(f"Validating Tarkov game name: {verification_data.tarkov_game_name}")
        if not is_valid_game_name(verification_data.tarkov_game_name):
            logger.warning(f"Invalid Tarkov game name provided: {verification_data.tarkov_game_name}")
            embed = discord.Embed(
                title="❌ Invalid Player Name",
                description="Please enter a name between 3 and 15 characters, using only letters, numbers (max 4), underscores '_', and hyphens '-'.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def process_verification(self, interaction: discord.Interaction, verification_data: VerificationData):
        verified_status = DatabaseManager.check_verified_legit_status(verification_data.tarkov_profile_id)

        if verified_status["is_verified"]:
            await self.handle_already_verified(interaction, verification_data, verified_status)
        else:
            await self.handle_new_verification(interaction, verification_data)

    async def handle_already_verified(self, interaction: discord.Interaction, verification_data: VerificationData, verified_status: dict):
        logger.info(f"Player {verification_data.tarkov_game_name} (ID: {verification_data.tarkov_profile_id}) is already verified")

        embed = await create_already_verified_embed(interaction, self.bot, verified_status)
        embed.add_field(
            name="Player Name",
            value=f"[{verification_data.tarkov_game_name}](https://tarkov.dev/player/{verification_data.tarkov_profile_id})",
            inline=True,
        )
        embed.add_field(
            name="Account ID",
            value=f"[{verification_data.tarkov_profile_id}](https://tarkov.dev/player/{verification_data.tarkov_profile_id})",
            inline=True,
        )

        DatabaseManager.add_verified_legit(
            verifier_user_id=verification_data.verifier_id,
            server_id=verification_data.server_id,
            verified_time=verification_data.verified_time,
            tarkov_game_name=verification_data.tarkov_game_name,
            tarkov_profile_id=verification_data.tarkov_profile_id,
            twitch_name=verification_data.twitch_name,
            notes=verification_data.notes,
        )

        await interaction.response.send_message(
            "Thanks for the verification. This player was already verified as legitimate.",
            embed=embed,
            ephemeral=True,
        )

    async def handle_new_verification(self, interaction: discord.Interaction, verification_data: VerificationData):
        logger.info(f"Verifying player {verification_data.tarkov_game_name} (ID: {verification_data.tarkov_profile_id}) as legitimate")
        DatabaseManager.add_and_mark_verified_legit(
            verifier_user_id=verification_data.verifier_id,
            server_id=verification_data.server_id,
            verified_time=verification_data.verified_time,
            tarkov_game_name=verification_data.tarkov_game_name,
            tarkov_profile_id=verification_data.tarkov_profile_id,
            twitch_name=verification_data.twitch_name,
            notes=verification_data.notes,
        )

        embed = self.create_verification_embed(interaction, verification_data)

        logger.debug("Fetching server settings for report channel")
        server_settings = DatabaseManager.get_server_settings()
        await send_to_report_channels(self.bot, server_settings, embed)

        logger.info("Player verification submitted successfully")
        await interaction.response.send_message(
            "Player has been verified as legitimate and all related reports have been absolved.",
            ephemeral=True,
        )

    def create_verification_embed(self, interaction: discord.Interaction, verification_data: VerificationData) -> discord.Embed:
        embed = discord.Embed(
            title="Player Verified as Legitimate",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Verified By", value=f"<@{verification_data.verifier_id}>", inline=True)
        embed.add_field(name="\u200B", value=f"\u200B", inline=True)
        embed.add_field(name="Time", value=f"<t:{verification_data.verified_time}>", inline=True)
        embed.add_field(
            name="Player Name",
            value=f"[{verification_data.tarkov_game_name}](https://tarkov.dev/player/{verification_data.tarkov_profile_id})",
            inline=True,
        )
        embed.add_field(
            name="Account ID",
            value=f"[{verification_data.tarkov_profile_id}](https://tarkov.dev/player/{verification_data.tarkov_profile_id})",
            inline=True,
        )
        if verification_data.twitch_name:
            embed.add_field(
                name="Twitch Name",
                value=f"[{verification_data.twitch_name}](https://www.twitch.tv/{verification_data.twitch_name})",
                inline=True,
            )
        if verification_data.notes:
            embed.add_field(name="Notes", value=f"```\n{verification_data.notes}\n```", inline=False)
        embed.add_field(name="From Discord Server", value=f"'{interaction.guild.name}'", inline=False)
        return embed


class VerifyLegit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="verify_legit",
        description="Verify a player as legitimate and absolve them of reports.",
    )
    async def verify_legit(self, interaction: discord.Interaction):
        logger.info(f"Verify legit command called by {interaction.user}")

        if not await self.check_guild_configuration(interaction):
            return

        await self.send_instructions(interaction)

    async def check_guild_configuration(self, interaction: discord.Interaction) -> bool:
        if not DatabaseManager.get_server_settings(interaction.guild_id):
            logger.warning(f"Server {interaction.guild_id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` first.",
                ephemeral=True,
            )
            return False
        return True

    async def send_instructions(self, interaction: discord.Interaction):
        logger.debug("Sending initial response with verify legit button")
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
            view=VerifyLegitButton(self.bot, interaction),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(VerifyLegit(bot))
