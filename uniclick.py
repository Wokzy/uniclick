"""
Uniclick application
"""

import os
import sys
import copy
import utils
import tg_api
import asyncio
import datetime

from constants import (
	clr,
	BUTTON_NAMINGS,
	MISC_MESSAGES,
	TG_SESSIONS_DIR,
)

from telegram import (
	InlineKeyboardButton,
	InlineKeyboardMarkup,
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
	def __init__(self, user_id:int = 0, chat_id:int = 0, tg_sessions:dict = {}, current_config:dict = {}):
		""" 
		Tg sessions are filenames of current sesisons
		tg_sessions : {session_name:telethon.TelegramCliett}
		"""

		self.user_id = user_id
		self.chat_id = chat_id

		self.current_state = None

		self.tg_sessions = copy.deepcopy(tg_sessions)
		self.current_config = copy.deepcopy(current_config)

		self.sessions_dir = os.path.join(TG_SESSIONS_DIR, str(self.user_id))


	def to_json(self) -> dict:
		sessions = {sname: 
					{'phone':item['phone'],
					'password':item['password'],
					'user_id':item['user_id']}
					for sname, item in self.tg_sessions.items()}

		return {
			"user_id":self.user_id,
			"chat_id":self.chat_id,
			"tg_sessions":sessions,
			"current_config":self.current_config,
		}


class Bot:
	def __init__(self):
		""" self.connected_users = {user_id:}"""

		self.connected_users = utils.load_users(instance=BotUser)

		self._local_state_methods = {'add_account':self.add_account}
		self._external_state_methods = {'auth_session':tg_api.auth_session}


	def save_all_data(self):
		""" Save all bot data """
		print(f'{clr.cyan}Saving....')

		utils.save_users(self.connected_users)

		print(f'Saved{clr.yellow}')


	async def async_save(self, update, context):
		""" Async alias for save_all_data """
		self.save_all_data()


	async def load_tg_sessions(self, update, context) -> dict:
		if context._user_id != CONFIG['admin_userid']:
			return

		print(f'{clr.yellow}Loading sessions....')

		for user in self.connected_users.values():
			if not os.path.exists(user.sessions_dir):
				os.mkdir(user.sessions_dir)

			for session in user.tg_sessions.keys():
				client = await tg_api.init_client(os.path.join(user.sessions_dir, session))

				if await client.is_user_authorized():
					user.tg_sessions[session]['client'] = client

		print(f'{clr.green}Loaded!{clr.yellow}')

		await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['load_tg_sessions'])


	async def graceful_stop(self, update, context):
		if context._user_id != CONFIG['admin_userid']:
			return

		self.save_all_data()

		for user in self.connected_users.values():
			for session in user.tg_sessions.keys():
				client = user.tg_sessions[session]['client']
				if client.is_connected():
					client.disconnect()

		await context.bot.send_message(context._chat_id, text=MISC_MESSAGES['graceful_stop'])


	async def handle_message(self, update, context) -> None:
		if context._user_id not in self.connected_users.keys():
			return

		user = self.connected_users[context._user_id]

		if user.current_state is not None:
			for prefix in self._external_state_methods.keys():
				if user.current_state.startswith(prefix):
					await self._external_state_methods[prefix](update, context, user)
					return

			for prefix in self._local_state_methods.keys():
				if user.current_state.startswith(prefix):
					await self._local_state_methods[prefix](update, context)
					return


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

		user = self.connected_users[context._user_id]
		user.current_state = None

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
			await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['main_menu'],
										   reply_markup=keyboard)


	async def add_account(self, update, context) -> None:
		user = self.connected_users[context._user_id]

		if user.current_state is None:
			await context.bot.answer_callback_query(update.callback_query.id)
			await update.callback_query.edit_message_text(text=MISC_MESSAGES['session_name'])

			user.current_state = 'add_account'
			return

		user.current_state = None
		session_name = update.message.text[:12]


		if ' ' in session_name or session_name in user.tg_sessions.keys():
			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu'),
						 InlineKeyboardButton(BUTTON_NAMINGS.try_again, callback_data='add_account')]]
			keyboard = InlineKeyboardMarkup(keyboard)

			await context.bot.send_message(user.chat_id, text=MISC_MESSAGES['wrong_session_name'], reply_markup=keyboard)
			return

		client = await tg_api.init_client(os.path.join(user.sessions_dir, session_name))
		user.tg_sessions[session_name] = {'client':client}
		await tg_api.auth_session(update, context, user, session_name=session_name)


	async def my_accounts(self, update, context) -> None:
		user = self.connected_users[context._user_id]

		await context.bot.answer_callback_query(update.callback_query.id)

		text = 'Choose an account from list:'
		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]]

		for name in user.tg_sessions.keys():
			keyboard.append([InlineKeyboardButton(name, callback_data=f'get_user_session {name}')])

		keyboard = InlineKeyboardMarkup(keyboard)

		await update.callback_query.edit_message_text(text=text,
													  reply_markup=keyboard)


	async def get_user_session(self, update, context):
		await context.bot.answer_callback_query(update.callback_query.id)
		user = self.connected_users[context._user_id]

		name = update.callback_query.data.split(' ')[1]
		_user_data = await user.tg_sessions[name]['client'].get_me()
		await update.callback_query.edit_message_text(text=_user_data.stringify(),
													  reply_markup=utils.main_menu_keyboard())


	async def admin_panel(self, update, context) -> None:
		await context.bot.answer_callback_query(update.callback_query.id)


	async def faq(self, update, context) -> None:
		await context.bot.answer_callback_query(update.callback_query.id)




def main():
	print(f'{clr.green}Starting bot...')
	bot = Bot()

	application = Application.builder().token(CONFIG['bot_token']).read_timeout(7).get_updates_read_timeout(42).build()

	application.add_handler(CommandHandler("start", bot.user_start))
	application.add_handler(CommandHandler("main_menu", bot.main_menu))
	application.add_handler(CommandHandler("save_all", bot.async_save))
	application.add_handler(CommandHandler("load_data", bot.load_tg_sessions))
	application.add_handler(CommandHandler("graceful_stop", bot.graceful_stop))
	application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

	callback_handlers = {
			bot.main_menu        : "main_menu",
			bot.add_account      : "add_account",
			bot.my_accounts      : "my_accounts",
			bot.admin_panel      : "admin_panel",
			bot.faq              : "faq",
			bot.get_user_session : "get_user_session",
	}

	for function, pattern in callback_handlers.items():
		application.add_handler(CallbackQueryHandler(function, pattern=pattern))

	print(f'{clr.cyan}Bot is online{clr.yellow}')

	application.run_polling()
	bot.save_all_data()


if __name__ == '__main__':
	utils.init_environment()
	main()
