import discord
from discord.ext import commands

import os

from DATA.Database import Database

async def get_prefix(bot, message):
    if not message.guild:
        return "!"

    prefixe = await bot.db.fetchval('prefixes', 'prefix', f'g_id = :g_id', g_id=message.guild.id)

    if not prefixe:
        return commands.when_mentioned_or("!")(bot, message)

    return commands.when_mentioned_or(prefixe)(bot, message)


bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')

bot.db = Database('DATA/bot.db')

TOKEN = open('DATA/TOKEN.txt', 'r').readline().strip()

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print('------')

    bot.channels_words = await get_channels_words()

async def get_channels_words():
    words = await bot.db.fetchall('words', ['g_id', 'chn_id', 'word'])
    if words is None:
        return dict()

    channels_words = dict()
    for word in words:
        g_id = str(word[0])
        chn_id = str(word[1])

        if g_id not in channels_words:
            channels_words[g_id] = dict()

        if chn_id not in channels_words[g_id]:
            channels_words[g_id][chn_id] = list()

        channels_words[g_id][chn_id].append(word[2])

    return channels_words



for cog in os.listdir("./cogs"):
    if cog.endswith(".py") and not cog.startswith("_"):
        try:
            cog = f"cogs.{cog.replace('.py', '')}"
            bot.load_extension(cog)
        except Exception as e:
            print(f"{cog} can not be loaded:")
            raise e

bot.run(TOKEN)
