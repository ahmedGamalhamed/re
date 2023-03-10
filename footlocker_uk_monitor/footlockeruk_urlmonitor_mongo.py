import os
import requests
from requests.exceptions import ProxyError, ConnectionError
import cfscrape as cfs
import random
from time import sleep
from bs4 import BeautifulSoup as BS
from lxml import html
import urllib3
import json
from log import log
import threading
import sqlite3
from dhooks import Webhook, Embed
import random
from datetime import datetime
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
	embed.set_author(name='Foot Locker UK ' , icon_url="https://www.gmkfreelogos.com/logos/F/img/Foot_Locker.gif")
	embed.add_field(name='Status', value=product['prod_status'])
	embed.add_field(name='Link', value=product['prod_url'])

	if product['prod_sale']:
		embed.add_field(name='Price', value="SALE: " + product['prod_price'])
	else:
		embed.add_field(name='Price', value=product['prod_price'])

	atc_value = ""
	if len(product['prod_size']) == 0:
		atc_value = "Sold Out"
	else:
		for size in product['prod_size']:
			atc_name = "[{}]".format(size)
			atc_value = atc_value + atc_name + '\n'
	embed.add_field(name='Available Sizes', value=atc_value)

	embed.set_footer(text='Foot Locker UK' + ' Monitor ', icon_url="")
	embed.set_thumbnail(product['prod_image'])
	try:
		hook.send(embed=embed)
	except Exception as e:
		print_error_log(str(e) +  str(embed.to_dict()))

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


class FootlockerMonitor(threading.Thread):

	def __init__(self, proxies, config, all_in_ones):
		threading.Thread.__init__(self)
		self.proxies        = proxies
		self.all_in_ones    = all_in_ones
		self.db_name        = config['dbname']
		self.base_url       = config['base_url']
		self.mon_cycle      = config['directurl_monitor_cycle']
		self.webhooks_url   = config['all_in_ones_webhooksurl']
		self.homepage_url       = config['homepage_url']
		self.keyword_search_url = config['keyword_search_url']
		self.user_agent         = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36"
		self.keyword        = "DirectUrl"
		self.mongodbserver      = config['mongodbserver']
		self.mongodatabase      = config['mongodatabase']
		self.client         = MongoClient(self.mongodbserver)
		self.database       = self.client[self.mongodatabase]
		self.collection     = self.database[self.db_name]
		self.session = requests.session()
		headers = {
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": self.user_agent,
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
			'Accept-Language': 'en-US,en;q=0.9',
			"Accept-Encoding": "gzip, deflate",
			"Sec-Fetch-Mode": "navigate",
			"Sec-Fetch-Site": "none",
			"Sec-Fetch-User": "?1"
		}
		self.session.headers = headers
		self.session.proxies = get_proxy(self.proxies)
		self.scraper = cfs.create_scraper(delay=10, sess=self.session)

	def visit_homepage(self):
		
		while True:
			try:
				response = self.scraper.get(self.homepage_url, timeout=5)
			except Exception as e:
				continue
			if (response.status_code == 200):
				# log("s", "Get Home")
				return
			else:
				print_error_log("Access Denied {}:".format(str(response.status_code)))
				sleep(2)
				continue
	# part of size selection
	def get_ajax_url(self, url):
		while True:
			try:
				res = self.scraper.get(url, timeout=10)
			except Exception as e:
				print_error_log("Fail Get Product Detail Page URL: [{}]".format(url))
				continue
			if res.status_code == 200:
				break
			else:
				return

		if "All rights reserved" in res.text:
			detail_html = BS(res.content, features="lxml")
			size_contents = detail_html.find_all('div', 'fl-load-animation')
			ajax_url = "" 
			for _ in size_contents:
				try:
					ajax_url = _['data-ajaxcontent-url']
					break
				except:
					continue

			if len(ajax_url) == 0:
				return

			temp = {}
			product_name = detail_html.find('h1', 'fl-product-details--headline').find('span').string
			product_img_url = "https:" + detail_html.find(id="s7viewerImage")['data-scene7-viewer-image-url'] + \
								detail_html.find(id="s7viewerImage")['data-scene7-viewer-assetid'] + "_01?wid=763&hei=538"

			product_price_html = detail_html.find('div', 'fl-product-details--price')
			
			temp.update({'prod_sale': False})
			if product_price_html.find('span', 'fl-price--sale-hint'):
				temp.update({'prod_sale': True})
				prod_price = product_price_html.find_all('span')[2].string
				prod_oldprice = product_price_html.find('span', 'fl-price--old--value').find('span').string
			else:
				prod_price = product_price_html.find('span', 'fl-price--sale').find('span').string
				prod_oldprice = prod_price

			temp.update({'product_price': prod_price})
			temp.update({'prod_oldprice': prod_oldprice})
			temp.update({'product_url': url})
			temp.update({'ajax_url': ajax_url})
			temp.update({'product_name': product_name})
			temp.update({'product_img_url': product_img_url})
			try:
				self.ajax_response_parser(temp)
			except Exception as e:
				print_error_log(str(e))
		else:
			print_error_log('Parsing Product Detail:'+ str(res.status_code))

	#parsing size selection part
	def ajax_response_parser(self, url):
		product = {}
		self.scraper.headers.update({"referer": url['product_url']})
		self.scraper.headers.update({"x-requested-with": "XMLHttpRequest"})
		try:
			res = self.scraper.get(url['ajax_url'], timeout=10)
		except Exception as e:
			return

		if res.status_code == 200:
			try:
				ajax_content = BS(res.json()['content'], features='lxml')
			except:
				return
			temp_html = ajax_content.find('div', 'add-to-cart-form-quantity')
			product_size_json = json.loads(temp_html.find('div')['data-product-variation-info-json'])

			sizes = []
			for key in product_size_json.keys():
				if product_size_json[key]['inventoryLevel'] != 'RED':
					size = "UK" + product_size_json[key]['sizeValue']
					sizes.append(size)

			monitor_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			prod_id = url['product_url'].split('=')[1]

			store_name = "Footlocker UK"
			product.update({'_id' : "-".join((store_name, prod_id))})
			product.update({'prod_id': prod_id})
			product.update({'prod_name': url['product_name']})
			product.update({'prod_url': url['product_url']})
			product.update({'prod_price': url['product_price']})
			product.update({'prod_oldprice': url['prod_oldprice']})
			product.update({'prod_image': url['product_img_url']})
			product.update({'prod_size': sizes})
			product.update({'prod_sale': url['prod_sale']})
			product.update({'prod_status' : "New"})
			product.update({'prod_updatedtime': monitor_time})
			product.update({'prod_site': store_name})

			# print(product)
			alert = self.add_to_product_mongodb(product, self.keyword)
			if alert:
				webhooks_url = self.webhooks_url
				if alert == 'New':
					product.update({'prod_status': "New arrival"})
				elif alert == "Restock":
					product.update({'prod_status': "Restock"})
				send_discord(product, webhooks_url)
		else: 
			log('f', "Status code: {}".format(res.status_code))

	def add_to_product_mongodb(self, product, type):
		alert = None
		try:
			self.collection.insert_one(product)
			shortcode = generate(size=11)
			self.collection.find_one_and_update({'_id': product['_id']} , { '$set': { "prod_shortcode" : shortcode }})
			log('s', "Found New Product <{}> in FootLocker UK [{}].".format(product['prod_name'], type.upper()))
			alert = "New"
		except DuplicateKeyError:
			old_prod = self.collection.find_one({'_id': product['_id']})
			old_prod_sizes = old_prod['prod_size']
			old_status = old_prod['prod_status']
			if (len(old_prod_sizes) == 0 and len(product['prod_size']) > 0) or len(old_prod_sizes) + 1 < len(product['prod_size']):
				log('s', "Found Restocked Product <{}>.in FootLocker UK [{}]".format(product['prod_name'], type.upper()))
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
			log('i', 'Searching product in Footlocker UK [{}]'.format(self.keyword.upper()))
			self.visit_homepage()
			try:
				for url in self.all_in_ones:
					self.get_ajax_url(url)
					sleep(2)
			except Exception as e:
				print_error_log(str(e))
				continue
			sleep(self.mon_cycle)

def print_error_log(error_message):
	monitor_time = datetime.now().strftime('%m-%d-%Y %H:%M:%S')
	dir = "./logs/"
	if not os.path.exists(dir):
		os.makedirs(dir)

	with open("logs/error_logs.txt", 'a+') as f:
		f.write("[{}] \t {} \n".format(monitor_time, error_message))
	
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

	all_in_ones = read_from_txt("all_in_one_urls.txt")
	log('i', str(len(proxies)) + " proxies loaded.")
	log('i', str(len(all_in_ones)) + " AllInOne Urls loaded.")

	newthread = FootlockerMonitor(proxies, config, all_in_ones)
	newthread.start()
	sleep(2)
		

