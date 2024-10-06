"""
Bot constants
"""
import sys


DEBUG = '--debug' in sys.argv
ONLY_BOT = '--only-bot' in sys.argv
if DEBUG:
	print('running in debug mode')

CONFIG_FNAME = 'config.json'
TG_SESSIONS_DIR = 'sessions/'
USER_DATA_DIR = 'user_data/'
CACHE_DIR = '_chache/'

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
	main_menu                   = "Main menu"
	authorize                   = "Authorize"
	my_accounts                 = "My accounts"
	add_account                 = "Add account"
	faq                         = "FAQ"
	admin_panel                 = "Admin panel"
	return_to_main_menu         = "Return to main menu"
	try_again                   = "Try again"
	delete_account              = "Disconnect account"
	go_back                     = "go back"
	confirm_account_deletion    = "Yes, im 100/100 sure"
	default_login               = "VIA Phone number"
	qr_login                    = "VIA QR CODE"
	change_config               = "Change config"
	disable_app                 = "Disable"
	enable_app                  = "Enable"
	channel_participaiton_check = "Check"


MISC_MESSAGES = {
	"init_message":"Welcome to Uniclick bot, please authorize your telegram account to continue",
	"main_menu":"Main menu:",
	"session_name":"Enter session name (not more than 12 chars):",
	"wrong_session_name":"Wrong session name or session with exaclty the same name already exists",
	"incorrect_phone_format":"Invalid phone number",
	"enquire_auth_data":"⚡️ Send the mobile number in the correct form\n❗️Format: (country code and number without spaces) \n+10000000000 or 10000000000",
	"enquire_auth_code":"⚡️ Send OTP / Login Code from Telegram:",
	"failed_to_authorize":"❌ The information was not entered correctly.\nPlease try again.",
	"authorized_successfully":"✅ Your account has been added successfully.",
	"invalid_phone_code":"Login code you entered is invalid",
	"load_tg_sessions":"Loaded!",
	"graceful_stop":"You can now stop bot application",
	"confirm_account_deletion":"Are you sure about disconnection of {} account?",
	"login_password_required":"⚡️ Submit the two-factor account password (2FA):",
	"choose_login_option":"Choose login option:",
	"change_param":"Choose parameter to be changed:",
	"invalid_value":"Invalid value",
	"change_param_succeeded":"Parameter was changed successfully",
	"channel_participaiton_check":"To continue, please join all following channels"
}

