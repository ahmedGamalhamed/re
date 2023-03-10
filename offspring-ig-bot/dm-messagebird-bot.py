# bot.py
import os
import random
import sqlite3
from discord import Client
from discord.enums import ChannelType
from discord.ext import commands
from dotenv import load_dotenv
import phonenumbers
import messagebird
from datetime import datetime

DB_NAME = "Bots"
PHONETABLENAME = 'phonenumber'
OffspringIG = "https://www.instagram.com/offspringhq/"

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
access_key = os.getenv('ACCESS_KEY')


def read_from_txt(filename):
    '''
    (None) -> list of str
    Loads up all sites from the sitelist.txt file in the root directory.
    Returns the sites as a list
    '''
    # Initialize variables
    raw_lines = []
    lines = []

    # Added by ME
    path = filename

    # Load data from the txt file
    f = open(path, "r")
    raw_lines = f.readlines()
    f.close()

    # Parse the data
    for line in raw_lines:
        list = line.strip()
        if list != "":
            lines.append(list)

    # Return the data
    return lines


keywords = read_from_txt("keywords.txt")

# messagebird client
client = messagebird.Client(access_key)

# Command Bot
commandbot = commands.Bot(command_prefix='!')


@commandbot.event
async def on_ready():
    print(f'{commandbot.user.name} has connected to Discord!')


@commandbot.command(name="check")
async def checknumber(ctx):
    if ctx.channel.type == ChannelType.private:
        phonenumber = check_number_from_db(ctx.author.id)
        if phonenumber:
            await ctx.author.send("You have {} added".format(str(phonenumber)))  # Send response author's channel
        else:
            await ctx.author.send("You have no number assigned to you")


@commandbot.command(name="add")
async def addphonenumber(ctx, number: str):
    if ctx.channel.type == ChannelType.private:
        try:
            phone_number = phonenumbers.parse(number, "GB")
            national_number = phone_number.national_number
            counry_code = phone_number.country_code
        except Exception as e:
            await ctx.author.send("You have not entered correctly")
            return
        if phonenumbers.is_possible_number(phone_number):
            if phonenumbers.is_valid_number(phone_number):
                alert = add_number_to_db(ctx.author.id, ctx.author.name, ctx.author.discriminator, national_number,
                                         counry_code)
                if alert:
                    print("{} added his phonenumber: {} ".format(ctx.author.name, national_number))
                    await ctx.author.send(
                        "You have succesfully added {}".format(number))  # Send response author's channel
                else:
                    await ctx.author.send("You can only add 1 number")
            else:
                await ctx.author.send("You have entered invalid number")
        else:
            await ctx.author.send("You have not entered correctly")


@addphonenumber.error
async def addnumber_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.author.send('You have to enter phonenumber')
    else:
        print("An Error: ", error)


@commandbot.command(name="delete")
async def checknumber(ctx):
    if ctx.channel.type == ChannelType.private:
        phonenumber = delete_number_from_db(ctx.author.id)
        if phonenumber:
            print("{} deleted his phonenumber : {}".format(ctx.author.name, phonenumber))
            await ctx.author.send("You have deleted {}".format(phonenumber))
        else:
            await ctx.author.send("There is no number to delete")


@commandbot.command(name="update")
async def checknumber(ctx):
    if ctx.channel.type == ChannelType.private:
        await ctx.author.send("update")  # Send response author's channel


@commandbot.command(name="sms")
@commands.has_any_role(608061319501053955, 615707632430481427)
async def sms(ctx, *, msg: str):
    phonenumber_list = get_phonenumbers_from_db()
    p_list = [str(p[1]) + str(p[0]) for p in phonenumber_list]
    try:
        message = client.message_create(
            '447765294933',
            p_list,
            msg
        )
        print("Success sending sms : ", message.id)
    except messagebird.client.ErrorException as e:
        for error in e.errors:
            print(error)
        return
    await ctx.send(f'Success sending the message `{msg}` to everyone on the list.')


@commandbot.event
async def on_message(message):
    await commandbot.process_commands(message)
    if message.author == commandbot.user:
        return
    if message.channel.type == ChannelType.private:
        return
    if message.channel.name == "offspring-ig":
        try:
            caption = message.embeds[0].fields[0].value
        except:
            return
        #TODO HERE IF statement

        for keyword in keywords:
            if keyword.lower() in caption.lower():
                phonenumber_list = get_phonenumbers_from_db()
                posted_ts_string = message.embeds[0].fields[1].value
                posted_ts = datetime.strptime(posted_ts_string, "%Y/%m/%d %H:%M:%S").timestamp()
                cur_ts = datetime.now().timestamp()
                dt_seconds = cur_ts - posted_ts
                if dt_seconds < 120:
                    for embedproxy in message.embeds[0].fields:
                        if embedproxy.name == "Link":
                            postlink = embedproxy.value
                            print("Found post: ", postlink)
                            if len(phonenumber_list) > 0:
                                send_sms(phonenumber_list, postlink, OffspringIG)
    else:
        return


def create_table(tbl_name, db_name):
    db_dir = "./dbs/"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    conn = sqlite3.connect(db_dir + db_name + '.db')
    c = conn.cursor()
    create_tbl_query = """CREATE TABLE IF NOT EXISTS """ + "tbl_" + tbl_name + \
                       """(id INTEGER UNIQUE not null PRIMARY KEY, username TEXT, discriminator TEXT, phonenumber INTEGER, countrycode INTEGER)"""
    try:
        c.execute(create_tbl_query)
    except Exception as e:
        conn.close()
        raise (e)
    conn.commit()
    conn.close()


def check_number_from_db(id):
    conn = sqlite3.connect("./dbs/" + DB_NAME + '.db')
    c = conn.cursor()
    query = """SELECT phonenumber FROM tbl_""" + PHONETABLENAME + """ WHERE id=?"""
    try:
        result = c.execute(query, (id,)).fetchone()
    except Exception as e:
        conn.close()
        raise (e)
    conn.commit()
    conn.close()
    if result:
        return result[0]
    else:
        return False


def add_number_to_db(id, name, dis, number, countrycode):
    alert = None
    phonenumber = None

    conn = sqlite3.connect("./dbs/" + DB_NAME + '.db')
    c = conn.cursor()
    query = """INSERT INTO tbl_""" + PHONETABLENAME + """(id, username, discriminator, phonenumber, countrycode) VALUES (?, ?, ?, ?, ?)"""
    try:
        c.execute(query, (id, name, dis, number, countrycode))
        alert = True
    except Exception as e:
        query = """SELECT phonenumber FROM tbl_""" + PHONETABLENAME + """ WHERE id=?"""
        phonenumber = c.execute(query, (id,)).fetchone()[0]
        if phonenumber:
            alert = False
        else:
            c.execute("""UPDATE tbl_""" + PHONETABLENAME + """ SET phonenumber=? WHERE id=?""", (number, id))
            alert = True

    conn.commit()
    conn.close()
    if alert:
        return True
    else:
        return False


def delete_number_from_db(id):
    conn = sqlite3.connect("./dbs/" + DB_NAME + '.db')
    c = conn.cursor()
    try:
        query = """SELECT phonenumber FROM tbl_""" + PHONETABLENAME + """ WHERE id=?"""
        phonenumber = c.execute(query, (id,)).fetchone()[0]
    except:
        conn.close()
        return False
    if phonenumber:
        query = """DELETE FROM  tbl_""" + PHONETABLENAME + """ WHERE id=?"""
        try:
            c.execute(query, (id,))
        except Exception as e:
            conn.close()
            return False
    else:
        return False
    conn.commit()
    conn.close()
    return phonenumber


def get_phonenumbers_from_db():
    conn = sqlite3.connect("./dbs/" + DB_NAME + '.db')
    c = conn.cursor()
    try:
        query = """SELECT phonenumber, countrycode FROM tbl_""" + PHONETABLENAME
        phonenumbers = c.execute(query).fetchall()
    except Exception as e:
        conn.close()
        raise (e)
    conn.commit()
    conn.close()
    return phonenumbers


def send_sms(phonenumber_list, postlink, offspringig):
    p_list = []
    for p in phonenumber_list:
        p_list.append(str(p[1]) + str(p[0]))
    print(p_list)
    try:
        # TODO HERE Confirm sender ID!
        message = client.message_create(
            '447765294933',
            p_list,
            'Raffle live! \n {} \n {}'.format(postlink, offspringig)
        )
        print("Success sending sms : ", message.id)
    except messagebird.client.ErrorException as e:
        for error in e.errors:
            print(error)


if (__name__ == "__main__"):
    create_table(PHONETABLENAME, DB_NAME)
    commandbot.run(token)
