from collections import deque
from datetime import datetime
import discord
from discord.ext import commands
from discord.ext.commands import Context

from books import BestBooks, readable_skyblock_book_name

import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


class PaginationView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed]) -> None:
        super().__init__()

        self.embeds = embeds
        self.queue = deque(embeds)
        self.initial = embeds[0]
        self.len = len(embeds)
        self.current_page = 1

        self.children[0].disabled = True

    async def update(self, interaction: discord.Interaction):
        if self.current_page == self.len:
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False

        if self.current_page == 1:
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False

        await interaction.edit_original_response(view=self)

    @discord.ui.button(emoji="◀️")
    async def previous(self, interaction: discord.Interaction, _):
        # this rotation thing is hella confusing.
        self.queue.rotate(1)
        embed = self.queue[0]
        self.current_page -= 1
        await interaction.response.edit_message(embed=embed)
        await self.update(interaction)

    @discord.ui.button(emoji="▶️")
    async def next(self, interaction: discord.Interaction, _):
        self.queue.rotate(-1)
        embed = self.queue[0]
        self.current_page += 1
        await interaction.response.edit_message(embed=embed)
        await self.update(interaction)


@bot.command()
async def check_best_books(ctx: Context):
    books = await BestBooks.fetch()

    if not books.books:
        await ctx.send("Unsuccessful api request.")
        return

    embeds = []
    for idx, book_chunk in enumerate(books.as_chunks(3)):
        embed = discord.Embed(
            title="Best combinable books for profit",
            description="Here are the currently most profitable *(according to their GS (glob's score))* combinable books from book 1 to book 5.",
            colour=0x00B0F4,
            timestamp=datetime.now(),
        )

        rank = 1 + 3 * idx
        for book_name, book in book_chunk.items():
            embed.add_field(
                name=f"#{rank} ➜ {readable_skyblock_book_name(book_name)} (GS of {book.score:,.2f})",
                value=f"▸**Buy order for 16x {book.min.readable_name} at:** {book.min.buy_order_price * 16:,.2f} coins \n"
                f"⠀       ▸{book.min.buy_order_price:,.2f} coins per unit.\n"
                f"⠀       ▸{book.min.weekly_instant_sells} units sold instantly in the last week.\n"
                f"▸**Sell order for {book.max.readable_name} at:** {book.max.sell_order_price:,.2f} coins \n"
                f"⠀       ▸Total margin: {book.margin:,.2f} coins\n"
                f"⠀       ▸{book.max.weekly_instant_buys} units bought instantly in the last week.",
                inline=False,
            )

            rank += 1

        embed.set_footer(
            icon_url="https://cdn.discordapp.com/avatars/802900343393615932/3016cbdbad93f6b8799afc7f8c00f290.webp?size=80",
        )

        embeds.append(embed)

    view = PaginationView(embeds)

    await ctx.send(embed=view.initial, view=view)


bot.run(os.environ["TOKEN"])
