
import sys
import time
import json
import utils
import asyncio
import datetime

from apps import simpletap
from telethon import TelegramClient
from telethon.sync import functions

#http://t.me/token1win_bot/start?startapp=refId7463475999


CONFIG = utils.load_config()
CHANGE_URL_TIMEOUT = datetime.timedelta(days=1)


async def get_simpletap_url(client):
	return await utils.get_base_app_url(client, simpletap.BOT_NAME, simpletap.APP_URL)


async def init_client():
	_start_time = datetime.datetime.now()

	client = TelegramClient('sessions/test', CONFIG['app_id'], CONFIG['app_hash'])
	await client.start()
	user_info = await client.get_me()

	simpletap_url = await get_simpletap_url(client)
	if '--debug' in sys.argv:
		print(simpletap_url)

	if '--exit' in sys.argv:
		await client.disconnect()
		return

	app = simpletap.SimpleTap(simpletap_url, user_info.id)


	while len(simpletap.get_essnsial_tasks(app)) > 0:
		print('Completing essential tasks')
		await simpletap.complete_essential_tasks(client, app)

	print("Entering main loop...")
	try:
		while True:
			app.update_all()

			time.sleep(3)
			if (datetime.datetime.now() - _start_time) > CHANGE_URL_TIMEOUT:
				simpletap_url = await get_simpletap_url(client)
				app.update_base_url(new_url=simpletap_url)
				_start_time = datetime.datetime.now()
	except Exception:
		pass

	# print(user_info.id)

	print('Exiting...')
	await client.disconnect()

