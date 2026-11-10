"""Executed only by an isolated emulator keymap; no real catalog is queried."""
import json
import xbmc


def directory(path):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
               'params': {'directory': path, 'media': 'video'}}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        raise RuntimeError('directory request failed')
    return response.get('result', {}).get('files', [])


try:
    # Kodi disables a new, manually copied profile add-on by default. The real
    # backup's Addons database records Brazuka enabled; this synthetic profile
    # has no database, so enable ONLY the disposable stub for this test.
    enable = {'jsonrpc': '2.0', 'id': 2, 'method': 'Addons.SetAddonEnabled',
              'params': {'addonid': 'plugin.video.BrazucaPlay.Matrix', 'enabled': True}}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(enable)))
    if response.get('result') != 'OK':
        raise RuntimeError('could not enable the synthetic stub')
    entries = directory('plugin://plugin.video.smarted/?route=series')
    targets = [item['file'] for item in entries if item.get('label') == 'Séries']
    if len(entries) != 6 or len(targets) != 1:
        raise RuntimeError('unexpected bridge directory')
    children = directory(targets[0])
    if not any(item.get('label') == 'Teste isolado' for item in children):
        raise RuntimeError('fixture did not receive the bridge URL')
    xbmc.log('SMARTED_TEST_BRIDGE_JSONRPC_OK', xbmc.LOGWARNING)
except Exception as exc:
    xbmc.log('SMARTED_TEST_BRIDGE_JSONRPC_FAILED: ' + str(exc), xbmc.LOGERROR)
