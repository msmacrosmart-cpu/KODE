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


if __name__ == '__main__':
    main()
