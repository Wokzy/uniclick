"""
Bot constants
"""
import sys
from locales import english_lc


DEBUG = '--debug' in sys.argv
ONLY_BOT = '--only-bot' in sys.argv
if DEBUG:
	print('running in debug mode')

CONFIG_FNAME = 'config.json'
TG_SESSIONS_DIR = 'sessions/'
USER_DATA_DIR = 'user_data/'
CACHE_DIR = '_chache/'


LOCALES = {'eng':{"module":english_lc, "button":"🇺🇸 English"}}
DEFAULT_LOCALE = LOCALES['eng']['module']

class clr:
	"""
		Logging colors
	"""
	blue = '\033[94m'
	cyan = '\033[96m'
	green = '\033[92m'
	yellow = '\033[93m'
	red = '\033[91m'
	white = '\033[0m'
	bold = '\033[1m'
