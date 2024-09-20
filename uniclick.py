
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

import sys
import asyncio
from tg_client import init_client

if __name__ == "__main__":
	if '--debug' in sys.argv:
		asyncio.run(init_client())
	else:
		asyncio.run(init_client(session_name="tg_session"))


