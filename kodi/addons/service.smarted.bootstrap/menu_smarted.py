# -*- coding: utf-8 -*-
"""Troca o menu generico do Kodi pelo menu SMARTEDTV (categorias do Brazuca Play).

A skin padrao (base Bingie) traz um menu superior estatico gerado a partir das
rotas do Brazuca Play. Como o Kodi guarda os includes da skin em cache e o
script.skinshortcuts mantem dados do menu antigo no perfil, no primeiro boot
depois da atualizacao o menu velho continuaria aparecendo. Esta rotina roda uma
vez por versao: limpa os dados antigos e recarrega a skin.
"""
from __future__ import absolute_import, unicode_literals

import os

import xbmc
import xbmcvfs

MARCADOR = 'menu-smarted-v2.done'


def _perfil(*partes):
    return xbmcvfs.translatePath(
        os.path.join('special://profile/addon_data', *partes))


def limpar_menu_antigo():
    """Apaga os dados do skinshortcuts gravados para a skin padrao."""
    pasta = _perfil('script.skinshortcuts')
    if not xbmcvfs.exists(pasta):
        return []
    removidos = []
    try:
        _, arquivos, _ = xbmcvfs.listdir(pasta)
    except Exception:  # noqa: BLE001 - listdir pode falhar em perfis antigos
        return []
    for nome in arquivos:
        if 'novatv' not in nome.lower():
            continue
        caminho = os.path.join(pasta, nome)
        try:
            xbmcvfs.delete(caminho)
            removidos.append(nome)
        except Exception:  # noqa: BLE001
            pass
    return removidos


def garantir_menu(xbmc_module=xbmc, log=None):
    """Executa a troca uma unica vez e devolve o que foi feito."""
    log = log or (lambda *a, **k: None)
    pasta = _perfil('service.smarted.bootstrap')
    marcador = os.path.join(pasta, MARCADOR)
    if xbmcvfs.exists(marcador):
        return {'applied': False, 'removed': []}
    removidos = limpar_menu_antigo()
    if not xbmcvfs.exists(pasta):
        xbmcvfs.mkdirs(pasta)
    try:
        with xbmcvfs.File(marcador, 'w') as arquivo:
            arquivo.write('ok')
    except Exception as erro:  # noqa: BLE001
        log('menu: marcador nao gravado (%s)' % erro)
    xbmc_module.executebuiltin('ReloadSkin()')
    log('menu SMARTEDTV ativado (dados antigos removidos: %s)'
        % (', '.join(removidos) or 'nenhum'))
    return {'applied': True, 'removed': removidos}


# --- validacao real dos botoes da barra (roda no aparelho e grava o resultado) --
BRAZUCA = 'plugin://plugin.video.BrazucaPlay.Matrix/'
DESTINOS = [
    ('TV', BRAZUCA + '?mode=21&url=%23menu_canais&name=TV&iconimage=DefaultFolder.png'
     '&fanart=DefaultFolder.png&description=Menu'),
    ('Filmes', BRAZUCA + '?mode=27&url=%23filmes_menu&name=Filmes&iconimage=DefaultFolder.png'
     '&fanart=DefaultFolder.png&description=Menu'),
    ('Séries', BRAZUCA + '?mode=27&url=%23series_menu&name=Series&iconimage=DefaultFolder.png'
     '&fanart=DefaultFolder.png&description=Menu'),
    ('Doramas', BRAZUCA + '?mode=31&url=%23doramas_menu&name=Doramas&iconimage=DefaultFolder.png'
     '&fanart=DefaultFolder.png&description=Menu'),
    ('Novelas', BRAZUCA + '?mode=25&url=%23novelas_menu&name=Novelas&iconimage=DefaultFolder.png'
     '&fanart=DefaultFolder.png&description=Menu'),
    ('Animes', BRAZUCA + '?mode=22&url=%23animes_menu&name=Animes&iconimage=DefaultFolder.png'
     '&fanart=DefaultFolder.png&description=Menu'),
    ('Desenhos', BRAZUCA + '?mode=28&url=%23desenhos_menu&name=Desenhos&iconimage=DefaultFolder.png'
     '&fanart=DefaultFolder.png&description=Menu'),
]
MARCADOR_NAV = 'nav-check-v1.done'


def _jsonrpc_local(method, params):
    import json
    payload = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    try:
        return json.loads(xbmc.executeJSONRPC(payload))
    except Exception as erro:  # noqa: BLE001
        return {'error': {'message': str(erro)}}


def verificar_destinos(log, jsonrpc=None):
    """Confere, no proprio aparelho, se cada botao abre um diretorio com itens.

    Devolve linhas `PASS Filmes 20 itens` / `FALHA Filmes: <motivo>`. E o teste
    real dos oito botoes: com o mesmo caminho usado no clique, mostra se o
    diretorio carrega (problema seria o comando) ou se volta vazio (problema
    seria o caminho).
    """
    chamar = jsonrpc or _jsonrpc_local
    linhas = []
    for rotulo, url in DESTINOS:
        resposta = chamar('Files.GetDirectory', {'directory': url, 'media': 'files'}) or {}
        itens = ((resposta.get('result') or {}).get('files')) or []
        if itens:
            linhas.append('PASS %s %d itens' % (rotulo, len(itens)))
        else:
            motivo = (resposta.get('error') or {}).get('message', 'sem itens')
            linhas.append('FALHA %s: %s' % (rotulo, motivo))
    for linha in linhas:
        log('nav-check: ' + linha)
    return linhas


def rodar_validacao_navegacao(log, jsonrpc=None):
    """Executa a validacao uma vez, grava o log e devolve as linhas."""
    pasta = _perfil('service.smarted.bootstrap')
    marcador = os.path.join(pasta, MARCADOR_NAV)
    if xbmcvfs.exists(marcador):
        return None
    linhas = verificar_destinos(log, jsonrpc)
    if not xbmcvfs.exists(pasta):
        try:
            xbmcvfs.mkdirs(pasta)
        except Exception:  # noqa: BLE001
            pass
    try:
        arquivo = xbmcvfs.File(os.path.join(pasta, 'smarted-nav-check.log'), 'w')
        try:
            arquivo.write('\n'.join(linhas))
        finally:
            arquivo.close()
        aberto = xbmcvfs.File(marcador, 'w')
        try:
            aberto.write('ok')
        finally:
            aberto.close()
    except Exception as erro:  # noqa: BLE001
        log('nav-check: nao foi possivel gravar o log (%s)' % erro)
    return linhas
