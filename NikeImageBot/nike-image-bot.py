import os
import random
from discord import Client, File
from discord.enums import ChannelType
from discord.ext import commands
from dotenv import load_dotenv
import phonenumbers
import messagebird
from datetime import datetime
from NikeImgMaker import NikeStoreScraper
import time
from urllib.parse import quote
import subprocess

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, InvalidName, DuplicateKeyError

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
access_key = os.getenv('ACCESS_KEY')
mongodb_server = os.getenv('MONGODB_SERVER')
mongodb_database = os.getenv('MONGODB_DATABASE')
afilliate_collection = os.getenv('MONGODB_COLLECTION')

try:
    client    = MongoClient(mongodb_server)
    client.admin.command("ismaster")
    database  = client[mongodb_database]
    collection = database[afilliate_collection]
    print("MongoDB Connection Success!")
except Exception as e:
    raise(e)

class FileNotFound(Exception):
    ''' Raised when a file required for the program to operate is missing. '''

class NoDataLoaded(Exception):
    ''' Raised when the file is empty. '''

class OutOfProxies(Exception):
    ''' Raised when there are no proxies left '''

class ProductNotFound(Exception):
    ''' Raised when there are no proxies left '''


def read_from_txt(filename):
    raw_lines = []
    lines = []
    path = "data/" + filename
    try:
        f = open(path, "r")
        raw_lines = f.readlines()
        f.close()
    except:
        raise FileNotFound()
    for line in raw_lines:
        list = line.strip()
        if list != "":
            lines.append(list)

    if(len(lines) == 0):
        raise NoDataLoaded()
    # Return the data

    return lines

def get_proxy(proxy_list):
    '''
    (list) -> dict
    Given a proxy list <proxy_list>, a proxy is selected and returned.
    '''
    # Choose a random proxy
    proxy = random.choice(proxy_list)

    # Set up the proxy to be used
    proxies = {
        "http": "http://" + str(proxy),
        "https": "https://" + str(proxy)
    }

    # Return the proxy
    return proxies

async def send_afilliateurl(ctx, url):
    object = collection.find_one({ "storename" : "NikeStore" })
    if object:
        af_url = object['affiliate']
        if "awin1.com" in af_url:
            merged_url = quote("[[{}]]".format(url))
        else:
            merged_url = quote("{}".format(url))
        await ctx.send("{}{}".format(af_url, merged_url))
    else:
        await ctx.send("No assigned afilliate url")

#Command Bot
commandbot = commands.Bot(command_prefix='!')

@commandbot.event
async def on_ready():
    print(f'{commandbot.user.name} has connected to Discord!')

@commandbot.command(name="nike")
async def addurl(ctx, url: str):
    if  ctx.channel.type == ChannelType.private:
        async with ctx.typing():
            proxies = read_from_txt("proxies.txt")
            base_url = "https://www.nike.com"
            if "https://www.nike.com" in url:
                if NikeStoreScraper(url, base_url, proxies=proxies).run():
                    with open('data/imgs/final.jpg', 'rb') as fp:
                        await ctx.send(file=File(fp, 'result.png'))
                        await send_afilliateurl(ctx, url)
                else:
                    await ctx.send("Sorry,I can not find product!")
            else:
                await ctx.send("You have entered invalid url")

@commandbot.command(name="tagged")
async def runTagged(ctx):
    if  ctx.channel.type == ChannelType.private:
        async with ctx.typing():
            try:
                subprocess.Popen(['scl', 'enable', 'rh-python36', 'bash'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                subprocess.Popen(['python', '/root/Desktop/DiscordBots/instagram_scraper_new/ig_tagged_story_mongo.py'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                await ctx.send("Tagged scraper started!")
            except Exception as e:
                print(repr(e))
                await ctx.send("Failed running tagged scraper")

@addurl.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.author.send('You have to enter valid url')
    else: 
        print("An Error: ", error)

if (__name__=="__main__"):
    commandbot.run(token)
