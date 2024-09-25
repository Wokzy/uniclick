"""
Core of application and airdrops management
"""

import queue
import asyncio
import telethon
import threading

import utils
from apps import simpletap
from tg_api import init_client


class AppsService(threading.Thread):
	""" Unique thread is started for each Bot user """
	def __init__(self, config:dict):
		""" 
		update_queue stores update requests such as config change in format {'type':, 'data':}
		staus_queue stores current statuses of each app in format {'app_name':{status:}}
		"""

		super().__init__(daemon=True)

		self.clients = {}
		self.config = config

		self.update_queue = queue.Queue()
		self.status_queue = queue.Queue()
		self.applications = {}
		self.application_initializers = {'simpletap':simpletap.simpletap_init}
		self.applications_updaters = {'simpletap':simpletap.simpletap_update}


	def run(self):
		loop = asyncio.new_event_loop()
		loop.run_until_complete(self.main())


	async def main(self):

		while True:
			print('main loop')
			await self.fetch_updates()
			await self.init_applications()
			await self.update_applications()
			await self.fetch_status()

			await asyncio.sleep(2)


	async def fetch_updates(self):
		""" Apply updates from queue """

		while not self.update_queue.empty():
			print('fetch_updates')
			request = self.update_queue.get()

			if request['type'] == 'update_config':
				self.config = request[data]
			elif request['type'] == 'remove_client':
				del self.clients[request['data']]
				del self.applications[request['data']]
			elif request['type'] == 'add_client':
				self.clients[request['data']] = await init_client(request['data'])
				self.applications[request['data']] = {}


	async def fetch_status(self):
		""" Get applications statuses and warnings """

		status = {cl_name:{name:{'status':app.status, 'warning':app.warning} for name, app in self.applications[cl_name].items()} for cl_name in self.clients.keys()}

		while not self.status_queue.empty():
			self.status_queue.get()

		self.status_queue.put(status)


	async def init_applications(self):
		""" Start applications objects"""

		print('init_applications')

		for cl_name, client in self.clients.items():
			for name, method in self.application_initializers.items():
				if self.config[name]['enabled']:
					self.applications[cl_name]['simpletap'] = await simpletap.simpletap_init(client, self.config[name])
					# self.applications[cl_name][name] = await method(client, self.config[name])


	async def update_applications(self):
		""" Update each application """

		print('update_applications')
		print(self.clients)

		for cl_name, client in self.clients.items():
			_rm_list = []

			for name, method in self.applications_updaters.items():
				if self.config[name]['enabled']:
					await simpletap.simpletap_update(app=self.applications[cl_name][name], client=client)
					# await method(app=self.applications[cl_name][name], client=client)
				elif name in self.applications[cl_name]:
					_rm_list.append(name)

			for name in _rm_list:
				del self.applications[cl_name][name]
