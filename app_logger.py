
import datetime
from constants import DEBUG


class Logger:
	def __init__(self):
		pass


	def log_string(self, string: str, on_debug=True) -> None:
		if DEBUG or not on_debug:
			date = datetime.datetime.now().strftime("%d %h %H:%M:%S")
			print(f'[{date}] {string}')



class AppLogger(Logger):
	def __init__(self, app_name):
		self.app_name = app_name
		super().__init__()


	def log_app(self, user_id: int, string: str, on_debug=True) -> None:
		self.log_string(string = f'({self.app_name}) ({user_id}) {string}', on_debug=on_debug)
