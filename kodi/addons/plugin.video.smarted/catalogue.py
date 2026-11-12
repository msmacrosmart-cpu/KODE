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
                          'properties': ['title', 'plot', 'year', 'thumbnail', 'fanart', 'art',
                                         'genre', 'rating', 'votes', 'premiered', 'dateadded',
                                         'sorttitle', 'duration']}}
    response = json.loads(rpc(json.dumps(request)))
    if not isinstance(response, dict) or 'error' in response or not isinstance(response.get('result'), dict):
        raise ValueError('Brazuca directory unavailable')
    files = response['result'].get('files', [])
    if not isinstance(files, list):
        raise ValueError('Unexpected directory response')
    return files


def _votos(valor):
    """Votos como numero (o addon manda '1,200', '12k', '1.2 mi' ou inteiro)."""
    try:
        if isinstance(valor, int):
            return valor
        if not isinstance(valor, str):
            return 0
        texto = valor.strip().lower().replace(' ', '')
        multiplicador = 1
        if texto.endswith('mil'):
            multiplicador, texto = 1000, texto[:-3]
        elif texto.endswith('mi'):
            multiplicador, texto = 1000000, texto[:-2]
        elif texto.endswith('k'):
            multiplicador, texto = 1000, texto[:-1]
        texto = texto.replace('.', '').replace(',', '')
        return int(float(texto)) * multiplicador if texto else 0
    except (TypeError, ValueError):
        return 0


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
            'year': item.get('year') if isinstance(item.get('year'), int) else 0,
            'genre': _genre(item.get('genre')),
            'rating': _rating(item.get('rating')),
            'premiered': _premiered(item),
            'votes': _votos(item.get('votes')),
            'dateadded': item.get('dateadded') if isinstance(item.get('dateadded'), str) else '',
            'duration': item.get('duration') if isinstance(item.get('duration'), int) else 0}


def _log_hero(result, bruto):
    """Diagnostico curto: quantos itens de Lancamentos vem com ficha."""
    try:
        import xbmc

        def tem(chave):
            return sum(1 for item in bruto if isinstance(item, dict) and item.get(chave))

        nivel = getattr(xbmc, 'LOGINFO', 20)
        chaves = sorted(bruto[0].keys()) if bruto and isinstance(bruto[0], dict) else []
        xbmc.log('SMARTED-TV: lancamentos bruto=%d plot=%d genre=%d dateadded=%d '
                 'premiered=%d rating=%d year=%d chaves=%s'
                 % (len(bruto), tem('plot'), tem('genre'), tem('dateadded'),
                    tem('premiered'), tem('rating'), tem('year'), chaves), nivel)
        if result:
            primeiro = result[0]
            xbmc.log('SMARTED-TV: lancamentos primeiro=%r ficha=(plot=%d genre=%d nota=%s '
                     'data=%s ano=%s dur=%s)'
                     % (primeiro['title'], len(primeiro['plot']), len(primeiro['genre']),
                        primeiro['rating'], primeiro['premiered'], primeiro['year'],
                        primeiro['duration']), nivel)
    except Exception:
        pass


def _genre(value):
    """O Kodi devolve genero como lista; o addon manda um texto so."""
    if isinstance(value, (list, tuple)):
        nomes = [nome for nome in value if isinstance(nome, str) and nome]
        return ', '.join(nomes)
    return value if isinstance(value, str) else ''


def _rating(value):
    try:
        nota = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(nota, 1) if 0 < nota <= 10 else 0.0


def _premiered(item):
    """Data real do addon (ele grava a data em ``dateadded``)."""
    for chave in ('premiered', 'dateadded'):
        valor = item.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()[:10]
    return ''


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
    bruto = directory(rpc, folder)
    result = []
    for item in bruto:
        entry = _entry(item)
        # Skip non-playable command entries in the hero. They remain accessible
        # through the add-on's native menu, but cannot be played as movies.
        if entry and (entry['folder'] or entry['playable']):
            result.append(entry)
        if len(result) >= limit:
            break
    _log_hero(result, bruto)
    return result


# --- carrossel: desce a árvore do addon até o nível de conteúdo real ---------
#
# As linhas da Home não podem listar pastas de menu ("CATEGORIA: GÊNEROS",
# "TODAS SÉRIES"): o usuário quer pôsteres de filmes, séries e canais que
# reproduzem ao dar OK. O caminho até o conteúdo é definido pelo próprio addon
# e pode mudar entre versões, por isso ele é percorrido em tempo de execução
# por ``walk`` (poucas chamadas JSON-RPC, sem inventar item nenhum).

CARROSSEL = {
    # alvo: (raiz, profundidade máxima, palavras que escolhem o ramo)
    'canais': ((21, '#todoscanais'), (21, '#menu_canais'), 3,
               ('pluto', 'canais', 'aovivo', 'brasil', 'filmes')),
    'filmes': ((27, '#filmes_menu'), None, 2,
               ('lancamento', 'recente', 'filmes', 'categoria')),
    'series': ((27, '#series_menu'), None, 2,
               ('todas', 'series', 'novelas')),
    'novelas': ((25, '#novelas_menu'), None, 2, ('novela',)),
    'animes': ((22, '#animes_menu'), None, 2, ('anime',)),
    'doramas': ((31, '#doramas_menu'), None, 2, ('dorama',)),
    'desenhos': ((28, '#desenhos_menu'), None, 2, ('desenho',)),
}

MAX_ENTRIES = 20


# Pastas que não levam a conteúdo: buscar, configurar ou verificar abrem
# teclado/diálogo e devolvem diretório vazio. Se houver alternativa, ficam por
# último para o carrossel nunca descer por elas.
DESVIO = ('pesquis', 'buscar', 'search', 'configura', 'ajuste', 'definicao',
          'verificar', 'adulto', 'login', 'conta')


def _order(folders, prefer):
    """Coloca primeiro as pastas cujo rótulo casa com o alvo."""
    def score(entry):
        label = normalize(entry.get('label', ''))
        if any(word in label for word in DESVIO):
            return len(prefer) + 1
        for position, word in enumerate(prefer):
            if word and word in label:
                return position
        return len(prefer)
    return sorted(folders, key=score)


def walk(rpc, root, depth=2, prefer=(), limit=MAX_ENTRIES):
    """Desce ``root`` até achar mídia; devolve (itens, achou_midia).

    - se o nível atual já tem mídia (arquivos), devolve só a mídia;
    - senão desce pela pasta preferida (uma por nível, no máximo ``depth``);
    - se chegar ao fim sem mídia, devolve o nível mais fundo (nunca vazio).
    """
    url, level = root, 0
    while True:
        try:
            entries = [entry for entry in (_entry(item) for item in directory(rpc, url)) if entry]
        except Exception:
            return [], False
        if not entries:
            return [], False
        media = [entry for entry in entries if not entry['folder']]
        folders = _order([entry for entry in entries if entry['folder']], prefer)
        if media and (len(media) * 2 >= len(entries) or not folders or level >= depth - 1):
            return media[:limit], True
        if not folders or level + 1 >= depth:
            # limite atingido: entrega o nível de conteúdo mais próximo
            return (media or entries)[:limit], bool(media)
        url, level = folders[0]['url'], level + 1


def carousel(rpc, alvo):
    """Percorre a árvore do addon para o alvo e devolve (itens, origem, achou_midia)."""
    if alvo not in CARROSSEL:
        raise ValueError('alvo desconhecido')
    roots = CARROSSEL[alvo]
    depth, prefer = roots[2], roots[3]
    for root in roots[:2]:
        if not root:
            continue
        items, found = walk(rpc, brazuca(*root), depth=depth, prefer=prefer)
        if items:
            return items, root[1], found
    return [], '', False
