import os
import requests
import secrets
import hashlib
import base64
import urllib.parse
import json
import re
import sys

class Account:
	session = None
	common_headers = {
	  'cache-control': 'no-cache', 
	  'origin': 'https://www.mlb.com', 
	  'pragma': 'no-cache',
	  'priority': 'u=1, i', 
	  'referer': 'https://www.mlb.com/', 
	  'sec-ch-ua': '"Chromium";v="126", "Google Chrome";v="126", "Not-A.Brand";v="8"', 
	  'sec-ch-ua-mobile': '?0', 
	  'sec-ch-ua-platform': '"macOS"', 
	  'sec-fetch-dest': 'empty', 
	  'sec-fetch-mode': 'cors', 
	  'sec-fetch-site': 'same-site', 
	  'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
	}
	verify=True
	okta_user_agent_extended = 'okta-auth-js/7.0.2 okta-signin-widget-7.14.0'
	client_id = '0oap7wa857jcvPlZ5355'
	
	hls_content_types = ['application/vnd.apple.mpegurl', 'application/x-mpegURL', 'audio/mpegurl']
	
	code_verifier = None
	identify_stateHandle = None
	authenticators_password_id = None
	okta_id = None
	access_token = None
	deviceId = None
	sessionId = None
	
	feed_keys = ['videoFeeds', 'audioFeeds']
	
	utils = None

	def __init__(self, utils):
		self.session = requests.session()
		self.utils = utils
		
		
	def logout(self):
		self.utils.save_cookies('')
		self.session = requests.session()
		self.utils.reset_cache_db()
		self.code_verifier = None
		self.identify_stateHandle = None
		self.authenticators_password_id = None
		self.okta_id = None
		self.access_token = None
		self.deviceId = None
		self.sessionId = None
		self.utils.set_setting('mlb_account_email', '')
		self.utils.set_setting('mlb_account_password', '')

	def login(self, mlb_account_email, mlb_account_password):
		self.utils.set_setting('mlb_account_email', mlb_account_email)
		self.utils.set_setting('mlb_account_password', mlb_account_password)
		self.get_token()
		
	def get_expiresAt(self, expiry):
		if isinstance(expiry, int):
			return self.utils.add_time(self.utils.get_utc_now(), seconds=expiry)		
		else:
			return self.utils.stringToDate(expiry, '%Y-%m-%dT%H:%M:%S.%fZ')
		
	def get_code_verifier(self):
		try:
			self.code_verifier = self.utils.get_cached_session_data('code_verifier')[0][0]
		except:
			self.get_interaction_handle()
		return self.code_verifier
	
	def get_interaction_handle(self):
		try:
			url = 'https://ids.mlb.com/oauth2/aus1m088yK07noBfh356/v1/interact'
			#url = 'http://localhost:56239/mlb/interact.php'
			headers = {
			  'accept': 'application/json',
			  'accept-language': 'en', 
			  'content-type': 'application/x-www-form-urlencoded', 
			  'x-okta-user-agent-extended': self.okta_user_agent_extended
			}
			self.code_verifier = secrets.token_hex(22)[:-1]
			self.utils.save_cached_session_data('code_verifier', self.code_verifier)
			data = urllib.parse.urlencode({
			  'client_id': self.client_id,
			  'scope': 'openid email',
			  'redirect_uri': 'https://www.mlb.com/login',
			  'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(self.code_verifier.encode('utf-8')).digest()).decode('utf-8').replace('=', ''),
			  'code_challenge_method': 'S256',
			  'state': secrets.token_urlsafe(),
			  'nonce': secrets.token_urlsafe()
			})
			r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
			return r.json()['interaction_handle']
		except Exception as e:
			self.utils.log('failed to get interaction_handle ' + str(e))
			self.utils.log(r.text)
			sys.exit(0)
			
	def get_introspect_stateHandle(self):
		try:
			introspect_stateHandle = self.utils.get_cached_session_data('introspect_stateHandle')[0][0]
		except:
			try:
				url = 'https://ids.mlb.com/idp/idx/introspect'
				#url = 'http://localhost:56239/mlb/introspect.php'
				headers = {
				  'accept': 'application/ion+json; okta-version=1.0.0',
				  'accept-language': 'en', 
				  'content-type': 'application/ion+json; okta-version=1.0.0', 
				  'x-okta-user-agent-extended': self.okta_user_agent_extended
				}
				data = json.dumps({
				  'interactionHandle': self.get_interaction_handle()
				})
				r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
				response_json = r.json()
				introspect_stateHandle = response_json['stateHandle']
				introspect_expiresAt = self.get_expiresAt(response_json['expiresAt'])
				self.utils.save_cached_session_data('introspect_stateHandle', introspect_stateHandle, introspect_expiresAt)
			except Exception as e:
				self.utils.log('failed to get introspect_stateHandle ' + str(e))
				self.utils.log(r.text)
				sys.exit(0)
		return introspect_stateHandle
		
	def get_identify_stateHandle(self):
		try:
			self.identify_stateHandle = self.utils.get_cached_session_data('identify_stateHandle')[0][0]
		except:
			self.get_identify()
		return self.identify_stateHandle
		
	def get_authenticators_password_id(self):
		try:
			self.authenticators_password_id = self.utils.get_cached_session_data('authenticators_password_id')[0][0]
		except:
			self.get_identify()
		return self.authenticators_password_id
			
	def get_identify(self):	
		try:
			url = 'https://ids.mlb.com/idp/idx/identify'
			#url = 'http://localhost:56239/mlb/identify.php'
			headers = {
			  'accept': 'application/ion+json; okta-version=1.0.0',
			  'accept-language': 'en', 
			  'content-type': 'application/json',  
			  'x-okta-user-agent-extended': self.okta_user_agent_extended
			}
			data = json.dumps({
			  'identifier': self.utils.get_setting('mlb_account_email'),
			  'rememberMe': True,
			  'stateHandle': self.get_introspect_stateHandle()
			})
			r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
			response_json = r.json()
			self.identify_stateHandle = response_json['stateHandle']
			identify_expiresAt = self.get_expiresAt(response_json['expiresAt'])
			self.utils.save_cached_session_data('identify_stateHandle', self.identify_stateHandle, identify_expiresAt)
			for x in response_json['authenticators']['value']:
				if x['type'] == 'password':
					self.authenticators_password_id = x['id']
					self.utils.save_cached_session_data('authenticators_password_id', self.authenticators_password_id)
					break
		except Exception as e:
			self.utils.log('failed to get identify_stateHandle ' + str(e))
			self.utils.log(r.text)
			sys.exit(0)
			
	def get_challenge(self):
		try:
			identify_stateHandle = self.get_identify_stateHandle()
			authenticators_password_id = self.get_authenticators_password_id()
			url = 'https://ids.mlb.com/idp/idx/challenge'
			#url = 'http://localhost:56239/mlb/challenge.php'
			headers = {
			  'accept': 'application/ion+json; okta-version=1.0.0',
			  'accept-language': 'en', 
			  'content-type': 'application/json', 
			  'x-okta-user-agent-extended': self.okta_user_agent_extended
			}
			data = json.dumps({
			  'authenticator': {
				'id': authenticators_password_id
			  },
			  'stateHandle': identify_stateHandle
			})
			r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
		except Exception as e:
			self.utils.log('failed to get challenge ' + str(e))
			self.utils.log(r.text)
			sys.exit(0)
	
	def get_okta_id(self):
		try:
			self.okta_id = self.utils.get_cached_session_data('okta_id')[0][0]
		except:
			self.get_answer()
		return self.okta_id
	
	def get_answer(self):
		try:
			self.get_challenge()
			url = 'https://ids.mlb.com/idp/idx/challenge/answer'
			#url = 'http://localhost:56239/mlb/answer.php'
			headers = {
			  'accept': 'application/ion+json; okta-version=1.0.0',
			  'accept-language': 'en', 
			  'content-type': 'application/json', 
			  'x-okta-user-agent-extended': self.okta_user_agent_extended
			}
			data = json.dumps({
			  'credentials': {
				'passcode': self.utils.get_setting('mlb_account_password')
			  },
			  'stateHandle': self.get_identify_stateHandle()
			})
			r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
			response_json = r.json()
			self.okta_id = response_json['user']['value']['id']
			self.utils.save_cached_session_data('okta_id', self.okta_id)
			for x in response_json['successWithInteractionCode']['value']:
				if x['name'] == 'interaction_code':
					return x['value']
		except Exception as e:
			self.utils.log('failed to get answer ' + str(e))
			self.utils.log(r.text)
			sys.exit(0)
			
	def get_token(self):	
		try:
			self.access_token = self.utils.get_cached_session_data('access_token')[0][0]
		except:
			try:
				interaction_code = self.get_answer()
				url = 'https://ids.mlb.com/oauth2/aus1m088yK07noBfh356/v1/token'
				#url = 'http://localhost:56239/mlb/token.php'
				headers = {
				  'accept': 'application/json',
				  'accept-language': 'en', 
				  'content-type': 'application/x-www-form-urlencoded', 
				  'x-okta-user-agent-extended': self.okta_user_agent_extended
				}
				data = urllib.parse.urlencode({
				  'client_id': self.client_id,
				  'redirect_uri': 'https://www.mlb.com/login',
				  'grant_type': 'interaction_code',
				  'code_verifier': self.get_code_verifier(),
				  'interaction_code': interaction_code
				})
				r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
				response_json = r.json()
				self.access_token = response_json['access_token']
				access_token_expiresAt = self.get_expiresAt(int(response_json['expires_in']))
				self.utils.save_cached_session_data('access_token', self.access_token, access_token_expiresAt)
			except Exception as e:
				self.utils.log('failed to get access_token ' + str(e))
				self.utils.log(r.text)
				sys.exit(0)
		return self.access_token
		
	def get_deviceId(self):
		try:
			self.deviceId = self.utils.get_cached_session_data('deviceId')[0][0]
		except:
			self.get_session()
		return self.deviceId
		
	def get_sessionId(self):
		try:
			self.sessionId = self.utils.get_cached_session_data('sessionId')[0][0]
		except:
			self.get_session()
		return self.sessionId
			
	def get_session(self):
		try:
			url = 'https://media-gateway.mlb.com/graphql'
			#url = 'http://localhost:56239/mlb/graphql.php'
			headers = {
			  'accept': 'application/json, text/plain, */*',
			  'accept-encoding': 'gzip, deflate, br',
			  'accept-language': 'en-US,en;q=0.5',
			  'authorization': 'Bearer ' + self.get_token(),
			  'connection': 'keep-alive',
			  'content-type': 'application/json', 
			  'x-client-name': 'WEB', 
			  'x-client-version': '7.8.1'
			}
			data = json.dumps({
			  "operationName": "initSession",
			  "query": "mutation initSession($device: InitSessionInput!, $clientType: ClientType!, $experience: ExperienceTypeInput) {\n    initSession(device: $device, clientType: $clientType, experience: $experience) {\n        deviceId\n        sessionId\n        entitlements {\n            code\n        }\n        location {\n            countryCode\n            regionName\n            zipCode\n            latitude\n            longitude\n        }\n        clientExperience\n        features\n    }\n  }",
			  "variables": {
				"device": {
				  "appVersion": "7.8.1",
				  "deviceFamily": "desktop",
				  "knownDeviceId": "",
				  "languagePreference": "ENGLISH",
				  "manufacturer": "Apple",
				  "model": "Macintosh",
				  "os": "macos",
				  "osVersion": "10.15"
				},
				"clientType": "WEB"
			  }
			})
			r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
			response_json = r.json()
			self.deviceId = response_json['data']['initSession']['deviceId']
			self.utils.save_cached_session_data('deviceId', self.deviceId)
			self.sessionId = response_json['data']['initSession']['sessionId']
			self.utils.save_cached_session_data('sessionId', self.sessionId)
		except Exception as e:
			self.utils.log('failed to get deviceId and sessionId ' + str(e))
			self.utils.log(r.text)
			sys.exit(0)
			
	def get_playback(self, mediaId):
		try:
			url, token = self.utils.get_cached_stream(mediaId)[0][0]
		except:
			try:
				deviceId = self.get_deviceId()
				sessionId = self.get_sessionId()
				url = 'https://media-gateway.mlb.com/graphql'
				#url = 'http://localhost:56239/mlb/graphql.php'
				headers = {
				  'accept': 'application/json, text/plain, */*',
				  'accept-encoding': 'gzip, deflate, br',
				  'accept-language': 'en-US,en;q=0.5',
				  'authorization': 'Bearer ' + self.get_token(),
				  'connection': 'keep-alive',
				  'content-type': 'application/json', 
				  'x-client-name': 'WEB', 
				  'x-client-version': '7.8.1'
				}
				data = json.dumps({
				  "operationName": "initPlaybackSession",
				  "query": "mutation initPlaybackSession(\n        $adCapabilities: [AdExperienceType]\n        $mediaId: String!\n        $deviceId: String!\n        $sessionId: String!\n        $quality: PlaybackQuality\n    ) {\n        initPlaybackSession(\n            adCapabilities: $adCapabilities\n            mediaId: $mediaId\n            deviceId: $deviceId\n            sessionId: $sessionId\n            quality: $quality\n        ) {\n            playbackSessionId\n            playback {\n                url\n                token\n                expiration\n                cdn\n            }\n            adScenarios {\n                adParamsObj\n                adScenarioType\n                adExperienceType\n            }\n            adExperience {\n                adExperienceTypes\n                adEngineIdentifiers {\n                    name\n                    value\n                }\n                adsEnabled\n            }\n            heartbeatInfo {\n                url\n                interval\n            }\n            trackingObj\n        }\n    }",
				  "variables": {
					"adCapabilities": [
					  "NONE"
					],
					"deviceId": deviceId,
					"mediaId": mediaId,
					"quality": "PLACEHOLDER",
					"sessionId": sessionId
				  }
				})
				r = self.utils.http_post(url, {**self.common_headers, **headers}, data, self.session)
				response_json = r.json()
				url = re.sub(r"[\/]([A-Za-z0-9_]+)[\/]", r"/", response_json['data']['initPlaybackSession']['playback']['url'], flags=re.M)
				token = response_json['data']['initPlaybackSession']['playback']['token']
				expiration = response_json['data']['initPlaybackSession']['playback']['expiration']
				self.utils.save_cached_stream(mediaId, url, token, expiration)
			except Exception as e:
				self.utils.log('failed to get playback ' + str(e))
				self.utils.log(r.text)
				sys.exit(0)
		return url, token
			
	def proxy_file(self, parsed_qs):
		token = None
		skip = None
		if 'mediaId' in parsed_qs:
			mediaId = parsed_qs['mediaId'][0]
			url, token = self.get_playback(mediaId)
		elif 'url' in parsed_qs:
			url = parsed_qs['url'][0]
			if 'token' in parsed_qs:
				token = parsed_qs['token'][0]
		if 'skip' in parsed_qs:
			skip = parsed_qs['skip'][0]
				
		try:
			headers = {
			  'accept': '*/*',
			  'accept-encoding': 'gzip, deflate, br',
			  'accept-language': 'en-US,en;q=0.5',
			  'connection': 'keep-alive'
			}
			if token is not None:
				headers['x-cdn-token'] = token
			r = self.utils.http_get(url, {**self.common_headers, **headers}, self.session)
			content_type = r.headers['content-type']
			# paths inside HLS manifests need to be adjusted
			if content_type in self.hls_content_types:
				# first set all relative URLs to their absolute paths
				absolute_url_prefix = os.path.dirname(url)
				content = re.sub(r"^(?!#|http|\Z).*", r""+absolute_url_prefix+r"/\g<0>", r.text, flags=re.M)
				# do the same for URI parameters
				absolute_url_prefix = ',URI="' + absolute_url_prefix
				content = re.sub(r",URI=\"([^(?:http)][^\"]+)", r""+absolute_url_prefix+r"/\g<1>", content, flags=re.M)
				# now add our local proxy prefix
				proxied_url_prefix = 'file?'
				if token is not None:
					proxied_url_prefix += 'token=' + token + '&'
				if skip is not None:
					proxied_url_prefix += 'skip=' + skip + '&'
				proxied_url_prefix += 'url='
				content = re.sub(r"^(?!#|\Z).*", r""+proxied_url_prefix+r"\g<0>", content, flags=re.M)
				# and the same for URI parameters
				proxied_url_prefix = ',URI="' + proxied_url_prefix
				content = re.sub(r",URI=\"((?:http)([^\"]+))", r""+proxied_url_prefix+r"\g<1>", content, flags=re.M)
				content_encoding = 'utf8'
				
				# remove subtitles and extraneous lines for Kodi Inputstream Adaptive compatibility
				content = re.sub(r"(?:#EXT-X-MEDIA:TYPE=SUBTITLES[\S]+\n)", r"", content, flags=re.M)
				content = re.sub(r"(?:#EXT-X-I-FRAME-STREAM-INF:[\S]+\n)", r"", content, flags=re.M)
				if skip == 'commercials':
					content = re.sub(r"^(#EXT-OATCLS-SCTE35[\S\s]+?#EXT-X-CUE-IN)", r"#EXT-X-DISCONTINUITY", content, flags=re.M)
				else:
					content = re.sub(r"^(?:#EXT-OATCLS-SCTE35:[\S]+\n)", r"", content, flags=re.M)
					content = re.sub(r"^(?:#EXT-X-CUE-[\S]+\n)", r"", content, flags=re.M)
			else:
				content = r.content
				content_encoding = None
			return content, content_type, content_encoding
		except Exception as e:
			self.utils.log('failed to get proxy file ' + str(e))
			self.utils.log(r.text)
			sys.exit(0)
			
	def filter_games(self, games):
	    filtered_games = []
	    for game in games['results']:
	    	try:
	    		filtered_feeds = []
	    		for feed_key in self.feed_keys:
	    			for feed in game[feed_key]:
	    				if feed['entitled'] == True and feed['mediaState'] != 'MEDIA_OFF' and ('blackedOut' not in feed or feed['blackedOut'] == False):
	    					if 'mediaFeedType' in feed:
	    						label = feed['mediaFeedType'].capitalize() + ' TV'
	    						icon = 'video.svg'
	    						type = 'video'
	    					else:
	    						label = feed['type'].capitalize()
	    						if feed['language'] == 'es':
	    							label += ' Spanish'
	    						label += ' Radio'
	    						icon = 'audio.svg'
	    						type = 'audio'
	    					filtered_feed = {
	    					  'title': feed['callLetters'] + ' (' + label + ')',
	    					  'icon': icon,
	    					  'mediaId': feed['mediaId'],
	    					  'type': type,
	    					  'state': feed['mediaState']
	    					}
	    					filtered_feeds.append(filtered_feed)
	    		if len(filtered_feeds) == 0:
	    			filtered_feed = { 'title': 'No feeds currently available to you' }
	    			filtered_feeds.append(filtered_feed)
	    			if self.utils.get_utc_now() < self.utils.stringToDate(game['gameData']['gameDate'], "%Y-%m-%dT%H:%M:%S%z"):
	    				filtered_feed = { 'title': 'Game has not started yet' }
	    				filtered_feeds.append(filtered_feed)
	    			elif self.utils.get_setting('mlb_account_email') is not None or self.utils.get_setting('mlb_account_password') is not None:
	    				filtered_feed = { 'title': 'May require a subscription' }
	    				filtered_feeds.append(filtered_feed)
	    			else:
	    				filtered_feed = { 'title': 'You may need to log in' }
	    				filtered_feeds.append(filtered_feed)
	    		away_probable = game['gameData']['away']['probablePitcherLastName'] if game['gameData']['away']['probablePitcherLastName'] != '' else 'TBD'
	    		home_probable = game['gameData']['home']['probablePitcherLastName'] if game['gameData']['home']['probablePitcherLastName'] != '' else 'TBD'
	    		filtered_game = {
				  'time': self.utils.get_display_time(self.utils.stringToDate(game['gameData']['gameDate'], "%Y-%m-%dT%H:%M:%S%z", True)),
				  'title': game['gameData']['away']['teamName'] + ' at ' + game['gameData']['home']['teamName'],
				  'subtitle': away_probable + ' vs. ' + home_probable,
				  'icon': 'image?away_teamId={0}&home_teamId={1}&width=72'.format(str(game['gameData']['away']['teamId']), str(game['gameData']['home']['teamId'])),
				  'thumb': 'image?away_teamId={0}&home_teamId={1}&width=750'.format(str(game['gameData']['away']['teamId']), str(game['gameData']['home']['teamId'])),
				  'fanart': 'image?venueId=%s' % str(game['gameData']['venueId']),
				  'feeds' : filtered_feeds
				}
	    		if game['gameData']['doubleHeader'] == 'Y':
	    			filtered_game['title'] += ' Game ' + game['gameData']['gameNumber']
	    		filtered_games.append(filtered_game)
	    	except Exception as e:
	    		self.utils.log('failed to filter game ' + str(e))
	    		self.utils.log(json.dumps(game))
	    return filtered_games
			
	def get_navigation(self, d):
		# includes replace function to work around some Python versions not supporting "%-d" for day of month without leading zero
		try:
			navigation = {
			  'current':
			  {
				'title': self.utils.dateToString(self.utils.stringToDate(d, '%Y-%m-%d'), '%A %B %d, %Y').replace(' 0', ' '),
				'date': str(self.utils.stringToDate(d, '%Y-%m-%d'))
			  },
			  'previous':
			  {
				'title': '<< Previous Day',
				'date': self.utils.dateToString(self.utils.add_time(self.utils.stringToDate(d, '%Y-%m-%d'), days=-1), '%Y-%m-%d')
			  },
			  'next':
			  {
				'title': 'Next Day >>',
				'date': self.utils.dateToString(self.utils.add_time(self.utils.stringToDate(d, '%Y-%m-%d'), days=1), '%Y-%m-%d')
			  }
			}
			return navigation
		except Exception as e:
			self.utils.log('failed to get navigation ' + str(e))        
        
	def get_games(self, date_string='today', days=0):
		url = 'https://mastapi.mobile.mlbinfra.com/api/epg/v3/search?exp=MLB'
		#url = 'http://localhost:56239/mlb/games.json?'
		if days > 0:
			d = self.utils.process_date_string('today')
			url += '&startDate=' + d + '&endDate=' + str(self.utils.add_time(self.utils.stringToDate(d, '%Y-%m-%d'), days=days))
		else:
			d = self.utils.process_date_string(date_string)
			url += '&date=' + d
		try:
			data = json.loads(self.utils.get_cached_games(d)[0][0])
		except:
			try:
				headers = {
				  'accept': '*/*',
				  'accept-language': 'en-US,en;q=0.9',
				  'content-type': 'application/json'
				}
				if self.utils.get_setting('mlb_account_email') is not None and self.utils.get_setting('mlb_account_password') is not None:
					access_token = self.get_token()
					okta_id = self.get_okta_id()
					if access_token is not None and okta_id is not None:
						headers['authorization'] = 'Bearer ' + access_token
						headers['x-okta-id'] = okta_id
				r = self.utils.http_get(url, {**self.common_headers, **headers}, self.session)
				data = {
				  'navigation': self.get_navigation(d),
				  'games': self.filter_games(r.json())
				}
				data = json.dumps(data)
				expires_in = 60
				if d != self.utils.process_date_string('today'):
					expires_in = 3600
				expiration = self.get_expiresAt(expires_in)
				self.utils.save_cached_games(d, json.dumps(data), expiration)
			except Exception as e:
				self.utils.log('failed to get games ' + str(e))
				self.utils.log(r.text)
				sys.exit(0)
		return data
		
	def get_image_url(self, parsed_qs):
		url = 'icon.png'
		if 'venueId' in parsed_qs:
			url = 'http://cd-images.mlbstatic.com/stadium-backgrounds/color/light-theme/1920x1080/%s.png' % str(parsed_qs['venueId'][0])
		elif 'away_teamId' in parsed_qs:
			if int(parsed_qs['away_teamId'][0]) in range(108,158) and int(parsed_qs['home_teamId'][0]) in range(108,158):
				if 'width' in parsed_qs:
					width = parsed_qs['width'][0]
				else:
					width = 750
				url = 'https://img.mlbstatic.com/mlb-photos/image/upload/ar_167:215,c_crop/fl_relative,l_team:{1}:fill:spot.png,w_1.0,h_1,x_0.5,y_0,fl_no_overflow,e_distort:100p:0:200p:0:200p:100p:0:100p/fl_relative,l_team:{0}:logo:spot:current,w_0.38,x_-0.25,y_-0.16/fl_relative,l_team:{1}:logo:spot:current,w_0.38,x_0.25,y_0.16/w_{2}/team/{0}/fill/spot.png'.format(str(parsed_qs['away_teamId'][0]), str(parsed_qs['home_teamId'][0]), str(width))
				
		return url