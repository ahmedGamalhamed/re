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

def send_discord(photo, webhooks_url):

    hook = Webhook(webhooks_url)
    embed = Embed(
        title='**' + photo['title'] + '**',
        color=0x1e0f3,
        timestamp='now'  # sets the timestamp to current time
    )
    embed.set_author(name='FaceBook' , icon_url="http://files.softicons.com/download/social-media-icons/ios-7-style-social-media-icons-by-design-bolts/png/256x256/Facebook.png")
    if photo['link']:
        embed.add_field(name='Link', value= photo['link'])
    if photo['url']:
        embed.set_image(photo['url'])
    embed.set_footer(text='Facebook Photo Monitor ', icon_url="")
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
    path = filename

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

def create_table(tablename, db_name):
    db_dir = "./dbs/"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    conn = sqlite3.connect(db_dir + db_name + '.db')
    c = conn.cursor()
    create_tbl_query = """CREATE TABLE IF NOT EXISTS """ + "tbl_" + tablename + \
        """(id TEXT UNIQUE not null PRIMARY KEY)"""
    try:
        c.execute(create_tbl_query)
    except Exception as e:
        raise(e)
    # create_idx_query = """CREATE UNIQUE INDEX """ + "idx_" + \
    #     tablename + " ON tbl_" + tablename + """(id)"""
    # try:
    #     c.execute(create_idx_query)
    # except Exception:
    #     pass
    conn.commit()
    c.close()
    conn.close()


def add_to_product_db(photo, table_name, db_name):
    # Initialize variables
    id   = photo['id']
    alert = None
    # Create database
    conn = sqlite3.connect("./dbs/" + db_name + '.db')
    c = conn.cursor()

    # Add product to database if it's unique
    try:
        c.execute("""INSERT INTO tbl_""" + table_name +
                  """(id) VALUES (?)""", (id,))
        log('s', "Found NEW Photo ID:[{}]".format(id))
        alert = "NEW"
    except:
        pass
    # Close database
    conn.commit()
    c.close()
    conn.close()
    # Return whether or not it's a new product
    return alert



class FacebookPhotoScraper(threading.Thread):

    def __init__(self, proxies, config, tablename, db_name, photourls):
        threading.Thread.__init__(self)
        self.proxies        = proxies
        self.db_name        = db_name
        self.tablename      = tablename
        self.photourls      = photourls
        self.webhooks_url   = config['webhooks_url']
        self.mon_cycle      = config['monitoring_cycle']
        self.user_agent     = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"
        self.session        = requests.session()
        self.scraper = cfs.create_scraper(delay=10, sess=self.session)


    def search_photos(self, url):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent,
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'Accept-Language': 'en-US,en;q=0.9',
            "Accept-Encoding": "gzip, deflate, br"
        }
        while True:
            self.proxy = get_proxy(self.proxies) #TODO ADD proxie on real server.
            try:
                with self.scraper.get(url, timeout=5, headers=headers, stream=True, proxies=self.proxy) as response:
                    contents = brotli.decompress(response.content)
                
                json_datas = json.loads(contents.split(b'<script>new (require("ServerJS"))().handle(')[1].split(b");</script>")[0])
                for item in json_datas['pre_display_requires'][3][3][1]['__bbox']['result']['data']['page']['posted_photos']['edges']:
                    post_url = item['node']['url']
                    post_id  = item['node']['id']
                    post_url = item['node']['url']
                    self.get_photo_url(post_url, post_id, post_url)
                return True
            except KeyError:
                log('f', 'Invalid URL: [{}]'.format(url))
                return
            except IndexError:
                log('f', 'Invalid URL: [{}]'.format(url))
                return
            except Exception as e:
                sleep(2)
                # raise (e)
                continue

    def get_photo_url(self, url, id, post_url):
        try:
            response = self.scraper.get(url, timeout=5, proxies=self.proxy)
            if response.status_code == 200:
                photo = {}
            else:
                print_error_log("Fail in :" + url + ": due to " + str(response.status_code))
                return
        except Exception as e:
            print_error_log("Fail in :" + url + ": due to " + str(e))
            return

        try:
            content = response.text.split('<!--')[1].split('-->')[0]
            with open('response.html', 'wb') as f:
                f.write(response.content)

            html = BS(content, features='lxml')
            try:
                imageurl = html.find_all('img', 'scaledImageFitWidth img')['src']
            except :
                content = response.text.split('<!--')[2].split('-->')[0]
                html = BS(content, features='lxml')
                imageurl = html.find('img', 'scaledImageFitWidth img')['src']

            title    = html.find('h5').find('a').string
            photo.update({'url' : imageurl})
            photo.update({'id' : id})
            photo.update({'link' : post_url })
            photo.update({'title' : title})
            alert = add_to_product_db(photo, self.tablename, self.db_name)
            if alert and alert == "NEW":
                send_discord(photo, self.webhooks_url)
        except Exception as e:
            # print(response.url)
            # raise (e)
            print_error_log(str(e) + ": " + url)
            

    def run(self):
        log('s', "Start Facebook Photoscraping ...")
        while True:
            try:
                for url in self.photourls:
                    if "https" in url:
                        log('i', "Searching Photos from [{}]".format(url))
                        self.search_photos(url)
                        sleep(2)
            except Exception as e:
                # raise (e)
                print_error_log(str(e))
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
    photourls = read_from_txt("photo_urls.txt")
    log('i', str(len(photourls)) + " URLs loaded.")

    dbname= "facebook"
    tablename = "photos"
    create_table(tablename, dbname)
    newthread = FacebookPhotoScraper(proxies, config, tablename, dbname, photourls)
    newthread.start()
    sleep(2)

