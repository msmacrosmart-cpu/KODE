"""Read real Brazuca directories without inventing catalogue data or streams."""
import json
from urllib.parse import parse_qs, urlsplit

from routes import brazuca
from search import TAGS, normalize

ADDON = 'plugin.video.BrazucaPlay.Matrix'


def _brazuca_url(value):
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        return url.scheme == 'plugin' and url.netloc == ADDON
    except ValueError:
        return False


def directory(rpc, url):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
               'params': {'directory': url, 'media': 'video',
                          'properties': ['title', 'plot', 'year', 'thumbnail', 'fanart', 'art']}}
    response = json.loads(rpc(json.dumps(request)))
    if not isinstance(response, dict) or 'error' in response or not isinstance(response.get('result'), dict):
        raise ValueError('Brazuca directory unavailable')
    files = response['result'].get('files', [])
    if not isinstance(files, list):
        raise ValueError('Unexpected directory response')
    return files


def _entry(item):
    if not isinstance(item, dict) or not _brazuca_url(item.get('file')):
        return None
    label, kind = item.get('label'), item.get('filetype')
    if not isinstance(label, str) or kind not in ('directory', 'file'):
        return None
    params = parse_qs(urlsplit(item['file']).query, keep_blank_values=True)
    if params.get('url', [''])[0] == 'here':
        return None
    title = item.get('title') or TAGS.sub('', label).strip()
    if not isinstance(title, str) or not title:
        return None
    mode = params.get('mode', [''])[0]
    return {'url': item['file'], 'label': label, 'title': title,
            'folder': kind == 'directory', 'playable': kind == 'file' and mode != '11',
            'thumbnail': item.get('thumbnail') if isinstance(item.get('thumbnail'), str) else '',
            'fanart': item.get('fanart') if isinstance(item.get('fanart'), str) else '',
            'plot': item.get('plot') if isinstance(item.get('plot'), str) else '',
            'year': item.get('year') if isinstance(item.get('year'), int) else 0}


def movie_overview(rpc):
    """Flatten native genres and the first alphabetical page into one menu.

    Native search, releases, alphabetical pagination and other options remain
    available. Failures keep their original folder rather than losing access.
    """
    menu = [_entry(item) for item in directory(rpc, brazuca(27, '#filmes_menu'))]
    menu = [item for item in menu if item]
    if not menu:
        raise ValueError('Movie menu unavailable')
    def find(*names):
        return next((item for item in menu if normalize(item['label']) in names), None)
    search = find('pesquiseporfilmes', 'pesquisarfilmes')
    launches = find('categorialancamentos', 'lancamentos')
    genres = find('categoriageneros', 'generos')
    alphabet = find('categoriaordemalfabetica', 'ordemalfabetica')
    used = [item for item in (search, launches, genres, alphabet) if item]
    result = [item for item in (search, launches) if item]
    failed = []
    for label, folder in (('gêneros', genres), ('ordem alfabética', alphabet)):
        if not folder:
            continue
        try:
            entries = [_entry(item) for item in directory(rpc, folder['url'])]
            entries = [item for item in entries if item]
            if not entries:
                raise ValueError('Empty source')
            result.extend(entries)
            # Keep the original alphabetical route for further pages.
            if folder is alphabet:
                result.append(folder)
        except Exception:
            result.append(folder)
            failed.append(label)
    result.extend(item for item in menu if item not in used)
    # Kodi's Files.GetDirectory does not export add-on-specific context menus.
    # Keep an explicit route to the unwrapped menu for native favorite actions.
    native = _entry({'label': 'Abrir menu original do Brazuca',
                     'file': brazuca(27, '#filmes_menu'), 'filetype': 'directory'})
    if native:
        result.append(native)
    return result, failed


def recent_movies(rpc, limit=10):
    """Use the add-on's own Lançamentos folder, preserving its destinations.

    This is the source's ordering, not a verified global popularity ranking.
    An absent or unavailable folder returns an empty list rather than fake data.
    """
    menu = directory(rpc, brazuca(27, '#filmes_menu'))
    folder = next((entry.get('file') for entry in menu if isinstance(entry, dict)
                   and entry.get('filetype') == 'directory'
                   and isinstance(entry.get('label'), str)
                   and normalize(entry['label']) in ('lancamentos', 'categorialancamentos')
                   and _brazuca_url(entry.get('file'))), None)
    if not folder:
        return []
    result = []
    for item in directory(rpc, folder):
        entry = _entry(item)
        if entry:
            result.append(entry)
        if len(result) >= limit:
            break
    return result
