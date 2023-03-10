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
from nanoid import generate

from pymongo import MongoClient, TEXT, IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, InvalidName, DuplicateKeyError


class FileNotFound(Exception):
    ''' Raised when a file required for the program to operate is missing. '''


class NoDataLoaded(Exception):
    ''' Raised when the file is empty. '''

class OutOfProxies(Exception):
    ''' Raised when there are no proxies left '''

class ProductNotFound(Exception):
    ''' Raised when there are no proxies left '''

def send_discord(product, webhooks_url, channel_name):
    try:
        hook = Webhook(webhooks_url)
        embed = Embed(
            title='**' + product['prod_name'] + '**',
            color=0x1e0f3,
            timestamp='now'  # sets the timestamp to current time
        )
        embed.set_author(name='NikeStore' , icon_url="http://pngimg.com/uploads/nike/nike_PNG11.png")
        embed.add_field(name='Status', value=product['prod_status'])
        embed.add_field(name='Link', value=product['prod_url'])
        
        atc_value = ""
        if len(product['prod_size']) > 0:
            for size in product['prod_size']:
                atc_name = "[{}]".format(size)
                atc_value = atc_value + str(atc_name) + '\n'
        else:
            atc_value = "Out of Stock"

            if product['prod_status'] == "Comming Soon":
                atc_value = "Comming Soon"

        embed.add_field(name='Available Sizes', value=atc_value)
        if product['prod_sale']:
            embed.add_field(name='Price', value="Sale: " + product['prod_price'])
        else:
            embed.add_field(name='Price', value=product['prod_price'])
        embed.set_footer(text='NikeStore Monitor ', icon_url="")

        embed.set_thumbnail(product['prod_image'])
    except Exception as err:
        print_error_log("Making Discord :" + str(err))

    try:
        hook.send(embed=embed)
    except Exception as e:
        print_error_log(str(e) + ":" + channel_name)

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

class NikeStoreScraper(threading.Thread):

    def __init__(self, proxies, config, item):
        threading.Thread.__init__(self)
        self.proxies        = proxies
        self.item           = item
        self.db_name        = config['dbname']
        self.mon_cycle      = item['monitoring_cycle']
        self.base_url       = config['base_url']
        self.sale_webhooks_url = config['mornitor_urls'][1]['webhooks_url']
        self.webhooks_url   = item['webhooks_url']
        self.user_agent     = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"
        self.session        = requests.session()
        self.scraper        = cfs.create_scraper(delay=10, sess=self.session)
        self.mongodbserver  = config['mongodbserver']
        self.mongodatabase  = config['mongodatabase']

        self.type           = self.item.get('type')
        self.client         = MongoClient(self.mongodbserver)
        self.database       = self.client[self.mongodatabase]
        self.collection     = self.database[self.db_name]


    def search_Nikestore(self, type, param):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'Accept-Language': 'en-US,en;q=0.9',
            "Accept-Encoding": "gzip, deflate, br"
        }
        while True:
            proxies = get_proxy(self.proxies) #TODO ADD proxie on real server.
            try:
                if type == "keyword":
                    params  = { "q" : param, "vst": param }
                    url = self.item['keyword_search_url']
                    response = self.scraper.get(url, params=params, timeout=5, headers=headers, proxies=proxies)
                else:
                    url = param
                    response = self.scraper.get(url, timeout=5, headers=headers, proxies=proxies)
                if response.status_code == 200:
                    # log('s', "Get main page Success!")
                    # with open('dummy/homepage.html', 'wb') as f:
                    #     f.write(response.content)
                    break
                elif response.status_code == 404:
                    log('f', "404 Page not found: [{}]".format(response.url))
                    return
                else:
                    log('f', 'Access Denied {}'.format(response.status_code))
                    continue
            except Exception as e:
                log('f', repr(e))
                continue
        try:
            prod_info_json = json.loads(response.text.split('INITIAL_REDUX_STATE=')[1].split(';</script>')[0])
            # with open('json_data.json', "w") as f:
            #     json.dump(prod_info_json, f)
            for product_block in prod_info_json['Wall']['products']:
                if product_block['cardType'] == "default" and not "{countryLangRegion}" in product_block['url']:
                    for product in product_block['colorways']:
                        if product['label'] in ["IN_STOCK", "JUST_IN", "COMING_SOON"]:
                            prod_url = "https://www.nike.com/gb" + product['pdpUrl'].split('{countryLang}')[1]
                            prod_id  = product['pid']
                            self.get_product_detail(prod_url, prod_id)
        except Exception as e:
            log('f', "Can not find any product in [{}]".format(url) + str(e))
            
    def get_product_detail(self, url, prod_id):
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
                proxies = get_proxy(self.proxies)
                response  = self.scraper.get(url, timeout=5, headers=headers, proxies=proxies)
                break
            except Exception as e:
                proxies = get_proxy(self.proxies)
                try:
                    response = self.scraper.get(url, timeout=5, headers=headers, proxies=proxies)
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
                # with open('detail.html', 'wb') as f:
                #     f.write(response.content)
                html = BS(response.content.decode('utf-8','ignore'), features='lxml')
                prod_block = html.find(id="PDP")
                name = prod_block.find(id="pdp_product_title").string

                is_sale = False
                try:
                    price = prod_block.find('div', 'css-11s12ax').string
                    wasprice = price
                except:
                    price = prod_block.find('div', "css-s56yt7").string
                    wasprice = prod_block.find('div', "is--striked-out").string
                    is_sale = True

                image = html.find('meta', {"property":"og:image"}).get('content')

                prod_info_json = json.loads(response.text.split('INITIAL_REDUX_STATE=')[1].split(';</script>')[0])
                prod_code = os.path.basename(url)
                try:
                    size_json = prod_info_json['Threads']['products'][prod_code]
                except KeyError:
                    key = list(prod_info_json['Threads']['products'].keys())[0]
                    size_json = prod_info_json['Threads']['products'][key]
                    url = response.url + "/" + prod_code
                sizes = []
                if size_json['state'] == "IN_STOCK":
                    for availsku in size_json['availableSkus']:
                        for sku  in size_json['skus']:
                            if availsku['id'] == sku['skuId']:
                                sizes.append(sku['localizedSizePrefix'] + sku['localizedSize'].split(" ")[0])
                
                monitor_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                store_name = "NikeStore"
                product.update({'_id' : "-".join((store_name, prod_id))})
                product.update({'prod_id': prod_id})
                product.update({'prod_name': name})
                product.update({'prod_url': url})
                product.update({'prod_price': price})
                product.update({'prod_oldprice': wasprice})
                product.update({'prod_image': image})
                product.update({'prod_size': sizes})
                product.update({'prod_sale': is_sale})
                product.update({'prod_status' : "New"})
                product.update({'prod_updatedtime': monitor_time})
                product.update({'prod_site': store_name})

                alert = self.add_to_product_mongodb(product, self.type)
                if alert:
                    webhooks_url = self.webhooks_url
                    if alert == 'New':
                        product.update({'prod_status': "New arrival"})
                    else:
                        product.update({'prod_status': alert})
                    if size_json['state'] == "LAUNCH":
                        product.update({'prod_status': "Comming Soon"})
                    if is_sale:
                        webhooks_url = self.sale_webhooks_url
                    send_discord(product, webhooks_url, self.type)
            except Exception as e:
                pass
        else:
            log("f", "Status code:{} : {}".format(str(response.status_code), url))
            return False

    def add_to_product_mongodb(self, product, type):
        alert = None
        try:
            self.collection.insert_one(product)
            shortcode = generate(size=11)
            self.collection.find_one_and_update({'_id': product['_id']} , { '$set': { "prod_shortcode" : shortcode }})
            log('s', "Found New Product <{}> in NikeStore UK [{}].".format(product['prod_name'], type.upper()))
            alert = "New"
        except DuplicateKeyError:
            old_prod = self.collection.find_one({'_id': product['_id']})
            old_prod_sizes = old_prod['prod_size']
            old_status = old_prod['prod_status']
            old_price = old_prod['prod_price']
            now_price = product['prod_price']
            if (len(old_prod_sizes) == 0 and len(product['prod_size']) > 0) or len(old_prod_sizes) + 1 < len(product['prod_size']):
                log('s', "Found Restocked Product <{}>.in NikeStore UK [{}]".format(product['prod_name'], type.upper()))
                alert = "Restock"
                old_status = alert
            elif now_price != old_price:
                alert = "Price Change"
                log('s', "Price Changed Product <{}>.in NikeStore UK [{}]".format(product['prod_name'], type.upper()))
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
            try:
                log('i', "Start NikeStore Scraping from [{}]...".format(self.item.get('type')))
                self.start_scrape(self.item)
            except Exception as e:
                print_error_log(str(e))
            sleep(self.mon_cycle)


    def start_scrape(self, item):
        if item.get('type') == "keyword":
            for keyword in item.get('search_keywords'):
                self.search_Nikestore("keyword", keyword)
        else:
            for url in self.item.get('search_urls'):
                self.search_Nikestore("url", url)
    
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
    keywords = read_from_txt("keywords.txt")

    log('i', str(len(proxies)) + " proxies loaded.")
    log('i', str(len(keywords)) + " keywords loaded.")

    for item in config['mornitor_urls']:
        if item['type'] == 'keyword':
            item['search_keywords'] = keywords
        
        newthread = NikeStoreScraper(proxies, config, item)
        newthread.start()
        sleep(2)
