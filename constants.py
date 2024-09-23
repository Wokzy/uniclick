"""
Bot constants
"""

CONFIG_FNAME = 'config.json'
TG_SESSIONS_DIR = 'sessions/'
USER_DATA_DIR = 'user_data/'

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


class BUTTON_NAMINGS:
	main_menu = "Main menu"
	authorize = "Authorize"
	my_accounts = "My accounts"
	add_account = "Add account"
	faq = "FAQ"
	admin_panel = "Admin panel"


MISC_MESSAGES = {
	"init_message":"Welcome to Uniclick bot, please authorize your telegram account to continue",
	"main_menu":"Main menu:"
}

