"""Filter the real Brazuca channel directory, without storing channel data.

Brazuca's '#todoscanais' route merges its normal channel sources and, when
configured, its pro source. Pluto has a separate directory, queried separately.
No streams or channel names are shipped with SMARTED-TV.
"""
from urllib.parse import parse_qs, unquote_plus, urlsplit

from search import normalize

ADDON_ID = 'plugin.video.BrazucaPlay.Matrix'


def channel_items(files):
    """Keep only genuine channel destinations returned by the add-on."""
    matched = []
    for item in files:
        if not isinstance(item, dict):
            continue
        label = item.get('label', '')
        path = item.get('file', '')
        kind = item.get('filetype', '')
        if not isinstance(label, str) or not isinstance(path, str) or kind not in ('file', 'directory'):
            continue
        try:
            parsed = urlsplit(path)
        except ValueError:
            continue
        if parsed.scheme != 'plugin' or parsed.netloc != ADDON_ID:
            continue
        params = parse_qs(parsed.query, keep_blank_values=True)
        if unquote_plus(params.get('url', [''])[0]) == 'here':
            continue
        mode = params.get('mode', [''])[0]
        matched.append({'label': label, 'url': path, 'folder': kind == 'directory',
                        'playable': kind == 'file' and mode != '11',
                        'thumb': item.get('thumbnail') if isinstance(item.get('thumbnail'), str) else '',
                        'fanart': item.get('fanart') if isinstance(item.get('fanart'), str) else ''})
    return matched


def matches(files, query):
    needle = normalize(query)
    if not needle:
        return []
    return [item for item in channel_items(files) if needle in normalize(item['label'])]
