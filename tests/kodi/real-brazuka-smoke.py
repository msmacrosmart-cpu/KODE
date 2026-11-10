"""Disposable emulator test against the public Brazuca 2.1.4 package.

No private profile, credentials, user favorites or playback are involved.
"""
import json
import os
import sys
import xbmc

sys.path.insert(0, os.path.dirname(__file__))
import routes


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
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_MENUS_OK', xbmc.LOGWARNING)
except Exception as exc:
    xbmc.log('SMARTED_TEST_PUBLIC_BRAZUCA_MENUS_FAILED: ' + str(exc), xbmc.LOGERROR)
