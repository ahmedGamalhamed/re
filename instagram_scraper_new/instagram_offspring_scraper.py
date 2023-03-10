import requests
import threading
from utils import get_proxy, read_from_txt, get_config, log, create_table, add_to_post_db, print_error_log
import cfscrape as cfs
from bs4 import BeautifulSoup as BS
from time import sleep
import xml.sax.saxutils as saxutils
from datetime import datetime
from dhooks import Webhook, Embed
import json
import re

def send_post_to_discord(post, webhooks_url, icon):
	hook = Webhook(webhooks_url)
	embed = Embed(
		title='**' + "Instagram Bot" + '**',
		color=0x1e0f3,
		timestamp='now'  # sets the timestamp to current time
	)
	embed.set_author(name=post['username'] , icon_url=icon)
	embed.add_field(name='Caption', value=post['caption'])
	embed.add_field(name='Posted Time', value=post['post_time'])

	if post['isVideo']:
		embed.add_field(name='Type', value="Video Post")
	elif post['isGallery']:
		embed.add_field(name='Type', value="Image Gallery")
	embed.add_field(name='Link', value=post['post_link'])
	embed.set_footer(text='Instagram Monitor ', icon_url="")
	embed.set_image(post['image_link'])

	try:
		hook.send(embed=embed)
	except Exception as e:
		print_error_log(1, str(e))

class InstagramScraper():
	def __init__(self, **kwargs):
		self.config                 = kwargs['config']
		self.proxies                = kwargs['proxies']
		self.stories_url            = self.config.get('stories_url') 
		self.post_webhooks_url      = self.config.get('post_webhooks_url')
		self.tagged_webhooks_url    = self.config.get('tagged_webhooks_url')
		self.hashtag_webhooks_url   = self.config.get('hashtag_webhooks_url')
		self.story_webhooks_url     = self.config.get('story_webhooks_url')
		self.offspringhq_webhooks_url           = self.config.get('offspringhq_webhooks_url')
		self.offspringhq_story_webhooks_url     = self.config.get('offspringhq_story_webhooks_url')
		self.story_base_url         = self.config.get('story_base_url')
		self.ins_icon               = self.config.get('instagram_icon_url')
		self.hash_tag_base_url      = self.config.get('hash_tag_base_url')
		self.tagged_url             = self.config.get('tagged_url')
		self.base_url               = self.config.get('base_url')
		self.login_url              = self.config.get('login_url')
		self.post_base_url          = self.config.get('post_base_url')
		self.monitoing_cycle        = self.config['moncycle_post_hashtag']['monitoring_cycle']
		self.interval_between_task  = self.config['moncycle_post_hashtag']['interval_between_task']
		self.user_agent             = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"
		self.is_login               = False
		self.is_creattable = False

	def start_post_hash_scrape(self, username, dbname):

		self.session = requests.session()
		self.scraper = cfs.create_scraper(delay=10, sess=self.session)
		start_url = self.base_url + username
		webhooks_url = self.offspringhq_webhooks_url

		headers = {
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": self.user_agent,
			"Connection": "keep-alive",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
			'Accept-Language': 'en-US,en;q=0.9',
			"Accept-Encoding": "gzip, deflate, br"
		}
		while True:
			proxies = get_proxy(self.proxies)
			try:
				response = self.scraper.get(start_url, headers=headers, proxies=proxies, timeout=5)
			except Exception as e:
				# log('f', "Post Scrape:" + str(e))
				continue
			if response.status_code == 200:
				if "login" in response.url:
					# print(response.url)
					continue
				else:
					log("i", response.url)
					break
			elif response.status_code == 404:
				log('f', "Incorrect {} Username:[{}]".format(dbname.upper(), username))
				return
			elif response.status_code == 429:
				sleep(10)
				return
			else:
				log('f', 'Post page Status code :' + str(response.status_code))
				continue
		if "Sorry, this page" in response.text:
			log('f', "Incorrect {} Username:[{}]".format(dbname.upper(), username))
			return
		try:
			shared_data = json.loads(response.text.split("window._sharedData = ")[1].split(";</script>")[0])
			# with open('shared_data.json', 'w', encoding='utf-8') as f:
			#     json.dump(shared_data, f)
			if dbname == "post":
				lists = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']
			elif dbname == "hashtag":
				lists = shared_data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['edges']
			else:
				return
			for item in lists:
				shortcode = item['node']['shortcode']
				alert = add_to_post_db(shortcode, username, dbname )
				if alert and (alert == "New") :
					try:
						self.get_post_detail(shortcode, username, webhooks_url)
					except:
						continue
		except Exception as e:
			print_error_log(1, "Fail get {} --> Username:[{}] : URL: {}".format(dbname.upper(), username, response.url))

	def get_post_detail(self, postlink, username, webhooks_url):
		post_url = self.post_base_url + postlink
		while True:
			proxies = get_proxy(self.proxies)
			try:
				response = self.scraper.get(post_url, timeout=5, proxies=proxies)
			except:
				try:
					response = self.scraper.get(post_url, timeout=5, proxies=proxies)
				except Exception as e:
					continue
			if response.status_code == 200:
				break
			elif response.status_code == 404:
				log('f', "Incorrect Post Link:[{}]".format(postlink))
				return
			else:
				continue
		post = { }
		html = BS(response.content, features='lxml')
		isVideo = False
		isGallery = False

		shared_data = json.loads(response.text.split("window._sharedData = ")[1].split(";</script>")[0])

		try:
			caption = shared_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_media_to_caption']['edges'][0]['node']['text']
			caption = saxutils.unescape(caption)
			if len(caption) > 1001:
				caption = caption[:1000] + "..."
		except:
			caption = 'No caption'

		taken_at_timestamp = shared_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['taken_at_timestamp']
		timeStamp = str(datetime.fromtimestamp(int(taken_at_timestamp))).replace('-', '/')

		is_video = shared_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['is_video']
		if is_video:
			isVideo = True
			
		try:
			gallery = shared_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']
			isGallery = True
		except:
			isGallery = False

		try:
			imageLink = html.find('meta', {"property" : "og:image" })['content']
		except:
			imageLink = ""

		post.update({'caption': caption})
		post.update({'isVideo': isVideo})
		post.update({'isGallery': isGallery})
		post.update({'post_link': post_url})
		post.update({'post_time': timeStamp})
		post.update({'image_link': imageLink})
		post.update({'username': username})
		send_post_to_discord(post, webhooks_url, self.ins_icon)

	def run(self):
		while True:
			try:
				log('s', "Start Tasks")
				self.start()
			except Exception as e:
				print_error_log(1, str(e))
				continue
			sleep(self.monitoing_cycle)
			
	def start(self):
		postusername = "offspringhq"
		if not self.is_creattable:
			create_table(postusername, "post")
			self.is_creattable = True
		else:
			log("i", "Start Scraping [{}] Posts ... ".format(postusername))
			self.start_post_hash_scrape(postusername, "post")
			sleep(self.interval_between_task) #Timeinterva between tasks

if (__name__ == "__main__"):
	# config = get_config("config_test.json")#When TEST
	# proxies = read_from_txt("proxies.txt")#When TEST
	config = get_config("config.json")#When REAL
	proxies = read_from_txt("proxies_offspring.txt")#When REAL
	log('i', str(len(proxies)) + "\t Proxies loaded.")

	insScraper = InstagramScraper(
						proxies=proxies, 
						config=config)
	insScraper.run()
