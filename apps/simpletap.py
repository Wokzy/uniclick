
import sys
import time
import copy
import utils
import urllib
import requests
import datetime


from app_logger import AppLogger
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest


# CONFIG = utils.load_config()['apps']['simpletap']

COMPLETE_1WIN_TOKEN = False
HTTP_MAX_RETRY = 5 # amount of http request retries
BOT_NAME = 'Simple_Tap_Bot'
APP_URL = 'https://simpletap.app/'
API_URL = 'https://api.thesimpletap.app/api/v1/public/telegram/'

ESSENTIAL_TASKS_TG_CHANNELS = ['smpl_app', 'alexfromsimple']
UPDATE_URL_TIMEOUT = datetime.timedelta(days=1)
# EXCEPTIONAL_TASKS = frozenset({9900628480, 9900628482})


class SimpleTap:
	def __init__(self, base_url:str, user_id:int, config:dict):
		self.name = 'SimpleTap'

		self.base_url = base_url
		self.user_id = user_id
		self.auth_data = self.extract_auth_data()
		self.session = requests.Session()
		self.url_update_timer = datetime.datetime.now()

		self.logger = AppLogger(self.name)
		self.status = None
		self.warning = None

		self.config = config

		self.inline_report_info = 'fetching balace...'


	def get_post_headers(self) -> dict:
		""" Standart headers for post request"""
		return {
				'Accept':'application/json, text/plain, */*',
				'Accept-Encoding':'gzip, deflate, br, zstd',
				'Accept-Language':'en-US,en;q=0.5',
				'Connection':'keep-alive',
				# 'Content-Length':'358',
				'Sec-Fetch-Dest':'empty',
				'Sec-Fetch-Mode':'cors',
				'Sec-Fetch-Site':'cross-site',
				'Sec-GPC':'1',
				'TE':'trailers',
				'DNT':'1',
				'Host':'api.thesimpletap.app',
				'Origin':'https://simpletap.app',
				'Referer':'https://simpletap.app/',
				'Content-Type':'application/json',
				'User-Agent':'Mozilla/5.0 (iPhone; U; CPU like Mac OS X; en) AppleWebKit/420+ (KHTML, like Gecko) Version/3.0 Mobile/1A543 Safari/419.3',
			}


	def extract_auth_data(self) -> str:
		""" Get auth data from url """
		# print(self.base_url)
		return urllib.parse.unquote(self.base_url).split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]


	def update_base_url(self, new_url:str):
		self.base_url = new_url
		self.auth_data = self.extract_auth_data()

		self.session.close()
		self.session = requests.Session()


	def fetch_user_data(self) -> dict:
		""" Fetch data using profile method """
		return self.make_post_request('profile')['data']


	def get_mining_blocks(self) -> dict:
		return {block['mineId']:block for block in self.make_post_request('get-mining-blocks')['data']['mines']}


	def get_task_list(self) -> dict:
		""" Returns task list """

		payload = {"lang":"en", "platform":2}
		return self.make_post_request('get-task-list-2', payload=payload)['data']


	def _tap_coins(self, user_data:dict) -> None:
		""" Make availible taps """

		if user_data['availableTaps'] > 10:
			self.make_post_request('tap', {'count':user_data['availableTaps']})

			self.logger.log_app(self.user_id, f"Made {user_data['availableTaps']} taps")


	def _farm_coins(self, user_data:dict) -> None:
		""" Start farming and claim """

		if user_data['activeFarmingSeconds'] >= user_data['maxFarmingSecondSec']:
			# print('Claiming farm...')
			self.make_post_request('claim')
			self.make_post_request('activate')

		if user_data['activeFarmingSeconds'] == 0:
			# print('Staring farming...')
			self.make_post_request('activate')


	def _spin_wheel(self, user_data:dict) -> None:
		""" Wheel spinning """

		if user_data['spinCount'] > 0:
			# print('Spinning wheel')
			self.make_post_request('claim-spin', payload={'amount':user_data['spinCount']})
			# print(f'Spinned wheel {user_data["spinCount"]}')


	def _purchace_mining_blocks(self) -> None:
		""" Buy 'mining' blocks (passive profit) """

		global blocks
		blocks = self.get_mining_blocks()

		def __buy_mining(name, force='') -> bool:
			global blocks
			blocks = self.get_mining_blocks()

			if blocks[name]['dependencyMineId'] is not None:
				while blocks[name]['dependencyMineLevel'] > blocks[blocks[name]['dependencyMineId']]['currentLevel']:
					if not __buy_mining(blocks[blocks[name]['dependencyMineId']]['mineId'], force=name):
						return False

			if blocks[name]['nextPrice'] > self.fetch_user_data()['balance']:
				return False

			try:
				self.make_post_request('buy-mining-block', payload={"mineId":blocks[name]['mineId'], "level":blocks[name]['currentLevel'] + 1})
			except AssertionError as e:
				self.logger.log_app(self.user_id, e)

			string = f'Upgraded {blocks[name]["mineId"]} to level {blocks[name]["currentLevel"] + 1}'
			if force:
				self.logger.log_app(self.user_id, f"{string} (required by {force})")
			else:
				self.logger.log_app(self.user_id, string)

			return True


		for name in list(blocks.keys()):
			if blocks[name]['currentLevel'] < self.config['max_cards_level']:
				__buy_mining(name)


	def _complete_tasks(self) -> None:
		""" Complete inessential tasks, which does not require any effort """

		tasks = [task for task in self.get_task_list()['social'] if not task['isRequire'] and task['status'] < 3]

		# _easy_url_patterns = ['apps.apple.com', 'bit.ly', 'tiktok.com', 'linkedin.com', 'instagram.com', 'twitter.com', 'x.com']
		# print(tasks)
		for task in tasks:
			# if task['id'] in EXCEPTIONAL_TASKS:
			# 	continue

			# for url in _easy_url_patterns:
				# if task['url'] is None or url in task['url']:
					# print(f'Completing task {task["id"]}')

			if task['status'] == 1:
				self.make_post_request('start-task-start-2', payload={'type':task['type'], 'id':task['id']})
			self.make_post_request('check-task-check-2', payload={'type':task['type'], 'id':task['id']})


	def update_all(self):
		# print('updating all')
		user_data = self.fetch_user_data()

		self.inline_report_info = f'balance: {user_data["balance"]}'

		self._tap_coins(user_data)
		self._farm_coins(user_data)
		self._spin_wheel(user_data)
		self._purchace_mining_blocks()
		self._complete_tasks()


	def make_post_request(self, method:str, payload:dict = {}) -> dict:
		"""  """

		data = copy.deepcopy(payload)
		data['authData'] = self.auth_data
		data['userId'] = self.user_id

		headers = self.get_post_headers()
		url = urllib.parse.urljoin(API_URL, method)

		_error_message = f"Error encountered in: {url}"

		# print(url)

		result = None
		for i in range(HTTP_MAX_RETRY):
			try:
				result = self.session.post(url, headers=headers, json=data)
			except Exception as e:
				time.sleep(3)
				# print(e, 'retrying....')
				# if result.status_code == 104:
				# 	time.sleep(2)
				# time.sleep(1)
				continue

			if result.status_code in {200, 201} and result.json()['result'] == 'OK':
				return result.json()

			time.sleep(1)

		# self.logger.log_app(self.user_id, result.text)
		assert result.status_code in {200, 201}, _error_message + f'\n{result.status_code}: {result.text} {result.request}'
		assert result.json()['result'] == 'OK', _error_message + f'\n{result.json()}'
		return result.json()



def get_essnsial_tasks(class_instance:SimpleTap):
	return [i for i in class_instance.get_task_list()['social'] if i['isRequire'] and i['status'] in {1, 2, 0}]


async def token1win_(client:TelegramClient, class_instance:SimpleTap):
	await client.send_message('token1win_bot', f'/start')
	app_url = await utils.get_base_app_url(
						client = client,
						bot_name='token1win_bot',
						app_url='https://cryptocklicker-frontend-rnd-prod.100hp.app/',
						)

	# if '--debug' in sys.argv:
	# 	print(app_url)

	if requests.get(app_url).status_code != 200:
		class_instance.logger.log_app(class_instance.user_id, f"WARNING: token1win error: status code is not 200", False)



async def complete_essential_tasks(client:TelegramClient, class_instance:SimpleTap):
	""" status == 3 means that the task was completed """
	tasks = get_essnsial_tasks(class_instance)
	message = ''

	async def __complete():
		for task in tasks:
			if task['status'] == 1:
				class_instance.make_post_request('start-task-start-2', payload={'type':task['type'], 'id':task['id']})

			for channel in ESSENTIAL_TASKS_TG_CHANNELS:
				if channel in task['url']:
					await client(JoinChannelRequest(channel = channel))
					response = class_instance.make_post_request('check-task-check-2', payload={'type':task['type'], 'id':task['id']})
					# await client(LeaveChannelRequest(channel = channel))

			class_instance.make_post_request('check-task-check-2', payload={'type':task['type'], 'id':task['id']})

			if COMPLETE_1WIN_TOKEN and 'token1win_bot' in task['url']:
				await token1win_(client, class_instance)

			# message = f'Go to {task['url']} and run the application to complete one of the manual essential tasks'

	await __complete()
	attemts = 3

	while len(get_essnsial_tasks(class_instance)) > 0 and attemts > 0:
		class_instance.warning = 'Smth wrong with essential tasks completion, try to run token1win_bot (that is one of the problematic tasks)'
		await __complete()
		attemts -= 1


async def get_simpletap_url(client:TelegramClient) -> str:
	return await utils.get_base_app_url(client, BOT_NAME, APP_URL)


async def simpletap_init(client:TelegramClient, config) -> SimpleTap:
	# await client.send_message('Simple_Tap_Bot', f'/start')

	url = await get_simpletap_url(client)
	user = await client.get_me()

	return SimpleTap(url, user.id, config=config)


async def simpletap_update(app:SimpleTap, client:TelegramClient) -> None:

	try:
		try:
			if len(get_essnsial_tasks(app)) > 0:
				if app.status is None:
					app.status = 'completing essential tasks'

				await complete_essential_tasks(client, app)
		except:
			pass

		if (datetime.datetime.now() - app.url_update_timer) > UPDATE_URL_TIMEOUT:
			if '--debug' in sys.argv:
				app.logger.log_app(app.user_id, f"updating url")
			app.url_update_timer = datetime.datetime.now()
			app.update_base_url(new_url = await get_simpletap_url(client))

		# print('update all')
		app.update_all()
		app.status = None
		app.warning = None
	except Exception as e:
		app.logger.log_app(app.user_id, str(e))
		app.status = 'warning'
		app.warning = e

