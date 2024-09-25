
import os
import utils
import asyncio
import telethon

# from apps import simpletap
from constants import (
	BUTTON_NAMINGS,
	MISC_MESSAGES,
	TG_SESSIONS_DIR,
	clr,
)


CONFIG = utils.load_config()


async def init_client(session_name='test') -> telethon.TelegramClient:
	client = telethon.TelegramClient(session_name, CONFIG['app_id'], CONFIG['app_hash'])
	await client.connect()
	return client


async def auth_session(update, context, user, session_name:str = '') -> None:
	""" Auth telegram account and save it as user tg_session"""

	if user.current_state is None:
		user.current_state = f'auth_session enquire_auth_data {session_name}'
		await context.bot.send_message(user.chat_id,
									   text=MISC_MESSAGES['enquire_auth_data'],
									   parse_mode='HTML')
		return

	state, session_name = user.current_state.split(' ')[1:]
	client = user.tg_sessions[session_name]['client']
	user.current_state = None

	if state == 'enquire_auth_data':
		auth_data = update.message.text.split(' ')
		await update.message.delete()

		phone, password = auth_data[0], None
		if len(auth_data) > 1:
			password = auth_data[1]

		if not phone.isnumeric():
			await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['incorrect_phone_format'],
										   reply_markup=utils.main_menu_keyboard())
			return

		await client.send_code_request(phone=phone, force_sms=False)
		user.tg_sessions[session_name]['phone'] = phone
		user.tg_sessions[session_name]['password'] = password

		user.current_state = f"auth_session enquire_auth_code {session_name}"
		await context.bot.send_message(user.chat_id, text=MISC_MESSAGES['enquire_auth_code'])
		return


	if state == 'enquire_auth_code':
		code = update.message.text.replace('-', '')
		session = user.tg_sessions[session_name]

		try:
			me = await client.sign_in(phone=session['phone'], code=code, password=session['password'])
		except telethon.errors.rpcerrorlist.PhoneCodeInvalidError:
			await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['invalid_phone_code'],
										   reply_markup=utils.main_menu_keyboard())
			del user.tg_sessions[session_name]
			return
		except telethon.errors.rpcerrorlist.SessionPasswordNeededError:
			me = await client.sign_in(phone=session['phone'], password=session['password'])
		except Exception:
			await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['failed_to_authorize'],
										   reply_markup=utils.main_menu_keyboard())
			del user.tg_sessions[session_name]
			return
		finally:
			client.disconnect()

		# if not await client.is_user_authorized():
		# 	await context.bot.send_message(user.chat_id,
		# 								   text=MISC_MESSAGES['failed_to_authorize'],
		# 								   reply_markup=utils.main_menu_keyboard())
		# 	del user.tg_sessions[session_name]
		# 	return

		user.tg_sessions[session_name] = {'user_id':me.id}
		user.app_service.update_queue.put({'type':'add_client', 'data':{'path':os.path.join(user.sessions_dir, session_name), 'name':session_name}})

		await context.bot.send_message(user.chat_id,
									   text=MISC_MESSAGES['authorized_successfully'],
									   parse_mode="HTML",
									   reply_markup=utils.main_menu_keyboard())

