# -*- coding: utf-8 -*-
"""Navegacao superior do SMARTEDTV alimentada pelos favoritos do Brazuca Play.

Fonte da verdade: o MESMO ``userdata/addon_data/plugin.video.BrazucaPlay.Matrix/
favorites.dat`` que o addon grava quando a pessoa toca em "Adicionar aos
Favoritos". O SMARTED-TV apenas le esse arquivo (nunca escreve).

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

from catalogue import _entry as catalogo_entry
from catalogue import directory as catalogo_directory
from favorites import CATEGORIES, load, plugin_url
from routes import brazuca

# slots existentes na Home (cada um e um botao da barra superior)
SLOTS = 10
CACHE_NAME = 'navegacao.json'
MAX_LABEL = 26
TAGS = re.compile(r'\[/?(?:B|I|COLOR(?: [^\]]+)?|UPPERCASE|LOWERCASE|CAPITALIZE)\]', re.I)

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


def root_entries(rpc):
    """Menu raiz do proprio addon (mode 0), quando nao ha favoritos."""
    if rpc is None:
        return []
    try:
        bruto = catalogo_directory(rpc, brazuca(0, ''))
    except Exception:
        return []
    items = []
    for item in bruto:
        entrada = catalogo_entry(item)
        if entrada and (entrada['folder'] or entrada['playable']):
            items.append(_entry(entrada['label'], entrada['url'],
                                playable=entrada['playable'], origem='menu'))
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


def build(path, rpc=None, log=None):
    """Devolve ``(entradas, origem)``: favoritos, menu do addon ou pastas."""
    favoritos = favorites_entries(path)
    if favoritos:
        if log:
            log('navegacao: %d favoritos do Brazuca' % len(favoritos))
        return _dedupe(favoritos), 'favoritos'
    menu = root_entries(rpc)
    if menu:
        if log:
            log('navegacao: sem favoritos, usando o menu do addon (%d)' % len(menu))
        return _dedupe(menu), 'menu'
    if log:
        log('navegacao: sem favoritos e sem menu, usando as pastas do addon')
    return _dedupe(folder_entries()), 'pastas'


def apply_skin_strings(entries, execute):
    """Publica rotulos dos botoes da barra e limpa os slots sem favorito."""
    for slot in range(1, SLOTS + 1):
        nome = 'smarted_nav_%d' % slot
        if slot <= len(entries):
            execute('Skin.SetString(%s,%s)' % (nome, entries[slot - 1]['label']))
        else:
            execute('Skin.Reset(%s)' % nome)


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
    url = entry['url'].replace(',', '%2C')
    if entry['playable']:
        return 'PlayMedia(%s)' % url
    return 'ActivateWindow(Videos,%s,return)' % url
