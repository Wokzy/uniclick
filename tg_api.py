
import io
import os
import utils
import qrcode
import asyncio
import telethon

# from apps import simpletap
from constants import (
	clr,
	CACHE_DIR,
	MISC_MESSAGES,
	BUTTON_NAMINGS,
	TG_SESSIONS_DIR,
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
			del user.tg_sessions[session_name]
			return

		result = await client.sign_in(phone=phone)
		user.tg_sessions[session_name]['phone'] = phone
		user.tg_sessions[session_name]['password'] = password
		user.tg_sessions[session_name]['phone_code_hash'] = result.phone_code_hash

		user.current_state = f"auth_session enquire_auth_code {session_name}"
		await context.bot.send_message(user.chat_id, text=MISC_MESSAGES['enquire_auth_code'], parse_mode='HTML')
		return


	if state == 'enquire_auth_code':
		code = update.message.text.replace('-', '')
		session = user.tg_sessions[session_name]
		me = None


		for i in range(5):
			try:
				me = await client.sign_in(phone=session['phone'],
										  code=code,
										  phone_code_hash=session['phone_code_hash'],
										  password=session['password'])
			except telethon.errors.rpcerrorlist.PhoneCodeInvalidError:
				await context.bot.send_message(user.chat_id,
											   text=MISC_MESSAGES['invalid_phone_code'],
											   reply_markup=utils.main_menu_keyboard())
				del user.tg_sessions[session_name]
				return
			except telethon.errors.rpcerrorlist.SessionPasswordNeededError:
				me = await client.sign_in(phone=session['phone'],
										  password=session['password'],
										  phone_code_hash=session['phone_code_hash'])
			except Exception:
				continue

			if me is not None:
				break

		if me is None:
			await context.bot.send_message(user.chat_id,
											   text=MISC_MESSAGES['failed_to_authorize'],
											   reply_markup=utils.main_menu_keyboard())
			del user.tg_sessions[session_name]
			return

		client.disconnect()

		user.tg_sessions[session_name] = {'user_id':me.id}
		user.app_service.update_queue.put({'type':'add_client', 'data':{'path':os.path.join(user.sessions_dir, session_name), 'name':session_name}})

		await context.bot.send_message(user.chat_id,
									   text=MISC_MESSAGES['authorized_successfully'],
									   parse_mode="HTML",
									   reply_markup=utils.main_menu_keyboard())


async def auth_with_qrcode(update, context, user, session_name:str='') -> None:
	""" Login with qrcode """

	if user.current_state == None:
		client = user.tg_sessions[session_name]['client']

		qr_login = await client.qr_login()
		img = qrcode.make(qr_login.url)

		byte_buffer = io.BytesIO()
		img.save(byte_buffer)

		await context.bot.send_photo(user.chat_id, photo=byte_buffer.getvalue())

		try:
			await qr_login.wait(timeout=5.0)
		except telethon.errors.rpcerrorlist.SessionPasswordNeededError:
			await context.bot.send_message(user.chat_id, text=MISC_MESSAGES['login_password_required'])
			user.current_state = f'auth_with_qrcode {session_name}'
			return
		except asyncio.TimeoutError:
			await context.bot.send_message(user.chat_id, text="The time to login is up, please try again and be quicker")
			return

		me = await client.get_me()
		client.disconnect()

		user.tg_sessions[session_name] = {'user_id':me.id}
		user.app_service.update_queue.put({'type':'add_client', 'data':{'path':os.path.join(user.sessions_dir, session_name), 'name':session_name}})

		await context.bot.send_message(user.chat_id,
									   text=MISC_MESSAGES['authorized_successfully'],
									   parse_mode="HTML",
									   reply_markup=utils.main_menu_keyboard())

		return

	session_name = user.current_state.split(' ')[1]
	password = update.message.text

	await update.message.delete()

	client = user.tg_sessions[session_name]['client']

	for i in range(5):
		try:
			me = await client.sign_in(password=password)
		except:
			continue

	client.disconnect()
	if me is None:
		await context.bot.send_message(user.chat_id,
										   text=MISC_MESSAGES['failed_to_authorize'],
										   reply_markup=utils.main_menu_keyboard())
		del user.tg_sessions[session_name]
		return

	user.tg_sessions[session_name] = {'user_id':me.id}
	user.app_service.update_queue.put({'type':'add_client', 'data':{'path':os.path.join(user.sessions_dir, session_name), 'name':session_name}})

	await context.bot.send_message(user.chat_id,
								   text=MISC_MESSAGES['authorized_successfully'],
								   parse_mode="HTML",
								   reply_markup=utils.main_menu_keyboard())
