#!/usr/bin/python3

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

'''
Dependencies:

pip install rocket-python
pip install python-ws4py
pip install python-pyee

These are not available in SUSE packages, so copy them from github and put
them in the same folder for the time being:

DDPClient.py - from
https://github.com/hharnisc/python-ddp -
hharnisc@gmail.com - MIT License

ejson.py - from

https://github.com/lyschoening/meteor-ejson-python - lars@lyschoening.de - MIT License
'''

import socket
import ssl
import certifi
import urllib3
import threading
import time

import ast

import html_parser

import configparser

import rocket_listener

use_irc = False
use_rocket = False

# Load the configuration file
config = configparser.ConfigParser()
config.read("botto.config")

if config["General"]["use_rocket"] == "True":
	use_rocket = True
	rocket_server = config["Rocket"]["server"]
	rocket_room = config["Rocket"]["room"]
	rocket_username = config["Rocket"]["username"]
	rocket_pass = config["Rocket"]["password"]
	rocket_adminname = config["Rocket"]["admin_name"]

if config["General"]["use_irc"] == "True":
	use_irc = True
	irc_server = config["IRC"]["server"]
	irc_port = int(config["IRC"]["port"])
	irc_channel = config["IRC"]["channel"]
	irc_nick = config["IRC"]["nick"]
	irc_adminname = config["IRC"]["admin_name"]
	exitcode = "logout " + irc_nick

interval = int(config["General"]["interval"])
if interval == 0:
	interval = 60

# ---------------------------------- Start IRC ------------------------------------------

# very simple IRC functinoality to get us going - convert this into a class and its own module later
def irc(server, port):
	raw_ircmsg = ""
	authenticated = False
	channel_joined = False

	# create an ssl socket for IRC
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	irc_socket = ssl.wrap_socket(s)
	irc_socket.connect((server, port))

	while True:
		received = irc_socket.recv(2048).decode("UTF-8").replace("\r","");
		# print("[Raw] " + received)

		raw_ircmsg += received

		while raw_ircmsg.find("\n") != -1:
			# print("[Queue] " + raw_ircmsg.replace("\n","\\n").replace("\r","\\r"))

			pos = raw_ircmsg.find("\n")
			ircmsg = raw_ircmsg[:pos]
			raw_ircmsg = raw_ircmsg[pos+1:]

			parts = ircmsg.split(" :",1)

			data=""
			if len(parts) > 1:
				data = parts[1]

			protocol = parts[0].lower().split(" ")

			# keep mixed case version for sender and message_target
			uc_protocol = parts[0].split(" ")

			# mesage with defined sender
			if ircmsg[0] == ":":
				sender_hostmask = uc_protocol[0][1:]
				sender = sender_hostmask.split('!',1)[0]

				if len(protocol) > 1:
					message_type = protocol[1]

				if len(uc_protocol) > 2:
					message_target = uc_protocol[2]

			# message without defined sender, e.g. PING, ERROR
			else:
				message_type = protocol[0]

			if message_type == "notice":
				if message_target.lower() == "auth":
					print("[Auth] " + data)

					if not authenticated:
						authenticated = True
						send(irc_socket, "USER "+ irc_nick + " " + irc_nick + " " + irc_nick + " " + irc_nick + "\n")
						send(irc_socket, "NICK "+ irc_nick + "\n")
				else:
					print("[Notice] " + data)

			elif message_type == "privmsg":
				message = data

				if data.lower().split(" ",1)[0] == "\x01action":
					print("[" + message_target + "] * "+sender+" " + data[8:-1])
				else:
					print("[" + message_target + "] "+sender+": " + data)

				if sender.lower() == irc_adminname.lower() and message_target == irc_channel:
					if message.lower().rstrip() == exitcode.lower():
						sendmsg("Logging out.")
						send(irc_socket, "QUIT \n")
						return
					elif message.lower() == "fetch":
						request = pool_manager.request("GET", "https://maintenance.suse.de/overview/testing.html")

						print(request.data.decode("utf-8")) # Response text.
						print(request.status) # Status code.
						print(request.headers["Content-Type"]) # Content type.


						# currently crashes here
						etree.fromstring(request.data.decode("utf-8"),"html5")

			# RPL_WELCOME, RPL_YOURHOST, RPL_CREATED
			elif message_type in ["001","002","003"]:
				print("[Welcome] " + data)

			# RPL_MYINFO
			elif message_type == "004":
				print("[Server Info] " + " ".join(protocol[3:]) + " " + data)

			# RPL_ISUPPORT
			elif message_type == "005":
				print("[Support] " + " ".join(protocol[3:]) + " " + data)

			# RPL_YOURID
			elif message_type == "042":
				print("[ID] " + " " + protocol[3] + " " + data)

			# RPL_LUSERCLIENT, RPL_LUSERME, RPL_LOCALUSERS, RPL_GLOBALUSERS
			elif message_type in ["251", "255", "265", "266"]:
				print("[Users] " + data)

				# if we came this far we can request to join channels
				if not channel_joined:
					channel_joined = True
					join_channel(irc_socket, irc_channel)

			# RPL_LUSEROP, RPL_LUSERUNKNOWN, RPL_LUSERCHANNELS
			elif message_type in ["252", "253", "254"]:
				print("[Users] " + protocol[3] + " " + data)

			# RPL_NAMREPLY
			elif message_type == "353":
				print("[Names] " + protocol[4] + ": " + data)

			# RPL_ENDOFNAMES
			elif message_type == "366":
				print("[Names] " + protocol[3] + ": " + data)

			# RPL_MOTD, RPL_MOTDSTART, RPL_ENDOFMOTD
			elif message_type in ["372","375","376"]:
				print("[MOTD] " + data)

			elif message_type == "mode":
				print("[Mode] " + sender + " sets mode " + protocol[3] + " on " + message_target)

			elif message_type == "join":
				print("[Join] " + sender + " joined channel " + data)

			elif message_type == "ping":
				send(irc_socket, "PONG :" + data + "\n")

			else:
				print(ircmsg)
				print(protocol)

def send(s, command, silent=False):
	if not silent:
		print("=> " + command.strip("\n"))
	s.send(bytes(command, "UTF-8"))

def join_channel(s, name):
	send(s, "JOIN "+ name + "\n")

# ---------------------------------- End IRC --------------------------------------------

def sendmsg(message):
	if use_irc:
		print("[" + irc_channel + "] "+ irc_nick +": " + message)
		send("PRIVMSG "+ irc_channel +" :"+ message +"\n", True)

	if use_rocket:
		rocket.send_message(message)

class Scraper(threading.Thread):
	def __init__(self, event):
		threading.Thread.__init__(self)
		self.stopped = event

	def run(self):
		while not self.stopped.wait(interval):
			# for ssl connections to external websites
			# we trust our own website to be genuine, so set CERT_NONE
			pool_manager = urllib3.PoolManager(cert_reqs='CERT_NONE', ca_certs=certifi.where())
			# don't complain in the logs about insecure requests, please
			urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

			request = pool_manager.request("GET", "https://maintenance.suse.de/overview/testing.html")

			# parse website only if it was loaded correctly
			if request.status == 200:
				# print(request.headers["Content-Type"]) # Content type.
				data = request.data.decode("utf-8") # Response text.

				print("Checking incidents ...")

				parser = html_parser.htmlParser()
				parser.feed(data)

				new_incidents = []
				assigned_incidents = []
				for incident in parser.incident_list:
					if not incident in known_incidents:
						if parser.incident_list[incident].find('[qam-sle]') != -1:
							new_incidents.append(repr(incident))
							known_incidents[incident] = '[qam-sle]'
					elif known_incidents[incident] == '[qam-sle]':
						if parser.incident_list[incident].find('[qam-sle]') == -1:
							known_incidents[incident] = parser.incident_list[incident]
							assigned_incidents.append(repr(incident) + " => " + parser.incident_list[incident])

				if len(new_incidents):
					sendmsg("New incidents: " + repr(new_incidents))

				if len(assigned_incidents):
					sendmsg("Assigned incidents: " + repr(assigned_incidents))

				lost_incidents = []
				for incident in known_incidents:
					if not incident in parser.incident_list:
						print("Lost incident: "+repr(incident))

						# remember this incident was lost
						lost_incidents.append(incident)

				if len(lost_incidents):
					# remove the incidents from known incidents
					sendmsg("Lost incidents: "+repr(lost_incidents))
					for i in lost_incidents:
						del known_incidents[i]

				f = open("incidents.txt", "w")
				f.write(repr(known_incidents))
				f.close()
			else:
				print("Loading website failed: " + str(request.status))

# do more useful things here once the main functionality works
def main():
	stopFlag = threading.Event()
	scraper_thread = Scraper(stopFlag)
	scraper_thread.start()

	#scrape_timer = threading.Timer(interval, scrape)
	#scrape()

	sendmsg("Running!")

	# basically endless loop until you press enter
	input()

	sendmsg("Exited!")

	# this will stop the timer
	stopFlag.set()
	# scrape_timer.cancel()

# only one server/channel for the moment, think about multiple connections later
if use_irc:
	irc_thread = threading.Thread(target=irc, args=(irc_server,irc_port))
	irc_thread.start()

# only one server/room for the moment, think about multiple connections later
if use_rocket:
	rocket = rocket_listener.Rocket()
	rocket.connect_to_server(rocket_server, 443, rocket_username, rocket_pass, rocket_room);

known_incidents = {}

try:
	f = open('incidents.txt')
	print("Loading incident database.")
	known_incidents = ast.literal_eval(f.read())
	f.close()
except FileNotFoundError:
	print("Creating new incident database.")
	f = open("incidents.txt", "w")
	f.write(repr({}))
	f.close()

# main loop - do something useful once the core functionality works
main()
