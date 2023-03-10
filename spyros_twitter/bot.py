import asyncio
import os

import aiohttp
import discord
from discord.ext import commands
from bitlyshortener import Shortener

from DATA.Database import Database


# For bitly shortener
tokens = ["62c176ee93b4489162d5bb376a60ebbfa9647757"]


async def get_prefix(bot, message):
    if not message.guild:
        return "!"

    prefix = await bot.db.fetchval('prefixes', 'prefix', f'g_id = :g_id', g_id=message.guild.id)

    if not prefix:
        return commands.when_mentioned_or("!")(bot, message)

    return commands.when_mentioned_or(prefix)(bot, message)


async def create_db():
    bot.db = await Database.create('DATA/bot.db')


async def create_aiohttp_session():
    bot.aiohttp_session = aiohttp.ClientSession()


async def close_aiohttp_session():
    await bot.aiohttp_session.close()


bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')
bot.shortener = Shortener(tokens=tokens, max_cache_size=512)

TOKEN = open('DATA/TOKEN.txt', 'r').readline().strip()

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print('------')


for cog in os.listdir("./cogs"):
    if cog.endswith(".py") and not cog.startswith("_"):
        try:
            cog = f"cogs.{cog.replace('.py', '')}"
            bot.load_extension(cog)
        except Exception as e:
            print(f"{cog} can not be loaded:")
            raise e


bot.loop.run_until_complete(create_db())
bot.loop.run_until_complete(create_aiohttp_session())
bot.run(TOKEN)

loop = asyncio.new_event_loop()
loop.run_until_complete(close_aiohttp_session())
