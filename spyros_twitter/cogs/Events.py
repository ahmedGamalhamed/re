import discord
from discord.ext import commands

from utils import get_urls, expand_urls, get_good_url


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exception):
        if isinstance(exception, commands.BadArgument) or isinstance(exception, commands.MissingRequiredArgument):
            await ctx.send("Invalid or missing arguments")
        elif isinstance(exception, commands.CheckFailure):
            command_ = ctx.message.content.strip(ctx.prefix)
            if not any([command_.startswith("help"), command_.split()[0] == "h"]):
                await ctx.send("You don't have the required permissions to run this command.")
        elif isinstance(exception, commands.CommandNotFound):
            print(f"Command {ctx.message.content} not found")
            return

        raise exception

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.id == self.bot.user.id:
            return

        chns = await self.bot.db.fetchone(
            "channels",
            ["g_id", "origin_id", "dest_id"],
            "g_id=:g_id AND origin_id=:origin_id",
            g_id=msg.guild.id,
            origin_id=msg.channel.id
        )
        if chns is None:
            return
        dest_id = chns[2]
        dest_chn = msg.guild.get_channel(dest_id)
        if dest_chn is None:
            return

        embeds = dict()
        embeds_data = dict()
        for i, embed in enumerate(msg.embeds):
            data = dict()

            embed_dict = embed.to_dict()

            title_txt = embed_dict.pop('title', '')
            if get_urls(embed_dict.pop('title', '')):
                data["title"] = title_txt

            description = embed_dict.pop('description', '')
            if get_urls(description):
                data["description"] = description

            if 'footer' in embed_dict:
                footer = embed_dict.pop('footer')
                footer_txt = footer.pop('text')
                if get_urls(footer_txt):
                    data["footer"] = footer_txt

            embeds[i] = embed
            embeds_data[i] = data

        to_send = list()
        should_skip = []
        for i, embed in embeds.items():
            new_embed = discord.Embed.from_dict(embed.to_dict())
            new_embed = new_embed.to_dict()

            for what, txt in embeds_data[i].items():
                short_urls = get_urls(txt)
                urls = expand_urls(short_urls, self.bot.aiohttp_session)

                good_urls = []
                async for url in urls:
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

                if len(good_urls) == 0:
                    should_skip.append(True)
                else:
                    should_skip.append(False)

                shorted_urls = self.bot.shortener.shorten_urls(good_urls)

                for j, old_url in enumerate(short_urls):
                    try:
                        # It takes the last `)` from the markdown hypertext syntax so we just append it here
                        # This leads to some double `)` but there is not much we can do about it
                        if old_url.startswith("http"):
                            new_embed[what] = new_embed[what].replace(old_url, shorted_urls[j] + ")")
                        else:
                            shorted_urls[j] = shorted_urls[j].lstrip("https://")
                            new_embed[what] = new_embed[what].replace(old_url, shorted_urls[j] + ")")
                    except IndexError:
                        # In case we don't have a url for it
                        new_embed[what] = new_embed[what].replace(old_url, "")
                    finally:
                        new_embed[what] = new_embed[what].replace(")]", "]")
                        new_embed[what] = new_embed[what].replace("))", ")")

            if any(not skip for skip in should_skip):
                print("Will be send")
                new_embed = discord.Embed.from_dict(new_embed)
                to_send.append(new_embed)
            else:
                print("Skipped")
                continue

        for embed in to_send:
            await dest_chn.send(embed=embed)


def setup(bot):
    bot.add_cog(Events(bot))
