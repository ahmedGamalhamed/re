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

class AccountBlock(Exception):
	def __init__(self,*args,**kwargs):
		Exception.__init__(self,*args,**kwargs)
	''' Raised when account is blocked due to many request Status code 429. '''

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
		print_error_log(2, str(e))

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

def send_account_verification_alert(login_username, webhooks_url):
	hook = Webhook(webhooks_url)
	embed = Embed(
		title='**' + "Instagram Account Verification Alert!" + '**',
		color=0x1e0f3,
		timestamp='now'  # sets the timestamp to current time
	)
	embed.add_field(name='Username', value=login_username)
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
		self.alert_webhooks_url     = self.config.get('alert_webhooks_url')
		self.offspringhq_webhooks_url           = self.config.get('offspringhq_webhooks_url')
		self.offspringhq_story_webhooks_url     = self.config.get('offspringhq_story_webhooks_url')
		self.story_base_url         = self.config.get('story_base_url')
		self.ins_icon               = self.config.get('instagram_icon_url')
		self.hash_tag_base_url      = self.config.get('hash_tag_base_url')
		self.tagged_url             = self.config.get('tagged_url')
		self.base_url               = self.config.get('base_url')
		self.login_url              = self.config.get('login_url')
		self.post_base_url          = self.config.get('post_base_url')
		self.account_switching_time_second = self.config.get("account_switching_time_hour") * 3600

		self.scrape_start_time_with_new_account = 0
		self.monitoing_cycle        = self.config['moncycle_story_tagged']['monitoring_cycle']
		self.interval_between_task  = self.config['moncycle_story_tagged']['interval_between_task']
		self.interval_between_user  = self.config['moncycle_story_tagged']['interval_between_user']
		self.user_agent             = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"
		self.is_login               = False
		self.accounts_list          = self.config.get('accounts')
		self.accounts_num           = len(self.config.get('accounts'))
		self.current_account_idx    = 0

		self.db_name        = config['dbname']
		self.mongodbserver  = config['mongodbserver']
		self.mongodatabase  = config['mongodatabase']
		self.client         = MongoClient(self.mongodbserver)
		self.database       = self.client[self.mongodatabase]
		self.collection     = self.database[self.db_name]
		

	def login(self, idx):
		self.login_username         = self.accounts_list[idx].get('login_username')
		self.login_password         = self.accounts_list[idx].get('login_password')
		headers = {
			"User-Agent": "Instagram 52.0.0.8.83 (iPhone; CPU iPhone OS 11_4 like Mac OS X; en_US; en-US; scale=2.00; 750x1334) AppleWebKit/605.1.15",
			"Referer": self.base_url,
		}

		self.session = requests.session()

		while True:
			self.proxy = get_proxy(self.proxies)
			try:
				response = self.session.get(self.base_url, timeout=5, proxies=self.proxy, headers=headers)
			except Exception as e:
				continue
			if response.status_code == 200:
				break
			else:
				continue
		csrf_token = self.session.cookies.get('csrftoken')
		login_payload = { "username": self.login_username, "password": self.login_password}
		login_headers = {
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": "Instagram 52.0.0.8.83 (iPhone; CPU iPhone OS 11_4 like Mac OS X; en_US; en-US; scale=2.00; 750x1334) AppleWebKit/605.1.15",
			"Connection": "keep-alive",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
			'Accept-Language': 'en-US,en;q=0.9',
			"Accept-Encoding": "gzip, deflate, br",
			"Content-Type": "application/x-www-form-urlencoded",
			"X-Requested-With": "XMLHttpRequest",
			"X-CSRFToken" : csrf_token,
		}
		while True:
			sleep(5)
			self.session.headers = login_headers
			try:
				login = self.session.post(self.login_url, data=login_payload, timeout=5, proxies=self.proxy)
			except:
				try:
					sleep(5)
					self.proxy = get_proxy(self.proxies)
					login = self.session.post(self.login_url, data=login_payload, timeout=5, proxies=self.proxy)
				except Exception as e:
					print(repr(e))
					continue
			try:
				login_text = login.json()
			except Exception as e:
				continue

			if login_text.get('authenticated') and login.status_code == 200:
				self.session.headers.update({'User-Agent' : self.user_agent})
				self.is_login = True
				log('s', "Login Success [{}]".format(self.login_username))
				print_error_log(2, "Login Success [{}]".format(self.login_username))
				self.get_login_activiry()
				break
			elif 'checkpoint_url' in login_text:
				checkpoint_url = login_text.get('checkpoint_url')
				log("i", 'Please verify your account [{}] at '.format(self.login_username) + self.base_url[0:-1] + checkpoint_url)
				try:
					sleep(5)
					self.login_challenge(checkpoint_url)
				except Exception as e:
					continue
				if self.is_login:
					log('s', "Account Verify and Login Success [{}]".format(self.login_username))
					print_error_log(2, "Account Verify and Login Success [{}]".format(self.login_username))
					break
				else:
					continue
			elif 'errors' in login_text:
				for count, error in enumerate(login_text['errors'].get('error')):
					count += 1
					log('f', 'Session error %(count)s: "%(error)s"' % locals())
			else:
				print(login_text)

	def get_login_activiry(self):
		try:
			response = self.session.get("https://www.instagram.com/session/login_activity/", timeout=5, proxies=self.proxy)
		except Exception as e:
			print_error_log(2, "Get login activity" + str(e))
		if response.status_code == 200:
			shared_data = json.loads(response.text.split("window._sharedData = ")[1].split(";</script>")[0])
			for item in shared_data['entry_data']['SettingsPages'][0]['data']['suspicious_logins']:
				self.clear_login_activity(item['id'])
				sleep(2)
			for item in shared_data['entry_data']['SettingsPages'][0]['data']['sessions']:
				if item['is_current']:
					self.current_login_sessionid = item['id']
				else:
					self.old_session_logout(item['id'])
				sleep(2)
		else:
			print_error_log(2, "Fail get login activity : Status code" + str(response.status_code))

	def old_session_logout(self, session_id):
		data = { "session_id" : session_id }
		csrf_token = self.session.cookies.get('csrftoken')
		headers = { "User-Agent": self.user_agent, "X-CSRFToken" : csrf_token }
		try:
			response = self.session.post("https://www.instagram.com/session/login_activity/logout_session/",headers=headers, data=data, timeout=5, proxies=self.proxy)
			if response.status_code == 200:
				log('s', "Clear old loggedin session SessionId : [{}]".format(session_id))
				return True
			else:
				print_error_log(2, "Fail Clear old loggedin session SessionId : [{}] Status code: {}".format(session_id + str(response.status_code)))
				return False
		except Exception as e:
			print_error_log(2, "Exception Clear old loggedin session " + str(e))
			return False


	def clear_login_activity(self, login_id):
		data = { "login_id" : login_id }
		csrf_token = self.session.cookies.get('csrftoken')
		headers = { "User-Agent": self.user_agent, "X-CSRFToken" : csrf_token }
		try:
			response = self.session.post("https://www.instagram.com/session/login_activity/avow_login/",headers=headers, data=data, timeout=5, proxies=self.proxy)
			if response.status_code == 200:
				log('s', "Verify old loggedin activy LoginId:[{}]".format(login_id))
			else:
				print_error_log(2, "Fail Verify old loggedin activy LoginId:[{}] Status code: {}".format(login_id,  str(response.status_code)))
		except Exception as e:
			print_error_log(2, "Exception Verify old loggedin activy : " + str(e))


	def login_challenge(self, checkpoint_url):
		self.session.headers.update({'Referer': self.base_url})
		req = self.session.get(self.base_url[:-1] + checkpoint_url, timeout=5, proxies=self.proxy)
		self.session.headers.update({'X-CSRFToken': req.cookies['csrftoken'], 'X-Instagram-AJAX': '1'})

		self.session.headers.update({'Referer': self.base_url[:-1] + checkpoint_url})
		send_account_verification_alert(self.login_username, self.alert_webhooks_url)
		mode = int(input('Choose a challenge mode (0 - SMS, 1 - Email): '))
		challenge_data = {'choice': mode}
		challenge = self.session.post(self.base_url[:-1] + checkpoint_url, data=challenge_data, allow_redirects=True, timeout=5, proxies=self.proxy)
		self.session.headers.update({'X-CSRFToken': challenge.cookies['csrftoken'], 'X-Instagram-AJAX': '1'})
		code = int(input('Enter code received: '))
		code_data = {'security_code': code}
		code = self.session.post(self.base_url[:-1] + checkpoint_url, data=code_data, allow_redirects=True, proxies=self.proxy, timeout=5)
		self.session.headers.update({'X-CSRFToken': code.cookies['csrftoken']})
		self.session.headers.update({'User-Agent': self.user_agent})
		self.cookies = code.cookies
		code_text = json.loads(code.text)
		if code_text.get('status') == 'ok':
			self.authenticated = True
			self.is_login = True
			self.get_login_activiry()
		elif 'errors' in code.text:
			for count, error in enumerate(code_text['challenge']['errors']):
				count += 1
				log("e", 'Session error %(count)s: "%(error)s"' % locals())
		else:
			pass
			# log('e', json.dumps(code_text))

	def start_tagged_scrape(self, username, dbname):
		while True:
			try:
				self.proxy = get_proxy(self.proxies)
				res = self.session.get(self.base_url + username, timeout=5, proxies=self.proxy)
			except Exception as e:
				# log('f', "Tagged :" + str(e))
				continue
			if res.status_code == 200:
				if "Sorry, this page" in res.text:
					log('f', "Incorrect Tagged Username:[{}]".format(username))
					return
				try:
					shared_data = json.loads(res.text.split("window._sharedData = ")[1].split(";</script>")[0])
					user = self.deep_get(shared_data, 'entry_data.ProfilePage[0].graphql.user')
				except Exception as e:
					log('f', "Incorrect Tagged Username:[{}]".format(username))
					return
				if user:
					break
				else:
					continue
			elif res.status_code == 404:
				log('f', "Incorrect Tagged Username:[{}]".format(username))
				return
			elif res.status_code == 429:
				print_error_log(2, "Account Block [{}]:".format(self.login_username) + str(res.status_code))
				raise AccountBlock()
			else:
				# log('f', "Get Tagged Link:" + str(res.status_code))
				continue

		while True:
			try:
				response = self.session.get(self.tagged_url.format(user['id']), timeout=5, proxies=self.proxy)
			except Exception as e:
				continue
			if response.status_code == 200:
				break
			elif response.status_code == 429:
				print_error_log(2, "Account Block [{}]:".format(self.login_username) + str(response.status_code))
				raise AccountBlock()
			else:
				return
		try:
			if response is not None:
				retval = json.loads(response.text)
				for item in retval['data']['user']['edge_user_to_photos_of_you']['edges']:
					post_code = item['node']['shortcode']
					alert = add_to_post_mongodb(self.collection, post_code, username, dbname)
					if alert and (alert == "New") :
						try:
							self.get_post_detail(post_code, username, self.tagged_webhooks_url)
							sleep(0.5)
						except AccountBlock:
							raise AccountBlock()
						except Exception:
							continue
		except AccountBlock:
			raise AccountBlock()
		except Exception:
			log('f', "Fail Get Tagged Post --> Username:[{}]".format(username))
			return

	def start_story_scrape(self, username, dbname):
		while True:
			try:
				self.proxy = get_proxy(self.proxies)
				res = self.session.get(self.base_url + username, timeout=5, proxies=self.proxy)
			except Exception as e:
				continue
			if res.status_code == 200:
				if "Sorry, this page" in res.text:
					log('f', "Incorrect Story Username:[{}]".format(username))
					return
				try:
					shared_data = json.loads(res.text.split("window._sharedData = ")[1].split(";</script>")[0])
					user = self.deep_get(shared_data, 'entry_data.ProfilePage[0].graphql.user')
				except Exception as e:
					log('f', "Incorrect Story Username:[{}]".format(username))
					return

				if user:
					break
				else:
					continue
			elif res.status_code == 404:
				log('f', "Incorrect Story Username:[{}]".format(username))
				return None
			elif res.status_code == 429:
				print_error_log(2, "Account Block [{}]:".format(self.login_username) + str(res.status_code))
				raise AccountBlock()
			else:
				continue
		while True:
			try:
				response = self.session.get(self.stories_url.format(user['id']), timeout=5, proxies=self.proxy)
			except Exception as e:
				continue
			if response.status_code == 200:
				break
			elif response.status_code == 429:
				print_error_log(2, "Account Block [{}]:".format(self.login_username) + str(response.status_code))
				raise AccountBlock()
			else:
				return None
		try:
			if response is not None:
				retval = json.loads(response.text)
				if retval['data'] and 'reels_media' in retval['data'] and len(retval['data']['reels_media']) > 0 and len(retval['data']['reels_media'][0]['items']) > 0:
					return [self.set_story_url(item) for item in retval['data']['reels_media'][0]['items']]
		except:
			log('f', "Incorrect Story Username:[{}]".format(username))
			return None
	
	def set_story_url(self, item):
		"""Sets the story url."""
		urls = []
		if 'video_resources' in item:
			urls.append(item['video_resources'][-1]['src'])
		if 'display_resources' in item:
			urls.append(item['display_resources'][-1]['src'])
		item['urls'] = urls
		return item

	def add_story_to_db(self, story_links, username, dbname):
		if username == "offspringhq":
			webhooks_url = self.offspringhq_story_webhooks_url
		else:
			webhooks_url = self.story_webhooks_url
		for item in story_links:
			story_url = self.story_base_url + username
			alert = add_to_post_db(item.get('id'), username, dbname )
			if (alert is not None) and (alert == "New") :
				post = {}
				post.update({'story_link' : story_url })
				if item.get('story_cta_url'):
					post.update({'swipe_up_link': item.get('story_cta_url')})
				else:
					post.update({'swipe_up_link': "None"})
				if item.get('display_url'):
					post.update({'image_link' : item.get('display_url')})
				else:
					post.update({'image_link' : "None"})
				post.update({'username': username})
				try:
					send_story_to_discord(post, webhooks_url, self.ins_icon)
				except:
					continue

	def deep_get(self, dict, path):
		def _split_indexes(key):
			split_array_index = re.compile(r'[.\[\]]+')  # ['foo', '0']
			return filter(None, split_array_index.split(key))
		ends_with_index = re.compile(r'\[(.*?)\]$')  # foo[0]
		keylist = path.split('.')
		val = dict
		for key in keylist:
			try:
				if ends_with_index.search(key):
					for prop in _split_indexes(key):
						if prop.isdigit():
							val = val[int(prop)]
						else:
							val = val[prop]
				else:
					val = val[key]
			except (KeyError, IndexError, TypeError):
				return None
		return val


	def get_post_detail(self, postlink, username, webhooks_url):
		post_url = self.post_base_url + postlink
		headers = {
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
		session = requests.session()
		self.proxy = get_proxy(self.proxies)
		session.proxies = self.proxy
		session.headers = headers

		response = session.get(post_url, timeout=5)

		if response.status_code == 200:
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

		elif response.status_code == 404:
			log('f', "Incorrect Post Link:[{}]".format(postlink))

		elif response.status_code == 429:
			print_error_log(2, "Account Block [{}]:".format(self.login_username) + str(response.status_code))
			raise AccountBlock()
		else:
			log('f', 'Fail Get Project Detail :[{}]'.format(postlink))

	def run(self):
		while True:
			try:
				cur_timestamp = datetime.timestamp(datetime.now())
				run_time = cur_timestamp - self.scrape_start_time_with_new_account

				if self.is_login and run_time < self.account_switching_time_second:
					self.start()
					# sleep(self.monitoing_cycle)

					#Added for one tiem cycle 2020-5-28 KGS
					log('s', "Ended Tagged Scraper")
					break
				
				else:
					self.scrape_start_time_with_new_account = datetime.timestamp(datetime.now())
					self.is_login = False
					self.login(self.current_account_idx)

					if self.current_account_idx == self.accounts_num - 1 :
						self.current_account_idx = 0
					else:
						self.current_account_idx = self.current_account_idx + 1

			except AccountBlock:
				log('f', "Account Is Blocked :[{}]...".format(self.login_username))
				log('i', "Changing Account...")
				if self.old_session_logout(self.current_login_sessionid):
					self.is_login = False
					log('s', "Logout Account: [{}]".format(self.login_username))
					print_error_log(2, "Logout Account: [{}]".format(self.login_username))
					if self.current_account_idx == self.accounts_num - 1:
						self.current_account_idx = 0
					else:
						self.current_account_idx = self.current_account_idx + 1
					continue
				else:
					log('f', "Logout Fail [{}]".format(self.login_username))
					continue

			except Exception as e:
				print_error_log(2, str(e))
				# raise(e)
				continue
			
	def start(self):
		log('s', "Start Tasks")

		taggedusernames = read_from_txt("taggedusernames.txt")
		log("i", "Start scrape Tagged posts ... {} Usernames loaded ".format(len(taggedusernames)))
		for taggedusername in taggedusernames:
			if taggedusername == "":
				continue
			log("i", "Extracting '{}' Tagged posts  ".format(taggedusername))
			self.start_tagged_scrape(taggedusername, "tagged")
			sleep(self.interval_between_user)
		
		sleep(self.interval_between_task)#Timeinterva between tasks
			
		storyusernames = read_from_txt("storyusernames.txt")
		log("i", "Start scrape Stories ... {} Usernames loaded ".format(len(storyusernames)) )
		for storyusername in storyusernames:
			if storyusername == "":
				continue
			storylinks = self.start_story_scrape(storyusername, "stories")
			if (storylinks is not None) and (len(storylinks) > 0):
				self.add_story_to_db(storylinks, storyusername, "stories")
			sleep(self.interval_between_user)

if (__name__ == "__main__"):
	# config = get_config("config_test.json")#When TEST
	# proxies = read_from_txt("proxies.txt")#When TEST
	config = get_config("config.json")#When REAL
	proxies = read_from_txt("proxies_story_tagged.txt")#When REAL
	log('i', str(len(proxies)) + "\t Proxies loaded.")

	insScraper = InstagramScraper(
						proxies=proxies, 
						config=config)
	insScraper.run()
