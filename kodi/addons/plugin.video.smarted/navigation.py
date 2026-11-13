# -*- coding: utf-8 -*-
"""Navegacao superior do SMARTEDTV alimentada pelos favoritos do Brazuca Play.

Fonte da verdade: o MESMO ``userdata/addon_data/plugin.video.BrazucaPlay.Matrix/
favorites.dat`` que o addon grava quando a pessoa toca em "Adicionar aos
Favoritos". O SMARTEDTV apenas le esse arquivo (nunca escreve).

Ordem: a do proprio addon (canais, filmes, series, novelas, animes, desenhos,
doramas) e, dentro de cada categoria, a ordem em que os favoritos foram salvos.
Cada entrada vira uma opcao da barra superior e guarda a URL nativa do addon,
para o OK abrir a pasta certa ou tocar o video direto.

Sem favoritos (perfil novo), a barra usa o menu raiz do proprio addon; se a rede
falhar, usa as pastas reais do addon. Nunca uma lista inventada.
"""
import json
import re
import time
from urllib.parse import urlencode

from catalogue import _entry as catalogo_entry
from catalogue import directory as catalogo_directory
from favorites import CATEGORIES, load, plugin_url
from routes import brazuca

# slots existentes na Home (cada um e um botao da barra superior)
SLOTS = 8
CACHE_NAME = 'navegacao.json'
MAX_LABEL = 26
TAGS = re.compile(r'\[/?(?:B|I|COLOR(?: [^\]]+)?|UPPERCASE|LOWERCASE|CAPITALIZE)\]', re.I)

# icones das categorias (arquivos da skin -> media/icons)
ICONES = (
    ('tv', 'icons/nav-tv.png'),
    ('filme', 'icons/nav-filmes.png'),
    ('serie', 'icons/nav-series.png'),
    ('dorama', 'icons/nav-doramas.png'),
    ('anime', 'icons/nav-animes.png'),
    ('novela', 'icons/nav-novelas.png'),
    ('desenho', 'icons/nav-desenhos.png'),
)
ICONE_PADRAO = 'icons/nav-pasta.png'
CANAL = 'mode=21'


def icon_for(entry):
    """Icone da skin que corresponde a categoria daquela pasta."""
    alvo = ((entry or {}).get('label') or '').lower()
    url = (entry or {}).get('url') or ''
    if CANAL in url or 'tv' in alvo.split():
        return 'icons/nav-tv.png'
    for chave, arquivo in ICONES:
        if chave in alvo:
            return arquivo
    return ICONE_PADRAO


def is_channel(entry):
    """TV ao vivo: destino de canais e nao de VOD (nao recebe cards)."""
    url = (entry or {}).get('url') or ''
    rotulo = ((entry or {}).get('label') or '').lower()
    return CANAL in url or 'tv ao vivo' in rotulo or rotulo.strip() == 'tv'


# ultimo recurso: pastas reais do addon (mesmas rotas que ele publica no menu)
PASTAS = (
    ('TV ao vivo', 21, '#menu_canais'),
    ('Filmes', 27, '#filmes_menu'),
    ('Séries', 27, '#series_menu'),
    ('Novelas', 25, '#novelas_menu'),
    ('Animes', 22, '#animes_menu'),
    ('Doramas', 31, '#doramas_menu'),
    ('Desenhos', 28, '#desenhos_menu'),
)


def clean_label(label):
    """Tira as tags de cor do addon e ajusta o tamanho para o botao."""
    texto = TAGS.sub('', label or '')
    texto = re.sub(r'\s+', ' ', texto).strip()
    texto = texto.replace(',', ' ')
    if len(texto) > MAX_LABEL:
        texto = texto[:MAX_LABEL - 1].rstrip() + '…'
    return texto


def _entry(label, url, playable=False, origem=''):
    return {'label': clean_label(label), 'url': url,
            'playable': bool(playable), 'origem': origem}


def favorites_entries(path):
    """Favoritos do addon na ordem dele; pastas e videos diretos."""
    dados = load(path)
    items = []
    for categoria in CATEGORIES:
        for favorito in dados.get(categoria, []):
            url = plugin_url(favorito)
            if not url:
                continue
            items.append(_entry(favorito['label'], url,
                                playable=favorito['mode'] in (11, 16),
                                origem=categoria))
    return items


# o menu raiz do addon tambem publica configuracoes/updates: nao sao pastas de
# conteudo e nao entram na barra
IGNORAR = ('configuracoes', 'verificarupdates', 'conteudosbaixados')


def root_entries(rpc):
    """Pastas reais do menu raiz do addon (mode 0), descobertas ao vivo."""
    if rpc is None:
        return []
    try:
        bruto = catalogo_directory(rpc, brazuca(0, ''))
    except Exception:
        return []
    items = []
    for item in bruto:
        entrada = catalogo_entry(item)
        if not entrada or not entrada['folder']:
            continue
        if any(chave in clean_label(entrada['label']).lower().replace(' ', '')
               for chave in IGNORAR):
            continue
        items.append(_entry(entrada['label'], entrada['url'], origem='menu'))
    return items


def folder_entries():
    """Pastas reais do addon: garantia de barra nunca vazia."""
    return [_entry(label, brazuca(mode, url), origem='pasta')
            for label, mode, url in PASTAS]


def _dedupe(items, limit=SLOTS):
    vistos = set()
    resultado = []
    for item in items:
        chave = item['url']
        if chave in vistos or not item['label']:
            continue
        vistos.add(chave)
        resultado.append(item)
        if len(resultado) >= limit:
            break
    return resultado


def build(path, rpc=None, log=None, favoritos_primeiro=False):
    """Devolve ``(entradas, origem)``.

    Ordem: as pastas REAIS do addon (menu raiz que ele mesmo publica, descoberto
    por Files.GetDirectory), depois os favoritos do Brazuca e, como rede de
    seguranca, as pastas conhecidas. Cada entrada guarda a URL nativa do addon,
    entao o OK abre exatamente o diretorio que o addon abriria.
    """
    if favoritos_primeiro:
        favoritos = favorites_entries(path)
        if favoritos:
            if log:
                log('navegacao: %d favoritos do Brazuca' % len(favoritos))
            return _dedupe(favoritos), 'favoritos'
    menu = root_entries(rpc)
    if menu:
        if log:
            log('navegacao: %d pastas reais do menu do addon' % len(menu))
        return _dedupe(menu), 'menu'
    favoritos = favorites_entries(path)
    if favoritos:
        if log:
            log('navegacao: menu indisponivel, usando %d favoritos' % len(favoritos))
        return _dedupe(favoritos), 'favoritos'
    if log:
        log('navegacao: sem menu e sem favoritos, usando as pastas do addon')
    return _dedupe(folder_entries()), 'pastas'


def apply_skin_strings(entries, execute):
    """Publica rotulo e URL de cada slot da barra (limpa os que sobram)."""
    for slot in range(1, SLOTS + 1):
        nome = 'smarted_nav_%d' % slot
        url = 'smarted_nav_url_%d' % slot
        icone = 'smarted_nav_icon_%d' % slot
        if slot <= len(entries):
            entrada = entries[slot - 1]
            execute('Skin.SetString(%s,%s)' % (nome, entrada['label']))
            execute('Skin.SetString(%s,%s)' % (url, buildin_url(entrada['url'])))
            execute('Skin.SetString(%s,%s)' % (icone, icon_for(entrada)))
        else:
            execute('Skin.Reset(%s)' % nome)
            execute('Skin.Reset(%s)' % url)
            execute('Skin.Reset(%s)' % icone)


SMARTED_BASE = 'plugin://plugin.video.smarted/'


def pasta_url(url, tv=False):
    """Link da ponte: a propria pasta decide se a tela e lista ou grade de cards."""
    dados = {'route': 'pasta', 'url': url}
    if tv:
        dados['tv'] = '1'
    return SMARTED_BASE + '?' + urlencode(dados)


def buildin_url(url):
    """URL pronta para um builtin (virgula fecha o argumento do comando)."""
    return (url or '').replace(',', '%2C')


def save_cache(filename, entries, origem, today=None):
    dados = {'data': today or time.strftime('%Y-%m-%d'),
             'origem': origem, 'entradas': entries}
    try:
        with open(filename, 'w', encoding='utf-8') as stream:
            json.dump(dados, stream, ensure_ascii=False)
    except OSError:
        return False
    return True


def load_cache(filename, today=None, aceitar_antigo=False):
    try:
        with open(filename, 'r', encoding='utf-8') as stream:
            dados = json.load(stream)
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get('entradas'), list):
        return None
    if not aceitar_antigo and dados.get('data') != (today or time.strftime('%Y-%m-%d')):
        return None
    entradas = [item for item in dados['entradas']
                if isinstance(item, dict) and item.get('label') and item.get('url')]
    if not entradas:
        return None
    return entradas


def resolve(entries, indice):
    """Entrada do slot pedido (ou None quando o slot nao existe)."""
    if not isinstance(indice, int) or indice < 0 or indice >= len(entries):
        return None
    return entries[indice]


def open_command(entry):
    """Builtin que abre a pasta (ou toca o video) daquele favorito."""
    url = buildin_url(entry['url'])
    if entry['playable']:
        return 'PlayMedia(%s)' % url
    return 'ActivateWindow(Videos,%s)' % url
