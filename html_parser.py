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

import time

from html.parser import HTMLParser

class htmlParser(HTMLParser):

	# simple state machine that will break if the maintenance website changes format
	# idle => look for <table> tag
	#	table_found => table tag found, look for <td> tag or </table> tag
	#		td_found => td tag found, look for first <a> tag
	#			a1_found => first <a> tag found, save partial incident string
	#				a1_parsed => partial incident string saved, look for second <a> tag
	#					a2_found => second <a> tag found, complete incident string
	#						a2_parsed => look for 6th <td> tag => td2_found, 7th <td> tag => line_done
	#							td2_found => td tag found, add incident string to the list => a2_parsed
	#						line_done => line parsing done
	#	table_found => table tag found, look for <td> tag or </table> tag
	#		...
	# idle

	state = 'idle'

	incident = ''
	incident_list = {}

	tds_read = 0

	def handle_starttag(self, tag, attrs):
		if self.state == 'idle':
			if tag == 'table':
				for attr in attrs:
					if attr[0] == 'id' and attr[1] == 'testing_table':
						self.incident_list = {}
						self.state = 'table_found'

		elif self.state == 'table_found':
			if tag == 'td':
				self.state = 'td_found'

		elif self.state == 'td_found':
			if tag == 'a':
				self.state = 'a1_found'

		elif self.state == 'a1_parsed':
			if tag == 'a':
				self.state = 'a2_found'

		elif self.state == 'a2_parsed':
			if tag == 'td':
				self.tds_read = self.tds_read + 1
				if self.tds_read == 6:
					self.state = 'td2_found'
				elif self.tds_read == 7:
					self.state = 'line_done'

	def handle_endtag(self, tag):
		if tag == 'tr':
			if self.state  not in ['table_found', 'line_done']:
				print("Unexpected end of table row! state: " + self.state)

			self.state = 'table_found'
			self.incident = ''

		elif self.state == 'table_found':
			if tag == 'table':
				self.state = 'idle'

	def handle_data(self, data):
		if self.state == 'a1_found':
			self.state = 'a1_parsed'
			self.incident = data

		elif self.state == 'a2_found':
			self.state = 'a2_parsed'
			self.incident = self.incident + ':' + data
			self.tds_read = 0

		elif self.state == 'td2_found':
			self.incident_list[self.incident] = data
			self.state = 'a2_parsed'
