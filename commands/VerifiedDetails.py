import logging

import discord
from discord import app_commands
from discord.ext import commands

from db.database import DatabaseManager
from helpers import checks
from helpers.pagination import Pagination
from helpers.utils import get_user_mention

logger = logging.getLogger("command")


class VerifiedDetails(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def verified_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        logger.debug(f"Verified autocomplete called with current: {current}")
        verified_users = DatabaseManager.get_all_verified_users()
        logger.debug(f"Retrieved {len(verified_users)} verified users from database")

        choices = []
        for user in verified_users:
            if current.lower() in str(user["tarkov_profile_id"]).lower() or current.lower() in user["tarkov_game_name"].lower():
                choice_name = f"{user['tarkov_game_name']} ({user['tarkov_profile_id']})"
                choices.append(app_commands.Choice(name=choice_name, value=str(user["tarkov_profile_id"])))

        logger.debug(f"Returning {len(choices)} autocomplete choices")
        return choices[:25]

    @app_commands.command(
        name="get_verified_details",
        description="Get detailed information about a verified user",
    )
    @app_commands.autocomplete(verified_user=verified_autocomplete)
    async def get_verified_details(self, interaction: discord.Interaction, verified_user: str):
        logger.debug(f"get_verified_details called with user: {verified_user}")

        if not checks.is_guild_id_configured(interaction.guild.id):
            logger.debug(f"Guild {interaction.guild.id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return

        try:
            logger.debug(f"Parsing verified user ID: {verified_user}")
            verified_user_id = int(verified_user)
        except ValueError:
            logger.debug(f"Invalid verified user ID format: {verified_user}")
            await interaction.response.send_message("Invalid verified user ID format.", ephemeral=True)
            return

        logger.debug(f"Fetching comprehensive verified user details for ID: {verified_user_id}")
        verified_details = DatabaseManager.get_comprehensive_verified_details(verified_user_id)

        if not verified_details:
            logger.debug(f"No details found for verified user ID: {verified_user_id}")
            await interaction.response.send_message("Verified user not found.", ephemeral=True)
            return

        logger.debug("Creating embeds")
        embeds = []

        # Create the main embed
        main_embed = discord.Embed(
            title="Verified User Details",
            color=discord.Color.green(),
        )
        
        verifier_mention = await get_user_mention(interaction.guild, self.bot, verified_details["verifier_user_id"])
        main_embed.add_field(
            name="Initial Verifier",
            value=f"{verifier_mention}",
            inline=True,
        )

        main_embed.add_field(
            name="Total Verifications",
            value=str(verified_details["verification_count"]),
            inline=True,
        )

        main_embed.add_field(
            name="Initial Verification",
            value=f"<t:{verified_details['first_verified_time']}:R>",
            inline=True,
        )
        main_embed.add_field(
            name="Tarkov Game Name",
            value=f"[{verified_details['tarkov_game_name']}](https://tarkov.dev/player/{verified_details['tarkov_profile_id']})",
            inline=True,
        )

        main_embed.add_field(
            name="Profile ID",
            value=f"[{verified_details['tarkov_profile_id']}](https://tarkov.dev/player/{verified_details['tarkov_profile_id']})",
            inline=True,
        )

        if verified_details["twitch_name"]:
            main_embed.add_field(
                name="Twitch Name",
                value=f"[{verified_details['twitch_name']}](https://twitch.tv/{verified_details['twitch_name']})",
                inline=True,
            )

        embeds.append(main_embed)

        # Create embeds for each note
        for note in verified_details["notes"]:
            note_embed = discord.Embed(
                title="Verification Note",
                color=discord.Color.blue(),
            )
            verifier_mention = await get_user_mention(interaction.guild, self.bot, note["verifier_user_id"])
            note_embed.add_field(
                name="Added By",
                value=f"{verifier_mention} <t:{note['timestamp']}:R>",
                inline=False,
            )
            note_embed.add_field(
                name="Note",
                value=f"```\n{note["content"]}\n```",
                inline=False,
            )
            embeds.append(note_embed)

        logger.debug(f"Created {len(embeds)} embeds")

        async def get_page(page):
            return embeds[page - 1], len(embeds)

        logger.debug("Creating pagination view")
        view = Pagination(interaction, get_page, timeout=120, delete_on_timeout=True, ephemeral=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(VerifiedDetails(bot))
