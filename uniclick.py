"""
Uniclick application
"""

import os
import sys
import copy
import asyncio
import datetime

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

import utils
import tg_api

from apps.apps_init import AppsService
from constants import (
	clr,
	BUTTON_NAMINGS,
	MISC_MESSAGES,
	TG_SESSIONS_DIR,
)


# TODO: init clients in dedicated thread
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

		self.app_service = AppsService(self.current_config)

		self.sessions_dir = os.path.join(TG_SESSIONS_DIR, str(self.user_id))


	def to_json(self) -> dict:
		sessions = {sname: 
					{'user_id':item['user_id']}
					for sname, item in self.tg_sessions.items()}

		return {
			"user_id":self.user_id,
			"chat_id":self.chat_id,
			"tg_sessions":sessions,
			"current_config":self.current_config,
		}


class Bot:
	def __init__(self):
		"""
			self.connected_users = {user_id:} 
			*_state_methods are used do redirect messages into dedicated methods
		"""

		self.connected_users = utils.load_users(instance=BotUser)

		self._local_state_methods = {'add_account':self.add_account,
									 'edit_config':self.edit_config
									 }
		self._external_state_methods = {'auth_session':tg_api.auth_session,
										'auth_with_qrcode':tg_api.auth_with_qrcode
										}


	def save_all_data(self) -> None:
		""" Save all bot data """
		# print(f'{clr.cyan}Saving....')

		utils.save_users(self.connected_users)

		# print(f'Saved{clr.yellow}')


	async def async_save(self, update, context) -> None:
		""" Async alias for save_all_data """
		self.save_all_data()


	def load_tg_sessions(self) -> None:

		print(f'{clr.yellow}Loading sessions....')
		for user in self.connected_users.values():

			if not os.path.exists(user.sessions_dir):
				os.mkdir(user.sessions_dir)

			for session in user.tg_sessions.keys():
				user.app_service.update_queue.put({'type':'add_client', 'data':{'path':os.path.join(user.sessions_dir, session), 'name':session}})

			user.app_service.start()

		print(f'{clr.green}Loaded!{clr.yellow}')


	async def graceful_stop(self, update, context) -> None:
		if context._user_id != CONFIG['admin_userid']:
			return

		self.save_all_data()

		for user in self.connected_users.values():
			user.app_service.stop()

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
					 [InlineKeyboardButton(BUTTON_NAMINGS.change_config, callback_data='view_config')],
					[InlineKeyboardButton(BUTTON_NAMINGS.faq, callback_data='faq')]]

		if context._user_id == CONFIG['admin_userid']:
			keyboard.append([InlineKeyboardButton(BUTTON_NAMINGS.admin_panel, callback_data='admin_panel')])

		keyboard = InlineKeyboardMarkup(keyboard)

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)

			if update.callback_query.message.text is not None:
				await update.callback_query.edit_message_text(text=MISC_MESSAGES['main_menu'],
															  reply_markup=keyboard)
				return

		await context.bot.send_message(user.chat_id,
									   text=MISC_MESSAGES['main_menu'],
									   reply_markup=keyboard)


	async def add_account(self, update, context) -> None:
		user = self.connected_users[context._user_id]

		if user.current_state is None and update.callback_query is not None:
			callback_data = update.callback_query.data.split(' ')[1::]

			await context.bot.answer_callback_query(update.callback_query.id)
			if len(callback_data) == 0:
				await update.callback_query.edit_message_text(text=MISC_MESSAGES['session_name'])

				user.current_state = 'add_account session_name'
			else:
				session_name = callback_data[1]
				client = await tg_api.init_client(os.path.join(user.sessions_dir, session_name))
				user.tg_sessions[session_name] = {'client':client}

				if callback_data[0] == 'default_login':
					await tg_api.auth_session(update, context, user, session_name=session_name)
				elif callback_data[0] == 'qr_login':
					await tg_api.auth_with_qrcode(update, context, user, session_name=session_name)

			self.save_all_data()
			return

		data = user.current_state.split(' ')[1::]
		user.current_state = None

		if data[0] == 'session_name':
			session_name = update.message.text[:12]

			if ' ' in session_name or session_name in user.tg_sessions.keys():
				keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu'),
							 InlineKeyboardButton(BUTTON_NAMINGS.try_again, callback_data='add_account')]]
				keyboard = InlineKeyboardMarkup(keyboard)

				await context.bot.send_message(user.chat_id, text=MISC_MESSAGES['wrong_session_name'], reply_markup=keyboard)
				return

			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')],
						[InlineKeyboardButton(BUTTON_NAMINGS.default_login, callback_data=f'add_account default_login {session_name}'),
						 InlineKeyboardButton(BUTTON_NAMINGS.qr_login, callback_data=f'add_account qr_login {session_name}')]]
			keyboard = InlineKeyboardMarkup(keyboard)

			await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['choose_login_option'],
										   reply_markup=keyboard)


	async def my_accounts(self, update, context) -> None:
		user = self.connected_users[context._user_id]

		await context.bot.answer_callback_query(update.callback_query.id)

		text = 'Choose an account from list:'
		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]]

		_rm_list = []
		for name in user.tg_sessions.keys():
			if name not in user.app_service.clients.keys():
				_rm_list.append(name)
				text += f'\n<b>Account {name} was removed due to telegram session error (try to recreate)</b>'

		for name in _rm_list:
			del user.tg_sessions[name]

		for name in user.tg_sessions.keys():
			keyboard.append([InlineKeyboardButton(name, callback_data=f'get_user_session {name}')])

		keyboard = InlineKeyboardMarkup(keyboard)

		await update.callback_query.edit_message_text(text=text,
													  parse_mode='HTML',
													  reply_markup=keyboard)


	async def get_user_session(self, update, context) -> None:
		await context.bot.answer_callback_query(update.callback_query.id)
		user = self.connected_users[context._user_id]

		session_name = update.callback_query.data.split(' ')[1]

		statuses = user.app_service.fetch_status()[session_name]
		text = ''

		for name, status in statuses.items():
			app_text = '{}\n\tStatus: {}\n\tWarnings:{}'

			if status['status'] is None:
				_status_text = 'active 🟢'
			elif status['status'] == 'error':
				_status_text = 'inactive due to error 🔺'
			else:
				_status_text = f'{status["status"]} 🟡'

			if status['warning'] is None:
				_warning_text = 'no warnings 🟢'
			else:
				_warning_text = f'{status["warning"]} 🟡'

			text += app_text.format(name, _status_text, _warning_text)

		keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.go_back, callback_data='my_accounts')],
					[InlineKeyboardButton(BUTTON_NAMINGS.delete_account, callback_data=f'delete_account default {session_name}')]]
		keyboard = InlineKeyboardMarkup(keyboard)

		if not text:
			text = 'No applications running'

		await update.callback_query.edit_message_text(text=text,
													  reply_markup=keyboard)


	async def delete_account(self, update, context) -> None:
		user = self.connected_users[context._user_id]

		state, name = update.callback_query.data.split(' ')[1::]

		if state == 'default':
			await context.bot.answer_callback_query(update.callback_query.id)

			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.go_back, callback_data='my_accounts'),
						 InlineKeyboardButton(BUTTON_NAMINGS.confirm_account_deletion, callback_data=f'delete_account confirm {name}')]]
			keyboard = InlineKeyboardMarkup(keyboard)

			await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['confirm_account_deletion'].format(name),
										   reply_markup=keyboard)
			return

		if state == 'confirm':
			user.app_service.update_queue.put({'type':'remove_client', 'data':name})
			del user.tg_sessions[name]

			await context.bot.answer_callback_query(update.callback_query.id, text='Account was deleted')
			await self.main_menu(update, context)


	async def admin_panel(self, update, context) -> None:
		await context.bot.answer_callback_query(update.callback_query.id)


	async def view_config(self, update, context) -> None:
		await context.bot.answer_callback_query(update.callback_query.id)
		user = self.connected_users[context._user_id]

		data = update.callback_query.data.split(' ')

		if len(data) == 1:

			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]]
			for app_name in user.current_config.keys():
				keyboard.append([InlineKeyboardButton(app_name, callback_data=f'view_config {app_name}')])

			keyboard = InlineKeyboardMarkup(keyboard)

			await update.callback_query.edit_message_text(text="Select an application:", reply_markup=keyboard)
		else:
			app_name = data[1]

			text = f'<b>Enabled</b>: {["No🔺", "Yes🟢"][user.current_config[app_name]["enabled"]]}'
			for param, value in user.current_config[app_name].items():
				if param != '__field_types':
					text += f'\n{param}: {value}'

			keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')],
						[InlineKeyboardButton(BUTTON_NAMINGS.change_config, callback_data=f'edit_config default {app_name}')]]

			if user.current_config[app_name]["enabled"]:
				_button_name = BUTTON_NAMINGS.disable_app
			else:
				_button_name = BUTTON_NAMINGS.enable_app

			keyboard.append([InlineKeyboardButton(_button_name, callback_data=f'edit_config toggle {app_name}')])
			keyboard = InlineKeyboardMarkup(keyboard)

			await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='HTML')


	async def edit_config(self, update, context) -> None:
		user = self.connected_users[context._user_id]

		def _apply_config():
			user.app_service.update_queue.put({'type':'update_config', 'data':user.current_config})
			self.save_all_data()

		if update.callback_query is not None:
			data = update.callback_query.data.split(' ')[1::]
			await context.bot.answer_callback_query(update.callback_query.id)

			if data[0] == 'toggle':
				user.current_config[data[1]]['enabled'] = not user.current_config[data[1]]['enabled']
				_apply_config()
				await update.callback_query.edit_message_text(text='Success!', reply_markup=utils.main_menu_keyboard())
			elif data[0] == 'default':
				keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]]
				for param, value in user.current_config[data[1]].items():
					if param not in {'enabled', '__field_types'}:
						keyboard.append([InlineKeyboardButton(param, callback_data=f'edit_config change_param {data[1]} {param}')])

				keyboard = InlineKeyboardMarkup(keyboard)
				await update.callback_query.edit_message_text(text=update.callback_query.message.text, reply_markup=keyboard)
			elif data[0] == 'change_param':
				await context.bot.send_message(user.chat_id, text=MISC_MESSAGES['change_param'])
				user.current_state = f'edit_config {data[1]} {data[2]}'

			return

		app_name, param = user.current_state.split(' ')[1::]
		new_value = update.message.text
		user.current_state = None

		validate = False
		if user.current_config[app_name]['__field_types'][param] == 'int':
			if new_value.isnumeric():
				new_value = int(new_value)
				validate = True

		if not validate:
			await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['invalid_value'],
										   reply_markup=utils.main_menu_keyboard())
			return

		user.current_config[app_name][param] = new_value
		_apply_config()

		await context.bot.send_message(user.chat_id,
									   text=MISC_MESSAGES['change_param_succeeded'],
									   reply_markup=utils.main_menu_keyboard())


	async def faq(self, update, context) -> None:
		await context.bot.answer_callback_query(update.callback_query.id)


# 🟢🟡🔺

def main():
	print(f'{clr.green}Starting bot...')
	bot = Bot()

	bot.load_tg_sessions()

	application = Application.builder().token(CONFIG['bot_token']).read_timeout(7).get_updates_read_timeout(42).build()

	application.add_handler(CommandHandler("start", bot.user_start))
	application.add_handler(CommandHandler("main_menu", bot.main_menu))
	application.add_handler(CommandHandler("save_all", bot.async_save))
	application.add_handler(CommandHandler("graceful_stop", bot.graceful_stop))
	application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

	callback_handlers = {
			bot.main_menu        : "main_menu",
			bot.add_account      : "add_account",
			bot.my_accounts      : "my_accounts",
			bot.admin_panel      : "admin_panel",
			bot.faq              : "faq",
			bot.get_user_session : "get_user_session",
			bot.delete_account   : "delete_account",
			bot.view_config      : "view_config",
			bot.edit_config      : "edit_config",
	}

	for function, pattern in callback_handlers.items():
		application.add_handler(CallbackQueryHandler(function, pattern=pattern))

	print(f'{clr.cyan}Bot is online{clr.yellow}')

	application.run_polling()
	bot.save_all_data()


if __name__ == '__main__':
	utils.init_environment()
	main()
