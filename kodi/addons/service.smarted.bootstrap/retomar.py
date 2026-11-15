# -*- coding: utf-8 -*-
"""Ponto de retomada: salva onde o usuário parou e fecha o player com calma.

Por que existe: quando o app é fechado (botão voltar duas vezes, "Sair" do
menu, controle da TV, app removido da lista de recentes), o Kodi é encerrado
pelo Android. Se o player ainda estiver aberto nesse instante, o encerramento
pode travar e o ponto de retomada não chega a ser gravado no banco de vídeos.

Aqui a gente faz o inverso:

* a cada ``INTERVALO`` segundos com vídeo tocando, grava um JSON pequeno em
  ``userdata/addon_data/service.smarted.bootstrap/retomar.json`` com o arquivo,
  o título e o tempo exato (``Player.GetItem`` + ``Player.GetProperties``);
* quando o Kodi pede para encerrar (``onAbortRequested``), salva uma última vez
  e manda ``PlayerControl(Stop)``, que é o caminho normal: o Kodi grava o ponto
  no banco dele e o player fecha sem estouro;
* na abertura seguinte, o menu VIP oferece "Continuar assistindo" com
  ``StartOffset`` no ponto salvo.

Tudo é opcional: qualquer falha (JSON-RPC indisponível, player em Addon) só
deixa de salvar. Nunca levanta exceção para quem chamou.
"""
from __future__ import absolute_import, unicode_literals

import json
import os
import time

import xbmc
import xbmcgui

INTERVALO = 20          # segundos entre uma gravação e outra
VALIDADE = 7 * 24 * 3600  # ponto mais velho que isso é ignorado
MINIMO = 20             # abaixo disso (segundos) não vale a pena retomar
ARQUIVO = 'retomar.json'
# id fixo: o módulo também roda de dentro do plugin, e `xbmcaddon.Addon()`
# devolveria a pasta do plugin em vez da pasta do serviço
ADDON_ID = 'service.smarted.bootstrap'


def _log(mensagem, nivel=None):
    xbmc.log('[smarted-retomar] %s' % mensagem, nivel or xbmc.LOGINFO)


def perfil():
    """Pasta do usuário do Kodi (special://userdata)."""
    return xbmcvfs_translate('special://userdata')


def xbmcvfs_translate(caminho):
    try:
        import xbmcvfs
        return xbmcvfs.translatePath(caminho)
    except Exception:  # noqa: BLE001 - Kodi antigo/py2
        return caminho


def pasta():
    destino = os.path.join(perfil(), 'addon_data', ADDON_ID)
    try:
        if not os.path.isdir(destino):
            os.makedirs(destino)
    except Exception:  # noqa: BLE001
        pass
    return destino


def caminho():
    return os.path.join(pasta(), ARQUIVO)


def _rpc(metodo, params=None):
    pedido = {'jsonrpc': '2.0', 'id': 1, 'method': metodo}
    if params is not None:
        pedido['params'] = params
    try:
        resposta = json.loads(xbmc.executeJSONRPC(json.dumps(pedido)))
    except Exception as erro:  # noqa: BLE001
        _log('JSON-RPC %s falhou (%s)' % (metodo, erro), xbmc.LOGDEBUG)
        return {}
    if isinstance(resposta, dict) and 'result' in resposta:
        return resposta['result']
    return {}


def ponto():
    """dict com o que está tocando agora, ou None."""
    ativos = _rpc('Player.GetActivePlayers').get('result', [])
    if not ativos:
        return None
    playerid = ativos[0].get('playerid', 1)
    item = _rpc('Player.GetItem', {
        'playerid': playerid,
        'properties': ['file', 'title', 'showtitle', 'season', 'episode', 'year'],
    }).get('item', {})
    estado = _rpc('Player.GetProperties', {
        'playerid': playerid,
        'properties': ['percentage', 'time', 'totaltime', 'speed'],
    })
    if not isinstance(item, dict) or not item.get('file'):
        return None
    tempo = estado.get('time') or {}
    segundos = (int(tempo.get('hours', 0)) * 3600 + int(tempo.get('minutes', 0)) * 60
                + int(tempo.get('seconds', 0)))
    total = estado.get('totaltime') or {}
    duracao = (int(total.get('hours', 0)) * 3600 + int(total.get('minutes', 0)) * 60
               + int(total.get('seconds', 0)))
    titulo = item.get('title') or item.get('label') or os.path.basename(item['file'])
    if item.get('showtitle') and item.get('showtitle') != titulo:
        titulo = '%s - %s' % (item['showtitle'], titulo)
    return {
        'arquivo': item['file'],
        'titulo': titulo,
        'posicao': segundos,
        'duracao': duracao,
        'porcentagem': round(float(estado.get('percentage', 0) or 0), 1),
        'playerid': playerid,
        'quando': int(time.time()),
    }


def salvar(dados=None):
    dados = dados if dados is not None else ponto()
    if not dados or dados.get('posicao', 0) < MINIMO:
        return False
    try:
        with open(caminho(), 'w', encoding='utf-8') as saida:
            json.dump(dados, saida, ensure_ascii=False)
        _log('ponto salvo: %s em %ds' % (dados.get('titulo'), dados.get('posicao')))
        return True
    except Exception as erro:  # noqa: BLE001
        _log('nao consegui salvar o ponto (%s)' % erro, xbmc.LOGWARNING)
        return False


def ultimo(maxidade=VALIDADE):
    """Último ponto salvo, se ainda fizer sentido retomar."""
    try:
        with open(caminho(), 'r', encoding='utf-8') as entrada:
            dados = json.load(entrada)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(dados, dict) or not dados.get('arquivo'):
        return None
    if dados.get('posicao', 0) < MINIMO:
        return None
    if maxidade and time.time() - int(dados.get('quando', 0)) > maxidade:
        return None
    return dados


def limpar():
    try:
        os.remove(caminho())
    except Exception:  # noqa: BLE001
        pass


def parar(playerid=None):
    """Manda o player parar pelo caminho normal (grava retomada no banco)."""
    if playerid is None:
        ativos = _rpc('Player.GetActivePlayers').get('result', [])
        if not ativos:
            return False
        playerid = ativos[0].get('playerid', 1)
    try:
        xbmc.executeJSONRPC(json.dumps({
            'jsonrpc': '2.0', 'id': 1, 'method': 'PlayerControl',
            'params': {'playerid': playerid, 'command': 'stop'},
        }))
        _log('player parado com calma (playerid %s)' % playerid)
        return True
    except Exception as erro:  # noqa: BLE001
        _log('PlayerControl falhou (%s)' % erro, xbmc.LOGWARNING)
        return False


def encerrar():
    """Salva o ponto e para o player. Chamado quando o Kodi vai fechar."""
    dados = ponto()
    if dados:
        salvar(dados)
        parar(dados.get('playerid'))
        time.sleep(0.5)          # deixa o Kodi gravar o ponto no banco
    return True


def continuar(dados=None):
    """Abre o último ponto salvo com StartOffset (menu VIP)."""
    dados = dados or ultimo()
    if not dados:
        return False
    try:
        item = xbmcgui.ListItem(label=dados.get('titulo') or 'Retomar')
        item.setPath(dados['arquivo'])
        item.setProperty('StartOffset', str(int(dados.get('posicao', 0))))
        if dados.get('titulo'):
            item.setInfo('video', {'title': dados['titulo']})
        xbmc.Player().play(dados['arquivo'], item)
        _log('retomando %s em %ds' % (dados.get('titulo'), dados.get('posicao', 0)))
        return True
    except Exception as erro:  # noqa: BLE001
        _log('nao consegui retomar (%s)' % erro, xbmc.LOGWARNING)
        return False


class MonitorRetomar(xbmc.Monitor):
    """Guarda o ponto durante a sessão e encerra o player ao fechar o app."""

    def __init__(self, log=None):
        xbmc.Monitor.__init__(self)
        self._log = log
        self._ultimo = 0

    def _registro(self, mensagem, nivel=None):
        if callable(self._log):
            self._log(mensagem)
        else:
            _log(mensagem, nivel)

    def onAbortRequested(self):
        try:
            encerrar()
            self._registro('ponto salvo e player encerrado antes de fechar')
        except Exception as erro:  # noqa: BLE001
            self._registro('falha ao encerrar (%s)' % erro)

    def run(self):
        while not self.abortRequested():
            if self.waitForAbort(INTERVALO):
                return
            dados = ponto()
            if not dados:
                continue
            if dados.get('posicao', 0) < MINIMO:
                continue
            salvar(dados)


def iniciar(log=None):
    """Thread de acompanhamento, uma por sessão do Kodi."""
    import threading

    monitor = MonitorRetomar(log)
    thread = threading.Thread(target=monitor.run, name='smarted-retomar')
    thread.daemon = True
    thread.start()
    _log('acompanhamento do ponto de retomada ligado')
    return monitor
