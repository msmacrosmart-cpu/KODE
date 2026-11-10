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
        if not isinstance(item, dict) or not _brazuca_url(item.get('file')):
            continue
        label = item.get('label')
        kind = item.get('filetype')
        if not isinstance(label, str) or kind not in ('directory', 'file'):
            continue
        params = parse_qs(urlsplit(item['file']).query, keep_blank_values=True)
        # 'here' is a decorative header, not a playable movie.
        if params.get('url', [''])[0] == 'here':
            continue
        mode = params.get('mode', [''])[0]
        title = item.get('title') or TAGS.sub('', label).strip()
        if not isinstance(title, str) or not title:
            continue
        result.append({'url': item['file'], 'label': label, 'title': title,
                       'folder': kind == 'directory',
                       'playable': kind == 'file' and mode != '11',
                       'thumbnail': item.get('thumbnail') if isinstance(item.get('thumbnail'), str) else '',
                       'fanart': item.get('fanart') if isinstance(item.get('fanart'), str) else '',
                       'plot': item.get('plot') if isinstance(item.get('plot'), str) else '',
                       'year': item.get('year') if isinstance(item.get('year'), int) else 0})
        if len(result) >= limit:
            break
    return result
