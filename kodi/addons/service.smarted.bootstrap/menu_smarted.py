# -*- coding: utf-8 -*-
"""Troca o menu generico do Kodi pelo menu SMARTEDTV (categorias do Brazuca Play).

A skin padrao (base Bingie) traz um menu superior estatico gerado a partir das
rotas do Brazuca Play. Como o script.skinshortcuts mantem dados do menu antigo
no perfil, no primeiro boot depois da atualizacao o menu velho poderia aparecer.
Esta rotina roda uma vez por versao: limpa os dados antigos e grava o marcador.

IMPORTANTE (correcao da tela preta): esta rotina NAO chama ``ReloadSkin()``.
O servico roda em paralelo com o boot; o reload derrubava a janela de entrada
(e/ou a Home recem-aberta), deixando o aparelho em tela preta por alguns
segundos. A Home do SMARTEDTV le os valores ``smarted_nav_*`` direto da skin e
o ``apply_navigation()`` os publica com ``Skin.SetString``, que atualiza a
interface sem recarregar a skin inteira. O menu antigo deixa de ser lido no
proximo boot, quando o Kodi monta a skin do zero.
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
    # Sem ReloadSkin(): veja o aviso no topo do modulo. O reload no meio do
    # boot era a causa da tela preta que so voltava ao tocar/reabrir.
    log('menu SMARTEDTV ativado sem recarregar a skin '
        '(dados antigos removidos: %s)'
        % (', '.join(removidos) or 'nenhum'))
    return {'applied': True, 'removed': removidos}


# --- validacao real dos botoes da barra (roda no aparelho e grava o resultado) --
# Destinos finais do Brazuca Play 2.1.4, copiados do codigo do addon:
#   TV       mode=21 url=#todoscanais            (lista de canais)
#   Filmes   mode=1  <gist>/lancamentos.xml
#   Series   mode=1  <gist>/SeriesBase
#   Doramas  mode=1  <gist>/DoramasBase
#   Novelas  mode=1  <gist>/novelas.xml
#   Animes   mode=1  <gist>/AnimesBase
#   Desenhos mode=1  <gist>/DesenhosBase
# No modo 1 o addon espera url = base16(base64(url)), igual ao proprio addDir().
BRAZUCA = 'plugin://plugin.video.BrazucaPlay.Matrix/?%s'
GIST_SERIES = 'https://gist.githubusercontent.com/skyrisk/16070347f20c87c72540f9f805b57a66/raw/'
GIST_NOVELAS = 'https://gist.githubusercontent.com/skyrisk/07f1f4cd1b203cbf2efec959c4e8645a/raw/'
GIST_FILMES = 'https://gist.githubusercontent.com/skyrisk/5b87797329c7b46422565ffbaab3be7e/raw/'


def _codificar(url):
    import base64
    return base64.b16encode(base64.b64encode(url.encode('utf-8'))).decode('ascii')


def _destino(mode, url, nome):
    from urllib.parse import quote_plus
    url = _codificar(url) if mode == 1 else quote_plus(url)
    return BRAZUCA % ('url=%s&mode=%d&name=%s&iconimage=DefaultFolder.png'
                      '&fanart=DefaultFolder.png&description=Menu'
                      % (quote_plus(url), mode, quote_plus(nome)))


DESTINOS = [
    ('TV', _destino(21, '#todoscanais', 'TV')),
    ('Filmes', _destino(1, GIST_FILMES + 'lancamentos.xml', 'Filmes')),
    ('Séries', _destino(1, GIST_SERIES + 'SeriesBase', 'Séries')),
    ('Doramas', _destino(1, GIST_SERIES + 'DoramasBase', 'Doramas')),
    ('Novelas', _destino(1, GIST_NOVELAS + 'novelas.xml', 'Novelas')),
    ('Animes', _destino(1, GIST_SERIES + 'AnimesBase', 'Animes')),
    ('Desenhos', _destino(1, GIST_SERIES + 'DesenhosBase', 'Desenhos')),
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


AJUSTES_SILENCIOSOS = {'donate_consider': '991231'}


def silenciar_avisos_brazuca(xbmcaddon_module=None, log=None):
    """Desliga o pedido de doacao do Brazuca Play (aviso nao critico).

    O addon mostra um dialogo de doacao sempre que a setting `donate_consider`
    esta vazia/vencida; e opcional e nao afeta a navegacao nem a reproducao,
    mas aparecia por cima da Home e travava o carregamento dos widgets.
    """
    try:
        if xbmcaddon_module is None:
            import xbmcaddon as xbmcaddon_module
        addon = xbmcaddon_module.Addon('plugin.video.BrazucaPlay.Matrix')
    except Exception as erro:  # noqa: BLE001
        if log:
            log('brazuca: addon ausente (%s)' % erro)
        return {}
    aplicados = {}
    for chave, valor in AJUSTES_SILENCIOSOS.items():
        try:
            if addon.getSetting(chave) != valor:
                addon.setSetting(chave, valor)
                aplicados[chave] = valor
        except Exception as erro:  # noqa: BLE001
            if log:
                log('brazuca: setting %s nao aplicada (%s)' % (chave, erro))
    if aplicados and log:
        log('brazuca: avisos nao criticos silenciados %s' % sorted(aplicados))
    return aplicados
