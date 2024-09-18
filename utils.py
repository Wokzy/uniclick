
import json

from telethon import TelegramClient
from telethon.sync import functions


def load_config(fname:str = 'config.json'):
	""" Load applcation config """

	with open(fname, 'r') as f:
		return json.load(f)


async def get_base_app_url(client:TelegramClient, bot_name:str, app_url:str, platform:str = 'ios', start_param:str = ''):
	""" Get application url with auth data """

	return (await client(
		functions.messages.RequestWebViewRequest(
			peer=bot_name,
			bot=bot_name,
			platform=platform,
			url=app_url,
			from_bot_menu=False,
			start_param=start_param
		)
	)).url
