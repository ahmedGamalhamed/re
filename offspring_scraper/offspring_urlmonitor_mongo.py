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
	embed.set_author(name='Offspring UK' , icon_url="https://www.offspring.co.uk/_ui/responsive/site-offspring/images/office-logo_sml.png")
	embed.add_field(name='Status', value=product['prod_status'])
	embed.add_field(name='Link', value=product['prod_url'])
	
	atc_value = ""
	if len(product['prod_size']) == 0:
		atc_value = "Sold Out"
	else:
		for size in product['prod_size']:
			atc_name = "[{}]".format(size)
			atc_value = atc_value + atc_name + '\n'

	embed.add_field(name='Available Sizes', value=atc_value)
	embed.add_field(name='Price', value=product['prod_price'])
	embed.set_footer(text='Offspring UK Monitor ', icon_url="")

	embed.set_thumbnail(product['prod_image'])

	try:
		hook.send(embed=embed)
	except Exception as e:
		print_error_log(str(e) + str(embed.to_dict()))


def get_proxy(proxy_list):
	'''
	(list) -> dict
	Given a proxy list <proxy_list>, a proxy is selected and returned.
	'''
	# Choose a random proxy
	proxy = random.choice(proxy_list)

	# Set up the proxy to be used
	proxies = {
		"http": str(proxy),
		"https": str(proxy)
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


class OffspringMonitor(threading.Thread):

	def __init__(self, proxies, config, allinone_urls):
		threading.Thread.__init__(self)
		self.proxies        = proxies
		self.all_in_ones_url = allinone_urls
		self.webhooks_url   = config['all_in_ones_webhooksurl']
		self.db_name        = config['dbname']
		self.base_url       = config['base_url']
		self.moncycle       = config['directurl_monitor_cycle']
		self.user_agent     = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"
		self.keyword 		= "DirectUrl"
		self.mongodbserver      = config['mongodbserver']
		self.mongodatabase      = config['mongodatabase']
		self.client         = MongoClient(self.mongodbserver)
		self.database       = self.client[self.mongodatabase]
		self.collection     = self.database[self.db_name]
		self.session = requests.session()
		self.scraper = cfs.create_scraper(delay=10, sess=self.session)

	def visithomepage(self):
		headers = {
			"User-Agent": self.user_agent,
			"Upgrade-Insecure-Requests": "1",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
			'Accept-Language': 'en-US,en;q=0.9',
			"Accept-Encoding": "gzip, deflate",
		}
		while True:
			proxies = get_proxy(self.proxies)
			try:
				response = self.scraper.get(self.base_url, timeout=5, headers=headers, proxies=proxies)
			except Exception as e:
				continue
			if response.status_code == 200:
				break
			elif response.status_code == 404:
				log('f', "404 page not found [{}]:".format(response.url))
				return
			else:
				# log('f', "Status code in visite Homepage:" + str(response.status_code))
				continue

	def search_product(self, url):
		prod_url = url
		while True:
			try:
				res = self.scraper.get(prod_url, timeout=5)
			except:
				proxies = get_proxy(self.proxies)
				try:
					res = self.scraper.get(prod_url, proxies=proxies, timeout=5)
				except:
					continue
			if res.status_code == 200:
				break
			elif res.status_code == 404:
				log('f', "404 page not found [{}]:".format(res.url))
				return
			else:
				continue
		if "no longer exists" in res.text:
			log('f', "404 page not found [{}]:".format(prod_url))
			return
		html = BS(res.content, features='lxml')
		prod_size = []
		try:
			for size in html.find(id="sizeShoe").find_all('option'):
				if size.get('value') != "":
					ss = "UK" + size.string.split('-')[0]
					prod_size.append(ss.strip())
		except:
			prod_size = []
		try:
			prod_name = html.find('h3', 'productName').string
			is_sale = False
			if html.find(id="WAS_price"):
				is_sale = True
				prod_oldprice = html.find(id="WAS_price").string.strip().split('was')[1].strip()
				prod_price = html.find(id="now_price").string.strip().split('NOW')[1].strip()
			else:
				prod_price = html.find(id="now_price").string.strip()
				prod_oldprice = prod_price

			prod_image = html.find(id="image_swap_target")['src']
			if not "https:" in prod_image:
				prod_image = "https:" + prod_image

			product = {}
			prod_id = os.path.basename(prod_url)
			
			monitor_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

			store_name = "Offspring UK"
			product.update({'_id' : "-".join((store_name, prod_id))})
			product.update({'prod_id': prod_id})
			product.update({'prod_name': prod_name})
			product.update({'prod_url': prod_url})
			product.update({'prod_price': prod_price})
			product.update({'prod_oldprice': prod_oldprice})
			product.update({'prod_image' : prod_image})
			product.update({'prod_size': prod_size})
			product.update({'prod_sale': is_sale})
			product.update({'prod_status' : "New"})
			product.update({'prod_updatedtime': monitor_time})
			product.update({'prod_site': store_name })

			alert = self.add_to_product_mongodb(product, self.keyword)
			if alert:
				webhooks_url = self.webhooks_url
				if alert == 'New':
					product.update({'prod_status': "New arrival"})
				elif alert == "Restock":
					product.update({'prod_status': "Restock"})
				send_discord(product, webhooks_url)
		except Exception as e:
			print_error_log(str(e))

	def add_to_product_mongodb(self, product, type):
		alert = None
		try:
			self.collection.insert_one(product)
			shortcode = generate(size=11)
			self.collection.find_one_and_update({'_id': product['_id']} , { '$set': { "prod_shortcode" : shortcode }})
			log('s', "Found New Product <{}> in Offspring UK [{}].".format(product['prod_name'], type.upper()))
			alert = "New"
		except DuplicateKeyError:
			old_prod = self.collection.find_one({'_id': product['_id']})
			old_prod_sizes = old_prod['prod_size']
			old_status = old_prod['prod_status']
			if (len(old_prod_sizes) == 0 and len(product['prod_size']) > 0) or len(old_prod_sizes) + 1 < len(product['prod_size']):
				log('s', "Found Restocked Product <{}>.in Offspring UK [{}]".format(product['prod_name'], type.upper()))
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
			log('i', "Start Offspring monitoring  [{}]".format(self.keyword))
			self.visithomepage()
			try:
				for url in self.all_in_ones_url:
					self.search_product(url)
					sleep(self.moncycle)
			except Exception as e:
				print_error_log(str(e))
				continue

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
	allinone_urls = read_from_txt('all-in-one-urls.txt')

	log('i', str(len(keywords)) + " Keywords loaded.")
	log('i', str(len(proxies)) + " Proxies loaded.")
	log('i', str(len(allinone_urls)) + " AllInOne Urls loaded.")

	newthread = OffspringMonitor(proxies, config, allinone_urls)
	newthread.start()

