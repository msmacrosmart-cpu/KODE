"""Unified search over Brazuca Play 2.1.4's public category indexes.

No catalogue is bundled. Playback and resolving are delegated to Brazuca.
The optional private/pro indexes in Brazuca are not yet supported.
"""
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from html import unescape
import re
import unicodedata
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from routes import BRAZUCA

# These are the same public feeds used by pesquisar_conteudo in Brazuca 2.1.4.
SOURCES = (
    ('Séries', 'https://gist.githubusercontent.com/skyrisk/16070347f20c87c72540f9f805b57a66/raw/SeriesBase'),
    ('Novelas', 'https://gist.githubusercontent.com/skyrisk/07f1f4cd1b203cbf2efec959c4e8645a/raw/novelas.xml'),
    ('Animes', 'https://gist.githubusercontent.com/skyrisk/16070347f20c87c72540f9f805b57a66/raw/AnimesBase'),
    ('Doramas', 'https://gist.githubusercontent.com/skyrisk/16070347f20c87c72540f9f805b57a66/raw/DoramasBase'),
    ('Desenhos', 'https://gist.githubusercontent.com/skyrisk/16070347f20c87c72540f9f805b57a66/raw/DesenhosBase'),
)
LIMIT_BYTES = 24 * 1024 * 1024
CHANNEL = re.compile(r'<channel>(.*?)</channel>', re.IGNORECASE | re.DOTALL)
TAGS = re.compile(r'\[/?(?:B|I|COLOR(?: [^\]]+)?|UPPERCASE|LOWERCASE|CAPITALIZE)\]', re.I)
MODES = (
    ('#series_list=', 6), ('serie3=', 26), ('wvmob=', 30),
    ('#novelas_list=', 6), ('novelas=', 25), ('novelas2=', 25),
    ('#animes_list=', 6), ('animes2=', 31), ('animes3=', 22), ('animes4=', 31),
    ('#doramas_list=', 6), ('doramas_resolver1=', 31),
    ('resolver1_tvshows=', 31), ('resolver2_tvshows=', 31),
    ('resolver3_tvshows=', 31), ('resolver4_tvshows=', 31),
    ('resolver5_tvshows=', 31), ('onedrive=', 31),
)


def normalize(value):
    plain = TAGS.sub('', unescape(value or ''))
    plain = unicodedata.normalize('NFKD', plain).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\W', '', plain).lower()


def field(block, name):
    match = re.search(r'<%s>(.*?)</%s>' % (name, name), block, re.I | re.S)
    return unescape(match.group(1).strip()) if match else ''


def select_mode(url):
    for prefix, mode in MODES:
        if url.startswith(prefix):
            if prefix == 'animes4=':
                url = 'resolver1_tvshows=' + url[len(prefix):]
            elif prefix == 'wvmob=':
                try:
                    url = 'wvmob=' + base64.b64decode(url[len(prefix):], validate=True).decode('utf-8')
                except (ValueError, UnicodeError):
                    pass
            return mode, url
    return None, url


def result_url(mode, url, name, thumb, fanart, description):
    # Brazuca 2.1.4 uses parse_qsl *then* unquote_plus. Encode user/feed fields
    # twice so +, percent escapes and literal ampersands survive both passes.
    values = {'url': url, 'name': name, 'iconimage': thumb, 'fanart': fanart, 'description': description}
    values = {key: quote_plus(value) for key, value in values.items()}
    values['mode'] = str(mode)
    return BRAZUCA + '?' + urlencode(values)


def _parse_channel(category, block):
    title = field(block, 'name')
    if not title:
        return None
    mode, url = select_mode(field(block, 'externallink'))
    if mode is None:
        return None  # Never guess an unknown resolver.
    thumb = field(block, 'thumbnail')
    try:
        decoded = base64.b64decode(thumb, validate=True).decode('utf-8')
        if decoded.startswith(('http://', 'https://')):
            thumb = decoded
    except (ValueError, UnicodeError):
        pass
    fanart, description = field(block, 'fanart'), field(block, 'info')
    return {'category': category, 'title': TAGS.sub('', title).strip(), 'thumb': thumb,
            'fanart': fanart, 'description': description,
            'url': result_url(mode, url, title, thumb, fanart, description)}


def parse_feed(category, raw, query):
    needle = normalize(query)
    if not needle:
        return []
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    matches = []
    for channel in CHANNEL.finditer(raw):
        block = channel.group(1)
        if needle not in normalize(field(block, 'name')):
            continue
        item = _parse_channel(category, block)
        if item:
            matches.append(item)
    return matches


def parse_recent_feed(category, raw, today=None, limit=None):
    """Use explicit first-air dates, never feed position as invented recency."""
    today = today or date.today()
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    results = []
    for channel in CHANNEL.finditer(raw):
        block = channel.group(1)
        try:
            release = datetime.strptime(field(block, 'tmdb_date'), '%d/%m/%Y').date()
        except ValueError:
            continue
        if release > today:
            continue
        if limit is not None:
            if limit <= 0:
                return []
            # Keep at most limit distinct candidates. Decode all art/plot only
            # when the item could enter the small top list.
            title = field(block, 'name')
            key = normalize(title)
            mode, _ = select_mode(field(block, 'externallink'))
            if not key or mode is None:
                continue
            previous = next((x for x in results if normalize(x['title']) == key), None)
            iso = release.isoformat()
            if previous and previous['release_date'] >= iso:
                continue
            if len(results) >= limit and previous is None and iso <= results[-1]['release_date']:
                continue
        item = _parse_channel(category, block)
        if item:
            item['release_date'] = release.isoformat()
            if limit is not None and previous:
                results.remove(previous)
            results.append(item)
            if limit is not None:
                results.sort(key=lambda x: x['release_date'], reverse=True)
                del results[limit:]
    return results


def recent_series(loader=None, limit=10, today=None):
    """Return date-ordered releases and unavailable sources; data is public only."""
    loader = loader or download
    by_source, failed = {}, set()
    # Avoid retaining several multi-megabyte feed payloads at once on TVs.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(loader, url): (index, name)
                   for index, (name, url) in enumerate(SOURCES)}
        for future in as_completed(futures):
            index, name = futures.pop(future)
            try:
                payload = future.result()
                text = payload.decode('utf-8', errors='replace') if isinstance(payload, bytes) else payload
                if not CHANNEL.search(text):
                    raise ValueError('Unexpected category index')
                by_source[index] = parse_recent_feed(name, text, today=today, limit=limit)
            except Exception:
                failed.add(index)
    combined = [item for index in range(len(SOURCES)) for item in by_source.get(index, [])]
    combined.sort(key=lambda item: item['release_date'], reverse=True)
    unique, seen = [], set()
    for item in combined:
        key = normalize(item['title'])
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique, [name for index, (name, _) in enumerate(SOURCES) if index in failed]


def download(url):
    request = Request(url, headers={'User-Agent': 'SMARTED-TV Kodi search/1.0', 'Accept': 'text/plain, application/xml'})
    with urlopen(request, timeout=15) as response:
        payload = response.read(LIMIT_BYTES + 1)
    if len(payload) > LIMIT_BYTES:
        raise ValueError('Category index exceeds size limit')
    return payload


def search(query, loader=download):
    """Return (results, failed category names); failures never become fake data."""
    if not normalize(query):
        return [], []
    results_by_source, failed = {}, set()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(loader, url): (index, name)
                   for index, (name, url) in enumerate(SOURCES)}
        for future in as_completed(futures):
            index, name = futures.pop(future)
            try:
                payload = future.result()
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8', errors='replace')
                if not CHANNEL.search(payload):
                    raise ValueError('Unexpected category index')
                results_by_source[index] = parse_feed(name, payload, query)
            except Exception:
                failed.add(index)
    results = [item for index in range(len(SOURCES)) for item in results_by_source.get(index, [])]
    return results, [name for index, (name, _) in enumerate(SOURCES) if index in failed]
