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
    if route == 'recent-movies':
        recent_movies(handle)
        return
    if route == 'movies':
        movies(handle)
        return
    if route == 'recent-series':
        recent_series(handle)
        return
    if route == 'channel-favorites':
        channel_favorites(handle)
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
    query = dialog.input('Buscar canais do Brazuca e Pluto TV')
    if not query or not normalize(query):
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    results, failures = [], []
    sources = (('Brazuca', '#todoscanais'), ('Pluto TV', '#plutotv_16'))
    for source, path in sources:
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
                   'params': {'directory': brazuca(21, path), 'media': 'video',
                              'properties': ['thumbnail', 'fanart']}}
        try:
            response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
            result = response.get('result', {})
            if 'error' in response or not isinstance(result, dict) or not isinstance(result.get('files', []), list):
                raise ValueError('Channel directory unavailable')
            results.extend(matches(result.get('files', []), query))
        except Exception:
            failures.append(source)
    if failures:
        dialog.notification('SMARTED-TV', 'Fontes indisponíveis: ' + ', '.join(failures),
                            xbmcgui.NOTIFICATION_WARNING, 7000)
    if len(failures) == len(sources):
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    if not results:
        dialog.notification('SMARTED-TV', 'Nenhum canal encontrado nas fontes disponíveis.', xbmcgui.NOTIFICATION_INFO, 5000)
    xbmcplugin.setContent(handle, 'videos')
    for result in results:
        item = xbmcgui.ListItem(label=result['label'])
        item.setArt({'thumb': result['thumb'], 'fanart': result['fanart']})
        item.setProperty('IsPlayable', 'true' if result['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=result['folder'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def recent_series(handle):
    import xbmc
    from search import SOURCES, recent_series as fetch_recent_series

    try:
        results, failed = fetch_recent_series()
    except Exception:
        xbmc.log('SMARTED-TV: lançamentos de séries indisponíveis', xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    if failed:
        xbmc.log('SMARTED-TV: fontes de séries indisponíveis: ' + ', '.join(failed), xbmc.LOGWARNING)
    xbmcplugin.setContent(handle, 'tvshows')
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
    for result in results:
        item = xbmcgui.ListItem(label='[%s] %s' % (result['category'], result['title']))
        item.setArt({'thumb': result['thumb'], 'poster': result['thumb'], 'fanart': result['fanart']})
        info = item.getVideoInfoTag()
        info.setTitle(result['title'])
        info.setPlot(result['description'])
        info.setYear(int(result['release_date'][:4]))
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=True)
    xbmcplugin.endOfDirectory(handle, succeeded=len(failed) < len(SOURCES), cacheToDisc=False)


def channel_favorites(handle):
    import xbmc
    import xbmcvfs
    from catalogue import directory
    from channel_search import channel_items
    from favorites import has_channel_favorites
    from routes import brazuca

    path = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.BrazucaPlay.Matrix/favorites.dat')
    if not has_channel_favorites(path):
        xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)
        return
    try:
        results = channel_items(directory(xbmc.executeJSONRPC, brazuca(15, 'canais')))
    except Exception:
        xbmc.log('SMARTED-TV: favoritos de canais indisponíveis', xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    xbmcplugin.setContent(handle, 'videos')
    for result in results:
        item = xbmcgui.ListItem(label=result['label'])
        item.setArt({'thumb': result['thumb'], 'fanart': result['fanart']})
        item.setProperty('IsPlayable', 'true' if result['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=result['folder'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def movies(handle):
    import xbmc
    from catalogue import movie_overview

    try:
        results, failed = movie_overview(xbmc.executeJSONRPC)
    except Exception:
        xbmcgui.Dialog().notification('SMARTED-TV', 'Menu de filmes indisponível.',
                                      xbmcgui.NOTIFICATION_WARNING, 7000)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    if failed:
        xbmcgui.Dialog().notification('SMARTED-TV', 'Abertura direta disponível para: ' + ', '.join(failed),
                                      xbmcgui.NOTIFICATION_WARNING, 7000)
    _add_movies(handle, results)


def _add_movies(handle, results):
    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
    for result in results:
        item = xbmcgui.ListItem(label=result['label'])
        item.setArt({'thumb': result['thumbnail'], 'poster': result['thumbnail'],
                     'fanart': result['fanart']})
        info = item.getVideoInfoTag()
        info.setTitle(result['title'])
        info.setPlot(result['plot'])
        if result['year'] > 0:
            info.setYear(result['year'])
        item.setProperty('IsPlayable', 'true' if result['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=result['folder'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def recent_movies(handle):
    import xbmc
    from catalogue import recent_movies as fetch_recent_movies

    try:
        results = fetch_recent_movies(xbmc.executeJSONRPC)
    except Exception:
        # A widget must not interrupt the Home with a dialog or leak URLs.
        xbmc.log('SMARTED-TV: lançamentos do Brazuca indisponíveis', xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    _add_movies(handle, results)


if __name__ == '__main__':
    main()
