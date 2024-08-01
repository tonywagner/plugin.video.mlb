# settings modules
import importlib.util
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import platform

import requests
import pickle
import urllib.parse

import sqlite3

import datetime
from datetime import date, timezone
import time


class Utils:

	# server initialization
	APP_DIRECTORY = None
	DATA_DIRECTORY = None
	MEDIA_DIRECTORY = None
	KODI = None
	LOCAL_STRING = None
	USER_DATA_DIRECTORY = None
	VERSION = None
	SETTINGS_FILE = None
	LOCAL_WEBSERVER_PORT = None
	LOCAL_WEBSERVER_USERNAME = None
	LOCAL_WEBSERVER_PASSWORD = None
	LOCAL_WEBSERVER_CONTENT_PROTECTION_STRING = None

	LOCAL_WEBSERVER_BASE = '/mlb/'

	COOKIES_FILE = None
	VERIFY = True

	DATABASE_FILE = None
	DATABASE_CONNECTION = None

	def server_init(self):
		# settings
		self.APP_DIRECTORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
		self.DATA_DIRECTORY = os.path.join(self.APP_DIRECTORY, 'resources', 'data')
		self.MEDIA_DIRECTORY = os.path.join(self.APP_DIRECTORY, 'resources', 'media')

		if importlib.util.find_spec('xbmc'):
			self.KODI = True
			import xbmc, xbmcaddon, xbmcvfs

			addon = xbmcaddon.Addon()
			addon_id = addon.getAddonInfo('id')
			addon_handle = xbmcaddon.Addon(id=addon_id)
			addon_handle.setSetting(id='initialize', value='')
			self.USER_DATA_DIRECTORY = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
			self.VERSION = addon.getAddonInfo('name') + ' (' + addon_id + ') ' + addon.getAddonInfo('version') + ' on Kodi version ' + xbmc.getInfoLabel('System.BuildVersion') + ', '
		else:
			self.KODI = False
			if os.environ.get('USER_DATA_DIRECTORY') is not None:
				self.USER_DATA_DIRECTORY = os.environ.get('USER_DATA_DIRECTORY')
			else:
				self.USER_DATA_DIRECTORY = os.path.join(self.APP_DIRECTORY, 'data')
			Path(self.USER_DATA_DIRECTORY).mkdir(parents=True, exist_ok=True)

			addon_file = os.path.join(self.APP_DIRECTORY, 'addon.xml')
			self.VERSION = self.get_addon_attribute(addon_file, 'id') + ' ' + self.get_addon_attribute(addon_file, 'version') + ' on '
	
		self.VERSION += 'Python ' + platform.python_version()
		self.log(self.VERSION)

		self.SETTINGS_FILE = os.path.join(self.USER_DATA_DIRECTORY, 'settings.xml')

		if not os.path.exists(self.SETTINGS_FILE):
			self.set_default_settings(os.path.join(self.APP_DIRECTORY, 'resources', 'settings.xml'))

		self.LOCAL_WEBSERVER_PORT = int(self.get_setting('local_webserver_port'))
		self.LOCAL_WEBSERVER_USERNAME = self.get_setting('local_webserver_username')
		self.LOCAL_WEBSERVER_PASSWORD = self.get_setting('local_webserver_password')
		self.LOCAL_WEBSERVER_CONTENT_PROTECTION_STRING = self.get_setting('local_webserver_content_protection_string')
		#self.LOCAL_WEBSERVER_BASE = '/mlb/'

		# requests
		self.COOKIES_FILE = os.path.join(self.USER_DATA_DIRECTORY, 'cookies')

		# database
		self.DATABASE_FILE = os.path.join(self.USER_DATA_DIRECTORY, 'cache.db')

		# debug: delete database file on restart
		#try:
		#	os.remove(self.DATABASE_FILE)
		#except:
		#	pass

		self.DATABASE_CONNECTION = sqlite3.connect(self.DATABASE_FILE, check_same_thread=False)
		self.DATABASE_CONNECTION.row_factory = sqlite3.Row

		self.initialize_cache_db()
	
	def addon_init(self):
		import xbmcaddon
		addon = xbmcaddon.Addon()
		addon_id = addon.getAddonInfo('id')
		addon_handle = xbmcaddon.Addon(id=addon_id)
		self.LOCAL_WEBSERVER_PORT = addon_handle.getSettingInt(id='local_webserver_port')
		self.LOCAL_STRING = addon.getLocalizedString


	# settings functions
	def get_addon_attribute(self, addon_file, attribute_name):
		try:
			tree = ET.parse(addon_file)
			root = tree.getroot()
			return str(root.attrib[attribute_name])
		except:
			pass
		return ''

	def get_setting(self, setting_name):
		try:
			tree = ET.parse(self.SETTINGS_FILE)
			root = tree.getroot()
			for element in root:
				if element.attrib['id'] == setting_name:
					return element.text
		except Exception as e:
			print(str(e))
			return None

	def set_default_settings(self, default_settings_file):
		try:
			new_settings = ET.Element('settings')
			new_settings.set('version', "2")
			tree = ET.parse(default_settings_file)
			root = tree.getroot()
			for section in root:
				for category in section:
					for group in category:
						for setting in group:
							setting_name = setting.attrib['id']
							for child in setting.findall('default'):
								setting_value = child.text
								if setting_value is None:
									setting_value = ''
								new_setting = ET.SubElement(new_settings, 'setting')
								new_setting.set('id', setting_name)
								new_setting.text = setting_value
			new_settings_xml = ET.tostring(new_settings)
			with open(self.SETTINGS_FILE, "wb") as f:
				f.write(new_settings_xml)
		except Exception as e:
			self.log('error setting default settings ' + str(e))

	def set_setting(self, setting_name, setting_value):
		tree = ET.parse(self.SETTINGS_FILE)
		root = tree.getroot()
		for element in root:
			if element.attrib['id'] == setting_name:
				element.text = setting_value
				break
		xml_string = ET.tostring(root)
		with open(self.SETTINGS_FILE, "wb") as f:
			f.write(xml_string)

	def get_cookies(self, session):
		try:
			with open(self.COOKIES_FILE, 'rb') as f:
				session.cookies.update(pickle.load(f))
		except:
			pass
	
	def save_cookies(self, cookies=None):
		with open(self.COOKIES_FILE, 'w+b') as f:
			pickle.dump(cookies if not None else session.cookies, f)

	def http_get(self, url, headers=None, session=None):
		if session:
			self.get_cookies(session)
			r = session.get(url, headers=headers, verify=self.VERIFY)
			self.save_cookies(session)
		else:
			r = requests.get(url, headers=headers, verify=self.VERIFY)
		return r

	def http_post(self, url, headers=None, data=None, session=None):
		if session:
			self.get_cookies(session)
			r = session.post(url, headers=headers, data=data, verify=self.VERIFY)
			self.save_cookies(session)
		else:
			r = requests.post(url, headers=headers, data=data, verify=self.VERIFY)
		return r

	def encode_post_data(self, data):
		return urllib.parse.urlencode(data)

	def log(self, message):			
		if importlib.util.find_spec('xbmc'):
			import xbmc
			xbmc.log(str(message))
		else:
			print(str(self.get_utc_now().astimezone()) + ' ' + str(message))

	def get_status(self):
		if self.get_setting('mlb_account_email') is not None and self.get_setting('mlb_account_password') is not None:
			return '<p>Logged In (<a href="logout">logout</a>)</p>'
		else:
			return ''

	# database functions
	def initialize_cache_db(self):
		cursor = self.DATABASE_CONNECTION.cursor()
		try:
			cursor.execute('CREATE TABLE streams (mediaId TEXT PRIMARY KEY, url TEXT, token TEXT, expiration TIMESTAMP)')
		except:
			pass
		try:
			cursor.execute('DELETE FROM streams WHERE expiration < datetime("now")')
		except:
			pass
		try:
			cursor.execute('CREATE TABLE session (id TEXT PRIMARY KEY, value TEXT, expiration TIMESTAMP)')
		except:
			# flush session table if missing entitlements, added in v2024.8.1
			try:
				cursor.execute('SELECT value FROM session WHERE id = "entitlements" LIMIT 1')
			except:
				try:
					cursor.execute('DELETE FROM session')
				except:
					pass
			pass
		try:
			cursor.execute('CREATE TABLE games (date TEXT PRIMARY KEY, games TEXT, expiration TIMESTAMP)')
		except:
			pass
		try:
			#cursor.execute('DELETE FROM games WHERE expiration < datetime("now")')
			cursor.execute('DELETE FROM games')
		except:
			pass
		# prune MILB teams from table for now
		try:
			cursor.execute('DELETE FROM teams WHERE sportId != 1')
		except:
			pass
		# delete teams table if missing new columns
		try:
			cursor.execute('SELECT logo_svg FROM teams LIMIT 1')
		except:
			try:
				cursor.execute('DROP TABLE teams')
			except:
				pass
		try:
			cursor.execute('CREATE TABLE teams (teamId INT PRIMARY KEY, abbreviation TEXT, sportId INT, name TEXT, nickname TEXT, level_name TEXT, level TEXT, league TEXT, venueId INT, logo TEXT, logo_svg TEXT, parentOrgName TEXT, parentOrgId INT)')
		except:
			pass
		self.DATABASE_CONNECTION.commit()
		cursor.close()
	
	def reset_cache_db(self):
		cursor = self.DATABASE_CONNECTION.cursor()
		try:
			cursor.execute('DELETE FROM streams')
		except:
			pass
		try:
			cursor.execute('DELETE FROM session')
		except:
			pass
		try:
			cursor.execute('DELETE FROM games')
		except:
			pass
		self.DATABASE_CONNECTION.commit()
		cursor.close()

	def save_cached_stream(self, mediaId, url, token, expiration):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('REPLACE INTO streams VALUES(?, ?, ?, ?)', [mediaId, url, token, expiration])
		self.DATABASE_CONNECTION.commit()
		cursor.close()

	def get_cached_stream(self, mediaId):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('SELECT url, token FROM streams WHERE mediaId = ? AND expiration > datetime("now")', [mediaId])
		result = cursor.fetchall()
		cursor.close()
		return result

	def get_any_cached_stream_token(self):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('SELECT token FROM streams LIMIT 1')
		result = cursor.fetchall()
		cursor.close()
		return result

	def save_cached_session_data(self, id, value, expiration=None):
		cursor = self.DATABASE_CONNECTION.cursor()
		if expiration is not None:
			cursor.execute('REPLACE INTO session (id, value, expiration) VALUES(?, ?, ?)', [id, value, expiration])
		else:
			cursor.execute('REPLACE INTO session (id, value) VALUES(?, ?)', [id, value])
		self.DATABASE_CONNECTION.commit()
		cursor.close()

	def get_cached_session_data(self, id):
		cursor = self.DATABASE_CONNECTION.cursor()
		query = 'SELECT value FROM session WHERE id = ? AND (expiration IS NULL or expiration > datetime("now"))'
		cursor.execute(query, [id])
		result = cursor.fetchall()
		cursor.close()
		return result

	def save_cached_games(self, date, games, expiration):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('REPLACE INTO games VALUES(?, ?, ?)', [date, games, expiration])
		self.DATABASE_CONNECTION.commit()
		cursor.close()

	def get_cached_games(self, date):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('SELECT games FROM games WHERE date = ? AND expiration > datetime("now")', [date])
		result = cursor.fetchall()
		cursor.close()
		return result

	def save_cached_team(self, teamId, abbreviation, sportId, name, nickname, level_name, level, league, venueId, logo, logo_svg, parentOrgName, parentOrgId):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('REPLACE INTO teams VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [teamId, abbreviation, sportId, name, nickname, level_name, level, league, venueId, logo, logo_svg, parentOrgName, parentOrgId])
		self.DATABASE_CONNECTION.commit()
		cursor.close()

	def get_cached_teams(self):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('SELECT * FROM teams ORDER BY sportId, name')
		result = cursor.fetchall()
		cursor.close()
		return result

	def get_cached_team_name(self, teamId):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('SELECT name FROM teams WHERE teamId = ? LIMIT 1', [teamId])
		result = cursor.fetchall()
		cursor.close()
		return result

	def get_cached_team_nickname(self, teamId):
		cursor = self.DATABASE_CONNECTION.cursor()
		cursor.execute('SELECT nickname FROM teams WHERE teamId = ? LIMIT 1', [teamId])
		result = cursor.fetchall()
		cursor.close()
		return result
		
	def get_image_url(self, teamId=None, away_teamId=None, home_teamId=None, venueId=None, width=750, format=None):
		url = 'icon.png'
		if venueId:
			url = 'http://cd-images.mlbstatic.com/stadium-backgrounds/color/light-theme/1920x1080/%s.png' % str(venueId)
		elif teamId:
			if format == 'svg':
				url = 'https://www.mlbstatic.com/team-logos/%s.svg' % str(teamId)
			else:
				url = 'https://www.mlbstatic.com/team-logos/share/%s.jpg' % str(teamId)
		elif away_teamId and home_teamId:
			if away_teamId in range(108,159) and home_teamId in range(108,159):
				url = 'https://img.mlbstatic.com/mlb-photos/image/upload/ar_167:215,c_crop/fl_relative,l_team:{1}:fill:spot.png,w_1.0,h_1,x_0.5,y_0,fl_no_overflow,e_distort:100p:0:200p:0:200p:100p:0:100p/fl_relative,l_team:{0}:logo:spot:current,w_0.38,x_-0.25,y_-0.16/fl_relative,l_team:{1}:logo:spot:current,w_0.38,x_0.25,y_0.16/w_{2}/team/{0}/fill/spot.png'.format(str(away_teamId), str(home_teamId), str(width))
				
		return url
	
	# date/time functions  
	def get_utc_now(self):
		return datetime.datetime.now(timezone.utc)
		
	def add_time(self, timestamp, days=0, hours=0, seconds=0):
		return timestamp + datetime.timedelta(days=days,hours=hours,seconds=seconds)
	
	def dateToString(self, d, date_format):
		return d.strftime(date_format)
			
	def process_date_string(self, date_string):
		if date_string == 'today':
			return str(date.today())
		elif date_string == 'yesterday':
			return str(self.add_time(date.today(), days=-1))
		else:
			return date_string
		
	def stringToDate(self, date_string, date_format, use_local_time=False):
		# workaround for embedded strptime bug https://bugs.python.org/issue27400
		try:
			new_date = datetime.datetime.strptime(str(date_string), date_format).astimezone()
		except TypeError:
			new_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date_string, date_format)))
			if use_local_time is True:
				new_date += datetime.timedelta(seconds=time.localtime().tm_gmtoff)
		return new_date
		
	def get_display_time(self, timestamp):
		display_time = timestamp.strftime('%I:%M %p').lstrip('0')
		return display_time	