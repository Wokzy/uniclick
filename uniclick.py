
# from telegram import (
# 	InlineKeyboardButton,
# 	InlineKeyboardMarkup,
# 	Update,
# )

# from telegram.ext import (
# 	Application,
# 	CommandHandler,
# 	ContextTypes,
# 	MessageHandler,
# 	CallbackQueryHandler,
# 	JobQueue,
# 	filters,
# )

import asyncio
from tg_client import init_client

if __name__ == "__main__":
	# test()
	# asyncio.run(init_client())
	asyncio.run(init_client(session_name="tg_session"))


