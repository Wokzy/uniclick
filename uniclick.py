"""
Uniclick application
"""

import os
import sys
import copy
import utils
import datetime

from constants import (
	clr,
	BUTTON_NAMINGS,
	MISC_MESSAGES,
)

from telegram import (
	InlineKeyboardButton,
	InlineKeyboardMarkup,
	Update,
)

from telegram.ext import (
	Application,
	CommandHandler,
	ContextTypes,
	MessageHandler,
	CallbackQueryHandler,
	JobQueue,
	filters,
)


CONFIG = utils.load_config()


class BotUser:
	def __init__(self, user_id:int = 0, chat_id:int = 0, tg_sessions:list[str] = [], current_config:dict = {}):
		""" 
		Tg sessions are filenames of current sesisons
		tg_clients : {session_name:telethon.TelegramCliett}
		"""

		self.user_id = user_id
		self.chat_id = chat_id

		self.current_state = None

		self.tg_sessions = copy.deepcopy(tg_sessions)
		self.current_config = copy.deepcopy(current_config)

		self.tg_clients = {}


	def to_json(self) -> dict:
		return {
			"user_id":self.user_id,
			"chat_id":self.chat_id,
			"tg_sessions":self.tg_sessions,
			"current_config":self.current_config,
		}


	def _load_sessions(self) -> dict:

		_rm_list = []
		for session in tg_sessions:
			client = tg_api.init_client(session)

			if not client.is_user_authorized:
				_rm_list.append(session)
			else:
				self.tg_clients[session] = client

		for session in _rm_list:
			self.tg_sessions.remove(session)


class Bot:
	def __init__(self):
		""" self.connected_users = {user_id:}"""

		self.connected_users = utils.load_users(instance=BotUser)


	def save_all_data(self):
		""" Save all bot data """
		utils.save_users(self.connected_users)


	async def handle_message(self, update, context) -> None:
		await context.bot.send_message(context._chat_id,
									   text=update.message.text)


	async def user_start(self, update, context) -> None:
		if context._user_id in self.connected_users:
			return

		self.connected_users[context._user_id] = BotUser(user_id=context._user_id,
														 chat_id=context._chat_id,
														 current_config=CONFIG['default_user_config'])

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
		keyboard = InlineKeyboardMarkup(keyboard)

		await context.bot.send_message(context._chat_id,
									   text=MISC_MESSAGES['init_message'],
									   reply_markup=keyboard)


	async def main_menu(self, update, context) -> None:
		if context._user_id not in self.connected_users.keys():
			return

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.my_accounts, callback_data='my_accounts'),
					 InlineKeyboardButton(BUTTON_NAMINGS.add_account, callback_data='add_account')],
					[InlineKeyboardButton(BUTTON_NAMINGS.faq, callback_data='faq')]]

		if context._user_id == CONFIG['admin_userid']:
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.admin_panel, callback_data='admin_panel')])

		keyboard = InlineKeyboardMarkup(keyboard)

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)

			if update.callback_query.message.text is not None:
				await update.callback_query.edit_message_text(text=MISC_MESSAGES['main_menu'],
															  reply_markup=keyboard)
		else:
			await context.bot.send_message(text=MISC_MESSAGES['main_menu'],
										   reply_markup=keyboard)


	async def add_account(self, update, context) -> None:
		return


	async def my_accounts(self, update, context) -> None:
		return


	async def admin_panel(self, update, context) -> None:
		return


	async def faq(self, update, context) -> None:
		return




def main():
	print(f'{clr.green}Starting bot...')
	bot = Bot()

	application = Application.builder().token(CONFIG['bot_token']).read_timeout(7).get_updates_read_timeout(42).build()

	application.add_handler(CommandHandler("start", bot.user_start))
	application.add_handler(CommandHandler("main_menu", bot.main_menu))
	application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

	callback_handlers = {
			bot.main_menu : "main_menu",
			bot.add_account : "add_account",
			bot.my_accounts : "my_accounts",
			bot.admin_panel : "admin_panel",
			bot.faq : "faq",
	}

	for function, pattern in callback_handlers.items():
		application.add_handler(CallbackQueryHandler(function, pattern=pattern))

	print(f'{clr.cyan}Bot is online')

	application.run_polling()
	bot.save_all_data()


if __name__ == '__main__':
	utils.init_environment()
	main()
