import discord
from discord.ext import commands
import json


async def is_guild_owner(ctx):
    return ctx.author.id == ctx.guild.owner.id

class Set_up(commands.Cog, name="Set Up"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Change the prefix for the server (default is `!`)", aliases=['pre'])
    @commands.check(is_guild_owner)
    async def prefix(self, ctx, *, pre: str):
        '''prefix [prefix]'''

        prefix = await self.bot.db.fetchone('prefixes', ['prefix'], f'g_id = :g_id', g_id=ctx.guild.id)

        if not prefix:
            await self.bot.db.insert('prefixes', ['g_id', 'prefix'], g_id=ctx.guild.id, prefix=pre)
        else:
            await self.bot.db.update('prefixes', 'prefix = :pre', pre=pre, condition=f"g_id = '{ctx.guild.id}'")

        await ctx.send(f"New prefix: `{pre}`")

def setup(bot):
    bot.add_cog(Set_up(bot))


