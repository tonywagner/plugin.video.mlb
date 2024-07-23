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


# settings functions
def get_addon_attribute(addon_file, attribute_name):
	try:
		tree = ET.parse(addon_file)
		root = tree.getroot()
		return str(root.attrib[attribute_name])
	except:
		pass
	return ''

def get_setting(setting_name):
	try:
		tree = ET.parse(SETTINGS_FILE)
		root = tree.getroot()
		for element in root:
			if element.attrib['id'] == setting_name:
				return element.text
	except:
		return None

def set_default_settings(default_settings_file):
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
		with open(SETTINGS_FILE, "wb") as f:
			f.write(new_settings_xml)
	except Exception as e:
		log('error setting default settings ' + str(e))

def set_setting(setting_name, setting_value):
	tree = ET.parse(SETTINGS_FILE)
	root = tree.getroot()
	for element in root:
		if element.attrib['id'] == setting_name:
			element.text = setting_value
			break
	xml_string = ET.tostring(root)
	with open(SETTINGS_FILE, "wb") as f:
		f.write(xml_string)

def get_cookies(session):
	try:
		with open(COOKIES_FILE, 'rb') as f:
			session.cookies.update(pickle.load(f))
	except:
		pass
	
def save_cookies(cookies=None):
	with open(COOKIES_FILE, 'w+b') as f:
		pickle.dump(cookies if not None else session.cookies, f)

def http_get(url, headers=None, session=None):
	if session:
		get_cookies(session)
		r = session.get(url, headers=headers, verify=VERIFY)
		save_cookies(session)
	else:
		r = requests.get(url, headers=headers, verify=VERIFY)
	return r

def http_post(url, headers=None, data=None, session=None):
	if session:
		get_cookies(session)
		r = session.post(url, headers=headers, data=data, verify=VERIFY)
		save_cookies(session)
	else:
		r = requests.post(url, headers=headers, data=data, verify=VERIFY)
	return r

def encode_post_data(data):
	return urllib.parse.urlencode(data)

def log(message):			
    if importlib.util.find_spec('xbmc'):
        xbmc.log(message)
    else:
        print(message)

def get_status():
	if get_setting('mlb_account_email') is not None and get_setting('mlb_account_password') is not None:
		return '<p>Logged In (<a href="logout">logout</a>)</p>'

# database functions
def initialize_cache_db():
	cursor = DATABASE_CONNECTION.cursor()
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
	# delete teams table if missing new columns
	try:
		cursor.execute('SELECT nickname FROM teams LIMIT 1')
	except:
		cursor.execute('DROP TABLE teams')
		pass
	try:
		cursor.execute('CREATE TABLE teams (teamId INT PRIMARY KEY, abbreviation TEXT, sportId INT, name TEXT, nickname TEXT, level_name TEXT, level TEXT, league TEXT, venueId INT, parentOrgName TEXT, parentOrgId INT)')
	except:
		pass
	DATABASE_CONNECTION.commit()
	cursor.close()
	
def reset_cache_db():
	cursor = DATABASE_CONNECTION.cursor()
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
	DATABASE_CONNECTION.commit()
	cursor.close()

def save_cached_stream(mediaId, url, token, expiration):
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('REPLACE INTO streams VALUES(?, ?, ?, ?)', [mediaId, url, token, expiration])
	DATABASE_CONNECTION.commit()
	cursor.close()

def get_cached_stream(mediaId):
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('SELECT url, token FROM streams WHERE mediaId = ? AND expiration > datetime("now")', [mediaId])
	result = cursor.fetchall()
	cursor.close()
	return result

def save_cached_session_data(id, value, expiration=None):
	cursor = DATABASE_CONNECTION.cursor()
	if expiration is not None:
		cursor.execute('REPLACE INTO session (id, value, expiration) VALUES(?, ?, ?)', [id, value, expiration])
	else:
		cursor.execute('REPLACE INTO session (id, value) VALUES(?, ?)', [id, value])
	DATABASE_CONNECTION.commit()
	cursor.close()

def get_cached_session_data(id):
	cursor = DATABASE_CONNECTION.cursor()
	query = 'SELECT value FROM session WHERE id = ? AND (expiration IS NULL or expiration > datetime("now"))'
	cursor.execute(query, [id])
	result = cursor.fetchall()
	cursor.close()
	return result

def save_cached_games(date, games, expiration):
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('REPLACE INTO games VALUES(?, ?, ?)', [date, games, expiration])
	DATABASE_CONNECTION.commit()
	cursor.close()

def get_cached_games(date):
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('SELECT games FROM games WHERE date = ? AND expiration > datetime("now")', [date])
	result = cursor.fetchall()
	cursor.close()
	return result

def save_cached_team(teamId, abbreviation, sportId, name, nickname, level_name, level, league, venueId, parentOrgName, parentOrgId):
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('REPLACE INTO teams VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [teamId, abbreviation, sportId, name, nickname, level_name, level, league, venueId, parentOrgName, parentOrgId])
	DATABASE_CONNECTION.commit()
	cursor.close()

def get_cached_teams():
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('SELECT * FROM teams ORDER BY sportId, name')
	result = cursor.fetchall()
	cursor.close()
	return result

def get_cached_team_name(teamId):
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('SELECT name FROM teams WHERE teamId = ? LIMIT 1', [teamId])
	result = cursor.fetchall()
	cursor.close()
	return result

def get_cached_team_nickname(teamId):
	cursor = DATABASE_CONNECTION.cursor()
	cursor.execute('SELECT nickname FROM teams WHERE teamId = ? LIMIT 1', [teamId])
	result = cursor.fetchall()
	cursor.close()
	return result
	
# date/time functions  
def get_utc_now():
	return datetime.datetime.now(timezone.utc)
        
def add_time(timestamp, days=0, hours=0, seconds=0):
	return timestamp + datetime.timedelta(days=days,hours=hours,seconds=seconds)
	
def dateToString(d, date_format):
	return d.strftime(date_format)
			
def process_date_string(date_string):
	if date_string == 'today':
		return str(date.today())
	elif date_string == 'yesterday':
		return str(add_time(date.today(), days=-1))
	else:
		return date_string
		
def stringToDate(date_string, date_format, use_local_time=False):
	# workaround for embedded strptime bug https://bugs.python.org/issue27400
	try:
		new_date = datetime.datetime.strptime(str(date_string), date_format).astimezone()
	except TypeError:
		new_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date_string, date_format)))
		if use_local_time is True:
			new_date += datetime.timedelta(seconds=time.localtime().tm_gmtoff)
	return new_date
		
def get_display_time(timestamp):
	display_time = timestamp.strftime('%I:%M %p').lstrip('0')
	return display_time

# settings
APP_DIRECTORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIRECTORY = os.path.join(APP_DIRECTORY, 'resources', 'data')
MEDIA_DIRECTORY = os.path.join(APP_DIRECTORY, 'resources', 'media')

if importlib.util.find_spec('xbmc'):
	KODI = True
	import xbmc, xbmcaddon, xbmcvfs

	addon = xbmcaddon.Addon()
	addon_id = addon.getAddonInfo('id')
	addon_handle = xbmcaddon.Addon(id=addon_id)
	addon_handle.setSetting(id='initialize', value='')
	LOCAL_STRING = addon.getLocalizedString
	USER_DATA_DIRECTORY = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
	VERSION = addon.getAddonInfo('name') + ' (' + addon_id + ') ' + addon.getAddonInfo('version') + ' on Kodi version ' + xbmc.getInfoLabel('System.BuildVersion') + ', '
else:
	KODI = False
	if os.environ.get('USER_DATA_DIRECTORY') is not None:
		USER_DATA_DIRECTORY = os.environ.get('USER_DATA_DIRECTORY')
	else:
		USER_DATA_DIRECTORY = os.path.join(APP_DIRECTORY, 'data')
	Path(USER_DATA_DIRECTORY).mkdir(parents=True, exist_ok=True)

	addon_file = os.path.join(APP_DIRECTORY, 'addon.xml')
	VERSION = get_addon_attribute(addon_file, 'id') + ' ' + get_addon_attribute(addon_file, 'version') + ' on '
	
VERSION += 'Python ' + platform.python_version()

SETTINGS_FILE = os.path.join(USER_DATA_DIRECTORY, 'settings.xml')

if not os.path.exists(SETTINGS_FILE):
	set_default_settings(os.path.join(APP_DIRECTORY, 'resources', 'settings.xml'))

LOCAL_WEBSERVER_PORT = int(get_setting('local_webserver_port'))
LOCAL_WEBSERVER_USERNAME = get_setting('local_webserver_username')
LOCAL_WEBSERVER_PASSWORD = get_setting('local_webserver_password')
LOCAL_WEBSERVER_CONTENT_PROTECTION_STRING = get_setting('local_webserver_content_protection_string')
LOCAL_WEBSERVER_BASE = '/mlb/'

# requests
COOKIES_FILE = os.path.join(USER_DATA_DIRECTORY, 'cookies')
VERIFY = True

# database
DATABASE_FILE = os.path.join(USER_DATA_DIRECTORY, 'cache.db')

DATABASE_CONNECTION = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
DATABASE_CONNECTION.row_factory = sqlite3.Row

initialize_cache_db()