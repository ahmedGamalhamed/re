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
        title='**' + product['product_name'] + '**',
        color=0x1e0f3,
        timestamp='now'  # sets the timestamp to current time
    )
    embed.set_author(name='Foot Locker UK ' , icon_url="https://www.gmkfreelogos.com/logos/F/img/Foot_Locker.gif")
    embed.add_field(name='Status', value=product['status'])
    embed.add_field(name='Release DateTime', value= product['product_releasedate'])
    embed.add_field(name='Link', value= product['product_url'])

    if product['product_image'] == "None":
        img_url = "https://runnerspoint.scene7.com/is/image/rpe/null_01?$fl_launchcalendar_product$"
    else:
        img_url = product['product_image']
    embed.set_thumbnail(img_url)

    embed.set_footer(text='FootLocker UK Calendar' + ' Monitor ', icon_url="")

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
        """(id TEXT UNIQUE not null PRIMARY KEY, url TEXT, image TEXT)"""
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
    id = product['product_id']
    url = product['product_url']
    image = product['product_image']
    name = product['product_name']
    releasedate = product['product_releasedate'].split(" ")[0]
    alert = None
    uniqe_id = id + releasedate

    # Create database
    conn = sqlite3.connect("./dbs/" + db_name + '.db')
    c = conn.cursor()

    # Add product to database if it's unique
    try:
        c.execute("""INSERT INTO tbl_""" + table_name +
                  """(id, url, image) VALUES (?, ?, ?)""", (uniqe_id, url, image))
        log('s', "Found NEW product <{}>".format(name))
        alert = "NEW"
    except:
        c.execute("""SELECT url, image FROM  tbl_""" + table_name +
                  """ WHERE id=?""", (uniqe_id, ))
        result = c.fetchall()[0]
        if url != result[0] and image != result[1]:
            c.execute("""UPDATE  tbl_""" + table_name + """ SET url=?, image=? WHERE id=?""", (url, image, uniqe_id))
            alert = "URL, IMG is CHANGED"
            log('s', "Found URL & IMAGE CHANGED product <{}>".format(name))
        elif url != result[0]:
            c.execute("""UPDATE  tbl_""" + table_name + """ SET url=? WHERE id=?""", (url, uniqe_id))
            alert = "URL is CHANGED"
            log('s', "Found URL CHANGED product <{}>".format(name))
        elif image != result[1]:
            c.execute("""UPDATE  tbl_""" + table_name + """ SET image=? WHERE id=?""", (image, uniqe_id))
            alert = "IMAGE is CHAGED"
            log('s', "Found IMAGE CHANGED product <{}>".format(name))
    # Close database
    conn.commit()
    c.close()
    conn.close()
    # Return whether or not it's a new product
    return alert



class FootlockerCalendarMonitor(threading.Thread):

    def __init__(self, proxies, config, tablename, db_name):
        threading.Thread.__init__(self)
        self.proxies = proxies
        self.db_name = db_name
        self.tablename      = tablename
        self.base_url       = config['base_url']
        self.homepage_url   = config['homepage_url']
        self.cal_url        = config['calendar_url']
        self.webhooks_url   = config['webhooks_url']
        self.calendar_json  = config['calendar_feed_json']
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
                    # log('s', "Get main page!")
                    return True
                else:
                    # log('e', "Get main page Status Code: " + str(response.status_code))
                    continue
            except Exception as e:
                continue

    def search_calendar_product(self):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer" : "https://www.footlocker.co.uk/en/content/release_calendar",
            "X-Requested-With": "XMLHttpRequest"
        }
        while True:
            try:
                response = self.scraper.get(self.calendar_json, timeout=5, headers=headers, proxies=self.proxy)
            except Exception as e:
                try:
                    self.proxy = get_proxy(self.proxies)
                    response = self.scraper.get(self.calendar_json, timeout=5, headers=headers, proxies=self.proxy)
                except Exception as err:
                    log('e', str(err))
                    continue

            if (response.status_code == 200):
                items = response.json()
                product = {}
                for item in items:
                    product_name = item['name']
                    if item['hasImage'] == "true":
                        product_image = item['image']
                    else:
                        product_image = "None"

                    product_id   = item['id']
                    product_releasedate  = item['releaseDatetime']

                    product_url = "None"
                    if len(item['deepLinks']) > 0:
                        for link in item['deepLinks']:
                            try:
                                if link['locale'] == 'en':
                                    product_url = link['link']
                            except Exception as e:
                                continue
                    product.update({'product_name' : product_name})
                    product.update({'product_image' : product_image})
                    product.update({'product_id' : product_id})
                    product.update({'product_releasedate' : product_releasedate})
                    product.update({'product_url' : product_url})
                    try:
                        alert = add_to_product_db(product, self.tablename, self.db_name)
                    except Exception as e:
                        print_error_log(str(e))
                        continue
                    if alert:
                        product.update({'status': alert})
                        send_discord(product, self.webhooks_url)
                return True
            else:
                continue

    def run(self):
        # TODO add while When live
        while True:
            log('i', "Start Footlocker Calendar monitoring")
            try:
                self.visithomepage()
                self.search_calendar_product()
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

    dbname= "flcalendar"
    tablename = "calendar"
    create_table(tablename, dbname)
    newthread = FootlockerCalendarMonitor(proxies, config, tablename, dbname)
    newthread.start()
    sleep(2)

