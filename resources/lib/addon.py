import os
import sys
from urllib.parse import urlencode, parse_qsl

import xbmc
import xbmcgui
import xbmcplugin
from xbmcaddon import Addon
from xbmcvfs import translatePath

import resources.lib.utils as utils

import datetime
import time

import json

LOCAL_WEBSERVER = 'http://localhost:' + str(utils.LOCAL_WEBSERVER_PORT) + utils.LOCAL_WEBSERVER_BASE

DIALOG = xbmcgui.Dialog()

URL = sys.argv[0]
HANDLE = int(sys.argv[1])

def get_url(**kwargs):
    return '{}?{}'.format(URL, urlencode(kwargs)) 


def get_data(link):
    return utils.http_get(LOCAL_WEBSERVER + link).json()  


def login(link):
    mlb_account_email = DIALOG.input(utils.LOCAL_STRING(30018), type=xbmcgui.INPUT_ALPHANUM)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
    if mlb_account_email:
        mlb_account_password = DIALOG.input(utils.LOCAL_STRING(30019), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        if mlb_account_password:
            data = utils.encode_post_data({
              'mlb_account_email': mlb_account_email,
              'mlb_account_password': mlb_account_password
            })
            r = utils.http_post(LOCAL_WEBSERVER + link, data=data)
        url = get_url(action='menu')
        xbmc.executebuiltin("Container.Update({0},replace)".format(url))


def logout(link):
    utils.http_get(LOCAL_WEBSERVER + link)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
    url = get_url(action='menu')
    xbmc.executebuiltin("Container.Update({0},replace)".format(url))


def select_date(link):
    d = DIALOG.numeric(type=1, heading=utils.LOCAL_STRING(30020), defaultt=datetime.datetime.now().strftime("%d/%m/%Y")).replace(' ', '')
    if d:
        # workaround for embedded strptime bug https://bugs.python.org/issue27400
        formatted_date = utils.stringToDate(d, "%d/%m/%Y").strftime("%Y-%m-%d")
        link += formatted_date
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        url = get_url(action='listing', link=link)
        xbmc.executebuiltin("Container.Update({0},replace)".format(url))


def list_menu():
    xbmcplugin.setPluginCategory(HANDLE, 'Sports')
    xbmcplugin.setContent(HANDLE, 'videos')
    menu = get_data('menu.json')
    for item in menu:
        list_item = xbmcgui.ListItem(label=item['title'])
        list_item.setArt({'icon': LOCAL_WEBSERVER + 'icon.png', 'fanart': LOCAL_WEBSERVER + 'fanart.jpg'})
        info_tag = list_item.getVideoInfoTag()
        info_tag.setMediaType('video')
        info_tag.setTitle(item['title'])
        action = 'listing'
        if 'link' not in item:
            action = 'select'
        url = get_url(action=action, link=item['data'])
        is_folder = True
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
    
    # add login/logout option
    title = utils.LOCAL_STRING(30014)
    action = 'logout'
    if utils.get_setting('mlb_account_email') is None or utils.get_setting('mlb_account_password') is None:
        title = utils.LOCAL_STRING(30013)
        action = 'login'
    list_item = xbmcgui.ListItem(label=title)
    url = get_url(action=action, link=action)
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
        
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def list_games(link):
    data = get_data(link)

    # navigation
    link_base = 'games.json?date='
    
    list_item = xbmcgui.ListItem(label=data['navigation']['previous']['title'])
    list_item.setArt({'icon': LOCAL_WEBSERVER + 'icon.png', 'fanart': LOCAL_WEBSERVER + 'fanart.jpg'})
    url = get_url(action='listing', link=link_base + data['navigation']['previous']['date'])
    is_folder = True
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)

    list_item = xbmcgui.ListItem(label='[B][COLOR=FFFFFF66]' + data['navigation']['current']['title'] + '[/COLOR][/B]')
    list_item.setArt({'icon': LOCAL_WEBSERVER + 'icon.png', 'fanart': LOCAL_WEBSERVER + 'fanart.jpg'})
    url = get_url(action='listing', link=link_base + data['navigation']['current']['date'])
    is_folder = True
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)

    games = data['games']
    xbmcplugin.setContent(HANDLE, 'videos')
    for game in games:
        title = game['time'] + ' ' + game['title'] + ' [COLOR=FF666666](' + game['subtitle'] + ')[/COLOR]'
        list_item = xbmcgui.ListItem(label=title)
        list_item.setArt({'icon': LOCAL_WEBSERVER + game['icon'], 'thumb': LOCAL_WEBSERVER + game['thumb'], 'fanart': LOCAL_WEBSERVER + game['fanart']})
        info_tag = list_item.getVideoInfoTag()
        info_tag.setTitle(game['title'])
        info_tag.setMediaType('video')
        info_tag.setPlot(game['subtitle'])
        list_item.setInfo('music', {'artist':game['subtitle']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='feeds', feeds_string=json.dumps(game['feeds']))
        is_folder = False
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)

    # more navigation
    list_item = xbmcgui.ListItem(label=data['navigation']['next']['title'])
    list_item.setArt({'icon': LOCAL_WEBSERVER + 'icon.png', 'fanart': LOCAL_WEBSERVER + 'fanart.jpg'})
    url = get_url(action='listing', link=link_base + data['navigation']['next']['date'])
    is_folder = True
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def list_feeds(feeds_string):
    feeds = json.loads(feeds_string)
    feed_index = DIALOG.select(utils.LOCAL_STRING(30015), [feed['title'] for feed in feeds])
    if feed_index > -1:
        if 'mediaId' in feeds[feed_index]:
            #list_start(feeds[feed_index]['mediaId'])
            play_media(feeds[feed_index]['mediaId'], 'none', 'none', feeds[feed_index]['icon'])


def list_start(mediaId):
    feeds = get_data('start.json')
    feed_index = DIALOG.select(utils.LOCAL_STRING(30016), [feed['title'] for feed in feeds])
    if feed_index > -1:
        list_skip(mediaId, feeds[feed_index]['value'])


def list_skip(mediaId, start):
    feeds = get_data('skip.json')
    feed_index = DIALOG.select(utils.LOCAL_STRING(30017), [feed['title'] for feed in feeds])
    if feed_index > -1:
        play_media(mediaId, start, feeds[feed_index]['value'])


def play_media(mediaId, start, skip, icon):
    path = LOCAL_WEBSERVER + 'stream.m3u8?mediaId=' + mediaId + '&start=' + start + '&skip=' + skip
    play_item = xbmcgui.ListItem(path=path, offscreen=True)
    play_item.setMimeType('application/vnd.apple.mpegurl')
    play_item.setContentLookup(False)
    if icon == 'video.svg':
        play_item.setProperty('inputstream', 'inputstream.adaptive')
    xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if not params or params['action'] == 'menu':
        list_menu()
    elif params['action'] == 'login':
        login(params['link'])
    elif params['action'] == 'logout':
        logout(params['link'])
    elif params['action'] == 'select':
        select_date(params['link'])
    elif params['action'] == 'listing':
        list_games(params['link'])
    elif params['action'] == 'feeds':
        list_feeds(params['feeds_string'])
    elif params['action'] == 'play':
        play_video(params['video'])
    else:
        raise ValueError(f'Invalid paramstring: {paramstring}!')