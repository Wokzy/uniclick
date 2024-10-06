
import os
import json

from telegram import (
	InlineKeyboardButton,
	InlineKeyboardMarkup,
)

from telethon import TelegramClient
from telethon.sync import functions

from constants import (
	CONFIG_FNAME,
	CACHE_DIR,
	TG_SESSIONS_DIR,
	USER_DATA_DIR,
	BUTTON_NAMINGS,
	MISC_MESSAGES,
)


def load_config(fname:str = CONFIG_FNAME) -> str:
	""" Load applcation config """

	with open(fname, 'r', encoding='utf-8') as f:
		return json.load(f)


def init_environment() -> None:
	if not os.path.exists(TG_SESSIONS_DIR):
		os.mkdir(TG_SESSIONS_DIR)

	if not os.path.exists(USER_DATA_DIR):
		os.mkdir(USER_DATA_DIR)

	if not os.path.exists(CACHE_DIR):
		os.mkdir(CACHE_DIR)


def save_users(users:dict) -> None:
	fname = os.path.join(USER_DATA_DIR, 'users.json')

	out = {user_id: user.to_json() for user_id, user in users.items()}

	with open(fname, 'w', encoding='utf-8') as f:
		json.dump(out, f, indent=4)


def load_users(instance) -> dict:
	fname = os.path.join(USER_DATA_DIR, 'users.json')

	if not os.path.exists(fname):
		return {}

	with open(fname, 'r', encoding='utf-8') as f:
		users = json.load(f)

	return {int(user_id): instance(**data) for user_id, data in users.items()}



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


async def channel_participaiton_check(update, context, channels: list[str], user_id: int = 0) -> bool:
	if not user_id:
		user_id = context._user_id

	for channel in channels:
		# print(channel)
		res = await context.bot.get_chat_member(f"@{channel}", user_id)
		if res.status != 'member':
			return False

	return True


def main_menu_keyboard():
	""" Main menu keyboard alias """
	return InlineKeyboardMarkup([[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]])
