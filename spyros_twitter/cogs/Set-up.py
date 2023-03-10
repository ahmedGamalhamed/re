import discord
from discord.ext import commands


async def is_guild_owner(ctx):
    return ctx.author.id == ctx.guild.owner.id

class Set_up(commands.Cog, name="Set Up"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Change the prefix for the server (default is `!`)", aliases=['pre'])
    @commands.check(is_guild_owner)
    async def prefix(self, ctx, *, pre: str):
        """prefix [prefix]"""

        prefix = await self.bot.db.fetchone('prefixes', ['prefix'], f'g_id = :g_id', g_id=ctx.guild.id)

        if not prefix:
            await self.bot.db.insert('prefixes', ['g_id', 'prefix'], g_id=ctx.guild.id, prefix=pre)
        else:
            await self.bot.db.update('prefixes', 'prefix = :pre', pre=pre, condition=f"g_id = '{ctx.guild.id}'")

        await ctx.send(f"New prefix: `{pre}`")

    @commands.command(brief="Add a channel for embeds to be copied from and send to the destination channel")
    @commands.has_permissions(administrator=True)
    async def add_chn(self, ctx, origin: discord.TextChannel, destination: discord.TextChannel):
        """add_chn [origin channel] [destination channel]"""
        await self.bot.db.insert(
            "channels",
            ["g_id", "origin_id", "dest_id"],
            g_id=ctx.guild.id,
            origin_id=origin.id,
            dest_id=destination.id
        )
        await ctx.send(f"Created a relationship from {origin.mention} to {destination.mention}")

    @commands.command(brief="Stop embeds being copied from this channel")
    @commands.has_permissions(administrator=True)
    async def rem_chn(self, ctx, origin: discord.TextChannel, dest: discord.TextChannel):
        """rem_chn [origin channel] [destination channel]"""
        await self.bot.db.delete(
            "channels",
            "g_id=:g_id AND origin_id=:origin_id AND dest_id=:dest_id",
            g_id=ctx.guild.id,
            origin_id=origin.id,
            dest_id=dest.id
        )
        await ctx.send(f"Removed the relation {origin.mention} to {dest.mention}")


def setup(bot):
    bot.add_cog(Set_up(bot))


