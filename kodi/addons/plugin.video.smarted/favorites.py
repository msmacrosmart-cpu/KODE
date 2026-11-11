"""Read Brazuca's own favorites file without ever modifying it.

Source of truth: ``userdata/addon_data/plugin.video.BrazucaPlay.Matrix/favorites.dat``
— the very same file the add-on writes when you press "Adicionar aos Favoritos".
SMARTED-TV only *reads* it, so Home never keeps a second, independent list.

The add-on stores::

    {"canais": [ [nome, url, mode, subtitle, iconimage, fanart, description], ... ], ...}

``url`` and ``subtitle`` come base64(b16(...)) encoded. Playable entries use
mode 11/16; anything else is a folder that the add-on itself resolves.
"""
import base64
import json
from pathlib import Path
from urllib.parse import urlencode

MAX_BYTES = 8 * 1024 * 1024
PLUGIN = 'plugin://plugin.video.BrazucaPlay.Matrix/'
CATEGORIES = ('canais', 'filmes', 'series', 'novelas', 'animes', 'desenhos', 'doramas', 'unknown')
PLAYABLE_MODES = (11, 16)
FOLDER_ICON = 'DefaultFolder.png'


def _decode(value):
    """Undo the add-on's base64(b16(...)) encoding, tolerating plain values."""
    if not isinstance(value, str) or not value:
        return ''
    try:
        return base64.b64decode(base64.b16decode(value.encode('ascii'))).decode('utf-8')
    except Exception:
        return value


def load(filename):
    """Return ``{categoria: [entradas decodificadas]}``; never raises, never writes."""
    try:
        path = Path(filename)
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            return {}
        with path.open('r', encoding='utf-8') as stream:
            data = json.load(stream)
    except (OSError, ValueError, TypeError):
        return {}
    if isinstance(data, list):
        data = {'unknown': data}
    if not isinstance(data, dict):
        return {}
    decoded = {}
    for category, entries in data.items():
        if not isinstance(category, str) or not isinstance(entries, list):
            continue
        clean = []
        for entry in entries:
            if not isinstance(entry, (list, tuple)) or len(entry) < 3:
                continue
            label = entry[0] if isinstance(entry[0], str) else str(entry[0])
            clean.append({
                'label': label,
                'url': _decode(entry[1]),
                'mode': _as_mode(entry[2]),
                'subtitle': _decode(entry[3]) if len(entry) > 3 else '',
                'thumb': entry[4] if len(entry) > 4 and isinstance(entry[4], str) else '',
                'fanart': entry[5] if len(entry) > 5 and isinstance(entry[5], str) else '',
                'plot': entry[6] if len(entry) > 6 and isinstance(entry[6], str) else '',
            })
        if clean:
            decoded[category] = clean
    return decoded


def _as_mode(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def has_favorites(filename):
    return any(load(filename).values())


def has_channel_favorites(filename):
    """Avoid opening the native favorites menu when it would notify on empty.

    Legacy lists, missing and malformed files are left untouched. The native
    add-on is still responsible for resolving and displaying valid favorites.
    """
    try:
        path = Path(filename)
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            return False
        with path.open('r', encoding='utf-8') as stream:
            data = json.load(stream)
        return isinstance(data, dict) and isinstance(data.get('canais'), list) and bool(data['canais'])
    except (OSError, ValueError, TypeError):
        return False


def plugin_url(entry):
    """Rebuild the exact URL the add-on would use for this favorite."""
    mode = entry['mode']
    icon = entry['thumb'] or FOLDER_ICON
    fanart = entry['fanart'] or icon
    if mode in PLAYABLE_MODES:
        if mode > 1:
            return PLUGIN + '?' + urlencode({
                'url': entry['url'], 'mode': mode, 'name': entry['label'],
                'iconimage': icon, 'description': entry['plot']})
        return entry['url']
    return PLUGIN + '?' + urlencode({
        'url': entry['url'], 'mode': mode, 'name': entry['label'],
        'iconimage': icon, 'fanart': fanart, 'description': entry['plot']})


def favorite_items(filename, category):
    """Kodi-ready dicts for one category of the add-on favorites."""
    items = []
    for entry in load(filename).get(category, []):
        url = plugin_url(entry)
        if not url:
            continue
        playable = entry['mode'] in PLAYABLE_MODES
        if not url.startswith('plugin://') and not playable:
            continue
        items.append({
            'label': entry['label'],
            'url': url,
            'folder': not playable,
            'playable': playable,
            'thumb': entry['thumb'],
            'poster': entry['thumb'],
            'fanart': entry['fanart'],
            'plot': entry['plot'],
        })
    return items


def categories(filename):
    """Categories that actually have favorites, in the add-on's own menu order."""
    data = load(filename)
    return [name for name in CATEGORIES if data.get(name)]
