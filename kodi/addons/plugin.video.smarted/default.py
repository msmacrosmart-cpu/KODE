"""Kodi directory bridge; does not collect or fabricate catalogue data."""
import sys
import os
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
    if route == 'sync-nav':
        sync_navigation(handle, force=params.get('force', ['0'])[0] == '1')
        return
    if route == 'abrir-nav':
        open_navigation(handle, params)
        return
    if route == 'navegacao':
        navigation_window(handle)
        return
    if route in ('carrossel', 'carousel'):
        carousel(handle, params)
        return
    if route.startswith('favoritos-'):
        favorites_window(handle, route.split('-', 1)[1])
        return
    entries = items(route)
    if not entries:
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    for label, url in entries:
        item = xbmcgui.ListItem(label=label)
        category = {'TV ao vivo': 'tv', 'Filmes': 'movies', 'Séries': 'series',
                    'Doramas': 'doramas', 'Animes': 'animes', 'Novelas': 'novelas',
                    'Desenhos': 'desenhos'}.get(label)
        if category:
            art = os.path.join(os.path.dirname(__file__), 'resources', 'categories', category + '.png')
            item.setArt({'poster': art, 'thumb': art, 'icon': art})
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


def _widget_cached(name, fetch, successful):
    # Kodi invokes each widget in an independent Python interpreter. Persist
    # only real successful results and coalesce duplicate same-day requests.
    try:
        import xbmcvfs
        from daily_cache import cached
        directory = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.smarted/widget-cache')
    except (ImportError, OSError):
        return fetch()
    return cached(directory, name, fetch, successful)


def _movie_cache_ok(value):
    required = ('label', 'url', 'title', 'folder', 'playable', 'thumbnail', 'fanart', 'plot', 'year')
    return isinstance(value, list) and 0 < len(value) <= 10 and all(
        isinstance(item, dict) and all(key in item for key in required) for item in value)


def _series_cache_ok(value):
    required = ('category', 'title', 'thumb', 'fanart', 'description', 'url', 'release_date')
    return isinstance(value, (list, tuple)) and len(value) == 2 and not value[1] and isinstance(value[0], list) and 0 < len(value[0]) <= 10 and all(
        isinstance(item, dict) and all(key in item for key in required) for item in value[0])


def recent_series(handle):
    import xbmc
    from search import SOURCES, recent_series as fetch_recent_series

    try:
        results, failed = _widget_cached('recent-series', fetch_recent_series, _series_cache_ok)
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


FAVORITES_FILE = 'special://profile/addon_data/plugin.video.BrazucaPlay.Matrix/favorites.dat'


def favorites_window(handle, category):
    """Lista os favoritos reais do Brazuca Play (mesma fonte da aba Favoritos).

    Usado pelas linhas da Home: le apenas o favorites.dat do addon e devolve os
    itens com a URL nativa dele, para o OK tocar o canal/filme ou abrir a pasta.
    """
    import xbmc
    import xbmcvfs
    from favorites import favorite_items

    path = xbmcvfs.translatePath(FAVORITES_FILE)
    try:
        results = favorite_items(path, category)
    except Exception:
        xbmc.log('SMARTED-TV: favoritos indisponiveis (%s)' % category, xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    if not results:
        xbmc.log('SMARTED-TV: sem favoritos em %s' % category, xbmc.LOGINFO)
        xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)
        return
    xbmcplugin.setContent(handle, 'movies')
    for result in results:
        item = xbmcgui.ListItem(label=result['label'])
        item.setArt({'thumb': result['thumb'], 'poster': result['poster'] or result['thumb'],
                     'icon': result['thumb'] or 'DefaultFolder.png',
                     'fanart': result['fanart']})
        info = item.getVideoInfoTag()
        info.setTitle(result['label'])
        info.setPlot(result['plot'])
        info.setMediaType('video')
        item.setProperty('IsPlayable', 'true' if result['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=result['folder'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


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
        arte = result['thumbnail']
        # o addon manda capa (poster do TMDB) e, para filmes, nenhum fanart:
        # usar a propria capa como fundo mantem o HERO com a imagem do filme
        fundo = result.get('fanart') or arte
        item.setArt({chave: valor for chave, valor in
                     (('thumb', arte), ('poster', arte), ('fanart', fundo)) if valor})
        info = item.getVideoInfoTag()
        info.setTitle(result['title'])
        info.setPlot(result['plot'])
        if result['year'] > 0:
            info.setYear(result['year'])
        if result.get('genre'):
            info.setGenres([nome.strip() for nome in result['genre'].split(',') if nome.strip()])
        if result.get('premiered'):
            info.setPremiered(result['premiered'])
        if result.get('rating'):
            info.setRating(result['rating'])
        if result.get('duration'):
            info.setDuration(result['duration'])
        if not result['folder']:
            info.setMediaType('video')
        item.setProperty('IsPlayable', 'true' if result['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, result['url'], item, isFolder=result['folder'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def recent_movies(handle):
    import xbmc
    from catalogue import recent_movies as fetch_recent_movies

    try:
        results = _widget_cached('recent-movies', lambda: fetch_recent_movies(xbmc.executeJSONRPC), _movie_cache_ok)
    except Exception:
        # A widget must not interrupt the Home with a dialog or leak URLs.
        xbmc.log('SMARTED-TV: lançamentos do Brazuca indisponíveis', xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    xbmc.log('SMARTED-TV: hero com %d filmes (ficha completa=%d)'
             % (len(results), sum(1 for item in results
                                  if item.get('plot') and item.get('genre'))),
             getattr(xbmc, 'LOGINFO', 20))
    _add_movies(handle, results)


CARROSSEL_CONTENT = {'series': 'tvshows', 'novelas': 'tvshows', 'animes': 'tvshows',
                     'doramas': 'tvshows', 'desenhos': 'tvshows'}


def _carrossel_ok(value):
    return (isinstance(value, dict) and isinstance(value.get('items'), list)
            and all(isinstance(entry, dict) and entry.get('url') and entry.get('label')
                    for entry in value['items']))


def _add_carrossel(handle, items, alvo):
    xbmcplugin.setContent(handle, CARROSSEL_CONTENT.get(alvo, 'videos'))
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
    for entry in items:
        item = xbmcgui.ListItem(label=entry['label'])
        art = {'thumb': entry.get('thumbnail') or '', 'poster': entry.get('thumbnail') or '',
               'icon': entry.get('thumbnail') or 'DefaultFolder.png',
               'fanart': entry.get('fanart') or ''}
        item.setArt({key: val for key, val in art.items() if val})
        info = item.getVideoInfoTag()
        info.setTitle(entry.get('title') or entry['label'])
        if entry.get('plot'):
            info.setPlot(entry['plot'])
        if entry.get('year'):
            info.setYear(int(entry['year']))
        if not entry['folder']:
            info.setMediaType('video')
        item.setProperty('IsPlayable', 'true' if entry['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, entry['url'], item, isFolder=entry['folder'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def carousel(handle, params):
    """Linha da Home com conteúdo real do addon (não a pasta de menu).

    ``alvo`` é canais, filmes, series, novelas, animes, doramas ou desenhos. A
    árvore do próprio addon é percorrida até o nível que entrega mídia (canais e
    filmes reproduzem; séries entregam as capas das séries). Se a rede falhar,
    a linha mostra os favoritos da categoria em vez de ficar vazia.
    """
    import xbmc
    import xbmcvfs
    from catalogue import carousel as fetch_carousel
    from favorites import favorite_items

    alvo = params.get('alvo', ['filmes'])[0]

    def fetch():
        items, origem, found = fetch_carousel(xbmc.executeJSONRPC, alvo)
        return {'items': items, 'origem': origem, 'found': found}

    try:
        value = _widget_cached('carrossel-' + alvo, fetch, _carrossel_ok)
    except Exception:
        xbmc.log('SMARTED-TV: carrossel %s indisponivel' % alvo, xbmc.LOGWARNING)
        value = {'items': [], 'origem': '', 'found': False}
    items = value.get('items') or []
    if items:
        xbmc.log('SMARTED-TV: carrossel %s com %d itens (%s)' % (alvo, len(items), value.get('origem')),
                 xbmc.LOGINFO)
        _add_carrossel(handle, items, alvo)
        return
    # rede indisponível: usa os favoritos reais da categoria (nunca linha vazia)
    try:
        path = xbmcvfs.translatePath(FAVORITES_FILE)
        favoritos = favorite_items(path, alvo)
    except Exception:
        favoritos = []
    if favoritos:
        xbmc.log('SMARTED-TV: carrossel %s em modo favoritos' % alvo, xbmc.LOGINFO)
        _add_carrossel(handle, [{'url': item['url'], 'label': item['label'],
                                 'title': item['label'], 'folder': item['folder'],
                                 'playable': item['playable'], 'thumbnail': item['thumb'],
                                 'fanart': item['fanart'], 'plot': item['plot'], 'year': 0}
                                for item in favoritos], alvo)
        return
    xbmc.log('SMARTED-TV: carrossel %s sem dados' % alvo, xbmc.LOGWARNING)
    xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)


NAV_CACHE = 'special://profile/addon_data/plugin.video.smarted/navegacao.json'


def _nav_paths():
    import xbmcvfs
    return (xbmcvfs.translatePath(FAVORITES_FILE),
            xbmcvfs.translatePath(NAV_CACHE))


def sync_navigation(handle, force=False):
    """Descobre as pastas reais do addon e publica a barra superior.

    No boot (``force=True``) consulta o menu raiz do Brazuca Play e guarda o
    resultado do dia. Abertura da Home reaproveita o cache para nao travar a
    tela; se o cache nao existir, descobre na hora.
    """
    import os
    import xbmc
    from navigation import apply_skin_strings, build, load_cache, save_cache

    favoritos, cache = _nav_paths()
    entradas = None if force else load_cache(cache)
    origem = 'cache'
    if not entradas:
        entradas, origem = build(favoritos, xbmc.executeJSONRPC, xbmc.log)
        if entradas and origem != 'pastas':
            pasta = os.path.dirname(cache)
            if pasta and not os.path.isdir(pasta):
                try:
                    os.makedirs(pasta)
                except OSError:
                    pass
            save_cache(cache, entradas, origem)
        elif origem == 'pastas':
            # sem menu e sem favoritos (rede fora): mantem o ultimo bom
            antigas = load_cache(cache, aceitar_antigo=True)
            if antigas:
                entradas, origem = antigas, 'cache'
    apply_skin_strings(entradas, xbmc.executebuiltin)
    xbmc.log('SMARTED-TV: navegacao com %d opcoes (%s)' % (len(entradas), origem),
             getattr(xbmc, 'LOGINFO', 20))
    for indice, entrada in enumerate(entradas[:4]):
        xbmc.log('SMARTED-TV: barra %d = %s' % (indice + 1, entrada['label']),
                 getattr(xbmc, 'LOGINFO', 20))
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def navigation_window(handle):
    """Lista as opcoes da navegacao (mesma fonte da barra) para conferencia."""
    import xbmc
    from navigation import load_cache

    favoritos, cache = _nav_paths()
    entradas = load_cache(cache, aceitar_antigo=True)
    if not entradas:
        from navigation import build
        entradas, _ = build(favoritos, xbmc.executeJSONRPC, xbmc.log)
    for entrada in entradas:
        item = xbmcgui.ListItem(label=entrada['label'])
        item.setProperty('IsPlayable', 'true' if entrada['playable'] else 'false')
        xbmcplugin.addDirectoryItem(handle, entrada['url'], item, isFolder=not entrada['playable'])
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def open_navigation(handle, params):
    """Abre o destino real do favorito escolhido na barra superior."""
    import xbmc
    from navigation import build, load_cache, open_command, resolve

    try:
        indice = int(params.get('indice', ['0'])[0])
    except (TypeError, ValueError):
        indice = 0
    favoritos, cache = _nav_paths()
    entradas = load_cache(cache, aceitar_antigo=True)
    if not entradas:
        entradas, _ = build(favoritos, xbmc.executeJSONRPC, xbmc.log)
    entrada = resolve(entradas, indice)
    if not entrada:
        xbmc.log('SMARTED-TV: navegacao sem opcao no slot %d' % indice, xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    comando = open_command(entrada)
    xbmc.log('SMARTED-TV: navegacao abrindo %s' % entrada['label'], xbmc.LOGINFO)
    xbmc.executebuiltin(comando)
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


if __name__ == '__main__':
    main()
