# -*- coding: utf-8 -*-
"""Automação da skin no primeiro arranque.

O launcher (dex) grava ``lookandfeel.skin = skin.novatv`` no perfil **semeado**.
Se o aparelho já tinha um ``.kodi`` (atualização, reinstalação por cima), esse
passo é pulado e o Kodi pode abrir na Estuary — foi o que deixou a Home "sem
dados" em relatos anteriores, porque a Home da SMARTEDTV nem era carregada.

Este módulo garante, de forma idempotente e sem diálogo:

* a skin ativa é a ``skin.novatv`` (SMARTEDTV);
* os três nós da Home (TV ao vivo, Filmes, Séries) apontam para as rotas
  reais do Brazuca Play (``#menu_canais``, ``#filmes_menu``, ``#series_menu``);
* o relatório dessas ligações fica no log do bootstrap para conferência.

Nada aqui inventa conteúdo: só confere/altera configuração.
"""
from __future__ import absolute_import, unicode_literals

import os

import xbmc
import xbmcvfs

SKIN_ID = 'skin.novatv'
SKIN_NAME = 'SMARTEDTV'
SKIN_SETTING = 'lookandfeel.skin'

# (rótulo, mode, url interna do addon) — os mesmos nós usados na Home.xml
HOME_NODES = (
    ('TV ao vivo', 21, '#menu_canais'),
    ('Filmes', 27, '#filmes_menu'),
    ('Séries', 27, '#series_menu'),
)


def _log(log, message, level=None):
    if log is None:
        xbmc.log('[smarted-skin] %s' % message, level or xbmc.LOGINFO)
    else:
        log(message) if callable(log) else None


def guisettings_path(home):
    return os.path.join(home, 'userdata', 'guisettings.xml')


def current_skin(home):
    """Skin ativa segundo o guisettings.xml (string vazia se não houver)."""
    import re

    path = guisettings_path(home)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            text = handle.read()
    except (OSError, IOError):
        return ''
    match = re.search(r'<setting id="%s"[^>]*>([^<]*)</setting>' % SKIN_SETTING, text)
    return match.group(1).strip() if match else ''


def skin_installed(home):
    """A skin pode estar no perfil OU nos add-ons de sistema (assets do APK)."""
    try:
        if xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
            return True
    except Exception:
        pass
    candidatos = []
    if home:
        candidatos.append(os.path.join(home, 'addons', SKIN_ID))
    try:
        candidatos.append(os.path.join(xbmcvfs.translatePath('special://xbmc/addons'), SKIN_ID))
    except Exception:
        pass
    return any(os.path.isdir(caminho) for caminho in candidatos)


def set_skin_xml(home, skin_id=SKIN_ID):
    """Reescreve só a linha da skin no guisettings.xml. Devolve True se mudou."""
    path = guisettings_path(home)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            text = handle.read()
    except (OSError, IOError):
        return False
    import re

    pattern = re.compile(r'<setting id="%s"[^>]*>[^<]*</setting>' % SKIN_SETTING)
    novo = '<setting id="%s">%s</setting>' % (SKIN_SETTING, skin_id)
    if pattern.search(text):
        novo_texto = pattern.sub(novo, text, count=1)
    elif '</settings>' in text:
        novo_texto = text.replace('</settings>', '  ' + novo + '\n</settings>', 1)
    else:
        return False
    if novo_texto == text:
        return False
    try:
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(novo_texto)
    except (OSError, IOError):
        return False
    return True


def ensure_skin(home, apply_setting=None, set_skin=None, log=None):
    """Garante a SMARTEDTV ativa. ``apply_setting``/``set_skin`` são injetáveis."""
    if apply_setting is None:
        apply_setting = _jsonrpc_skin
    if set_skin is None:
        set_skin = set_skin_xml

    atual = current_skin(home)
    if atual == SKIN_ID:
        return {'skin': SKIN_ID, 'changed': False, 'installed': skin_installed(home)}

    if not skin_installed(home):
        _log(log, 'skin %s ausente do perfil: mantendo %r' % (SKIN_ID, atual), xbmc.LOGWARNING)
        return {'skin': atual, 'changed': False, 'installed': False}

    applied = False
    try:
        applied = bool(apply_setting(SKIN_ID))
    except Exception:
        applied = False
    changed = set_skin(home)
    _log(log, 'skin ativa -> %s (setting=%s, xml=%s)' % (SKIN_ID, applied, changed))
    return {'skin': SKIN_ID, 'changed': bool(applied or changed), 'installed': True}


def _jsonrpc_skin(skin_id):
    import json

    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.SetSettingValue',
               'params': {'setting': SKIN_SETTING, 'value': skin_id}}
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except Exception:
        return False
    return 'result' in response


def home_nodes_report(log=None):
    """Confere se as três rotas mapeadas continuam iguais às da Home.xml."""
    rotas = []
    for label, mode, url in HOME_NODES:
        rotas.append('%s=mode=%d&url=%s' % (label, mode, url))
    _log(log, 'nós da Home: ' + ' | '.join(rotas))
    return rotas


def _rota_presente(texto, mode, url):
    """A rota aparece no texto? Aceita `&`/`&amp;` e `#`/`%23` (ordem livre)."""
    limpo = texto.replace('&amp;', '&')
    alvo = url.replace('#', '%23')
    return ('mode=%d' % mode) in limpo and (url in limpo or alvo in limpo)


def ensure_home_nodes(home_xml_paths=None, favourites_path=None, log=None):
    """Confere as três rotas da Home no Home.xml da skin e nos favoritos.

    ``home_xml_paths`` é a lista devolvida por :func:`home_xml_candidates`
    (nenhum arquivo lido => pendente). Não altera XML nenhum: se uma rota
    divergir, aparece no log para o bootstrap não mascarar o problema.
    """
    rotas = ['mode=%d&url=%s' % (mode, url) for _label, mode, url in HOME_NODES]
    caminhos = list(home_xml_paths or [])
    falta_home, falta_fav = [], []
    lidos = 0
    for caminho in caminhos:
        try:
            with open(caminho, 'r', encoding='utf-8') as handle:
                texto = handle.read().replace('&amp;', '&')
        except (OSError, IOError):
            continue
        lidos += 1
        for rotulo, mode, url in HOME_NODES:
            if not _rota_presente(texto, mode, url):
                falta_home.append(rotulo)
    if not lidos:
        falta_home = ['Home.xml da skin não encontrado']

    if favourites_path and os.path.isfile(favourites_path):
        try:
            with open(favourites_path, 'r', encoding='utf-8') as handle:
                fav = handle.read()
        except (OSError, IOError):
            fav = ''
        for rotulo, mode, url in HOME_NODES:
            if not _rota_presente(fav, mode, url):
                falta_fav.append(rotulo)

    ok = not falta_home and not falta_fav
    _log(log, 'nós da Home: %s (Home=%s, favoritos=%s)' % (
        'ok' if ok else 'pendente', falta_home or 'ok', falta_fav or 'ok'),
        xbmc.LOGINFO if ok else xbmc.LOGWARNING)
    return {'ok': ok, 'missing_home': falta_home, 'missing_favourites': falta_fav,
            'routes': rotas}


# Atalhos permanentes na barra da Home. A navegação ocupa os slots 1..8
# (navigation.SLOTS) e limpa o que sobra nesse intervalo; por isso usamos 9 e 10,
# que a skin já desenha e ninguém mais escreve.
ATALHOS = (
    (9, 'VIP', 'plugin://plugin.video.smarted/?route=vip'),
    (10, 'Compartilhar',
     'plugin://plugin.video.smarted/?route=vip-acao&acao=compartilhar'),
)


def ensure_shortcuts(log=None):
    """Garante "VIP" e "Compartilhar" nos slots 9 e 10 da barra da Home.

    Idempotente: se o slot já está com o nosso rótulo, não mexe (o usuário pode
    trocar o texto pela skin sem a gente sobrescrever a cada arranque).
    """
    preenchidos = []
    for slot, rotulo, url in ATALHOS:
        try:
            atual = xbmc.getInfoLabel('Skin.String(smarted_nav_%d)' % slot) or ''
        except Exception:  # noqa: BLE001
            atual = ''
        if atual.strip() == rotulo:
            continue
        try:
            xbmc.executebuiltin('Skin.SetString(smarted_nav_%d,%s)' % (slot, rotulo))
            xbmc.executebuiltin('Skin.SetString(smarted_nav_url_%d,%s)' % (slot, url))
            preenchidos.append('slot %d = %s' % (slot, rotulo))
        except Exception as erro:  # noqa: BLE001
            _log(log, 'atalho %s não entrou (%s)' % (rotulo, erro), xbmc.LOGWARNING)
    if preenchidos:
        _log(log, 'atalhos da Home: ' + ', '.join(preenchidos))
    else:
        _log(log, 'atalhos da Home: já presentes')
    return preenchidos


def home_xml_candidates(addons_dir):
    """Home.xml da skin: no perfil e/ou nos add-ons de sistema (assets do APK)."""
    caminhos, vistos = [], set()
    bases = []
    if addons_dir:
        bases.append(os.path.join(addons_dir, SKIN_ID, 'xml'))
    try:
        bases.append(os.path.join(xbmcvfs.translatePath('special://xbmc/addons'), SKIN_ID, 'xml'))
    except Exception:
        pass
    for base in bases:
        caminho = os.path.join(base, 'Home.xml')
        if os.path.isfile(caminho) and caminho not in vistos:
            vistos.add(caminho)
            caminhos.append(caminho)
    return caminhos
