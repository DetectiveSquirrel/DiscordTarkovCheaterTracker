import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from db.database import DatabaseManager
from helpers import checks
from helpers.pagination import Pagination
from helpers.utils import get_user_mention

logger = logging.getLogger("command")


@dataclass
class VerificationNote:
    verifier_user_id: int
    timestamp: int
    content: str


@dataclass
class VerifiedUserDetails:
    verifier_user_id: int
    verification_count: int
    first_verified_time: int
    latest_tarkov_game_name: str
    tarkov_profile_id: int
    twitch_name: str
    unique_verifiers: List[int]
    notes: List[VerificationNote]


class VerifiedDetails(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def verified_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        logger.debug(f"Verified autocomplete called with current: {current}")
        verified_users = DatabaseManager.get_all_verified_users()
        logger.debug(f"Retrieved {len(verified_users)} verified users from database")

        latest_verifications = defaultdict(lambda: {"verified_time": 0})
        for user in verified_users:
            profile_id = user["tarkov_profile_id"]
            if user["verified_time"] > latest_verifications[profile_id]["verified_time"]:
                latest_verifications[profile_id] = user

        choices = [
            app_commands.Choice(name=f"{user['tarkov_game_name']} ({user['tarkov_profile_id']})", value=str(user["tarkov_profile_id"]))
            for user in latest_verifications.values()
            if current.lower() in str(user["tarkov_profile_id"]).lower() or current.lower() in user["tarkov_game_name"].lower()
        ]

        logger.debug(f"Returning {len(choices)} autocomplete choices")
        return choices[:25]

    @app_commands.command(
        name="get_verified_details",
        description="Get detailed information about a verified user",
    )
    @app_commands.autocomplete(verified_user=verified_autocomplete)
    async def get_verified_details(self, interaction: discord.Interaction, verified_user: str):
        logger.debug(f"get_verified_details called with user: {verified_user}")

        if not await self.check_guild_configuration(interaction):
            return

        verified_user_id = await self.parse_verified_user_id(interaction, verified_user)
        if not verified_user_id:
            return

        verified_details = await self.fetch_verified_details(interaction, verified_user_id)
        if not verified_details:
            return

        embeds = await self.create_embeds(verified_details)
        await self.display_pagination(interaction, embeds)

    async def check_guild_configuration(self, interaction: discord.Interaction) -> bool:
        if not checks.is_guild_id_configured(interaction.guild.id):
            logger.debug(f"Guild {interaction.guild.id} not configured")
            await interaction.response.send_message(
                "Please configure the server with `/set_reporting_channel` and the channels id.",
                ephemeral=True,
            )
            return False
        return True

    async def parse_verified_user_id(self, interaction: discord.Interaction, verified_user: str) -> int:
        try:
            logger.debug(f"Parsing verified user ID: {verified_user}")
            return int(verified_user)
        except ValueError:
            logger.debug(f"Invalid verified user ID format: {verified_user}")
            await interaction.response.send_message("Invalid verified user ID format.", ephemeral=True)
            return None

    async def fetch_verified_details(self, interaction: discord.Interaction, verified_user_id: int) -> VerifiedUserDetails:
        logger.debug(f"Fetching comprehensive verified user details for ID: {verified_user_id}")
        details = DatabaseManager.get_comprehensive_verified_details(verified_user_id)

        if not details:
            logger.debug(f"No details found for verified user ID: {verified_user_id}")
            await interaction.response.send_message("Verified user not found.", ephemeral=True)
            return None

        # The first verification in all_verifications is the latest one
        latest_verification = details["tarkov_game_name"]  # This is already the latest name

        return VerifiedUserDetails(
            verifier_user_id=details["verifier_user_id"],
            verification_count=details["verification_count"],
            first_verified_time=details["first_verified_time"],
            latest_tarkov_game_name=latest_verification,
            tarkov_profile_id=details["tarkov_profile_id"],
            twitch_name=details.get("twitch_name"),
            unique_verifiers=details["unique_verifiers"],  # Add this line
            notes=[VerificationNote(**note) for note in details["notes"]],
        )

    async def create_embeds(self, verified_details: VerifiedUserDetails) -> List[discord.Embed]:
        logger.debug("Creating embeds")
        embeds = []

        main_embed = await self.create_main_embed(verified_details)
        embeds.append(main_embed)

        for note in verified_details.notes:
            note_embed = await self.create_note_embed(note)
            embeds.append(note_embed)

        logger.debug(f"Created {len(embeds)} embeds")
        return embeds

    async def create_main_embed(self, details: VerifiedUserDetails) -> discord.Embed:
        main_embed = discord.Embed(
            title="Verified User Details",
            color=discord.Color.green(),
        )

        initial_verifier_mention = await get_user_mention(details.verifier_user_id)
        main_embed.add_field(name="Initial Verifier", value=initial_verifier_mention, inline=True)
        main_embed.add_field(name="Total Verifications", value=f"` {str(details.verification_count)} `", inline=True)
        main_embed.add_field(name="Initial Verification", value=f"<t:{details.first_verified_time}:R>", inline=True)
        main_embed.add_field(
            name="Latest Tarkov Game Name",
            value=f"[{details.latest_tarkov_game_name}](https://tarkov.dev/player/{details.tarkov_profile_id})",
            inline=True,
        )
        main_embed.add_field(
            name="Profile ID",
            value=f"[{details.tarkov_profile_id}](https://tarkov.dev/player/{details.tarkov_profile_id})",
            inline=True,
        )

        if details.twitch_name:
            main_embed.add_field(
                name="Twitch Name",
                value=f"[{details.twitch_name}](https://twitch.tv/{details.twitch_name})",
                inline=True,
            )

        unique_verifier_mentions = [await get_user_mention(verifier_id) for verifier_id in details.unique_verifiers]
        main_embed.add_field(
            name="Unique Verifiers",
            value=", ".join(unique_verifier_mentions) if unique_verifier_mentions else "None",
            inline=False,
        )

        return main_embed

    async def create_note_embed(self, note: VerificationNote) -> discord.Embed:
        note_embed = discord.Embed(
            title="Verification Note",
            color=discord.Color.blue(),
        )
        verifier_mention = await get_user_mention(note.verifier_user_id)
        note_embed.add_field(
            name="Added By",
            value=f"{verifier_mention} <t:{note.timestamp}:R>",
            inline=False,
        )
        note_embed.add_field(
            name="Note",
            value=f"```\n{note.content}\n```",
            inline=False,
        )
        return note_embed

    async def display_pagination(self, interaction: discord.Interaction, embeds: List[discord.Embed]):
        async def get_page(page):
            return embeds[page - 1], len(embeds)

        logger.debug("Creating pagination view")
        view = Pagination(interaction, get_page, timeout=120, delete_on_timeout=True, ephemeral=True)
        await view.navigate()
        logger.info("Pagination view navigation started")


async def setup(bot):
    await bot.add_cog(VerifiedDetails(bot))
