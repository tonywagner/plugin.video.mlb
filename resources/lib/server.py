# coding=UTF-8
import urllib
import threading
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import json
from pathlib import Path
import os
import mimetypes

import resources.lib.utils as utils

from resources.lib.account import Account

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
	    return

    def do_HEAD(self):
        self.send_error(404)

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="MLB"')
        self.end_headers()

    def respond(self, content, content_type="text/html", content_encoding='utf8'):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        try:
        	self.send_header("Content-Length", str(len(content.encode())))
        except:
        	self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.write(content, content_encoding)

    def write(self, content, content_encoding='utf8'):
        try:
            if content_encoding is not None:
            	self.wfile.write(content.encode())
            else:
            	self.wfile.write(content)
        except:
            pass

    def redirect(self, url):
        self.send_response(307)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Location", url)
        self.end_headers()
        
    def get_requested_host(self):
        return 'http://' + self.headers['Host']

    def do_GET(self):
        parsed_url = urlparse(self.path)
        parsed_qs = parse_qs(parsed_url.query)
            
        # Require authentication
        if self.server.is_protected() and self.headers.get('Authorization') == None and ('content_protect' not in parsed_qs or parsed_qs['content_protect'][0] != utils.LOCAL_WEBSERVER_CONTENT_PROTECTION_STRING):
            self.do_AUTHHEAD()
            self.write('Not Authorized')

        elif self.server.is_protected() is False or self.headers.get('Authorization') == ('Basic ' + self.server.get_auth_key()) or ('content_protect' in parsed_qs and parsed_qs['content_protect'][0] == utils.LOCAL_WEBSERVER_CONTENT_PROTECTION_STRING):
        	data_file = Path(os.path.join(utils.DATA_DIRECTORY, os.path.basename(parsed_url.path)))
        	media_file = Path(os.path.join(utils.MEDIA_DIRECTORY, os.path.basename(parsed_url.path)))
        	
        	if parsed_url.path == (utils.LOCAL_WEBSERVER_BASE):
        		self.redirect(utils.LOCAL_WEBSERVER_BASE + "index.html")
        		
        	elif data_file.is_file():
        		body = data_file.read_text()
        		content_type = mimetypes.guess_type(data_file)[0]
        		self.respond(body, content_type=content_type)
        		
        	elif media_file.is_file():
        		content = media_file.read_bytes()
        		content_type = mimetypes.guess_type(media_file)[0]
        		self.respond(content, content_type=content_type, content_encoding=None)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + 'version'):
        		self.respond(utils.VERSION)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + 'status'):
        		self.respond(utils.get_status())
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + 'games.json'):
        		if 'date' in parsed_qs:
        			games_json = self.server.account.get_games(parsed_qs['date'][0])
        		else:
        			games_json = self.server.account.get_games()
        		self.respond(games_json)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + 'teams.json'):
        		teams_json = self.server.account.get_teams()
        		self.respond(teams_json)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + 'channels.m3u'):
        		content = self.server.account.get_channels_m3u(self.get_requested_host() + utils.LOCAL_WEBSERVER_BASE)
        		self.respond(content)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + 'guide.xml'):
        		content = self.server.account.get_guide_xml(self.get_requested_host() + utils.LOCAL_WEBSERVER_BASE)
        		self.respond(content)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + 'stream.m3u8') or parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + "file"):
        		content, content_type, content_encoding = self.server.account.proxy_file(parsed_qs)
        		self.respond(content, content_type, content_encoding)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + "image"):
        		image_url = self.server.account.get_image_url(parsed_qs)
        		self.redirect(image_url)
        		
        	elif parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + "logout"):
        		self.server.account.logout()
        		self.redirect(utils.LOCAL_WEBSERVER_BASE)
        		
        	else:
        		self.redirect(utils.LOCAL_WEBSERVER_BASE)

        else:
            self.do_AUTHHEAD()
            self.write('Invalid credentials')
            
    def do_POST(self):
    	if self.server.is_protected() is False or self.headers.get('Authorization') == ('Basic ' + self.server.get_auth_key()):
            parsed_url = urlparse(self.path)
            
            if parsed_url.path == (utils.LOCAL_WEBSERVER_BASE + "login"):
            	post_data = urllib.parse.parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))
            	self.server.account.logout()
            	self.server.account.login(post_data['mlb_account_email'][0], post_data['mlb_account_password'][0])
            	self.respond('<script>window.location.href = "' + utils.LOCAL_WEBSERVER_BASE + '"</script>')

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    key = ''
    local_server_protected = False
    content_protection_string = None
    
    account = None

    def __init__(self):
        self.account = Account(utils)
        
        super().__init__(('0.0.0.0', utils.LOCAL_WEBSERVER_PORT), RequestHandler)
        
        if utils.LOCAL_WEBSERVER_USERNAME is not None and utils.LOCAL_WEBSERVER_PASSWORD is not None:
            self.local_server_protected = True
            self.set_auth(utils.LOCAL_WEBSERVER_USERNAME, utils.LOCAL_WEBSERVER_PASSWORD)

    def set_auth(self, username, password):
    	self.local_server_protected = True
    	self.key = base64.b64encode(bytes('%s:%s' % (username, password), 'utf-8')).decode('ascii')

    def get_auth_key(self):
        return str(self.key)

    def is_protected(self):
        return self.local_server_protected

class Server(ThreadedHTTPServer):
	def __init__(self):
		
		server = ThreadedHTTPServer()
		server.allow_reuse_address = True
		httpd_thread = threading.Thread(target=server.serve_forever)
		httpd_thread.start()
		
		if utils.KODI:
			import xbmc
			
			xbmc.Monitor().waitForAbort()
			server.shutdown()
			server.server_close()
			server.socket.close()
			httpd_thread.join()