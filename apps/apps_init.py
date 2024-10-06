"""
Core of application and airdrops management
"""

import time
import queue
import asyncio
import telethon
import threading

import utils
from apps import simpletap
from app_logger import Logger
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
		self.logger = Logger()
		self.applications = {}
		self.application_initializers = {'simpletap':simpletap.simpletap_init}
		self.applications_updaters = {'simpletap':simpletap.simpletap_update}

		self.running = True


	def run(self):
		loop = asyncio.new_event_loop()
		loop.run_until_complete(self.main())


	def stop(self):
		self.running = False
		for client in self.clients.values():
			client.disconnect()


	async def main(self):
		self.running = True

		while self.running:
			await self.fetch_updates()
			await self.init_applications()
			await self.update_applications()

			time.sleep(3)


	async def fetch_updates(self):
		""" Apply updates from queue """

		self.update_queue.put({'type':'mock'})
		while not self.update_queue.empty():
			request = self.update_queue.get()

			if request['type'] == 'mock':
				break
			elif request['type'] == 'update_config':
				self.config = request['data']
			elif request['type'] == 'remove_client':
				await self.clients[request['data']].log_out()
				await self.clients[request['data']].disconnect()

				del self.clients[request['data']]
				del self.applications[request['data']]
			elif request['type'] == 'add_client':
				client = await init_client(request['data']['path'])
				if not await client.is_user_authorized():
					await client.disconnect()
					return

				await client.get_me()

				self.clients[request['data']['name']] = client
				self.applications[request['data']['name']] = {}


	def fetch_status(self):
		""" Get applications statuses and warnings """
		return {cl_name:{name:{'status':app.status, 'warning':app.warning} for name, app in self.applications[cl_name].items()} for cl_name in self.clients.keys()}


	async def init_applications(self):
		""" Start applications objects"""

		_rm_list = []

		for cl_name, client in self.clients.items():
			if not client.is_connected():
				await client.connect()

			if not await client.is_user_authorized():
				if client.is_connected():
					await client.disconnect()
				_rm_list.append(cl_name)
				continue

			for name, method in self.application_initializers.items():
				if self.config[name]['enabled'] and name not in self.applications[cl_name]:
					self.applications[cl_name][name] = await method(client, self.config[name])

		for cl_name in _rm_list:
			del self.clients[cl_name]


	async def update_applications(self):
		""" Update each application """

		for cl_name, client in self.clients.items():
			if not client.is_connected():
				await client.connect()

			_rm_list = []

			for name, method in self.applications_updaters.items():
				if self.config[name]['enabled']:
					await method(app=self.applications[cl_name][name], client=client)
				elif name in self.applications[cl_name]:
					_rm_list.append(name)

			for name in _rm_list:
				del self.applications[cl_name][name]
