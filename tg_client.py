
import asyncio

from telethon import TelegramClient
from telethon.sync import functions

import utils

from apps import simpletap



CONFIG = utils.load_config()


async def init_client():
	client = TelegramClient('sessions/test', CONFIG['app_id'], CONFIG['app_hash'])
	await client.start()
	user_info = await client.get_me()

	simpletap_url = await utils.get_base_app_url(client, simpletap.BOT_NAME, simpletap.APP_URL)
	# print(simpletap_url)
	app = simpletap.SimpleTap(simpletap_url, user_info.id)
	app.update_all()
	print(app.fetch_user_data())

	await client.disconnect()

if __name__ == "__main__":
	asyncio.run(init_client())

