import re
import time
import asyncio
from typing import List

import aiohttp
import discord
from yarl import URL


def get_urls(text) -> List[str]:
    """Get a list of urls from a string"""
    # return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    # Don't care about https:// in the start
    return re.findall('((?:https?://)?(?:[A-Za-z\d\-]+\.)+[A-Za-z]+/[A-Za-z\d%?\-]*)', text)


def get_prod_url(url: URL, break_at_q) -> str:
    if break_at_q:
        return url.human_repr().split("?")[0]
    else:
        return url.human_repr().split("&")[0]


def get_good_url(info, url: URL) -> str:
    aff_link = info[0]
    prod_first = bool(info[1])
    break_at_q = bool(info[2])

    prod_url = get_prod_url(url, break_at_q)
    if prod_first:
        return prod_url + aff_link
    else:
        return aff_link + prod_url


async def expand_urls(urls: List[str], session: aiohttp.ClientSession):
    for url in urls:
        try:
            async with session.get(url) as r:
                yield r.url
        except aiohttp.InvalidURL:
            continue


def n_embed_shoes(ctx, page: int, pages: int, shoes, cur: int):
    embed = discord.Embed(
        color=ctx.author.color,
        timestamp=ctx.message.created_at
    )
    embed.set_author(name="Recently used shoes", icon_url=ctx.bot.user.avatar_url)

    text = ""
    for i, shoe in enumerate(shoes):
        shoe_index = page + i
        text += (f"{shoe_index}: Shoe name: {shoe[0]}\n"
                 f"Image: {shoe[1]}\n"
                 f"----------\n")

    embed.description = text or "None"
    embed.set_footer(text=f"Page {page + 1}/{pages}")

    return embed, cur

def n_embed_stores(ctx, page: int, pages: int, stores, cur: int):
    embed = discord.Embed(
        color=ctx.author.color,
        timestamp=ctx.message.created_at
    )
    embed.set_author(name="Recently used stores", icon_url=ctx.bot.user.avatar_url)

    text = ""
    for i, store in enumerate(stores):
        store_index = page + i
        text += (f"{store_index}: Store name: {store[0]}\n"
                 f"Image: {store[1]}\n"
                 f"----------\n")

    embed.description = text or "None"
    embed.set_footer(text=f"Page {page + 1}/{pages}")

    return embed, cur


async def create_pages(ctx, lst, func, end_text):
    pages = 1 + (len(lst) // 10) if (len(lst) % 10) >= 1 else (len(lst) // 10)
    page = 0

    embed, cur = func(ctx, page, pages, lst, 0)

    msg = await ctx.send(embed=embed)

    for em in ["⬅", "➡", "❌"]:
        await msg.add_reaction(em)

    def check(r, member):
        return member != ctx.bot.user and r.message.id == msg.id

    t_end = time.time() + 120
    while time.time() < t_end:
        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            continue

        if str(reaction.emoji) == "➡":
            await msg.remove_reaction('➡', user)
            page += 1

            if page == pages:
                page -= 1
                continue

            new_embed, cur = func(ctx, page, pages, lst, cur + 10)
            await msg.edit(embed=new_embed)

        elif str(reaction.emoji) == "⬅":
            await msg.remove_reaction('⬅', user)
            page -= 1
            if page < 0:
                page = 0
                continue

            new_embed, cur = func(ctx, page, pages, lst, cur - 10)
            await msg.edit(embed=new_embed)

        elif str(reaction.emoji) == "❌":
            await msg.remove_reaction("❌", user)
            break

    await msg.remove_reaction('⬅', ctx.bot.user)
    await msg.remove_reaction('➡', ctx.bot.user)
    await msg.remove_reaction("❌", ctx.bot.user)

    embed = discord.Embed(
        color=ctx.author.color,
        description=f"`{ctx.prefix}{ctx.command}` to open again",
        timestamp=ctx.message.created_at
    )
    embed.set_author(name=end_text,
                     icon_url=ctx.bot.user.avatar_url)

    await msg.edit(embed=embed)
