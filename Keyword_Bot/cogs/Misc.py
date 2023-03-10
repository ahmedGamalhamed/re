import discord
from discord.ext import commands

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Info about the bot")
    async def info(self, ctx):
        '''info'''
        embed = discord.Embed(color=ctx.author.color, timestamp=ctx.message.created_at)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        embed.add_field(name="Language:", value="Python", inline=False)
        embed.add_field(name="Library used:", value="discord.py", inline=False)
        embed.add_field(name="Created by:", value="Spyros#1947", inline=False)

        # embed.add_field(name="\u200b", value="Message from creator: If you want your own bot or to support me then send me a message!")

        # embed.set_footer(text=f"Commissioned by tawniey#2442",
        #                  icon_url=ctx.guild.icon_url)

        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(Misc(bot))
