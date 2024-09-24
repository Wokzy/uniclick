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
	return_to_main_menu = "Return to main menu"
	try_again = "Try again"


MISC_MESSAGES = {
	"init_message":"Welcome to Uniclick bot, please authorize your telegram account to continue",
	"main_menu":"Main menu:",
	"session_name":"Enter session name (not more than 12 chars):",
	"wrong_session_name":"Wrong session name or session with exaclty the same name already exists",
	"incorrect_phone_format":"Invalid phone number",
	"enquire_auth_data":"Enter your auth data in format: <b>PhoneNumber</b> <b>[Password (optional)]</b>\nExample:\n12356358799 password",
	"enquire_auth_code":"Enter the code you recieved for login in format <b>1-2-3-4-5</b>:",
	"failed_to_authorize":"Failed to authorize, perhaps incorrect credentials",
	"authorized_successfully":"Successfully authorized your account, it can be managed in <b>My accounts</b> section",
	"invalid_phone_code":"Login code you entered is invalid"
}

