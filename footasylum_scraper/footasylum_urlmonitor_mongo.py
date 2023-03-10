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
from nanoid import generate
from pymongo import MongoClient, TEXT, IndexModel, ASCENDING
from pymongo.errors import ConnectionFailure, InvalidName, DuplicateKeyError

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
        title='**' + product['prod_name'] + '**',
        color=0x1e0f3,
        timestamp='now'  # sets the timestamp to current time
    )
    embed.set_author(name='FootAsylum UK' , icon_url="https://www.churchillsquare.com/wp-content/uploads/2018/10/footasylum-2.png")
    embed.add_field(name='Status', value=product['prod_status'])
    embed.add_field(name='Link', value=product['prod_url'])
    
    atc_value = ""
    if len(product['prod_size']) > 0:
        for size in product['prod_size']:
            atc_name = "[{}]".format(size)
            atc_value = atc_value + str(atc_name) + '\n'
    else:
        atc_value = "Sold out"

    embed.add_field(name='Available Sizes', value=atc_value)
    if product['prod_sale']:
        embed.add_field(name='Price', value="Sale: " + product['prod_price'])
    else:
        embed.add_field(name='Price', value=product['prod_price'])
    embed.set_footer(text='FootAsylum UK Monitor ', icon_url="")

    embed.set_thumbnail(product['prod_image'])

    try:
        hook.send(embed=embed)
        # print(embed.to_dict())
    except Exception as e:
        print_error_log(str(e) + ":" + str(embed.to_dict()))

def print_error_log(error_message):
    monitor_time = datetime.now().strftime('%m-%d-%Y %H:%M:%S')
    dir = "./logs/"
    if not os.path.exists(dir):
        os.makedirs(dir)

    with open("logs/error_logs.txt", 'a+') as f:
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
        f = open(path, "r")
        raw_lines = f.readlines()
        f.close()

    # Raise an error if the file couldn't be found
    except:
        log('e', "Couldn't locate <" + path + ">.")
        raise FileNotFound()

    # Parse the data
    for line in raw_lines:
        list = line.strip()
        if list != "":
            lines.append(list)

    if(len(lines) == 0):
        raise NoDataLoaded()

    # Return the data
    return lines


class FootasylumScraper(threading.Thread):

    def __init__(self, proxies, config, allinoneurls):
        threading.Thread.__init__(self)
        self.proxies        = proxies
        self.allinoneurls   = allinoneurls
        self.db_name        = config['dbname']
        self.mon_cycle      = config['monitoring_cycle']
        self.base_url       = config['base_url']
        self.webhooks_url   = config['all_in_ones_webhooksurl']
        self.user_agent     = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"
        self.is_createtable = False
        self.session        = requests.session()
        self.scraper        = cfs.create_scraper(delay=10, sess=self.session)

        self.mongodbserver      = config['mongodbserver']
        self.mongodatabase      = config['mongodatabase']
        self.client         = MongoClient(self.mongodbserver)
        self.database       = self.client[self.mongodatabase]
        self.collection     = self.database[self.db_name]


    def visit_homepage(self):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'Accept-Language': 'en-US,en;q=0.9',
            "Accept-Encoding": "gzip, deflate, br"
        }
        while True:
            self.proxy = get_proxy(self.proxies) #TODO ADD proxie on real server.
            try:
                response = self.scraper.get(self.base_url, timeout=5, headers=headers, proxies=self.proxy)
                if response.status_code == 200:
                    # log('s', "Get main page Success!")
                    break
                elif response.status_code == 404:
                    log('f', "Invalid Url: [{}]".format(response.url))
                    return
                else:
                    continue
            except Exception as e:
                # log('f', str(e))
                continue
            
    def get_product_detail(self, url):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'Accept-Language': 'en-US,en;q=0.9',
            "Accept-Encoding": "gzip, deflate, br"
        }
        i = 0
        while True:
            try:
                response  = self.scraper.get(url, timeout=5, headers=headers, proxies=self.proxy)
                break
            except Exception as e:
                self.proxy = get_proxy(self.proxies)
                try:
                    response = self.scraper.get(url, timeout=5, headers=headers, proxies=self.proxy)
                    break
                except:
                    i = i + 1
                    if i == 5:
                        return False
                    else:
                        continue

        if response.status_code == 200:
            product = {}
            try:
                json_data = json.loads(response.text.split("variants =")[1].split("settings = ")[0].replace("'", '"'), encoding='utf-8')
                sizes = []
                pid = BS(response.content, features='lxml').find('input', {'name':"pf_id"})['value']
                for key in json_data.keys():
                    data = json_data.get(key)
                    if pid == data.get('pf_id') and data.get('stock_status') == "in stock":
                        size = "UK" + data.get('option2')
                        is_sale = False
                        if data.get('sale_item') == "true":
                            is_sale = True
                        sizes.append(size)
                        price   = data.get('price').replace('Â', '')
                        old_price   = data.get('wasprice').replace('Â', '').replace("RRP ", '')
                        name    = data.get('name')
                image = self.base_url +  "/images/products/medium/{}.jpg".format(pid)
                monitor_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                store_name = "Footasylum"
                product.update({'_id' : "-".join((store_name, pid))})
                product.update({'prod_id' : pid})
                product.update({'prod_name': name})
                product.update({'prod_url': url})
                product.update({'prod_price': price})
                product.update({'prod_oldprice': old_price})
                product.update({'prod_image': image})
                product.update({'prod_size': sizes})
                product.update({'prod_sale': is_sale})
                product.update({'prod_status' : "New"})
                product.update({'prod_updatedtime': monitor_time})
                product.update({'prod_site': store_name})

                # print(product)
                alert = self.add_to_product_mongodb(product,"DirectUrls")
                if alert:
                    webhooks_url = self.webhooks_url
                    if alert == 'New':
                        product.update({'prod_status': "New arrival"})
                    elif alert == "Restock":
                        product.update({'prod_status': "Restock"})
                    send_discord(product, webhooks_url)

            except Exception as e:
                print_error_log("URL:" + url + " " + str(e))
        else:
            print_error_log("Status code:{} : {}".format(str(response.status_code), url))
            return False
 
    def add_to_product_mongodb(self, product, type):
        alert = None
        try:
            self.collection.insert_one(product)
            shortcode = generate(size=11)
            self.collection.find_one_and_update({'_id': product['_id']} , { '$set': { "prod_shortcode" : shortcode }})
            log('s', "Found New Product <{}> in Footasylum [{}].".format(product['prod_name'], type.upper()))
            alert = "New"
        except DuplicateKeyError:
            old_prod = self.collection.find_one({'_id': product['_id']})
            old_prod_sizes = old_prod['prod_size']
            old_status = old_prod['prod_status']
            if (len(old_prod_sizes) == 0 and len(product['prod_size']) > 0) or len(old_prod_sizes) + 1 < len(product['prod_size']):
                log('s', "Found Restocked Product <{}>.in Footasylum [{}]".format(product['prod_name'], type.upper()))
                alert = "Restock"
                old_status = alert
            self.collection.find_one_and_update( 
                {'_id': product['_id']}, 
                {'$set': {
                    'prod_name': product['prod_name'],
                    'prod_url' : product['prod_url'],
                    'prod_size': product['prod_size'], 
                    'prod_status': old_status, 
                    'prod_price': product['prod_price'], 
                    'prod_oldprice': product['prod_oldprice'], 
                    'prod_sale': product['prod_sale'],
                    'prod_updatedtime': product['prod_updatedtime'],
                    'prod_image' : product['prod_image']
                }})
        except Exception as e:
            print_error_log(str(e))
        return alert


    def run(self):
        while True:
            log('i', "Start Footasylum Scraping from [DirectUrls]...")
            try:
                self.visit_homepage()
                for url in self.allinoneurls:
                    self.get_product_detail(url)
            except Exception as e:
                print_error_log(str(e))
            sleep(self.mon_cycle)


def get_config(filename):
    path = "data/" + filename
    try:
        with open(path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        raise FileNotFound()
    
    return config

if (__name__ == "__main__"):
    config = get_config("config.json")
    proxies = read_from_txt("proxies.txt")
    all_in_ones = read_from_txt("all-in-one-urls.txt")

    log('i', str(len(proxies)) + " proxies loaded.")
    log('i', str(len(all_in_ones)) + " AllinOneUrls loaded.")

    newthread = FootasylumScraper(proxies, config, all_in_ones)
    newthread.start()
    sleep(2)
    
