import discord
from discord.ext import commands
import aiosqlite

import time
import asyncio

class Words(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def Nembed(self, ctx, page: int, pages, channels: dict, cur: int):

        embed = discord.Embed(
            color=ctx.author.color,
            timestamp=ctx.message.created_at
        )
        embed.set_author(name="Keywords:", icon_url=self.bot.user.avatar_url)

        text = ""
        # channels = {chn_id: {'word': [role, member], 'word2': [Member]}, }
        keys_that_I_want = list(channels.keys())[cur:cur+10]
        temp_d = {k:channels[k] for k in keys_that_I_want}
        for chn_id, word_dict in temp_d.items():
            channel = ctx.guild.get_channel(int(chn_id))

            text += f"{channel.mention}:\n"
            for word, to_notify in word_dict.items():
                text += f"\t- {word}: " + ', '.join([p.mention for p in to_notify]) + '\n'
            '----------'

        embed.description = text
        embed.set_footer(text=f"Page {page+1}/{pages}")

        return embed, cur

    async def create_pages(self, ctx, channels, end_text):
        pages = 1 + (len(channels) // 10) if (len(channels) % 10) >= 1 else (len(channels) // 10)
        page = 0

        embed, cur = self.Nembed(ctx, page, pages, channels, 0)
        msg = await ctx.send(embed=embed)

        await msg.add_reaction('⬅')
        await msg.add_reaction('➡')
        await msg.add_reaction('❌')

        def check(r, user):
            return user.id != self.bot.user.id and ctx.guild.id == r.message.guild.id and r.message.id == msg.id

        t_end = time.time() + 120
        while time.time() < t_end:
            try:
                res, user = await self.bot.wait_for('reaction_add', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                continue

            if str(res.emoji) == "➡":
                await msg.remove_reaction('➡', user)
                page += 1

                if page == pages:
                    page -= 1
                    continue

                new_embed, cur = self.Nembed(
                    ctx, page, pages, channels, cur + 10)
                await msg.edit(embed=new_embed)

            elif str(res.emoji) == "⬅":
                await msg.remove_reaction('⬅', user)
                page -= 1
                if page < 0:
                    page = 0
                    continue

                new_embed, cur = self.Nembed(
                    ctx, page, pages, channels, cur - 10)
                await msg.edit(embed=new_embed)

            elif str(res.emoji) == "❌":
                await msg.remove_reaction("❌", user)
                break

        await msg.remove_reaction('⬅', self.bot.user)
        await msg.remove_reaction('➡', self.bot.user)
        await msg.remove_reaction("❌", self.bot.user)

        embed = discord.Embed(
            color=ctx.author.color,
            description=f"`{ctx.prefix}{ctx.command}` to open again",
            timestamp=ctx.message.created_at
        )
        embed.set_author(name=end_text,
                         icon_url=self.bot.user.avatar_url)

        await msg.edit(embed=embed)

    @commands.command(brief='Add a word or phrase for the bot to monitor')
    @commands.has_permissions(administrator=True)
    async def add(self, ctx, word, channel: discord.TextChannel, people: commands.Greedy[discord.Member], roles: commands.Greedy[discord.Role]):
        """add [word/"phrase"] [channel] (list of people it will pm) (list of roles it will ping in the server)"""
        # await self.bot.db.insert('words', ['g_id', 'word', 'chn_id'], g_id=ctx.guild.id, word=word.lower(), chn_id=channel.id)
        if people + roles == []:
            await ctx.send("You need to specify at least one person or role")
            return

        if str(ctx.guild.id) in self.bot.channels_words:
            if str(channel.id) in self.bot.channels_words[str(ctx.guild.id)]:
                if word.lower() in self.bot.channels_words[str(ctx.guild.id)][str(channel.id)]:
                    await ctx.send(f"I am already listening for `{word}` in {channel.mention}")
                    return

        async with aiosqlite.connect("DATA/bot.db") as db:
            c = await db.execute(
                f"""
                INSERT INTO words (g_id, word, chn_id)
                     VALUES (:g_id, :word, :chn_id)
                """, {'g_id': ctx.guild.id, 'word': word.lower(), 'chn_id': channel.id}
            )
            to_notify_id = c.lastrowid
            await db.commit()

        # to_notify_id = await self.bot.db.fetchval('words', 'to_notify_id', condition="g_id = :g_id AND word = :w AND chn_id = :chn_id", g_id=ctx.guild.id, w=word, chn_id=channel.id)


        if to_notify_id is None:
            await ctx.send("Something went wrong")
            await self.bot.db.delete('words', "g_id = :g_id AND word = :w", g_id=ctx.guild.id, w=word)
            return

        for person in people:
            id_ = person.id
            await self.bot.db.insert("to_notify", ['id', 'type', 'id_to_notify'], id=to_notify_id, type=0, id_to_notify=id_)
            await asyncio.sleep(.25)

        for role in roles:
            id_ = role.id
            await self.bot.db.insert("to_notify", ['id', 'type', 'id_to_notify'], id=to_notify_id, type=1, id_to_notify=id_)
            await asyncio.sleep(.25)

        await ctx.send(f"Monitoring {channel.mention} for `{word}`")

        if str(ctx.guild.id) not in self.bot.channels_words:
            self.bot.channels_words[str(ctx.guild.id)] = dict()

        if str(channel.id) in self.bot.channels_words[str(ctx.guild.id)]:
            self.bot.channels_words[str(ctx.guild.id)][str(channel.id)].append(word)
        else:
            self.bot.channels_words[str(ctx.guild.id)][str(channel.id)] = [word]

    @commands.command(name="delete", brief='Stop monitoring for a word')
    @commands.has_permissions(administrator=True)
    async def delete_(self, ctx, word, channel: discord.TextChannel=None):
        """delete [word/"phrase"] (channel)"""
        g_id = str(ctx.guild.id)

        if g_id not in self.bot.channels_words:
            await ctx.send("Weird, I haven't seen your server before")
            return

        if channel is not None:
            chn_id = str(channel.id)
            if chn_id not in self.bot.channels_words[g_id]:
                await ctx.send("Are you sure this is the correct channel? because I couldn't find it")
                return

            if word not in self.bot.channels_words[g_id][chn_id]:
                await ctx.send("I couldn't find this word for this channel.")
                return

            self.bot.channels_words[g_id][chn_id].remove(word)
            if self.bot.channels_words[g_id][chn_id] == []:
                del self.bot.channels_words[g_id][chn_id]

                if self.bot.channels_words[g_id] == dict():
                    del self.bot.channels_words[g_id]

            to_notify_id = await self.bot.db.fetchval('words', 'to_notify_id', 'g_id = :g_id AND word = :w AND chn_id = :chn_id', g_id=int(g_id), w=word, chn_id=int(chn_id))

            await self.bot.db.delete('words', 'g_id = :g_id AND word = :w AND chn_id = :chn_id', g_id=int(g_id), w=word, chn_id=int(chn_id))
            await self.bot.db.delete('to_notify', 'id = :id', id=to_notify_id)

            await ctx.send(f"Stopped listening for `{word}` in {channel.mention}")
        else:
            chn_ids = []
            for chn_id, words in self.bot.channels_words[g_id].items():
                if word in words:
                    words.remove(word)
                    chn_ids.append(int(chn_id))

            if chn_ids == []:
                await ctx.send("I didn't find this word")
                return
            else:
                for chn_id in chn_ids:
                    if self.bot.channels_words[g_id][str(chn_id)] == []:
                        del self.bot.channels_words[g_id][str(chn_id)]

                        if self.bot.channels_words[g_id] == dict():
                            del self.bot.channels_words[g_id]

            to_notify_ids = await self.bot.db.fetchall('words', ['to_notify_id'], 'g_id = :g_id AND word = :w', g_id=int(g_id), w=word)

            await self.bot.db.delete('words', 'g_id = :g_id AND word = :w', g_id=int(g_id), w=word)
            for id_ in to_notify_ids:
                to_notify_id = id_[0]
                await self.bot.db.delete('to_notify', 'id = :id', id=to_notify_id)

            await ctx.send(f"Stopped listening for `{word}`")

    @commands.command(name="list", brief='List all the words that I am listening for')
    async def list_(self, ctx):
        """list"""
        g_id = str(ctx.guild.id)

        if g_id not in self.bot.channels_words:
            await ctx.send("I am not listening for any words in this server")
            return

        channels = dict()
        for chn_id, words in self.bot.channels_words[g_id].items():
            channels[chn_id] = dict()
            for word in words:
                # to_notify_id = await self.bot.db.fetchval('words', 'to_notify_id', condition="g_id = :g_id AND word = :w", g_id=int(g_id), w=word)
                to_notify_id = await self.bot.db.fetchval('words', 'to_notify_id', condition="g_id = :g_id AND word = :w AND chn_id = :chn_id", g_id=int(g_id), w=word, chn_id=int(chn_id))

                if to_notify_id is None:
                    print("Something went wrong")
                    continue

                people_to_notify = await self.bot.db.fetchall('to_notify', ['id_to_notify'], 'id = :id AND type=type', id=to_notify_id, type=0)
                roles_to_notify = await self.bot.db.fetchall('to_notify', ['id_to_notify'], 'id = :id AND type=type', id=to_notify_id, type=1)

                to_notify = []
                if people_to_notify is not None:
                    for person in people_to_notify:
                        m_id = person[0]
                        guild = self.bot.get_guild(int(g_id))
                        if guild is None:
                            continue
                        member = guild.get_member(m_id)
                        if member is None:
                            continue
                        to_notify.append(member)

                if roles_to_notify is not None:
                    for role in roles_to_notify:
                        role_id = role[0]
                        guild = self.bot.get_guild(int(g_id))
                        if guild is None:
                            continue
                        role = guild.get_role(role_id)
                        if role is None:
                            continue
                        to_notify.append(role)
                channels[chn_id][word] = to_notify
        await self.create_pages(ctx, channels, "Keywords list closed")



def setup(bot):
    bot.add_cog(Words(bot))
