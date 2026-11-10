"""Kodi directory bridge; does not collect or fabricate catalogue data."""
import sys
from urllib.parse import parse_qs

import xbmcgui
import xbmcplugin

from routes import items


def main():
    handle = int(sys.argv[1])
    params = parse_qs(sys.argv[2].lstrip('?'), keep_blank_values=True)
    route = params.get('route', ['root'])[0]
    if route == 'search-series':
        search_series(handle)
        return
    if route == 'search-channels':
        search_channels(handle)
        return
    entries = items(route)
    if not entries:
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    for label, url in entries:
        item = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(handle, url, item, isFolder=True)
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def search_series(handle):
    from search import SOURCES, normalize, search

    dialog = xbmcgui.Dialog()
    query = dialog.input('Buscar séries, novelas, animes, doramas e desenhos')
    if not query or not normalize(query):
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    results, failed = search(query)
    if failed:
        dialog.notification('SMARTED-TV', 'Fontes indisponíveis: ' + ', '.join(failed),
                            xbmcgui.NOTIFICATION_WARNING, 8000)
    if not results and len(failed) < len(SOURCES):
        dialog.notification('SMARTED-TV', 'Nenhum resultado nas fontes disponíveis.',
                            xbmcgui.NOTIFICATION_INFO, 5000)
    xbmcplugin.setContent(handle, 'tvshows')
    for result in results:
        label = '[%s] %s' % (result['category'], result['title'])
        item = xbmcgui.ListItem(label=label)
        item.setArt({'thumb': result['thumb'], 'poster': result['thumb'], 'fanart': result['fanart']})
        info = item.getVideoInfoTag()
        info.setTitle(result['title'])
        info.setPlot(result['description'])
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=True)
    xbmcplugin.endOfDirectory(handle, succeeded=len(failed) < len(SOURCES), cacheToDisc=False)


def search_channels(handle):
    import json
    import xbmc
    from channel_search import matches
    from routes import brazuca
    from search import normalize

    dialog = xbmcgui.Dialog()
    query = dialog.input('Buscar canais do Brazuca (exceto Pluto TV)')
    if not query or not normalize(query):
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
               'params': {'directory': brazuca(21, '#todoscanais'), 'media': 'video',
                          'properties': ['thumbnail', 'fanart']}}
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        if 'error' in response or not isinstance(response.get('result', {}).get('files'), list):
            raise ValueError('Channel directory unavailable')
        results = matches(response['result']['files'], query)
    except Exception:
        dialog.notification('SMARTED-TV', 'Não foi possível consultar os canais do Brazuca.',
                            xbmcgui.NOTIFICATION_WARNING, 7000)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    if not results:
        dialog.notification('SMARTED-TV', 'Nenhum canal encontrado.', xbmcgui.NOTIFICATION_INFO, 5000)
    xbmcplugin.setContent(handle, 'videos')
    for result in results:
        item = xbmcgui.ListItem(label=result['label'])
        item.setArt({'thumb': result['thumb'], 'fanart': result['fanart']})
        item.setProperty('IsPlayable', 'true' if result['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=result['folder'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


if __name__ == '__main__':
    main()
