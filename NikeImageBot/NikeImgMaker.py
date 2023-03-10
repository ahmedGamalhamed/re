import os
import requests
from requests.exceptions import ProxyError, ConnectionError
import cfscrape as cfs
from time import sleep
from bs4 import BeautifulSoup as BS
import json
from datetime import datetime
import random
import shutil
from PIL import Image, ImageFont, ImageDraw

class FileNotFound(Exception):
    ''' Raised when a file required for the program to operate is missing. '''

class NoDataLoaded(Exception):
    ''' Raised when the file is empty. '''

class OutOfProxies(Exception):
    ''' Raised when there are no proxies left '''

class ProductNotFound(Exception):
    ''' Raised when there are no proxies left '''


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

class NikeStoreScraper():
    def __init__(self, prod_url, base_url, proxies ):
        self.proxies        = proxies
        self.prod_url       = prod_url
        self.base_url       = base_url
        self.user_agent     = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"
        self.session        = requests.session()
        self.scraper        = cfs.create_scraper(delay=10, sess=self.session)

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
                    # print('Success', "Get main page Success!")
                    # with open('dummy/homepage.html', 'wb') as f:
                    #     f.write(response.content)
                    break
                elif response.status_code == 404:
                    return
                else:
                    continue
            except Exception as e:
                # print('Fail', str(e))
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
                # with open("detail.html", 'wb') as f:
                #     f.write(response.content)
                html = BS(response.content.decode('utf-8','ignore'), features='lxml')
                prod_block = html.find(id="PDP")
                name = prod_block.find(id="pdp_product_title").string

                is_sale = False
                try:
                    price = prod_block.find('div', 'css-1emn094').string
                    wasprice = price
                except:
                    price = prod_block.find('div', "css-1emn094").string
                    wasprice = prod_block.find('div', "css-1fkag4c").string
                    is_sale = True

                image = html.find_all('picture')[1].find('source')['srcset']

                prod_info_json = json.loads(response.text.split('INITIAL_REDUX_STATE=')[1].split(';</script>')[0])
                prod_code = os.path.basename(url)
                try:
                    size_json = prod_info_json['Threads']['products'][prod_code]
                except KeyError:
                    key = list(prod_info_json['Threads']['products'].keys())[0]
                    size_json = prod_info_json['Threads']['products'][key]
                    url = response.url + "/" + prod_code
                
                prod_id = size_json['productId']
                sizes = []
                if size_json['state'] == "IN_STOCK":
                    for availsku in size_json['availableSkus']:
                        for sku  in size_json['skus']:
                            if availsku['id'] == sku['skuId']:
                                sizes.append(sku['localizedSizePrefix'] + sku['localizedSize'].split(" ")[0])

                monitor_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
                product.update({'prod_site': "NikeStore"})
                # print(product)
                rounded_price = float(price.replace("£", ""))
                price = round(rounded_price)
                try:
                    self.download_prod_image(image)
                except Exception as e:
                    print(str(e))
                    raise(e)

                if len(sizes) > 0:
                    text = "{} - {} @ {}{}".format(sizes[0], sizes[-1], "£", price)
                else:
                    text = "Sold out @ {}".format(price)

                try:
                    self.make_image(text)
                    return True
                except Exception as e:
                    raise(e)
            except Exception as e:
                raise(e)
        else:
            print_error_log("Status code:{} : {}".format(str(response.status_code), url))
            return False

    def download_prod_image(self, image_url):
        resp = self.scraper.get(image_url, stream=True)
        local_file = open('data/imgs/prod_image.jpg', 'wb')
        resp.raw.decode_content = True
        shutil.copyfileobj(resp.raw, local_file)
        del resp

    def make_image(self, text):
        print("Making product image ...")
        im = Image.open("data/imgs/base-image-red.jpg")
        width, height = im.size
        d = ImageDraw.Draw(im)

        font = ImageFont.truetype(font="data/fonts/Helvetica-Neue-96-Black-Italic.ttf", size=60)
        w, h = d.textsize(text, font=font)

        location = ((width-w)/2, 750)
        text_color = (99, 99, 99)
        d.text(location, text, font=font, fill=text_color)

        im.save("data/imgs/result.jpg")

        im1 = Image.open('data/imgs/result.jpg')
        im2 = Image.open('data/imgs/prod_image.jpg')
        p = 850 / im2.size[0]
        resize_im2 = im2.resize((850, int(p * im2.size[1])))
        back_im = im1.copy()

        back_im.paste(resize_im2, (110, 850))
        back_im.save('data/imgs/final.jpg', quality=95)

    def run(self):
        try:
            print("Finding NikeStore product [{}] ...".format(self.prod_url))
            self.visit_homepage()
            if self.get_product_detail(self.prod_url):
                print("Success !")
                return True
            else:
                print("Fail please read logs file!")
                return False
        except Exception as e:
            print_error_log(str(e))
            print("Fail please read logs file!")
            # raise(e)
            return False

if (__name__ == "__main__"):
    proxies = read_from_txt("proxies.txt")
    url = "https://www.nike.com/gb/t/air-force-1-react-shoe-PgjMZ5/CT1020-102"
    base_url = "https://www.nike.com"
    newthread = NikeStoreScraper(url, base_url, proxies)
    newthread.run()
    
