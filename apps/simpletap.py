
import time
import copy
import urllib
import requests


HTTP_MAX_RETRY = 2 # amount of http request retries
BOT_NAME = 'Simple_Tap_Bot'
APP_URL = 'https://simpletap.app/'
API_URL = 'https://api.thesimpletap.app/api/v1/public/telegram/'


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
		print(self.base_url)
		return urllib.parse.unquote(self.base_url).split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]


	def update_base_url(self, new_url:str):
		self.base_url = base_url
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
			self.make_post_request('claim')
			self.make_post_request('activate')

		if user_data['activeFarmingSeconds'] == 0:
			self.make_post_request('activate')


	def update_all(self):
		user_data = self.fetch_user_data()

		self._tap_coins(user_data)
		self._farm_coins(user_data)


	def make_post_request(self, method:str, payload:dict = {}) -> dict:
		"""  """

		data = copy.deepcopy(payload)
		data['authData'] = self.auth_data
		data['userId'] = self.user_id

		headers = self.get_post_headers()
		url = urllib.parse.urljoin(API_URL, method)

		result = requests.post(url, headers=headers, json=data)
		_error_message = f"Error encountered in: {url}"

		# print(url)

		for i in range(HTTP_MAX_RETRY):
			if result.status_code in {200, 201} and result.json()['result'] == 'OK':
				return result.json()

			time.sleep(1)
			result = requests.post(url, headers=headers, json=data)

		assert result.status_code in {200, 201}, _error_message
		assert result.json()['result'] == 'OK', _error_message
		return result.json()
