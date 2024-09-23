
import os
import json

from telethon import TelegramClient
from telethon.sync import functions
from constants import (
	CONFIG_FNAME,
	TG_SESSIONS_DIR,
	USER_DATA_DIR,
)


def load_config(fname:str = CONFIG_FNAME) -> str:
	""" Load applcation config """

	with open(fname, 'r') as f:
		return json.load(f)


def init_environment() -> None:
	if not os.path.exists(TG_SESSIONS_DIR):
		os.mkdir(TG_SESSIONS_DIR)

	if not os.path.exists(USER_DATA_DIR):
		os.mkdir(USER_DATA_DIR)


def save_users(users:dict) -> None:
	fname = os.path.join(USER_DATA_DIR, 'users.json')

	out = {user_id: user.to_json() for user_id, user in users.items()}

	with open(fname, 'w') as f:
		json.dump(out, f, indent=4)


def load_users(instance) -> dict:
	fname = os.path.join(USER_DATA_DIR, 'users.json')

	if not os.path.exists(fname):
		return {}

	with open(fname, 'r') as f:
		users = json.load(f)

	return {user_id: instance(**data) for user_id, data in users}



async def get_base_app_url(client:TelegramClient, bot_name:str, app_url:str, platform:str = 'ios', start_param:str = '') -> str:
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
