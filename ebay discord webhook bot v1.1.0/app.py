__version__ = '1.1.0'

import requests
import html as html_lib
from collections import Mapping, Set, Sequence
from urllib.parse import quote
import datetime
import hashlib
import json
import time
import copy
import sys
import os
import re

LISTING_TYPES = {
	'ALL': None,
	'AUCTION': 'LH_Auction',
	'BUY': 'LH_BIN'
}

SORTING = {
	'ENDING': 1,
	'CHEEPEST': 2,
	'PRICIEST': 3,
	'NEAREST': 7,
	'NEWEST': 10,
	'BEST MATCH': 12,
	'CHEEPEST_TOTAL': 15,
	'PRICIEST_TOTAL': 16,
}

PAGE_LENGTHS = [25, 50, 100, 200]

DEBUG = False

class IncompletePage(Exception):
	pass

def save_json(filepath, data):
	with open(filepath, 'w') as file:
		json.dump(data, file)

def load_json(filepath, defaultData):
	if not os.path.exists(filepath):
		save_json(filepath, defaultData)
		return defaultData, False

	with open(filepath, 'r') as file:
		return json.load(file), True

class R2Scraper(object):
	headers = {
		'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0',
		'Accept-Language': 'Accept-Language: en-US,en;q=0.5',
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
		'DNT': '1',
		'Pragma': 'no-cache',
		'Cache-Control': 'no-cache',
		'Connection': 'keep-alive',
		'Upgrade-Insecure-Requests': '1',
		'Host': 'www.ebay.co.uk'
	}

	def __init__(self, ebay, discord, searches, data_path, proxies):
		self.ebay = ebay

		self.discord = discord

		if 'wait=true' not in self.discord['webhook_url']:
			self.discord['webhook_url'] += '?wait=true'


		proxypool = proxies[:]

		self.searches = searches
		for search in self.searches:
			search['id'] = hashlib.md5(''.join([str(search[key]) for key in ['query', 'seconds_interval', 'price_min', 'price_max', 'listing_type', 'sort_by', 'page_length']]).encode()).hexdigest()
			search['session'] = requests.Session()
			search['session'].headers.update(self.headers)
			if not proxies:
				continue

			if not proxypool:
				proxypool = proxies[:]
			proxy = proxypool.pop()
			search['session'].proxies = {
				'http': 'http://{}'.format(proxy),
				'https': 'https://{}'.format(proxy)
			}

		self.data, existed = load_json(data_path, {
			'searched': {},
			'listings': {
				'BUY': {},
				'AUCTION': {}
			}
		})

		self.first_run = not existed

	def run(self):
		if self.first_run:
			print('First run, silently running {} seconds'.format(self.discord['first_run_silence']))

		started = time.time()

		while True:
			now = time.time()
			print('[{}] Uptime: {:.2f}s'.format(datetime.datetime.now(), now - started))
			next_run = now + self.ebay['minimum_interval']

			# Notify of ending listings
			ending_listings = [listing for listing in self.data['listings'].values() if listing.get('ending') is not None]
			for notification in self.discord['notifications']:
				if notification.get('minutes_before') is None:
					continue

				for ending in ending_listings:
					if notification['id'] in ending['notifications']:
						continue

					notification_run = ending['ending'] - (notification['minutes_before'] * 60)
					if notification_run > now:
						next_run = min(next_run, notification_run)
						continue

					now = time.time()
					self.notify(ending, notification, now)


			for search in self.searches:
				last_searched = self.data['searched'].get(search['id'], 0)
				next_search = last_searched + search['seconds_interval']
				if next_search >= now:
					next_run = min(next_run, next_search)
					continue

				# Fetch listings
				print('Searching for "{}"...'.format(search['query']))
				listings, error = self.fetch_listings(search['session'], search['query'], (search['price_min'], search['price_max']), LISTING_TYPES[search['listing_type']], SORTING[search['sort_by']], search['page_length'], True)
				if error is not None:
					print('ERROR')
					print(error)
					if not isinstance(error, IncompletePage):
						continue

					print('Trying again instantly...')
					listings, error = self.fetch_listings(search['session'], search['query'], (search['price_min'], search['price_max']), LISTING_TYPES[search['listing_type']], SORTING[search['sort_by']], search['page_length'], True)
					if error is not None:
						print('ERROR')
						print(error)
						continue


				# Add new listings to data
				new_auctions = []
				new_buys = []
				for index, listing in enumerate(listings):
					for type in LISTING_TYPES:
						if listing['type'] != type or self.data['listings'].get(listing['id']) is not None:
							continue

						listing.update({ 
							'index': index,
							'notifications': {}
						})
						self.data['listings'][listing['id']] = listing
						next_run = 0

						if type == 'BUY':
							new_buys.append(listing)
						else:
							new_auctions.append(listing)

				if new_buys or new_auctions:
					save_json('data.json', self.data)

				print('Discovered {} new BUYs, and {} new AUCTIONs'.format(len(new_buys), len(new_auctions)))


				# Find correct new-listing notifications for each listing type
				all_notification = None
				buy_notification = None
				auction_notification = None
				for notification in self.discord['notifications']:
					if notification.get('minutes_before'):
						continue

					if notification['type'] == 'AUCTION':
						auction_notification = notification
					elif notification['type'] == 'BUY':
						auction_notification = notification
					else:
						all_notification = notification

				for listing in new_buys + new_auctions:
					if search.get('top_n_listings') and listing['index'] > search['top_n_listings'] - 1:
						continue

					if auction_notification and listing['type'] == 'AUCTION':
						self.notify(listing, auction_notification)
					elif buy_notification and listing['type'] == 'BUY':
						self.notify(listing, buy_notification)
					elif all_notification:
						self.notify(listing, all_notification)

				self.data['searched'][search['id']] = now
				next_run = min(next_run, now + search['seconds_interval'])

			now = time.time()
			while next_run > now:
				print('{:.2f}       \r'.format(next_run - now), end='', flush=True)
				now = time.time()
				time.sleep(1)
			print()

			if self.first_run and started + self.discord['first_run_silence'] <= now:
				print('First run silence exited')
				self.first_run = False

	def notify(self, listing, notification, now=time.time()):
		# https://discordapp.com/developers/docs/resources/webhook#execute-webhook
		if not self.first_run:
			human_details = {
				'now_12h': datetime.datetime.now().strftime('%I:%M %p')
			}
			if listing.get('ending'):
				human_details["ending_datetime"] = datetime.datetime.fromtimestamp(listing['ending'])
				human_details['ending_12h'] = human_details['ending_datetime'].strftime('%I:%M %p')

			try:
				out_data = {}
				if notification.get('message'):
					content, error = format_string('\n'.join(notification['message']), { **listing, **human_details }, 'INVALID_KEY')
					if error:
						print('Formatting Error')
						print(error)
					else:
						out_data['content'] = content

				if notification.get('json'):
					new_data = copy.deepcopy(notification['json'])

					for path, value in objwalk(new_data):
						if not isinstance(value, str):
							continue

						obj = new_data

						traversal = path[:]
						while len(traversal) > 1:
							obj = obj[traversal.pop(0)]

						new_value, error = format_string(value, { **listing, **human_details }, 'INVALID_KEY')
						if error:
							print('Formatting Error at {}'.format(path))
							print(error)
						else:
							obj[traversal[0]] = new_value

					out_data.update(new_data)
				time.sleep(self.discord['seconds_delay'])
				response = requests.post(self.discord['webhook_url'], data=json.dumps(out_data), headers={ 'Content-Type': 'application/json' }, timeout=self.ebay['request_timeout'])
			except requests.Timeout as te:
				print('ERROR')
				print(te)
				return False, te

			ratelimit_reset_after = int(response.headers.get('X-RateLimit-Reset-After', '0'))
			ratelimit_remaining = int(response.headers.get('X-RateLimit-Remaining', '0'))
			if not ratelimit_remaining and ratelimit_reset_after:
				time.sleep(int(ratelimit_reset_after))

			data = response.json()
			if 'message' in data:
				print('Discord error message: {}'.format(data['message']))
				if 'retry_after' in data:
					retry_after_seconds = data['retry_after'] / 1000
					print('Told to retry in {} seconds...'.format(retry_after_seconds))
					time.sleep(retry_after_seconds)
					return self.notify(listing, notification, time.time())
			if not response.ok:
				print('ERROR sending notification')
				print(response.status_code)
				print(out_data)
				print(data)

		listing['notifications'][notification['id']] = now
		if self.first_run:
			print('Notification #{} discovered - but not sent - for "{}"'.format(notification['id'], listing['title']))
		else:
			print('Notification #{} sent for "{}"'.format(notification['id'], listing['title']))

		save_json('data.json', self.data)

		return True, None

	def fetch_listings(self, session, query, price_range=None, listing_type=LISTING_TYPES['ALL'], sort_by=SORTING['BEST MATCH'], page_length=PAGE_LENGTHS[0], first_loop=False):
		params = {
			'_nkw': query,
			'_udlo': price_range[0] if price_range else None,
			'_udhi': price_range[1] if price_range and len(price_range) > 1 else None,
			'_sop': sort_by,
			'_ipg': page_length
		}
		if listing_type is not None:
			params[listing_type] = 1

		try:
			if first_loop:
				request = session.prepare_request(requests.Request('GET', 'http://www.ebay.co.uk/sch/i.html', params=params))
				session.get('http://www.ebay.co.uk/sch/FindingCustomization/?_fscp=http&_fcdm=1&_fcss={}&_fcps=3&_fcippl={}&_fcso=1&_fcpd=1&_fcsp={}&_fcsbm=1&_pppn=v3&_fcpe=7%7C5%7C3%7C2%7C4&_fcie=1&_fcse=10%7C42%7C43'.format(sort_by, page_length, request.url), timeout=self.ebay['request_timeout'])

			response = session.get('http://www.ebay.co.uk/sch/i.html', params=params, timeout=self.ebay['request_timeout'])
		except requests.Timeout as te:
			print('ERROR')
			print(te)
			return None, te

		if not response.ok:
			return None, response.status_code

		if DEBUG:
			with open('debug_{}.html'.format(time.time()), 'w') as f:
				f.write(response.text)

		return parse_listings_page(response.text)


def parse_old_listings_page(html):
	all_data = []
	list_items = html.split('<ul id="ListViewInner">')[1].split('<div id="AnswersPlaceHolderContainer9999">')[0].split('<li id="')[1:]
	for item in list_items:
		data = {}

		# ID, listing_id
		data.update(re.search(r'^(?P<id>.*?)".*listingId="(?P<listing_id>.*?)"', item).groupdict())

		image_url = re.search(r'<img.*?imgurl="(.*?)"', item, re.DOTALL)
		data['image_url'] = image_url.group(1) if image_url else re.search(r'<img.*?src="(.*?)"', item, re.DOTALL).group(1)

		data['url'] = '?'.join(re.search(r'<a.*?href="(.*?)"', item, re.DOTALL).group(1).split('?')[0:-1])

		data['title'] = re.search(r"alt='(.*?)'", item, re.DOTALL).group(1)

		# Condition
		if '<div class="lvsubtitle"' in item:
			data['misc_details'] = [re.search(r'<div class="lvsubtitle".*?>(.*?)</div>', item, re.DOTALL).group(1).strip()]

		data['type'] = 'BUY' if 'Buy it now' in re.search(r'<li class="lvformat">(.*)</li>', item, re.DOTALL).group(1) else 'AUCTION'

		if '<li class="timeleft' in item:
			data['ending'] = int(int(re.search(r'<li class="timeleft.*?timeMs="(.*?)"', item, re.DOTALL).group(1)) / 1000)

		# Country origin
		# re.search(r'<ul class="lvdetails.*?From (.*?)</li>', item, re.DOTALL).group(1).strip()

		# Prices
		prices_section = re.search(r'<ul class="lvprices.*?>(.*?)</ul>', item, re.DOTALL).group(1).strip()
		prices = [float(price.replace(',', '')) for price in re.findall(r'(\d.*?\.\d+)', re.search(r'<li class="lvprice.*?>(.*?)</li>', prices_section, re.DOTALL).group(1).strip())]
		data['curr_price'] = prices[0]
		data['prev_price'] = prices[1] if len(prices) > 1 else None

		shipping = re.search(r'(\d.*?\.\d+)', re.search(r'<li class="lvshipping">(.*?)</li>', prices_section, re.DOTALL).group(1).strip())
		data['shipping_price'] = float(shipping.group(1).replace(',', ''))if shipping is not None else 0


		# Seller information
		seller_section = re.search(r'<ul class="lvdetails.*?>(.*?)</ul>', item, re.DOTALL).group(1).strip()
		if 'Item: {}'.format(data['listing_id']) not in seller_section:
			return None, IncompletePage('Seller information absent')

		seller = re.search(r'Seller:\s+(?P<username>.*?)<', seller_section, re.DOTALL).groupdict()

		if 'class="selrat"' in seller_section:
			seller.update(re.search(r'class="selrat">\((?P<review_count>.*?)\).*?class="selrat">(?P<positive_percentage>.*?)?\%', seller_section, re.DOTALL).groupdict())
			seller['review_count'] = int(seller['review_count'].replace(',', ''))
			seller['positive_percentage'] = float(seller['positive_percentage'])
		else:
			seller.update({ 'review_count': None, 'positive_percentage': None })

		if "View seller's" in seller_section:
			seller.update(re.search(r'href="(?P<store_url>.*?)".*?:\s+(?P<name>.*?)"', seller_section, re.DOTALL).groupdict())
		else:
			seller.update({ 'store_url': None, 'name': None })

		data['seller'] = seller

		all_data.append(data)

	return all_data, None


def parse_listings_page(html):
	all_data = []

	items = re.split(r'<li class="s-item\s+?".*?>', html, flags=re.MULTILINE)[1:]
	if not len(items):
		return parse_old_listings_page(html)

	for item in items:
		data = {}

		data['id'] = hashlib.md5((data['title'] + data['image_url'] + data['url']).encode()).hexdigest()
		data['listing_id'] = data['id']

		# Title and Image URL
		data.update(re.search(r'<img class="s-item__image-img".*?alt="(?P<title>.*?)".*?src="(?P<image_url>.*?)"', item).groupdict())

		# Item URL
		data['url'] = re.search(r'<a class="s-item__link" href="(.*?)"', item).group(1)

		# Item quality
		data['quality'] = re.search(r'<span class="SECONDARY_INFO">(.*?)</span>', item).group(1)

		# Current price
		data['curr_price'] = float(re.search(r'<span class="s-item__price">.*?(\d+?\.\d+).*</span>', item).group(1).strip().replace(',', ''))

		# Previous price, or None
		prev_price = re.search(r'<span class="clipped">Previous Price</span>.*?(\d+?\.\d+).*?</span>', item)
		data['prev_price'] = float(prev_price.group(1).replace(',', '')) if prev_price else None

		# Shipping price, or 0
		shipping_price = re.search(r'<span class="s-item__shipping s-item__logisticsCost">.*?(\d+?\.\d+).*?</span>', item)
		data['shipping_price'] = float(shipping_price.group(1).replace(',', '')) if shipping_price else 0

		# Seller information
		seller_section = re.search(r'<span class="s-item__seller-info">(.*?)</a>', item).group(1).strip()
		seller = re.search(r'<span class="s-item__seller-info-text">Seller:\s+(?P<username>.*)\s+\((?P<review_count>.*?)\)\s+(?P<positive_percentage>.*?)?\%', seller_section).groupdict()
		seller['review_count'] = int(seller['review_count'].replace(',', ''))
		seller['positive_percentage'] = float(seller['positive_percentage'])
		if "View seller's" in seller_section:
			seller.update(re.search(r'href="(?P<store_url>.*?)".*?:\s+(?P<name>.*)</span>', seller_section).groupdict())
		data['seller'] = seller

		# Top rated plus member
		data['top_rated_plus'] = 'aria-label="Top Rated Plus"' in item

		# Misc details
		misc_details = []
		for subtitle in re.findall(r'<div class="s-item__subtitle">(.*?)</div>', item):
			details = [detail.strip() for detail in re.sub(r'<span.*?/span>', '\n', subtitle).strip().split('\n')]
			misc_details += [html_lib.unescape(detail) for detail in details if detail]
		data['misc_details'] = misc_details

		# Guaranteed by string
		guaranteed_by = re.search(r'<span class="s-item__dynamic s-item__guaranteedDelivery">Guaranteed by <span class="POSITIVE BOLD">(.*?)</span>', item)
		data['guaranteed_by'] = guaranteed_by.group(1).strip() if guaranteed_by else None

		# SME Discount
		sme_discount = re.search(r'<span class="s-item__sme s-item__smeInfo">(.*?)</span>', item)
		data['sme_discount'] = sme_discount.group(1).strip() if sme_discount else None

		all_data.append(data)

	return all_data, None


def objwalk(obj, path=[], memo=None):
	string_types = (str, unicode) if str is bytes else (str, bytes)
	iteritems = lambda mapping: getattr(mapping, 'iteritems', mapping.items)()

	if memo is None:
		memo = set()
	iterator = None
	if isinstance(obj, Mapping):
		iterator = iteritems
	elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, string_types):
		iterator = enumerate
	if iterator:
		if id(obj) not in memo:
			memo.add(id(obj))
			for path_component, value in iterator(obj):
				for result in objwalk(value, path + [path_component], memo):
					yield result
			memo.remove(id(obj))
	else:
			yield path, obj

def format_string(orig_str, mapping, missing_fill):
	while True:
		try:
			return orig_str.format(**mapping), None
		except Exception as error:
			if not isinstance(error, KeyError):
				return None, error
			key = str(error)[1:-1]
			mapping[key] = missing_fill

if __name__ == '__main__':
	with open('proxies.txt', 'r') as proxy_file:
		proxies = [line.strip() for line in proxy_file.read().split('\n') if line.strip()]
	with open('config.json', 'r') as config_file:
		config = json.load(config_file)

	if 'debug' in sys.argv:
		DEBUG = True

	scraper = R2Scraper(config['ebay'], config['discord'], config['searches'], 'data.json', proxies)
	if sys.argv[-1] != 'test-webhook':
		scraper.run()
	else:
		now = time.time()
		samples = [{
			"id": "123456",
			"listing_id": "987654",
			"url": "https://www.wikiwand.com/en/Standard_test_image",
			"image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/SIPI_Jelly_Beans_4.1.07.tiff/lossy-page1-320px-SIPI_Jelly_Beans_4.1.07.tiff.jpg",
			"title": "Jellybeans!",
			"misc_details": ["Edible", "Yummy"],
			"type": "BUY",
			"curr_price": 15.50,
			"prev_price": 14.50,
			"shipping_price": 0,
			"seller": {
				"username": "mr_jelly_bean",
				"review_count": 100,
				"positive_percentage": 99.5,
				"store_url": "http://stores.ebay.co.uk/mr_jelly_bean",
				"name": "Mr. Jelly Bean"
			},
			"notifications": {}
		}, {
			"id": "654321",
			"listing_id": "789456",
			"url": "https://knowpathology.com.au/2018/07/26/what-is-a-screening-test/",
			"image_url": "https://knowpathology.com.au/app/uploads/2018/07/Happy-Test-Screen-01-825x510.png",
			"title": "TV",
			"misc_details": ["Used", "Works"],
			"type": "AUCTION",    # AUCTION and BUY are the only options
			"ending": now + 60*15, # 60 seconds * 15 minutes from now
			"curr_price": 15.50,
			"prev_price": None,
			"shipping_price": 10,
			"seller": {
				"username": "tv_tom",
				"review_count": 447,
				"positive_percentage": 14.6,
				"store_url": "http://stores.ebay.co.uk/TvTom",
				"name": "TV Tom"
			},
			"notifications": {}
		}]
		for listing in samples:
			for notification in config['discord']['notifications']:
				scraper.notify(listing, notification, now)