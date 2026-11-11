# -*- coding: utf-8 -*-
"""Atalhos do Brazuca Play nos favoritos do Kodi (nativo, sem wizard).

O perfil semeado já traz ``userdata/favourites.xml``, mas ele pode ser perdido
(a pessoa apaga os favoritos, o Kodi regrava o arquivo ao sair, uma atualização
substitui o perfil...). Quando isso acontece a janela Favoritos abre vazia e a
Home não tem para onde apontar.

Este módulo recria os atalhos no boot, de forma **idempotente**: só acrescenta
o atalho que ainda não existe, nunca duplica e nunca apaga favoritos do usuário.
"""
from __future__ import absolute_import, unicode_literals

import os
from xml.etree import ElementTree
from xml.sax.saxutils import escape

try:  # Python 3 (Kodi 19+) e Python 2 por compatibilidade com o harness
    from urllib.parse import quote
except ImportError:  # pragma: no cover
    from urllib import quote

PLUGIN = 'plugin://plugin.video.BrazucaPlay.Matrix/'
THUMB = 'DefaultFolder.png'

# (rótulo, mode, url interna do plugin)
SHORTCUTS = (
    ('TV ao vivo', 21, '#menu_canais'),
    ('Filmes', 27, '#filmes_menu'),
    ('Séries', 27, '#series_menu'),
    ('Novelas', 25, '#novelas_menu'),
    ('Animes', 22, '#animes_menu'),
    ('Desenhos', 28, '#desenhos_menu'),
    ('Doramas', 31, '#doramas_menu'),
)

WINDOW_VIDEOS = 10025


def _q(value):
    return quote(value, safe='')


def shortcut_query(label, mode, url):
    """Query do plugin com os parâmetros que o addDir exige (iconimage/fanart)."""
    return 'mode=%d&url=%s&name=%s&iconimage=%s&fanart=%s&description=Menu' % (
        mode, _q(url), _q(label), THUMB, THUMB)


def shortcut_action(label, mode, url):
    return 'ActivateWindow(%d,"%s?%s",return)' % (
        WINDOW_VIDEOS, PLUGIN, shortcut_query(label, mode, url))


def favourites_path(home):
    return os.path.join(home, 'userdata', 'favourites.xml')


def load_entries(path):
    """Lê os favoritos existentes; devolve [] quando o arquivo não existe."""
    if not os.path.isfile(path):
        return []
    try:
        root = ElementTree.parse(path).getroot()
    except Exception:
        return []
    if root.tag != 'favourites':
        return []
    return list(root)


def has_shortcut(entries, mode, url):
    """True quando já existe um favorito apontando para este menu do plugin."""
    mode_token = 'mode=%d' % mode
    url_token = _q(url)
    for entry in entries:
        text = entry.text or ''
        if PLUGIN in text and mode_token in text and url_token in text:
            return True
    return False


def render(entries):
    lines = ['<favourites>']
    for entry in entries:
        attributes = ''
        name = entry.get('name')
        thumb = entry.get('thumb')
        if name is not None:
            attributes += ' name="%s"' % escape(name, {'"': '&quot;'})
        if thumb is not None:
            attributes += ' thumb="%s"' % escape(thumb, {'"': '&quot;'})
        lines.append('    <favourite%s>%s</favourite>' % (attributes, escape(entry.text or '')))
    lines.append('</favourites>')
    return '\n'.join(lines) + '\n'


def ensure_favourites(home, log=None):
    """Garante os atalhos do Brazuca Play. Devolve os rótulos adicionados."""
    path = favourites_path(home)
    entries = load_entries(path)
    added = []
    for label, mode, url in SHORTCUTS:
        if has_shortcut(entries, mode, url):
            continue
        node = ElementTree.Element('favourite', {'name': label, 'thumb': THUMB})
        node.text = shortcut_action(label, mode, url)
        entries.append(node)
        added.append(label)

    if not added:
        if log:
            log('favoritos: %d atalhos já presentes' % len(SHORTCUTS))
        return []

    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    temp = path + '.tmp'
    with open(temp, 'w') as handle:
        handle.write(render(entries))
    os.replace(temp, path)
    if log:
        log('favoritos: adicionados %s' % ', '.join(added))
    return added
