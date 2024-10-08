
import os
import json
import copy

from telegram import (
	InlineKeyboardButton,
	InlineKeyboardMarkup,
)

from telethon import TelegramClient
from telethon.sync import functions

from constants import (
	CACHE_DIR,
	CONFIG_FNAME,
	USER_DATA_DIR,
	DEFAULT_LOCALE,
	TG_SESSIONS_DIR,
	SUPPORTED_APPLICATIONS,
)


global cached_utils_info
cached_utils_info = {'app_photos':{}}


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


def save_app_photos(photos: dict[str, str], path: str) -> None:
	with open(path, 'w') as f:
		json.dump(photos, f, indent=4)


async def load_app_photos(bot, chat_id) -> None:
	global cached_utils_info
	_fname = os.path.join(CACHE_DIR, 'app_photos.json')

	if not os.path.exists(_fname):
		save_app_photos({}, _fname)

	with open(_fname, 'r') as f:
		data = json.load(f)

	if list(data.keys()) != list(SUPPORTED_APPLICATIONS.keys()):
		print('prepairing app photos')
		for name, chat_name in SUPPORTED_APPLICATIONS.items():
			chat = await bot.get_chat(chat_name)
			photo_file = await chat.photo.get_big_file()
			file_path = os.path.join(CACHE_DIR, f'{name}.png')

			await photo_file.download_to_drive(file_path)
			with open(file_path, 'rb') as f:
				msg = await bot.send_photo(chat_id, photo=f)

			data[name] = msg.photo[-1].file_id

	cached_utils_info['app_photos'] = copy.deepcopy(data)
	save_app_photos(data, _fname)


async def get_app_photo(bot, chat_id, app_name: str) -> str:
	global cached_utils_info

	if app_name not in cached_utils_info['app_photos']:
		await load_app_photos(bot, chat_id)

	return cached_utils_info['app_photos'][app_name]



async def channel_participaiton_check(update, context, channels: list[str], user_id: int = 0) -> bool:
	if not user_id:
		user_id = context._user_id

	for channel in channels:
		# print(channel)
		res = await context.bot.get_chat_member(f"@{channel}", user_id)
		if res.status not in {'owner', 'member', 'creator', 'admin'}:
			return False

	return True


def main_menu_keyboard():
	""" Main menu keyboard alias """
	return InlineKeyboardMarkup([[InlineKeyboardButton(DEFAULT_LOCALE.BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]])
