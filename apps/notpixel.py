
import time
import utils
import urllib
import requests
import datetime

from app_logger import AppLogger

API_URL = "https://notpx.app/api/v1/"
HTTP_MAX_RETRY = 5
BASE_URL_UPDATE_TIME = datetime.timedelta(minutes=20)

#/api/v1/mining/boost/check/paintReward

BOOST_UPGRADE_PRICELIST = {
	"paintReward":{
		2:5,
		3:100,
		4:200,
		5:300,
		6:500,
		7:600,
		8:-1,
	},
	"reChargeSpeed":{
		2:5,
		3:100,
		4:200,
		5:300,
		6:400,
		7:500,
		8:600,
		9:700,
		10:800,
		11:900,
		12:-1,
	},
	"energyLimit":{
		2:5,
		3:100,
		4:200,
		5:300,
		6:400,
		7:-1,
	}
}


class NotPixel:
	""" Notpixel Airdrop """
	def __init__(self, base_url:str, user_id:int, config:dict):
		self.name = "NotPixel"
		self.logger = AppLogger(self.name)

		self.base_url = base_url
		self.user_id = user_id
		self.config = config

		self.session = requests.Session()
		self.auth_data = utils.extract_auth_data(self.base_url)
		self.url_update_timer = datetime.datetime.now()


	def update_base_url(self, new_url:str):
		self.base_url = new_url
		self.auth_data = utils.extract_auth_data(self.base_url)

		self.session.close()
		self.session = requests.Session()


	def get_mining_status(self) -> dict:
		return self.make_get_request(method='mining/status')


	def get_user_balance(self) -> float:
		return float(self.get_mining_status()['userBalance'])


	def _purchace_boosts(self) -> None:
		""" Upgrade boosts """

		mining_status = self.get_mining_status()
		boosts = mining_status['boosts']
		balance = mining_status['userBalance']

		for name, level in boosts.items():
			price = BOOST_UPGRADE_PRICELIST[name][level + 1]
			if price == -1 or price > balance:
				continue

			# TEMPORARY DEBUG MEASURE
			if level == 2:
				continue

			result = self.make_get_request(method=f'mining/boost/check/{name}')
			if result[name]:
				self.logger.log_app(self.user_id, f"successfully upgraded {name} to level {level + 1}")
				balance -= price


	def _claim_farm(self) -> None:
		""" Claim farming """

		mining_status = self.get_mining_status()

		if mining_status['fromStart'] > mining_status['maxMiningTime'] // 100:
			result = self.make_get_request(method='mining/claim')
			print(result)


	def update_all(self) -> None:
		""" Do everything to earn notpixel """

		self._purchace_boosts()
		self._claim_farm()


	def __get_headers(self) -> dict:
		return {
			"Host": "notpx.app",
			"Accept": "application/json, text/plain, */*",
			"Accept-Language": "en-US,en;q=0.5",
			"Accept-Encoding": "gzip, deflate, br, zstd",
			"Content-Type": "application/json",
			"Authorization": f"initData {self.auth_data}",
			"Origin": "https://app.notpx.app",
			"Connection": "keep-alive",
			"Referer": "https://app.notpx.app/",
			"Sec-Fetch-Dest": "empty",
			"Sec-Fetch-Mode": "cors",
			"Sec-Fetch-Site": "same-site",
			"Priority": "u=0",
			"TE": "trailers",
		}


	def __check_auth_expiration(self) -> bool:
		return (datetime.datetime.now() - self.url_update_timer) <= BASE_URL_UPDATE_TIME


	def make_get_request(self, method:str, json_trigger:str = "{") -> dict:
		""" Make get request to NotPixel API """

		assert self.__check_auth_expiration(), "Auth token has expired"

		headers = self.__get_headers()

		url = urllib.parse.urljoin(API_URL, method)
		self.logger.log_app(user_id=self.user_id, string=url)

		# url ="https://notpx.app/api/v1/mining/boost/check/energyLimit"

		result = None
		# result = self.session.get(url=url, headers=headers)
		for i in range(HTTP_MAX_RETRY):
			try:
				result = self.session.get(url=url, headers=headers, timeout=5.0)
				break
			except:
				time.sleep(3)

		assert result is not None, "HTTP request failed"
		assert result.status_code in {200, 201, 202, 203, 204}, f"HTTP request returned {result.status_code} status code"

		if json_trigger in result.text:
			return result.json()
		return result.text
