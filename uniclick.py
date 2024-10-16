"""
Uniclick application
"""

import os
import sys
import copy
import uuid
import asyncio
import datetime

from telegram import (
	helpers,
	Update,
	InlineKeyboardButton,
	InlineKeyboardMarkup,
	InputTextMessageContent,
	InlineQueryResultArticle,
	InlineQueryResultCachedPhoto,
)

from telegram.ext import (
	filters,
	JobQueue,
	Application,
	ContextTypes,
	CommandHandler,
	MessageHandler,
	InlineQueryHandler,
	CallbackQueryHandler,
)

import utils
import tg_api

from apps.apps_init import AppsService
from constants import (
	clr,
	LOCALES,
	ONLY_BOT,
	DEFAULT_LOCALE,
	TG_SESSIONS_DIR,
	DEFAULT_CUSTOMER_DATA,
	SUPPORTED_APPLICATIONS,
)


CONFIG = utils.load_config()


class BotUser:
	def __init__(self, user_id:int = 0, chat_id:int = 0, tg_sessions:dict = {},
				 current_config:dict = {}, customer_data:dict = DEFAULT_CUSTOMER_DATA,
				 locale:str = "eng"):
		""" 
		Tg sessions are filenames of current sesisons
		tg_sessions : {session_name:telethon.TelegramCliett}
		Customer data is additional cosmetical data
		"""

		self.user_id = user_id
		self.chat_id = chat_id

		self.locale = locale
		self.locale_module = LOCALES[locale]['module']

		if not customer_data:
			customer_data = DEFAULT_CUSTOMER_DATA

		self.customer_data = copy.deepcopy(customer_data)

		self.current_state = None

		self.tg_sessions = copy.deepcopy(tg_sessions)
		self.current_config = copy.deepcopy(current_config)

		self.app_service = AppsService(self.current_config)

		self.sessions_dir = os.path.join(TG_SESSIONS_DIR, str(self.user_id))
		if not os.path.exists(self.sessions_dir):
			os.mkdir(self.sessions_dir)


	def to_json(self) -> dict:
		sessions = {}

		for sname, item in self.tg_sessions.items():
			if item.get('finished', False):
				sessions[sname] = item

		return {
			"user_id":self.user_id,
			"chat_id":self.chat_id,
			"tg_sessions":sessions,
			"current_config":self.current_config,
			"customer_data":self.customer_data,
			"locale":self.locale
		}


class Bot:
	def __init__(self):
		"""
			self.connected_users = {user_id:} 
			*_state_methods are used do redirect messages into dedicated methods
		"""

		self.connected_users = utils.load_users(instance=BotUser)

		self._local_state_methods = {'add_account':self.add_account,
									 'view_config':self.view_config,
									 'edit_config':self.edit_config,
									 }
		self._external_state_methods = {'auth_session':tg_api.auth_session,
										#'auth_with_qrcode':tg_api.auth_with_qrcode
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

			if '--debug' in sys.argv:
				print(user.tg_sessions)

			user.app_service.start()

		print(f'{clr.green}Loaded!{clr.yellow}')


	async def graceful_stop(self, update, context) -> None:
		if context._user_id not in CONFIG['admins']:
			return

		self.save_all_data()

		for user in self.connected_users.values():
			user.app_service.stop()

		await context.bot.send_message(context._chat_id, text=DEFAULT_LOCALE.MISC_MESSAGES['graceful_stop'])


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


	async def ref_start(self, update, context) -> None:
		""" Handler for referral start """
		inviter_id = int(context.args[0])
		await self.user_start(update, context, inviter_id=inviter_id)


	async def user_start(self, update, context, inviter_id=0) -> None:

		state = 'default'

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)
			state, inviter_id = update.callback_query.data.split(' ')[1::]
			inviter_id = int(inviter_id)

		if context._user_id in self.connected_users:
			return

		if state == 'default':
			keyboard = [[InlineKeyboardButton(LOCALES[lc]['button'], callback_data=f'user_start {lc} {inviter_id}')] for lc in LOCALES.keys()]
			keyboard = InlineKeyboardMarkup(keyboard)
			await context.bot.send_message(context._chat_id,
										   text="Select the bot language: ",
										   reply_markup=keyboard)
			return
		else:
			locale_module = LOCALES[state]['module']

		if not await utils.channel_participaiton_check(update, context, channels=CONFIG['required_channels']):
			keyboard = [[InlineKeyboardButton(locale_module.BUTTON_NAMINGS.channel_participaiton_check, callback_data=f"user_start {state} {inviter_id}")]]
			for channel in CONFIG['required_channels']:
				keyboard.insert(0, [InlineKeyboardButton(channel, url=f"t.me/{channel}")])

			keyboard = InlineKeyboardMarkup(keyboard)
			await context.bot.send_message(context._chat_id,
										   text=locale_module.MISC_MESSAGES['channel_participaiton_check'],
										   reply_markup=keyboard)
			return


		self.connected_users[context._user_id] = BotUser(user_id=context._user_id,
														 chat_id=context._chat_id,
														 locale=state,
														 current_config=CONFIG['default_user_config'])

		self.connected_users[context._user_id].app_service.start()
		user = self.connected_users[context._user_id]

		if inviter_id != 0 and user.user_id != inviter_id and user.customer_data.get('inviter_id', 0) == 0:
			# Referral system:
			user.customer_data['inviter_id'] = inviter_id
			self.connected_users[inviter_id].customer_data['free_credits'] += 1
			self.connected_users[inviter_id].customer_data['referral'].append(user.user_id)

		self.save_all_data()
		await self.main_menu(update, context)

		# keyboard = [[InlineKeyboardButton(BUTTON_NAMINGS.main_menu, callback_data='main_menu')]]
		# keyboard = InlineKeyboardMarkup(keyboard)

		# await context.bot.send_message(context._chat_id,
		# 							   text=MISC_MESSAGES['init_message'],
		# 							   reply_markup=keyboard)


	async def main_menu(self, update, context) -> None:
		if context._user_id not in self.connected_users.keys():
			return

		user = self.connected_users[context._user_id]
		user.current_state = None

		keyboard = [[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.my_accounts, callback_data='my_accounts'),
					 InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.add_account, callback_data='add_account')],
					[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.profile, callback_data='profile')],
					[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.invite_friends, callback_data='invite_friends')],
					[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.faq, url=CONFIG['faq_post_link'])]]

		if context._user_id in CONFIG['admins']:
			keyboard.append([InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.admin_panel, callback_data='admin_panel')])

		keyboard = InlineKeyboardMarkup(keyboard)

		if update.callback_query is not None:
			await context.bot.answer_callback_query(update.callback_query.id)

			if update.callback_query.message.text is not None:
				await update.callback_query.edit_message_text(text=user.locale_module.MISC_MESSAGES['main_menu'],
															  reply_markup=keyboard)
				return

		await context.bot.send_message(user.chat_id,
									   text=user.locale_module.MISC_MESSAGES['main_menu'],
									   reply_markup=keyboard)


	async def profile(self, update, context) -> None:
		""" Show brief user's info """

		await context.bot.answer_callback_query(update.callback_query.id)

		user_instance = update.callback_query.from_user
		user = self.connected_users[user_instance.id]
		text = f"👤 Name: {user_instance.first_name}\n" + \
			   f"🆔 ID: {user_instance.id}\n" + \
			   f"👥 Your referral: {len(user.customer_data['referral'])}\n" + \
			   f"🎁 Free credits: {user.customer_data['free_credits'] - len(user.tg_sessions)}\n" + \
			   f"🏷 The number of your accounts in the robot: {len(user.tg_sessions)}"

		await update.callback_query.edit_message_text(text=text,
													  reply_markup=utils.main_menu_keyboard())


	async def invite_friends(self, update, context) -> None:
		""" Refer friends and show some info """

		await context.bot.answer_callback_query(update.callback_query.id)

		user = self.connected_users[update.callback_query.from_user.id]

		text = f"👥 Your referral: {len(user.customer_data['referral'])}\n" + \
			   f"🎁 Free credit: {user.customer_data['free_credits'] - len(user.tg_sessions)}\n" + \
			   f"⚡️ By inviting your friends using the link below, you can get 1 free credit.\n" + \
			   f"Also, if your friends join the robot from your link, they will receive 2 free credits.\n" + \
			   f"Your invitation link 👇\n" + \
			   f"{helpers.create_deep_linked_url(context.bot.username, str(user.user_id))}"

		await update.callback_query.edit_message_text(text=text,
													  reply_markup=utils.main_menu_keyboard())


	async def add_account(self, update, context) -> None:
		"""Call auth_session method"""

		user = self.connected_users[context._user_id]

		if user.customer_data['free_credits'] <= len(user.tg_sessions):
			await context.bot.answer_callback_query(update.callback_query.id,
													text='You have not enough free credits')
			return

		await tg_api.auth_session(update, context, user=self.connected_users[context._user_id])


	async def my_accounts(self, update, context) -> None:
		user = self.connected_users[context._user_id]
		user.current_state = None

		await context.bot.answer_callback_query(update.callback_query.id)

		text = 'Choose an account from list:'
		keyboard = [[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]]

		_rm_list = []
		for name in user.tg_sessions.keys():
			if not user.tg_sessions[name].get('finished', False):
				_rm_list.append(name)
				continue

			if name not in user.app_service.clients.keys():
				print(user.app_service.clients.keys())
				if user.app_service.update_queue.empty():
					_rm_list.append(name)
					text += f'\n<b>Account {name} was removed due to telegram session error (try to recreate)</b>'
				else:
					text += f'\nAccount <b>{name}</b> is starting, please wait for some time'

		for name in _rm_list:
			del user.tg_sessions[name]

		for name in user.tg_sessions.keys():
			keyboard.append([InlineKeyboardButton(name, switch_inline_query_current_chat=f'{name}')]) # callback_data=f'get_user_session {name}'

		user.current_state = 'view_config'
		keyboard = InlineKeyboardMarkup(keyboard)

		await update.callback_query.edit_message_text(text=text,
													  parse_mode='HTML',
													  reply_markup=keyboard)


	async def get_user_session(self, update, context) -> None:
		await context.bot.answer_callback_query(update.callback_query.id)
		user = self.connected_users[context._user_id]

		session_name = update.callback_query.data.split(' ')[1]

		user.current_state = f'view_config {session_name}'

		statuses = user.app_service.fetch_status()[session_name]
		text = ''

		for name, status in statuses.items():
			app_text = '{}\n\tStatus: {}\n\tWarnings:{}\n\t{}'

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

			text += app_text.format(name,
									_status_text,
									_warning_text,
									user.app_service.applications[session_name][name].inline_report_info)

		keyboard = [[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.go_back, callback_data='my_accounts')],
					[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.delete_account, callback_data=f'delete_account default {session_name}')]]
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

			keyboard = [[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.go_back, callback_data='my_accounts'),
						 InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.confirm_account_deletion, callback_data=f'delete_account confirm {name}')]]
			keyboard = InlineKeyboardMarkup(keyboard)

			await context.bot.send_message(user.chat_id,
										   text=user.locale_module.MISC_MESSAGES['confirm_account_deletion'].format(name),
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
		""" Shows user his config """

		user = self.connected_users[update.message.from_user.id]
		session_name = user.current_state.split(' ')[1]
		app_name = update.message.text


		text = f'<b>Enabled</b>: {["No🔺", "Yes🟢"][user.current_config[session_name][app_name]["enabled"]]}'
		for param, value in user.current_config[session_name][app_name].items():
			if param != '__field_types':
				text += f'\n{param}: {value}'

		keyboard = [[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')],
					[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.change_config, callback_data=f'edit_config default {session_name} {app_name}')]]

		if user.current_config[session_name][app_name]["enabled"]:
			_button_name = user.locale_module.BUTTON_NAMINGS.disable_app
		else:
			_button_name = user.locale_module.BUTTON_NAMINGS.enable_app

		keyboard[-1].append(InlineKeyboardButton(_button_name, callback_data=f'edit_config toggle {session_name} {app_name}'))
		keyboard = InlineKeyboardMarkup(keyboard)

		await context.bot.send_message(user.chat_id, text=text, reply_markup=keyboard, parse_mode='HTML')


	async def edit_config(self, update, context) -> None:
		""" User editing own config """

		user = self.connected_users[context._user_id]

		def _apply_config():
			user.app_service.update_queue.put({'type':'update_config', 'data':user.current_config})
			self.save_all_data()

		if update.callback_query is not None:
			data = update.callback_query.data.split(' ')[1::]
			await context.bot.answer_callback_query(update.callback_query.id)

			if data[0] == 'toggle':
				user.current_config[data[1]][data[2]]['enabled'] = not user.current_config[data[1]][data[2]]['enabled']
				_apply_config()
				await update.callback_query.edit_message_text(text='Success!', reply_markup=utils.main_menu_keyboard())
			elif data[0] == 'default':
				keyboard = [[InlineKeyboardButton(user.locale_module.BUTTON_NAMINGS.return_to_main_menu, callback_data='main_menu')]]
				for param, value in user.current_config[data[1]][data[2]].items():
					if param not in {'enabled', '__field_types'}:
						keyboard.append([InlineKeyboardButton(param, callback_data=f'edit_config change_param {data[1]} {data[2]} {param}')])

				keyboard = InlineKeyboardMarkup(keyboard)
				await update.callback_query.edit_message_text(text=update.callback_query.message.text, reply_markup=keyboard)
			elif data[0] == 'change_param':
				await context.bot.send_message(user.chat_id, text=user.locale_module.MISC_MESSAGES['change_param'])
				user.current_state = f'edit_config {data[1]} {data[2]} {data[3]}'

			return

		session_name, app_name, param = user.current_state.split(' ')[1::]
		new_value = update.message.text
		user.current_state = None

		validate = False
		if user.current_config[session_name][app_name]['__field_types'][param] == 'int':
			if new_value.isnumeric():
				new_value = int(new_value)
				validate = True

		if not validate:
			await context.bot.send_message(user.chat_id,
										   text=user.locale_module.MISC_MESSAGES['invalid_value'],
										   reply_markup=utils.main_menu_keyboard())
			return

		user.current_config[session_name][app_name][param] = new_value
		_apply_config()

		await context.bot.send_message(user.chat_id,
									   text=user.locale_module.MISC_MESSAGES['change_param_succeeded'],
									   reply_markup=utils.main_menu_keyboard())


	async def inline_query(self, update, context) -> None:
		""" Inline query handler for config changing """
		query = update.inline_query.query

		user = self.connected_users[update.inline_query.from_user.id]
		print(query, query in user.app_service.clients)
		if user.current_state is None or not user.current_state.startswith('view_config') or query not in user.app_service.clients:
			result = [
				InlineQueryResultArticle(id=str(uuid.uuid4()),
										 title='main menu',
										 input_message_content=InputTextMessageContent('/main_menu'))
			]
			await update.inline_query.answer(result, cache_time=0)
			return

		session_name = query
		user.current_state = f'view_config {session_name}'

		result = []
		for name, chat_id in SUPPORTED_APPLICATIONS.items():
			# result.append(InlineQueryResultCachedPhoto(id=uuid.uuid4(),
			# 							 photo_file_id= await utils.get_app_photo(context.bot, user.chat_id, name),
			# 							 title=name,
			# 							 description=user.app_service.applications[session_name][name].inline_report_info,
			# 							 caption=user.app_service.applications[session_name][name].inline_report_info,
			# 							 input_message_content=InputTextMessageContent('simpletap'),
			# 							 ))
			_text = ""
			if name in user.app_service.applications[session_name]:
				_text = f"{user.app_service.applications[session_name][name].inline_report_info}"
			result.append(InlineQueryResultArticle(id=uuid.uuid4(),
												   thumbnail_url=CONFIG['app_images_urls'][name],
												   thumbnail_width=64,
												   thumbnail_height=64,
												   description=_text,
												   title=name,
												   input_message_content=InputTextMessageContent('simpletap')))

		await update.inline_query.answer(result, cache_time=0)



# 🟢🟡🔺

def main():
	print(f'{clr.green}Starting bot...')
	bot = Bot()

	if not ONLY_BOT:
		bot.load_tg_sessions()

	application = Application.builder().token(CONFIG['bot_token']).read_timeout(7).get_updates_read_timeout(42).build()

	application.add_handler(CommandHandler("start", bot.ref_start, filters.Regex(r"\d+")))
	application.add_handler(CommandHandler("start", bot.user_start))

	application.add_handler(CommandHandler("main_menu", bot.main_menu))
	application.add_handler(CommandHandler("save_all", bot.async_save))
	application.add_handler(CommandHandler("graceful_stop", bot.graceful_stop))

	application.add_handler(InlineQueryHandler(bot.inline_query))
	application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

	callback_handlers = {
			bot.main_menu        : "main_menu",
			bot.add_account      : "add_account",
			bot.my_accounts      : "my_accounts",
			bot.admin_panel      : "admin_panel",
			bot.get_user_session : "get_user_session",
			bot.delete_account   : "delete_account",
			bot.edit_config      : "edit_config",
			bot.user_start       : "user_start",
			bot.profile          : "profile",
			bot.invite_friends   : "invite_friends",
	}

	for function, pattern in callback_handlers.items():
		application.add_handler(CallbackQueryHandler(function, pattern=pattern))

	print(f'{clr.cyan}Bot is online{clr.yellow}')

	application.run_polling(allowed_updates=Update.ALL_TYPES)

	if not ONLY_BOT:
		bot.save_all_data()


if __name__ == '__main__':
	utils.init_environment()
	main()
