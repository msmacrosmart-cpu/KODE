"""Disposable emulator test against the public Brazuca 2.1.4 package.

No private profile, credentials, user favorites or playback are involved.
"""
import json
import os
import sys
from urllib.parse import parse_qs, unquote_plus, urlsplit
import xbmc

sys.path.insert(0, os.path.dirname(__file__))
import routes
import search
import channel_search


def rpc(method, params):
    response = json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    if 'error' in response:
        raise RuntimeError(method + ': ' + str(response['error'].get('message', 'error')))
    return response.get('result')


def directory(path):
    return rpc('Files.GetDirectory', {'directory': path, 'media': 'video'}).get('files', [])


try:
    # New manually copied addons are disabled by Kodi. Only the public test
    # copies in this disposable profile are enabled; no user profile is touched.
    for addon in ('script.module.six', 'script.module.kodi-six', 'script.module.certifi',
                  'script.module.chardet', 'script.module.idna', 'script.module.urllib3',
                  'script.module.requests', 'script.module.simplejson', 'plugin.video.BrazucaPlay.Matrix'):
        if rpc('Addons.SetAddonEnabled', {'addonid': addon, 'enabled': True}) != 'OK':
            raise RuntimeError('could not enable test addon ' + addon)
    categories = directory('plugin://plugin.video.smarted/?route=series')
    series = [item['file'] for item in categories if item.get('label') == 'Séries']
    if len(series) != 1 or len(directory(series[0])) < 2:
        raise RuntimeError('real series menu unavailable')
    if len(directory(routes.brazuca(27, '#filmes_menu'))) < 4:
        raise RuntimeError('real movies menu unavailable')
    movies = directory('plugin://plugin.video.smarted/?route=movies')
    if len(movies) < 10 or 'pesquis' not in search.normalize(movies[0].get('label', '')) or 'lancamentos' not in search.normalize(movies[1].get('label', '')):
        raise RuntimeError('movie overview did not include search, releases and genres')
    xbmc.log('SMARTED_TEST_MOVIE_OVERVIEW_OK', xbmc.LOGWARNING)
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_MENUS_OK', xbmc.LOGWARNING)
    # Use an actual public-series index entry, then ask the real add-on to
    # expand its resolver options. No title, URL or user data is logged.
    real_index = search.download(search.SOURCES[0][1])
    candidates = search.parse_feed('Séries', real_index, 'amor')
    for candidate in candidates:
        args = parse_qs(urlsplit(candidate['url']).query)
        target = unquote_plus(args.get('url', [''])[0])
        if args.get('mode') == ['6'] and target.startswith('#series_list='):
            if directory(candidate['url']):
                break
    else:
        raise RuntimeError('real series search result did not expand')
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_SEARCH_RESULT_OK', xbmc.LOGWARNING)
    tv_menu = directory('plugin://plugin.video.smarted/?route=tv')
    tv_options = [item['file'] for item in tv_menu if item.get('label') == 'Opções de TV']
    if len(tv_options) != 1 or not directory(tv_options[0]):
        raise RuntimeError('real TV options unavailable')
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_TV_OK', xbmc.LOGWARNING)
    channel_dir = directory(routes.brazuca(21, '#todoscanais'))
    if not channel_search.matches(channel_dir, 'tv'):
        raise RuntimeError('real channel search found no TV matches')
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_CHANNEL_SEARCH_OK', xbmc.LOGWARNING)
    featured = directory('plugin://plugin.video.smarted/?route=recent-movies')
    if not featured:
        raise RuntimeError('real Brazuca launch widget is empty')
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_LAUNCH_WIDGET_OK', xbmc.LOGWARNING)
    favorite_channels = directory('plugin://plugin.video.smarted/?route=channel-favorites')
    if not any('Canal sintético' in item.get('label', '') for item in favorite_channels):
        raise RuntimeError('synthetic favorite not returned by public Brazuca')
    xbmc.log('SMARTED_TEST_CHANNEL_FAVORITE_OK', xbmc.LOGWARNING)
    # Separately verify the official Kodi VideoPlayer with a generated local
    # clip. This does NOT validate a Brazuca resolver, server, or user stream.
    if rpc('Player.Open', {'item': {'file': 'special://xbmc/media/smoke-video.mp4'}}) != 'OK':
        raise RuntimeError('local Kodi player did not open')
    active = []
    for _ in range(40):
        active = rpc('Player.GetActivePlayers', {})
        video = next((p for p in active if p.get('type') == 'video'), None)
        if video:
            state = rpc('Player.GetProperties', {'playerid': video['playerid'], 'properties': ['time']})
            if state.get('time', {}).get('seconds', 0) >= 1:
                break
        xbmc.sleep(500)
    else:
        raise RuntimeError('local Kodi player did not advance')
    # Open the actual NovaTV OSD and operate its native play/pause control.
    xbmc.executebuiltin('ActivateWindow(VideoOSD)')
    for _ in range(30):
        if xbmc.getCondVisibility('Window.IsVisible(VideoOSD)'):
            break
        xbmc.sleep(200)
    else:
        raise RuntimeError('VideoOSD did not open')
    xbmc.executebuiltin('SendClick(12901,602)')
    for _ in range(30):
        state = rpc('Player.GetProperties', {'playerid': video['playerid'], 'properties': ['speed']})
        if state.get('speed') == 0:
            break
        xbmc.sleep(200)
    else:
        raise RuntimeError('OSD pause did not pause the local video')
    xbmc.executebuiltin('SendClick(12901,602)')
    for _ in range(30):
        state = rpc('Player.GetProperties', {'playerid': video['playerid'], 'properties': ['speed']})
        if state.get('speed') == 1:
            break
        xbmc.sleep(200)
    else:
        raise RuntimeError('OSD resume did not resume the local video')
    xbmc.log('SMARTED_TEST_NOVATV_OSD_PAUSE_OK', xbmc.LOGWARNING)
    rpc('Player.Stop', {'playerid': video['playerid']})
    xbmc.log('SMARTED_TEST_LOCAL_KODI_PLAYER_OK', xbmc.LOGWARNING)
except Exception as exc:
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_MENUS_FAILED: ' + str(exc), xbmc.LOGERROR)
