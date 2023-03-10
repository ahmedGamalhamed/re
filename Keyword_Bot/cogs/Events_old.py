import discord
from discord.ext import commands

import asyncio


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def detect_words(self, text, g_id, chn_id):
        words_found = []
        for word in self.bot.channels_words[g_id][chn_id]:
            if word in text.lower():
                words_found.append(word)
        return words_found

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
        if not msg.guild:
            return

        ctx = await self.bot.get_context(msg)
        if ctx.command is not None:
            return

        g_id = str(msg.guild.id)
        if g_id not in self.bot.channels_words:
            return

        chn_id = str(msg.channel.id)
        if chn_id not in self.bot.channels_words[g_id]:
            return

        embed_text = " "
        if msg.embeds != []:
            for embed in msg.embeds:
                embed_dict = embed.to_dict()
                embed_text += f"{embed_dict.pop('title', '')} "
                embed_text += f"{embed_dict.pop('description', '')} "

                if 'footer' in embed_dict:
                    embed_text += f"{embed_dict['footer'].pop('text', '')} "

                if 'author' in embed_dict:
                    embed_text += f"{embed_dict['author'].pop('name', '')} "

                for field in embed_dict['fields']:
                    embed_text += f"{field['name']} {field['value']} "

        words_in_embed = await self.detect_words(embed_text, g_id, chn_id)
        words_in_text = await self.detect_words(msg.content, g_id, chn_id)

        every_word = words_in_embed + words_in_text
        for word in every_word:
            await self.found_word(word, msg, g_id)
            await asyncio.sleep(.25)


    async def found_word(self, word, msg: discord.Message, g_id: int):
        to_notify_id = await self.bot.db.fetchval('words', 'to_notify_id', condition="g_id = :g_id AND word = :w and chn_id = :chn_id", g_id=g_id, w=word, chn_id=msg.channel.id)

        if to_notify_id is None:
            print("Something went wrong")
            return

        people_to_notify = await self.bot.db.fetchall('to_notify', ['id_to_notify'], 'id = :id AND type=type', id=to_notify_id, type=0)
        roles_to_notify = await self.bot.db.fetchall('to_notify', ['id_to_notify'], 'id = :id AND type=type', id=to_notify_id, type=1)
        text_to_send = await self.bot.db.fetchval('words', 'text_to_send', "to_notify_id = :t_n_id", t_n_id=to_notify_id)

        if people_to_notify is not None:
            for person in people_to_notify:
                m_id = person[0]
                guild = self.bot.get_guild(int(g_id))
                if guild is None:
                    continue
                member = guild.get_member(m_id)
                if member is None:
                    continue
                if msg.embeds != []:
                    for embed in msg.embeds:
                        await member.send(embed=embed, content=f"In {msg.channel}.\n{text_to_send if text_to_send else ''}")
                else:
                    await member.send(f"{msg.author} said `{msg.content}` in {msg.channel.mention}\n{text_to_send if text_to_send else ''}")
                await asyncio.sleep(.25)

        if roles_to_notify is not None:
            for role in roles_to_notify:
                role_id = role[0]
                guild = self.bot.get_guild(int(g_id))
                if guild is None:
                    continue
                role = guild.get_role(role_id)
                if role is None:
                    continue
                await msg.channel.send(f"{role.mention}\n{text_to_send if text_to_send else ''}")


def setup(bot):
    bot.add_cog(Events(bot))
