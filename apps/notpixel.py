
import time
import utils
import urllib
import random
import requests
import datetime

from app_logger import AppLogger

API_URL = "https://notpx.app/api/v1/"
BOT_NAME = "notpixel"
APP_URL = "https://app.notpx.app/"

HTTP_MAX_RETRY = 5
BASE_URL_UPDATE_TIME = datetime.timedelta(minutes=20)
ANTIDETECT_SLEEP_TIME_RANGE = (700, 1400)

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
		self.antidetect_sleep_timer = [datetime.datetime.now(),
									   datetime.timedelta(seconds=ANTIDETECT_SLEEP_TIME_RANGE[0]),
									   ]

		self.made_entire_loop = False

		self.status = 'starting'
		self.warning = None


	def update_base_url(self, new_url:str):
		self.base_url = new_url
		self.auth_data = utils.extract_auth_data(self.base_url)

		self.session.close()
		self.session = requests.Session()


	def get_mining_status(self) -> dict:
		return self.make_request(path='mining/status')


	def get_user_balance(self) -> float:
		return float(self.get_mining_status()['userBalance'])


	def _check_antidetect(self) -> bool:

		if not self.made_entire_loop:
			return True

		if (datetime.datetime.now() - self.antidetect_sleep_timer[0]) > self.antidetect_sleep_timer[1]:
			self.antidetect_sleep_timer[0] = datetime.datetime.now()
			self.antidetect_sleep_timer[1] = datetime.timedelta(seconds=random.randint(*ANTIDETECT_SLEEP_TIME_RANGE))
			return True

		return False


	def _complete_tasks(self) -> None:
		""" youtube.com and x.com task completion """

		tasks = ("x?name=notcoin", "x?name=notpixel")

		# https://notpx.app/api/v1/mining/task/check/x?name=notpixel

		for task in tasks:
			self.make_request(path=f'mining/task/check/{task}')


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

			result = self.make_request(path=f'mining/boost/check/{name}')
			if result[name]:
				self.logger.log_app(self.user_id, f"successfully upgraded {name} to level {level + 1}")
				balance -= price


	def _claim_farm(self) -> None:
		""" Claim farming """

		mining_status = self.get_mining_status()

		if mining_status['fromStart'] > mining_status['maxMiningTime'] // 100:
			result = self.make_request(path='mining/claim')
			self.logger.log_app(self.user_id, f"calimed farm")


	def _get_pixel_info(self, pixel_id:int) -> dict:
		""" Gets pixel info returned by API """

		return self.make_request(path=f'image/get/{pixel_id}')['pixel']


	def _paint_pattern_pixels(self) -> None:
		""" Attempts to paint random pixel """

		_pattern_coord_range = {'x':(340, 740), 'y':(340, 740)}
		mining_status = self.get_mining_status()

		for i in range(mining_status['charges']):
			pixel = (random.randint(*_pattern_coord_range['x']), random.randint(*_pattern_coord_range['y']))
			colors = [self._get_pixel_info(y*1000 + x)['color'] for x, y in ((pixel[0] - 1, pixel[1] - 1),
																		(pixel[0]    , pixel[1] - 1),
																		(pixel[0] + 1, pixel[1] - 1),
																		(pixel[0] + 1, pixel[1]    ),
																		(pixel[0] + 1, pixel[1] + 1),
																		(pixel[0]    , pixel[1] + 1),
																		(pixel[0] - 1, pixel[1] + 1),
																		(pixel[0] - 1, pixel[1]   ))]

			paint_color = [0, ""]
			for c in set(colors):
				r = colors.count(c)
				if r > paint_color[0]:
					paint_color[0] = r
					paint_color[1] = c

			paint_color = paint_color[1]

			request_payload = {
				"pixelId":(pixel[1]*1000 + pixel[0]),
				"newColor":paint_color,
			}

			result = self.make_request(path='repaint/start', method='post', payload=request_payload)
			# print(result, colors)

		if mining_status['charges'] > 0:
			self.logger.log_app(self.user_id, f"painted {mining_status['charges']} pixels")


	def update_all(self) -> None:
		""" Do everything to earn notpixel """

		if not self._check_antidetect() and self.status != 'starting':
			return

		self.made_entire_loop = False

		self._purchace_boosts()
		self._claim_farm()
		self._paint_pattern_pixels()
		try:
			self._complete_tasks()
		except:
			self.logger.log_app(user.user_id, f'Failed to _complete_tasks')

		self.made_entire_loop = True


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


	def make_request(self, path:str, method:str = 'get', json_trigger:str = "{", payload=None) -> dict:
		""" Make get request to NotPixel API """

		assert self.__check_auth_expiration(), "Auth token has expired"

		if payload == None:
			payload = {}
		headers = self.__get_headers()

		url = urllib.parse.urljoin(API_URL, path)
		# self.logger.log_app(user_id=self.user_id, string=url)

		# url ="https://notpx.app/api/v1/mining/boost/check/energyLimit"

		result = None
		# result = self.session.get(url=url, headers=headers)
		for i in range(HTTP_MAX_RETRY):
			try:
				if method == 'get':
					result = self.session.get(url=url, headers=headers, timeout=5.0)
				else:
					result = self.session.post(url=url, headers=headers, json=payload, timeout=5.0)
				break
			except:
				time.sleep(3)

		assert result is not None, "HTTP request failed"
		assert result.status_code in {200, 201, 202, 203, 204}, f"HTTP request returned {result.status_code} status code on {url}"

		if json_trigger in result.text:
			return result.json()
		return result.text


async def get_notpixel_url(client):
	return await utils.get_base_app_url(client, BOT_NAME, APP_URL)


async def notpixel_init(client, config) -> NotPixel:

	# await client.send_message('notpx_bot', f'/start')

	url = await get_notpixel_url(client)
	user = await client.get_me()

	app = NotPixel(url, user.id, config=config)

	try:
		app.make_request(path=url)
	except:
		pass

	return app


async def notpixel_update(app:NotPixel, client) -> None:

	try:
		if (datetime.datetime.now() - app.url_update_timer) > BASE_URL_UPDATE_TIME:
			app.logger.log_app(app.user_id, f"updating url")
			app.url_update_timer = datetime.datetime.now()
			app.update_base_url(new_url = await get_notpixel_url(client))

		app.update_all()
		app.status = None
		app.warning = None
	except Exception as e:
		app.logger.log_app(app.user_id, str(e))
		app.status = 'warning'
		app.warning = e

