import asyncio
from datetime import datetime
from typing import Optional, Iterable

import discord
import aiosqlite
from discord.ext import commands

from utils import expand_urls, get_good_url, create_pages, n_embed_shoes, n_embed_stores


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Create affiliate links")
    async def link(self, ctx, url: str):
        """link [url]"""
        # Even though it's one url `expand_url` is a generator that accepts a list
        # This is fine
        # Also it's possible the url is not a short url, this is fine as well
        urls = [url]
        good_urls = list()
        async for url in expand_urls(urls, self.bot.aiohttp_session):
            domain = url.host
            domain = domain.strip("www.")

            info = await self.bot.db.fetchone(
                "aff",
                ["affLink", "prod_first", "break_at_q"],
                "domain=:d",
                d=domain
            )
            if info is None:
                # Some links have a /{area code} part as well so we check in case this is one of them
                try:
                    code = url.parts[1]
                except IndexError:
                    continue
                else:
                    domain = domain + f"/{code}"
                    info = await self.bot.db.fetchone(
                        "aff",
                        ["affLink", "prod_first", "break_at_q"],
                        "domain=:d",
                        d=domain
                    )
                    if info is None:
                        continue

            good_urls.append(get_good_url(info, url))

        shorted_urls = self.bot.shortener.shorten_urls(good_urls)
        for final in shorted_urls:
            await ctx.send(final)

    async def get_answer(self, author: discord.Member, chn: discord.TextChannel, qualifies=None) -> Optional[str]:
        def check(msg):
            return msg.author == author and msg.channel == chn

        # qualifies is a list of strings or None, if the reply is in that, we return it.
        # If qualifies is None we assume anything is fine so we return it.
        while True:
            try:
                message = await self.bot.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                await chn.send("Too much time passes, you will have to try again.")
                return None
            else:
                cont = message.content.lower()
                if qualifies is None or cont.split()[0] in qualifies:
                    return cont
                else:
                    await chn.send("Wrong answer, please try again.")

    async def select_shoe(self, ctx: commands.Context, shoes: Iterable[aiosqlite.Row]) -> Optional[aiosqlite.Row]:
        await ctx.send("Reply with the index of the shoe you want to use.")
        await create_pages(ctx, shoes, n_embed_shoes, "Recently used shoes closed")

        answer = await self.get_answer(ctx.author, ctx.channel, range(len(shoes)))
        if answer is None:
            return None

        index = int(answer.strip()) - 1

        return shoes[index]

    async def select_store(self, ctx: commands.Context, stores: Iterable[aiosqlite.Row]) -> Optional[aiosqlite.Row]:
        await ctx.send("Reply with the index of the shoe you want to use.")
        await create_pages(ctx, stores, n_embed_stores, "Recently used stores closed")

        answer = await self.get_answer(ctx.author, ctx.channel, range(len(stores)))
        if answer is None:
            return None

        index = int(answer.strip()) - 1

        return stores[index]

    async def update_shoe_date(self, shoe):
        await self.bot.db.update(
            "shoe",
            "last_used = :now",
            "shoe_name = :name",
            name=shoe[0],
            now=datetime.now().isoformat()
        )

    async def update_store_date(self, store):
        await self.bot.db.update(
            "stores",
            "last_used = :now",
            "store_name = :name",
            name=store[0],
            now=datetime.now().isoformat()
        )

    async def update_shoe_price(self, shoe, new_price: float):
        await self.bot.db.update(
            "shoe",
            "last_price = :price",
            "shoe_name = :name",
            name=shoe[0],
            price=new_price
        )

    @commands.command(brief="Create an embed. Default destination is the channel the command was called in")
    async def embed(self, ctx, channel: discord.TextChannel = None):
        """embed (destination)"""
        channel = channel or ctx.channel
        embed = discord.Embed()

        await ctx.send(
            "**Select shoe**\n"
            "**a**: List recently used shoes\n"
            "**b**: Search for a shoe not shown (write the shoe name as well)\n"
            "**c**: Add new shoe (write the shoe name as well)"
        )
        answer = await self.get_answer(ctx.author, ctx.channel, ["a", "b", "c"])
        if answer is None:
            # TimeoutError
            return
        elif answer == "a":
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                c = await db.execute(
                    """
                        SELECT shoe_name, image, last_used, last_price
                          FROM shoe 
                      ORDER BY date(last_used)
                         LIMIT 20 
                    """
                )
                last_used = await c.fetchall()
                await c.close()

            shoe = await self.select_shoe(ctx, last_used)
            if shoe is None:
                await ctx.send("You took too long to answer")
                return

            await self.update_shoe_date(shoe)
        elif answer.startswith("b"):
            shoe = await self.bot.db.fetchone(
                "shoe",
                ["shoe_name", "image", "last_used", "last_price"],
                "name = :name",
                name=" ".join(answer.split()[1:])
            )
            if shoe is None:
                await ctx.send(f"I'm sorry I didn't find a shoe named `{' '.join(answer.split()[1:])}`")
                return

            await self.update_shoe_date(shoe)
        elif answer.startswith("c"):
            shoe_name = " ".join(answer.split()[1:])
            await ctx.send("Enter a url for the shoe's image")
            answer = await self.get_answer(ctx.author, ctx.channel)
            if answer is None:
                await ctx.send("You took too long to reply, sorry")
                return
            shoe_url = answer
            last_used = datetime.now().isoformat()
            await ctx.send("Enter a price for the shoe")
            answer = await self.get_answer(ctx.author, ctx.channel)
            if answer is None:
                await ctx.send("You took too long to reply, sorry")
                return
            try:
                shoe_price = float(answer.strip())
            except ValueError:
                await ctx.send("You took too long to reply, sorry")
                return

            shoe = (shoe_name, shoe_url, last_used, shoe_price)
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO shoe (shoe_name, image, last_used, last_price)
                         VALUES ($1, $2, $3, $4)
                    """, shoe
                )

        embed.title = shoe[0]
        embed.set_image(shoe[1])

        await ctx.send(
            "**Select store**\n"
            "**a**: List recently used stores\n"
            "**b**: Add new store (write the store name as well)"
        )
        answer = await self.get_answer(ctx.author, ctx.channel, ["a", "b"])
        if answer is None:
            await ctx.send("You took too long to reply, sorry")
            return
        elif answer == "a":
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                c = await db.execute(
                    """
                        SELECT store_name, image, last_used
                          FROM stores
                      ORDER BY date(last_used)
                         LIMIT 20 
                    """
                )
                last_used = await c.fetchall()
                await c.close()

            store = await self.select_shoe(ctx, last_used)
            if store is None:
                await ctx.send("You took too long to answer")
                return

            await self.update_store_date(store)
        elif answer.startswith("b"):
            name = " ".join(answer.split()[1:])
            await ctx.send("Enter a url for the store's image")
            answer = await self.get_answer(ctx.author, ctx.channel)
            if answer is None:
                await ctx.send("You took too long to reply")
                return
            url = answer
            store = (name, url, datetime.now().isoformat())
            async with aiosqlite.connect(self.bot.db.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO stores (store_name, image, last_used)
                         VALUES ($1, $2, $3)
                    """, store
                )

        embed.add_field(name="Store", value=f"[{store[0]}]({store[1]})")

        await ctx.send("Enter a url to be used as hypertext for the shoe name")
        url = await self.get_answer(ctx.author, ctx.channel)
        if url is None:
            await ctx.send("You took too long to reply, sorry")
            return

        embed.url = url

        await ctx.send("Select a region")
        region = await self.get_answer(ctx.author, ctx.channel)
        if region is None:
            await ctx.send("You took too long to reply, sorry")
            return

        embed.add_field(name="Region", value=region)

        await ctx.send(
            "Select:\n"
            "**a**: Instore 🚪\n"  # There is an invisible :door: emoji before the \n so yeah.. (try paste it to discord)
            "**b**: Shipping 📦\n"
            "**c**: Instore & Shipping 🚪 + 📦"
        )
        answer = await self.get_answer(ctx.author, ctx.channel, ["a", "b", "c"])
        if answer is None:
            await ctx.send("You took too long to reply, sorry")
            return
        elif answer == "a":
            take_from = "Instore 🚪"
        elif answer == "b":
            take_from = "Shipping 📦"
        elif answer == "c":
            take_from = "Instore & Shipping 🚪 + 📦"

        embed.add_field(name=take_from, value="_ _")

        await ctx.send(
            "**Select price**\n"
            f"**a**: Use last used price for this shoe ({shoe[-1]})\n"
            "**b**: New price (write the price as well)"
        )
        answer = await self.get_answer(ctx.author, ctx.channel, ["a", "b"])
        if answer is None:
            await ctx.send("You took too long to reply, sorry")
            return
        elif answer == "a":
            shoe_price = shoe[-1]
        elif answer.startswith("b"):
            try:
                shoe_price = float(answer.split()[1])
            except ValueError:
                await ctx.send("You didn't send a valid price, sorry")
                return

            await self.update_shoe_price(shoe, shoe_price)


        embed.add_field(name="Price", value=shoe_price)

        await ctx.send("Does this look good? [y/n]", embed=embed)
        answer = await self.get_answer(ctx.author, ctx.channel, ["y", "n"])
        if answer is None:
            await ctx.send("You took too long to reply, sorry")
            return
        elif answer == "y":
            await channel.send(embed=embed)
        elif answer == "n":
            await ctx.send("Cancelling..")


def setup(bot):
    bot.add_cog(Misc(bot))
