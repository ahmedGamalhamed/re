import os
import requests
from requests.exceptions import ProxyError, ConnectionError
import cfscrape as cfs
import random
from time import sleep
from bs4 import BeautifulSoup as BS
import json
from log import log
import threading
import sqlite3
from dhooks import Webhook, Embed
import random
from datetime import datetime
import brotli

class FileNotFound(Exception):
    ''' Raised when a file required for the program to operate is missing. '''


class NoDataLoaded(Exception):
    ''' Raised when the file is empty. '''

class OutOfProxies(Exception):
    ''' Raised when there are no proxies left '''

class ProductNotFound(Exception):
    ''' Raised when there are no proxies left '''

def send_discord(product, webhooks_url):

    hook = Webhook(webhooks_url)
    embed = Embed(
        title='**' + product['storename'] + " - " + product['title'] + '**',
        color=0x1e0f3,
        timestamp='now'  # sets the timestamp to current time
    )
    embed.set_author(name='Raffle' , icon_url="https://i.imgur.com/JMeTyaq.jpg")
    embed.add_field(name='Status', value=product['status'])
    embed.add_field(name='Link', value= product['link'])
    embed.set_thumbnail(product['avatar'])
    embed.set_footer(text='A' + ' New' +' Raffle ' + 'Has ' + ' Appeared' , icon_url="")

    try:
        hook.send(embed=embed)
    except Exception as e:
        print_error_log(str(e) + ":" + str(embed.to_dict()))

def print_error_log(error_message):
    monitor_time = datetime.now().strftime('%m-%d-%Y %H:%M:%S')
    with open("error_logs.txt", 'a+') as f:
        f.write("[{}] \t {} \n".format(monitor_time, error_message))

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


def read_from_txt(path):
    '''
    (None) -> list of str
    Loads up all sites from the sitelist.txt file in the root directory.
    Returns the sites as a list
    '''
    # Initialize variables
    raw_lines = []
    lines = []

    # Load data from the txt file
    try:
        f = open(path, "r")
        raw_lines = f.readlines()
        f.close()

    # Raise an error if the file couldn't be found
    except:
        log('e', "Couldn't locate <" + path + ">.")
        raise FileNotFound()

    if(len(raw_lines) == 0):
        raise NoDataLoaded()

    # Parse the data
    for line in raw_lines:
        lines.append(line.strip("\n"))

    # Return the data
    return lines


def create_table(tablename, db_name):
    db_dir = "./dbs/"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    conn = sqlite3.connect(db_dir + db_name + '.db')
    c = conn.cursor()
    create_tbl_query = """CREATE TABLE IF NOT EXISTS """ + "tbl_" + tablename + \
        """(link TEXT UNIQUE not null PRIMARY KEY, title TEXT, status TEXT)"""
    try:
        c.execute(create_tbl_query)
    except Exception as e:
        raise(e)
    create_idx_query = """CREATE UNIQUE INDEX """ + "idx_" + \
        tablename + " ON tbl_" + tablename + """(link)"""
    try:
        c.execute(create_idx_query)
    except Exception:
        pass
    conn.commit()
    c.close()
    conn.close()


def add_to_product_db(product, table_name, db_name):
    # Initialize variables
    title   = product['title']
    link    = product['link']
    status  = product['status']
    store   = product['storename']
    alert = None

    # Create database
    conn = sqlite3.connect("./dbs/" + db_name + '.db')
    c = conn.cursor()

    # Add product to database if it's unique
    try:
        c.execute("""INSERT INTO tbl_""" + table_name +
                  """(link, title, status) VALUES (?, ?, ?)""", (link, title, status))
        log('s', "Found NEW Link <{} - {}>".format(store, title))
        alert = "NEW"
    except:
        pass
    # Close database
    conn.commit()
    c.close()
    conn.close()
    # Return whether or not it's a new product
    return alert



class RaffleLinkzMonitor(threading.Thread):

    def __init__(self, proxies, config, tablename, db_name):
        threading.Thread.__init__(self)
        self.proxies        = proxies
        self.db_name        = db_name
        self.tablename      = tablename
        self.base_url       = config['base_url']
        self.webhooks_url   = config['webhooks_url']
        self.mon_cycle      = config['monitoring_cycle']
        self.user_agent     = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"

    def visithomepage(self):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent,
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'Accept-Language': 'en-US,en;q=0.9',
            "Accept-Encoding": "gzip, deflate, br"
        }
        self.session = requests.session()
        self.scraper = cfs.create_scraper(delay=10, sess=self.session)

        while True:
            self.proxy = get_proxy(self.proxies)
            try:
                response = self.scraper.get(self.base_url, timeout=5, headers=headers, proxies=self.proxy)
                if response.status_code == 200:
                    html = BS(brotli.decompress(response.content), features='lxml')
                    try:
                        for item in html.find_all('h1', 'entry-title'):
                            url = item.find('a').get('href')
                            self.get_post_url(url)
                    except Exception as e:
                        print_error_log(str(e))
                    return True
                else:
                    # log('f', "Status code {}".format(response.status_code))
                    continue
            except Exception as e:
                # log('f', "{}".format(str(e)))
                continue

    def get_post_url(self, url):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip, deflate, br"
        }
        try:
            response = self.scraper.get(url + "?unlock", timeout=5, proxies=self.proxy, headers=headers)
        except Exception as e:
            try:
                proxies = get_proxy(self.proxies)
                response = self.scraper.get(url + "?unlock", timeout=5, proxies=proxies, headers=headers)
            except Exception as e:
                print_error_log(str(e) + ": " + url)

        if response.status_code == 200:
            html = BS(brotli.decompress(response.content), features='lxml')
            title = html.find('h1', 'entry-title').string
            status = html.find('p', 'entry-meta').find_all('a')[1].string
            storename = html.find('p', 'entry-meta').find_all('a')[0].string
            avatar = html.find('div', 'post_author_avatar').get('style').split("(")[1].split(')')[0]

            # if "Social" in status:
            try:
                link = html.find('blockquote', 'instagram-media').get('data-instgrm-permalink')
            except:
                link = html.find('a','autohyperlink').get('href')
            product = {}
            product.update({'title': title})
            product.update({'link' : link})
            product.update({'status' : status})
            product.update({'avatar' : avatar})
            product.update({'storename' : storename})
            alert = add_to_product_db(product, self.tablename, self.db_name)
            if alert and alert == "NEW":
                try:
                    send_discord(product, self.webhooks_url)
                except Exception as e:
                    print_error_log(str(e))
        else:
            print_error_log("Get Url:" + url + ":" + str(response.status_code))

    def run(self):
        log('s', "Start RaffleLinkz monitoring...")
        # TODO add while When live
        while True:
            log('i', "Searching new Links ...")
            try:
                self.visithomepage()
            except Exception as e:
                print_error_log(str(e))
                continue
            sleep(self.mon_cycle)

def get_config():
    try:
        with open("./config.json", 'r') as f:
            config = json.load(f)
    except Exception as e:
        raise FileNotFound()

    return config

if (__name__ == "__main__"):
    config = get_config()
    proxies = read_from_txt("proxies.txt")
    log('i', str(len(proxies)) + " proxies loaded.")

    dbname= "raffle"
    tablename = "linkz"
    create_table(tablename, dbname)
    newthread = RaffleLinkzMonitor(proxies, config, tablename, dbname)
    newthread.start()
    sleep(2)
