
import time
import copy
import urllib
import requests

from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest


HTTP_MAX_RETRY = 2 # amount of http request retries
BOT_NAME = 'Simple_Tap_Bot'
APP_URL = 'https://simpletap.app/'
API_URL = 'https://api.thesimpletap.app/api/v1/public/telegram/'


__ESSENTIAL_TASKS_TG_CHANNELS = ['smpl_app', 'alexfromsimple']


def get_essnsial_tasks(class_instance):
	return [i for i in class_instance.make_post_request('get-task-list-2')['data']['social'] if i['isRequire'] and i['status'] < 3]


async def complete_essential_tasks(client:TelegramClient, class_instance):
	""" status == 3 means that the task was completed """
	tasks = get_essnsial_tasks(class_instance)
	message = ''

	for task in tasks:
		if task['status'] == 1:
			class_instance.make_post_request('start-task-start-2', payload={'type':task['type'], 'id':task['id']})

		for channel in __ESSENTIAL_TASKS_TG_CHANNELS:
			if channel in task['url']:
				await client(JoinChannelRequest(channel = channel))
				response = class_instance.make_post_request('check-task-check-2', payload={'type':task['type'], 'id':task['id']})
				await client(LeaveChannelRequest(channel = channel))

		class_instance.make_post_request('check-task-check-2', payload={'type':task['type'], 'id':task['id']})

		if 'token1win_bot' in task['url']:
			message = f'Go to {task['url']} and run the application to complete one of the manual essential tasks'

	if len(get_essnsial_tasks(class_instance)) == 0:
		print('Completed essential tasks')
	else:
		print(message)
		input('Print [Y] if you are done -> ')

	# return tasks


class SimpleTap:
	def __init__(self, base_url:str, user_id:int):
		self.base_url = base_url
		self.user_id = user_id
		self.auth_data = self.extract_auth_data()
		self.session = requests.Session()


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


	def _tap_coins(self, user_data:dict) -> None:
		""" Make availible taps """

		if user_data['availableTaps'] > 10:
			self.make_post_request('tap', {'count':user_data['availableTaps']})
			print(f"Made {user_data['availableTaps']} taps")


	def _farm_coins(self, user_data:dict) -> None:
		""" Start farming and claim """

		if user_data['activeFarmingSeconds'] >= user_data['maxFarmingSecondSec']:
			print('Claiming farm...')
			self.make_post_request('claim')
			self.make_post_request('activate')

		if user_data['activeFarmingSeconds'] == 0:
			print('Staring farming...')
			self.make_post_request('activate')


	def _spin_wheel(self, user_data:dict) -> None:
		""" Wheel spinning """
		if user_data['spinCount'] > 0:
			print('Spinning wheel')
			self.make_post_request('claim-spin', payload={'amount':user_data['spinCount']})
			print(f'Spinned wheel {user_data["spinCount"]}')


	def update_all(self):
		user_data = self.fetch_user_data()

		self._tap_coins(user_data)
		self._farm_coins(user_data)
		self._spin_wheel(user_data)


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
				result = requests.post(url, headers=headers, json=data)
			except:
				time.sleep(1)
				continue

			if result.status_code in {200, 201} and result.json()['result'] == 'OK':
				return result.json()

			time.sleep(1)

		assert result.status_code in {200, 201}, _error_message
		assert result.json()['result'] == 'OK', _error_message
		return result.json()
