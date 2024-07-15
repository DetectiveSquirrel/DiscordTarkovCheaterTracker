import asyncio
import time
from typing import Callable, Optional

import discord


class Pagination(discord.ui.View):
    def __init__(
        self,
        interaction: discord.Interaction,
        get_page: Callable,
        timeout: int = 30,
        delete_on_timeout: bool = False,
        ephemeral: bool = False,
    ):
        super().__init__(timeout=None)  # Set to None to manage timeout manually
        self.interaction = interaction
        self.get_page = get_page
        self.total_pages: Optional[int] = None
        self.index = 1
        self.timeout_duration = timeout
        self.timeout_timestamp = None
        self.task = None
        self.delete_on_timeout = delete_on_timeout
        self.timeout_field_name = "*Command Timeout:*"
        self.ephemeral = ephemeral
        self.embed_color = None

    async def navigate(self):
        await self._update_page(initial=True)

    async def edit_page(self, interaction: discord.Interaction):
        await self._update_page(interaction)

    async def _update_page(self, interaction: Optional[discord.Interaction] = None, initial: bool = False):
        self._update_timeout()
        embed, self.total_pages = await self.get_page(self.index)
        self._update_buttons()
        self._update_timeout_field(embed)
        self._update_footer(embed)

        if self.embed_color is None and embed.color:
            self.embed_color = embed.color
        else:
            embed.color = self.embed_color

        if initial:
            await self.interaction.response.send_message(embed=embed, view=self, silent=True, ephemeral=self.ephemeral)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

        if not self.task:
            self.task = asyncio.create_task(self._check_timeout())

    def _update_timeout(self):
        self.timeout_timestamp = int(time.time()) + self.timeout_duration

    def _update_timeout_field(self, embed: discord.Embed):
        timeout_value = f"*<t:{self.timeout_timestamp}:R>*"
        for index, field in enumerate(embed.fields):
            if field.name == self.timeout_field_name:
                embed.set_field_at(index, name=self.timeout_field_name, value=timeout_value, inline=False)
                return
        embed.add_field(name=self.timeout_field_name, value=timeout_value, inline=False)

    def _update_footer(self, embed: discord.Embed):
        embed.set_footer(text=f"Page {self.index} of {self.total_pages}")

    def _update_buttons(self):
        self.children[0].disabled = self.index == 1
        self.children[1].disabled = self.index == 1
        self.children[2].disabled = self.index == self.total_pages
        self.children[3].disabled = self.index == self.total_pages

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.blurple)
    async def first(self, interaction: discord.Interaction, button: discord.Button):
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.Button):
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.Button):
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.blurple)
    async def last(self, interaction: discord.Interaction, button: discord.Button):
        self.index = self.total_pages
        await self.edit_page(interaction)

    async def _check_timeout(self):
        while True:
            await asyncio.sleep(1)  # Check every second
            if time.time() > self.timeout_timestamp:
                await self._on_timeout()
                break

    async def _on_timeout(self):
        try:
            message = await self.interaction.original_response()
            if self.delete_on_timeout:
                await message.delete()
            else:
                embed = discord.Embed(description="This interaction has timed out.")
                await message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass
        self.stop()

    @staticmethod
    def compute_total_pages(total_items: int, results_per_page: int) -> int:
        return ((total_items - 1) // results_per_page) + 1
