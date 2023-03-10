import requests
import threading
from utils import *
import cfscrape as cfs
from bs4 import BeautifulSoup as BS
from time import sleep
import xml.sax.saxutils as saxutils
from datetime import datetime
from dhooks import Webhook, Embed
import json
import re

from pymongo import MongoClient, TEXT, IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, InvalidName, DuplicateKeyError

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

def send_story_to_discord(story, webhooks_url, icon):
	hook = Webhook(webhooks_url)
	embed = Embed(
		title='**' + "Instagram Bot" + '**',
		color=0x1e0f3,
		timestamp='now'  # sets the timestamp to current time
	)
	embed.set_author(name=story['username'] , icon_url=icon)
	embed.add_field(name='StoryLink', value=story['story_link'])
	embed.add_field(name='Swipe Up Link', value=story['swipe_up_link'])
	embed.set_image(story['image_link'])

	embed.set_footer(text='Instagram Monitor ', icon_url="")

	try:
		hook.send(embed=embed)
	except Exception as e:
		raise(e)

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
		self.interval_between_user  = self.config['moncycle_post_hashtag']['interval_between_user']
		self.user_agent             = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
		self.is_login               = False
		
		self.db_name        = config['dbname']
		self.mongodbserver  = config['mongodbserver']
		self.mongodatabase  = config['mongodatabase']
		self.client         = MongoClient(self.mongodbserver)
		self.database       = self.client[self.mongodatabase]
		self.collection     = self.database[self.db_name]
		self.headers = {
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": self.user_agent,
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
			'Accept-Language': 'en-US,en;q=0.9',
			"Accept-Encoding": "gzip, deflate, br",
			"cache-control": "max-age=0",
			"sec-fetch-dest": "document",
			"sec-fetch-mode": "navigate",
			"sec-fetch-site": "none",
			"sec-fetch-user": "?1"
		}

	def start_post_hash_scrape(self, username, dbname):

		self.session = requests.session()
		if dbname == "post":
			start_url = self.base_url + username
			webhooks_url = self.post_webhooks_url
		elif dbname == "hashtag":
			start_url = self.hash_tag_base_url + username
			webhooks_url = self.hashtag_webhooks_url
		while True:
			self.proxy = get_proxy(self.proxies)
			try:
				self.session.headers = self.headers
				self.session.proxies = self.proxy
				response = self.session.get(start_url, timeout=5)
			except Exception as e:
				# log('f', "Post Scrape:" + str(e))
				continue
			if response.status_code == 200:
				if "login" in response.url:
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
			if dbname == "post":
				lists = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']
			elif dbname == "hashtag":
				lists = shared_data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['edges']
			else:
				return
			for item in lists:
				shortcode = item['node']['shortcode']
				type = dbname
				alert = add_to_post_mongodb(self.collection, shortcode, username, type)
				if alert and (alert == "New") :
					try:
						self.get_post_detail(shortcode, username, webhooks_url)
					except:
						continue
		except Exception as e:
			print_error_log(1, "Fail get {} --> Username:[{}] Due to {}".format(dbname.upper(), username, str(e)))

	def get_post_detail(self, postlink, username, webhooks_url):
		post_url = self.post_base_url + postlink
		session = requests.session()
		while True:
			try:
				self.proxy = get_proxy(self.proxies)
				session.proxies = self.proxy
				session.headers = self.headers
				response = session.get(post_url, timeout=5)
			except:
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
		monitor_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

		post.update({'caption': caption})
		post.update({'isVideo': isVideo})
		post.update({'isGallery': isGallery})
		post.update({'post_link': post_url})
		post.update({'post_time': timeStamp})
		post.update({'image_link': imageLink})
		post.update({'username': username})
		post.update({'added_datetime': monitor_time})
		
		update_post_data(self.collection, postlink, post)
		send_post_to_discord(post, webhooks_url, self.ins_icon)

	def run(self):
		while True:
			try:
				self.start()
			except Exception as e:
				print_error_log(1, str(e))
				continue
			sleep(self.monitoing_cycle)
			
	def start(self):
		log('s', "Start Tasks")

		postusernames = read_from_txt("postusernames.txt")
		log("i", "Start scrape Posts ... {} Usernames loaded ".format(len(postusernames)))
		for postusername in postusernames:
			if postusername == "":
				continue
			self.start_post_hash_scrape(postusername, "post")
			sleep(self.interval_between_user)

		sleep(self.interval_between_task) #Timeinterva between tasks

		hashtags = read_from_txt("hashtags.txt")
		log("i", "Start scrape Hashtag posts ... {} Hashtags loaded ".format(len(hashtags)))
		for hashtag in hashtags:
			if hashtag == "":
				continue
			self.start_post_hash_scrape(hashtag, "hashtag")
			sleep(self.interval_between_user)

if (__name__ == "__main__"):
	# config = get_config("config_test.json")#When TEST
	# proxies = read_from_txt("proxies.txt")#When TEST
	config = get_config("config.json")#When REAL
	proxies = read_from_txt("proxies_post_hashtag.txt")#When REAL
	log('i', str(len(proxies)) + "\t Proxies loaded.")

	insScraper = InstagramScraper(
						proxies=proxies, 
						config=config)
	insScraper.run()
