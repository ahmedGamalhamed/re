from threading import Thread
import os
from time import sleep, time
import random
import sqlite3
import ast
import json

import requests
from bs4 import BeautifulSoup as BS
from discord_webhook import DiscordEmbed, DiscordWebhook
from dotenv import load_dotenv
from cloudscraper import create_scraper

load_dotenv()

WEB_HOOKS_URL = os.getenv('WEB_HOOKS_URL')
MONITOR_CYCLE_SECOND = os.getenv('MONITOR_CYCLE_SECOND')


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
# Database
tableName = "products"
dbName = "OpenSea"
BASE_URL = "https://opensea.io"


def sendToWebhooks(product):

    webhook = DiscordWebhook(url=WEB_HOOKS_URL)
    iconURL = "https://storage.googleapis.com/opensea-static/Logomark/Blue%20Logomark.png"
    # create embed object for webhook
    try:
        embed = DiscordEmbed(title=product['prodName'], color=242424, url=product['prodURL'])
        embed.set_author(name='OpenSea', icon_url=iconURL)
        # embed.set_image(url=product['prodImage'])
        embed.set_thumbnail(url=product['prodImage'])
        embed.set_footer(text='OpenSea Monitor')
        embed.set_timestamp()

        embed.add_embed_field(name='TokenID', value='{}'.format(product['tokenId']))
        embed.add_embed_field(name='Symbol', value='{}'.format(product['symbol']))
        embed.add_embed_field(name='{}'.format(product['bid_type']), value='{}'.format(product['prodPrice']))
        embed.add_embed_field(name='Status', value='{}'.format(product['status']))
        # embed.add_embed_field(name='Icon', value=product['price_icon'])

        webhook.add_embed(embed)
        response = webhook.execute()

    except Exception as e:
        # print(repr(e))
        pass

def connectDB(tableName, dbName):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    dbPath = os.path.join(DATA_DIR , dbName + ".db")
    conn = sqlite3.connect(dbPath)
    c = conn.cursor()
    create_tbl_query = """CREATE TABLE IF NOT EXISTS """ + "tbl_" + tableName + \
        """(id TEXT UNIQUE not null PRIMARY KEY, name TEXT, price TEXT)"""
    try:
        c.execute(create_tbl_query)
    except Exception as e:
        raise(e)
    
    return conn


def insertIntoDB(conn, product):
    # Initialize variables
    id = product['prodID']
    name = product['prodName']
    price = product['prodPrice']
    alert = None

    c = conn.cursor()

    # Add product to database if it's unique
    try:
        c.execute("""INSERT INTO tbl_""" + tableName +
                    """(id, name, price) VALUES (?, ?, ?)""", (id, name, price))
        print("Found new product <{}>".format(name))
        alert = "New"
    except Exception as e:
        c.execute("""UPDATE  tbl_""" + tableName + """ SET price=? WHERE id=?""", (price, id))

    # Close database
    conn.commit()
    c.close()

    # Return whether or not it's a new product
    return alert


def create_session():
    # session = requests.session()
    # session.headers = {
    #     "User-Agent" : "Mozilla/5.0 (Linux; Android 10; SM-A205U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36",
    #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
    # }
    session = create_scraper(browser={
        "browser" : "chrome",
        "mobile" : True
    })

    return session



def getProducPage(session, url, connection, proxies_list=[]):
    while True:
        try:
            prixies = get_proxy(proxies_list)
            session.proxies = prixies
            # response = session.get(BASE_URL, timeout=10)
            response = session.get(url, timeout=10)
        except Exception as e:
            print(repr(e))
            sleep(1)
            continue

        if response.status_code == 200:
            try:
                return getProduct(response.content, connection)
            except Exception as e:
                print(repr(e))
                return True
        else:
            print("Status Code : {}".format(response.status_code))
            sleep(1)
            continue

def is_available(prodname, keywords):

    if len(keywords) == 0:
        return True

    for keyword in keywords:
        if keyword.lower() in prodname.lower():
            return True

    return False


def getProduct(page_content, connection):

    # with open("res.html", "wb") as f:     
        # f.write(page_content)

    soup = BS(page_content, "html5lib")

    data_json = json.loads(soup.find(id="__NEXT_DATA__").text)
    # with open("res.json", "w", encoding="utf-8") as f:
    #     json.dump(data_json, f, ensure_ascii=False)

    prod_list = []
    count = 0
    for product in data_json['props']['relayCache'][0][1]['json']['data']['assets']['search']['edges']:

        try:
            name = product['node']['asset']['collection']['name']
            image = product['node']['asset']['displayImageUrl']
            product_id = product['node']['asset']['id']
            tokenId = product['node']['asset']['tokenId']
            prod_url = BASE_URL + "/assets/" + product['node']['asset']['assetContract']['address'] + "/{}".format(tokenId)
            
            if product['node']['asset']['orderData']['bestBid']:
                price_icon = product['node']['asset']['orderData']['bestBid']['paymentAssetQuantity']['asset']['imageUrl']
                decimals = product['node']['asset']['orderData']['bestBid']['paymentAssetQuantity']['asset']['decimals']
                price = int(product['node']['asset']['orderData']['bestBid']['paymentAssetQuantity']['quantity']) / (10 ** decimals)
                symbol = product['node']['asset']['orderData']['bestBid']['paymentAssetQuantity']['asset']['symbol']
                bid_type = "Top Bid"
            else:
                price_icon = product['node']['asset']['orderData']['bestAsk']['paymentAssetQuantity']['asset']['imageUrl']
                decimals = product['node']['asset']['orderData']['bestAsk']['paymentAssetQuantity']['asset']['decimals']
                price = int(product['node']['asset']['orderData']['bestAsk']['paymentAssetQuantity']['quantity']) / (10 ** decimals)
                symbol = product['node']['asset']['orderData']['bestAsk']['paymentAssetQuantity']['asset']['symbol']
                bid_type = "Min Bid"

            count += 1
            if symbol == "ETH":
                pass
            else:
                continue

            if count > 8:
                break

        except Exception as e:
            print(repr(e))
            continue

        prod = {}
        prod.update({"prodName" : name})
        prod.update({"prodURL" : prod_url})
        prod.update({"prodID" : product_id})
        prod.update({"prodPrice" : price})
        prod.update({"prodImage" : image})
        prod.update({"price_icon" : price_icon})
        prod.update({"symbol" : symbol})
        prod.update({"tokenId" : tokenId})
        prod.update({"bid_type" : bid_type})

        status = insertIntoDB(connection, prod)

        if status :
            if status == "New":
                prod.update({"status" : "New Arrival"})

            sendToWebhooks(prod)

    return True


def monitor_thead(url, proxiesList):

    #Create DB
    connection = connectDB(tableName, dbName)

    while True:
        print("Monitoring ... {}".format(url))
        thread_run(url, proxiesList, connection)
        sleep(int(MONITOR_CYCLE_SECOND))


def thread_run(url, proxiesList, connection):
    session = create_session()
    getProducPage(session, url, connection, proxies_list=proxiesList)
        

def loadProxies():
    proxyList = read_from_txt("proxies.txt")
    return proxyList

def loadKeywords():
    keywords = read_from_txt("keywords.txt")
    return keywords


def loadEndPoints():
    endpoints = read_from_txt("endpoints.txt")
    return endpoints


def read_from_txt(filename):
    '''
    (None) -> list of str
    Loads up all sites from the sitelist.txt file in the root directory.
    Returns the sites as a list
    '''
    # Initialize variables
    raw_lines = []
    lines = []

    #Added by ME 
    path = "data/" + filename

    # Load data from the txt file
    try:
        with open(path, "r") as f:
            raw_lines = f.readlines()

    # Raise an error if the file couldn't be found
    except Exception as e:
        print("Couldn't locate <" + path + ">.")
        return lines

    # Parse the data
    for line in raw_lines:
        list = line.strip()
        if list != "":
            lines.append(list)

    # Return the data
    return lines


def get_proxy(proxy_list):
    '''
    (list) -> dict
    Given a proxy list <proxy_list>, a proxy is selected and returned.
    '''
    # Choose a random proxy
    if len(proxy_list) == 0:
        return None

    proxy = random.choice(proxy_list)

    proxySeg = proxy.split(":")
    proxies = {}

    if len(proxySeg) == 4:
        reformatProxy = "{}:{}@{}:{}".format(proxySeg[2], proxySeg[3], proxySeg[0], proxySeg[1])
        proxies = {
            "http": "http://" + reformatProxy,
            "https": "https://" + reformatProxy
        }
    elif len(proxySeg) ==2:
        # Set up the proxy to be used
        proxies = {
            "http": "http://" + str(proxy),
            "https": "https://" + str(proxy)
        }
    else:
        print("Wrong Proxy format")
        return {}
    # Return the proxy
    return proxies


def main():

    proxies_list = loadProxies()
    URLLIST = loadEndPoints()
    NUMTHREADS = len(URLLIST)

    for i in range(NUMTHREADS):
        url = URLLIST[i]
        worker = Thread(target=monitor_thead,  args=(url, proxies_list))
        worker.start()


if __name__ == "__main__":
    main()