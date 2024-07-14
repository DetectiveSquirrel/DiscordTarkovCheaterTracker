from typing import List
import discord
from discord import app_commands
from discord.ext import commands
import time
from db.database import DatabaseManager
from helpers.utils import get_user_mention
import logging
import re

logger = logging.getLogger("command")


class VerifyLegit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="verify_legit",
        description="Verify a player as legitimate and absolve them of reports.",
    )
    async def verify_legit(self, interaction: discord.Interaction):
        logger.info(f"Verify legit command called by {interaction.user}")

        if not DatabaseManager.get_server_settings(interaction.guild_id):
            logger.warning(f"Server {interaction.guild_id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` first.",
                ephemeral=True,
            )
            return

        class VerifyLegitButton(discord.ui.View):
            def __init__(self, bot):
                super().__init__()
                self.bot = bot

            @discord.ui.button(
                label="Verify Player",
                style=discord.ButtonStyle.primary,
                custom_id="verify_legit_button",
            )
            async def verify_button(
                self, button_interaction: discord.Interaction, button: discord.ui.Button
            ):
                logger.debug(
                    f"Verify legit button clicked by {button_interaction.user}"
                )
                if button_interaction.user != interaction.user:
                    logger.warning(
                        f"Unauthorized button click by {button_interaction.user}"
                    )
                    await button_interaction.response.send_message(
                        "This button is not for you.", ephemeral=True
                    )
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
                label="Player's Twitch Name",
                placeholder="Enter the player's Twitch name (optional)",
                required=False,
            )
            notes = discord.ui.TextInput(
                label="Verification Notes",
                placeholder="Enter any additional notes about the verification",
                style=discord.TextStyle.paragraph,
                required=False,
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                logger.debug(
                    f"Verify legit modal submitted by {modal_interaction.user}"
                )
                tarkov_game_name = self.tarkov_game_name.value.strip()
                tarkov_profile_id = int(self.tarkov_profile_id.value)
                twitch_name = (
                    self.twitch_name.value.strip() if self.twitch_name.value else None
                )
                notes = self.notes.value.strip() if self.notes.value else None
                verified_time = int(time.time())

                logger.debug(f"Validating Tarkov game name: {tarkov_game_name}")
                if not re.match(r"^(?!.*\d{5})[a-zA-Z0-9_-]{3,15}$", tarkov_game_name):
                    logger.warning(
                        f"Invalid Tarkov game name provided: {tarkov_game_name}"
                    )
                    embed = discord.Embed(
                        title="❌ Invalid Player Name",
                        description="Please enter a name between 3 and 15 characters, using only letters, numbers (max 4), underscores '_', and hyphens '-'.",
                        color=discord.Color.red(),
                    )
                    await modal_interaction.response.send_message(
                        embed=embed, ephemeral=True
                    )
                    return

                # Check if the player is already verified
                verified_status = DatabaseManager.check_verified_legit_status(
                    tarkov_profile_id
                )

                if verified_status["is_verified"]:
                    logger.info(
                        f"Player {tarkov_game_name} (ID: {tarkov_profile_id}) is already verified"
                    )

                    # Create embed for already verified player
                    embed = discord.Embed(
                        title="Player Already Verified as Legitimate",
                        color=discord.Color.blue(),
                    )
                    embed.set_thumbnail(url=modal_interaction.user.display_avatar.url)

                    # Get the first verifier and verification time
                    first_verifier_id = verified_status["verifier_ids"][0]
                    first_verification_time = verified_status["verification_times"][0]

                    first_verifier_mention = await get_user_mention(
                        modal_interaction.guild, self.bot, first_verifier_id
                    )

                    embed.add_field(
                        name="First Verified By",
                        value=first_verifier_mention,
                        inline=True,
                    )
                    embed.add_field(
                        name="Total Verifications",
                        value=f"` {str(verified_status["count"])} `",
                        inline=True,
                    )
                    embed.add_field(
                        name="First Verified Time",
                        value=f"<t:{first_verification_time}>",
                        inline=True,
                    )
                    embed.add_field(
                        name="Player Name",
                        value=f"[{tarkov_game_name}](https://tarkov.dev/player/{tarkov_profile_id})",
                        inline=True,
                    )
                    embed.add_field(
                        name="Account ID",
                        value=f"[{tarkov_profile_id}](https://tarkov.dev/player/{tarkov_profile_id})",
                        inline=True,
                    )

                    # Still log the new verification
                    DatabaseManager.add_verified_legit(
                        verifier_user_id=modal_interaction.user.id,
                        server_id=modal_interaction.guild_id,
                        verified_time=verified_time,
                        tarkov_game_name=tarkov_game_name,
                        tarkov_profile_id=tarkov_profile_id,
                        twitch_name=twitch_name,
                        notes=notes,
                    )

                    await modal_interaction.response.send_message(
                        "Thanks for the verification. This player was already verified as legitimate.",
                        embed=embed,
                        ephemeral=True,
                    )
                else:
                    logger.info(
                        f"Verifying player {tarkov_game_name} (ID: {tarkov_profile_id}) as legitimate"
                    )
                    DatabaseManager.add_and_mark_verified_legit(
                        verifier_user_id=modal_interaction.user.id,
                        server_id=modal_interaction.guild_id,
                        verified_time=verified_time,
                        tarkov_game_name=tarkov_game_name,
                        tarkov_profile_id=tarkov_profile_id,
                        twitch_name=twitch_name,
                        notes=notes,
                    )

                    embed = discord.Embed(
                        title="Player Verified as Legitimate",
                        color=discord.Color.green(),
                    )
                    embed.set_thumbnail(url=modal_interaction.user.display_avatar.url)
                    embed.add_field(
                        name="Verified By",
                        value=f"<@{modal_interaction.user.id}>",
                        inline=True,
                    )
                    embed.add_field(name="\u200B", value=f"\u200B", inline=True)
                    embed.add_field(
                        name="Time", value=f"<t:{verified_time}>", inline=True
                    )
                    embed.add_field(
                        name="Player Name",
                        value=f"[{tarkov_game_name}](https://tarkov.dev/player/{tarkov_profile_id})",
                        inline=True,
                    )
                    embed.add_field(
                        name="Account ID",
                        value=f"[{tarkov_profile_id}](https://tarkov.dev/player/{tarkov_profile_id})",
                        inline=True,
                    )
                    if twitch_name:
                        embed.add_field(
                            name="Twitch Name",
                            value=f"[{twitch_name}](<https://www.twitch.tv/{twitch_name}>)",
                            inline=True,
                        )
                    if notes:
                        embed.add_field(name="Notes", value=f"```\n{notes}\n```", inline=False)
                    embed.add_field(
                        name="From Discord Server",
                        value=f"'{modal_interaction.guild.name}'",
                        inline=False,
                    )

                    logger.debug("Fetching server settings for report channel")
                    server_settings = DatabaseManager.get_server_settings()
                    for setting in server_settings:
                        channel_id = setting.get("channel_id")
                        if channel_id:
                            logger.debug(
                                f"Sending verification to channel {channel_id}"
                            )
                            report_channel = self.bot.get_channel(channel_id)
                            if report_channel:
                                try:
                                    await report_channel.send(embed=embed, silent=True)
                                    logger.info(
                                        f"Verification sent to channel {channel_id}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Failed to send verification to channel {channel_id}: {e}"
                                    )
                            else:
                                logger.warning(
                                    f"Could not find report channel with ID {channel_id}"
                                )
                        else:
                            logger.warning(
                                f"No report channel configured for server settings: {setting}"
                            )

                    logger.info("Player verification submitted successfully")
                    await modal_interaction.response.send_message(
                        "Player has been verified as legitimate and all related reports have been absolved.",
                        ephemeral=True,
                    )

        logger.debug("Sending initial response with verify legit button")
        await interaction.response.send_message(
            "Please click the button below to open the verification form.",
            view=VerifyLegitButton(self.bot),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(VerifyLegit(bot))
