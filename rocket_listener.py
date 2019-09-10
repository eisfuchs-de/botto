# Copyright 2019 Dario Abatianni
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; version 2.1.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Dario Abatianni <dabatianni@suse.de>
#
# ----------------------------------------------------------------------------

import hashlib

# for Rocket.Chat's "realtime" API to listen for events
import json
import ejson
from DDPClient import DDPClient

# Rocket.Chat REST API for sending messages
from rocketchat.api import RocketChatAPI

class Rocket():

	# pre declare variables to be able to use them anywhere without error messages
	client: DDPClient
	room_name=''
	room_id=''
	sub_id=0
	server=''
	port=443
	username=''
	pass_hash=''

	def send_message(msg):
		rocket_api.send_message(message)

	# ---------------- callbacks for the realtime API ---------------------

	def subscription_callback(self, data, data2):
		print('* SUBSCRIBED - data: {} data2: {}'.format(str(data), str(data2))
)

	def connected(self):
		print('* CONNECTED'
)

		self.client.call("login", ([{
					"user": { "username": self.username },
					"password": {
						"digest": self.pass_hash,
						"algorithm":"sha-256"
					}}]), self.login)

	def login(self, error, result):
		print('* LOGIN - data: {} {}'.format(str(error), str(result))
)
		self.sub_id = self.client.subscribe('stream-room-messages', ([self.room_id, False]), self.subscription_callback)

	def closed(self, code, reason):
		print('* CONNECTION CLOSED {} {}'.format(code, reason)
)
	
	def failed(self, collection, data):
		print('* FAILED - data: {}'.format(str(data))
)

	def reconnected(self):
		print('* RECONNECTED'
)

	def version_mismatch(self, versions):
		print('* VERSION MISMATCH - versions: {}'.format(str(versions))
)

	def changed(self, collection, id, fields, cleared):
		print('* CHANGED {} {}'.format(collection, id)
)

		for key, value in fields.items():
			print('  - FIELD {} {}'.format(key, "")
)
		for key, value in cleared.items():
			print('  - CLEARED {} {}'.format(key, value)
)

		if collection == "stream-room-messages":

			username=fields["args"][0]["u"]["username"]
			if username != self.username:
				print("##############################")
				print(username+" said: "+fields["args"][0]["msg"])
				rocket_api.send_message(username+" said: "+fields["args"][0]["msg"], rocket_room_id)
				print("##############################")

	def added(self, collection, id, fields):
		print('* ADDED {} {}'.format(collection, id)
)
		for key, value in fields.items():
			print('  - FIELD {} {}'.format(key, value)
)

	def removed(self, collection, id):
		print('* REMOVED {} {}'.format(collection, id)
)

	def received_message(self, message):
		print('* RECEIVED_MESSAGE {}'.format(ejson.loads(str(message)))
)

	# -------------- end callbacks for the realtime API -------------------

	def connect_to_server(self,server,port,username,password,room_name):
		self.server=server
		self.port=port
		self.room_name=room_name
		self.username=username

		# python stupidity fix - a single "%" is used as placeholder for formats
		rocket_pass=password.replace("%","%%").encode('utf-8')

		# create a sha256 hex digest hash of the password for the realtime API login which will be
		# used later in one of the event handlers
		self.pass_hash=hashlib.sha256(rocket_pass).hexdigest()

		# connect to REST API for sending messages
		rocket_api = RocketChatAPI(
			settings =
			{
				"username": self.username, "password": rocket_pass, "domain": "https://"+self.server
			})

		# not sure if this does anything useful to overwrite the password in memory
		password='*********************************'
		rocket_pass='*********************************'

		# get the room ID so we can subscribe to its stream in one of the event handlers
		self.room_id = rocket_api.get_room_id(self.room_name)

		self.client = DDPClient('wss://'+self.server+':'+str(self.port)+'/websocket', True, 10.0, True)

		# set up event handlers
		self.client.on('connected', self.connected)
		self.client.on('socket_closed', self.closed)
		self.client.on('reconnected', self.reconnected)
		self.client.on('failed', self.failed)
		self.client.on('version_mismatch', self.version_mismatch)
		self.client.on('added', self.added)
		self.client.on('changed', self.changed)
		self.client.on('removed', self.removed)

		self.client.ddpsocket.on('received_message', self.received_message)

		# connect to server, everything else will be handled by events
		self.client.connect()

		# announce that we're running (disabled for testing, it gets annoying)
		# rocket_api.send_message("Botto running! Waiting for command.", self.room_id)

	def disconnect(self):
		self.client.unsubscribe(sub_id)
