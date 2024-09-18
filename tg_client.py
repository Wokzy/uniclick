
import asyncio

from telethon import TelegramClient
from telethon.sync import functions

import json
import utils

from apps import simpletap

#http://t.me/token1win_bot/start?startapp=refId7463475999


CONFIG = utils.load_config()

simpletap_url = 'https://simpletap.app/#tgWebAppData=query_id%3DAAEBczBSAAAAAAFzMFJTmCOe%26user%3D%257B%2522id%2522%253A1378906881%252C%2522first_name%2522%253A%2522Yegor%2522%252C%2522last_name%2522%253A%2522Yershov%2522%252C%2522username%2522%253A%2522Wokzy1%2522%252C%2522language_code%2522%253A%2522en%2522%252C%2522allows_write_to_pm%2522%253Atrue%257D%26auth_date%3D1726633601%26hash%3De30bf69172b531a1aa2117e39cf26666dcd10315e7a1c7d048d96f5f0cf23fb5&tgWebAppVersion=7.4&tgWebAppPlatform=ios'

def test():

	app = simpletap.SimpleTap(simpletap_url, 1378906881)
	app.update_all()
	print(json.dumps(simpletap.get_essnsial_tasks(app), indent=4))


async def init_client():
	client = TelegramClient('sessions/test', CONFIG['app_id'], CONFIG['app_hash'])
	await client.start()
	user_info = await client.get_me()

	# simpletap_url = await utils.get_base_app_url(client, simpletap.BOT_NAME, simpletap.APP_URL)
	app = simpletap.SimpleTap(simpletap_url, 1378906881)
	# app.update_all()

	await simpletap.complete_essential_tasks(client, app)
	# print(user_info.id)

	await client.disconnect()

if __name__ == "__main__":
	# test()
	asyncio.run(init_client())

