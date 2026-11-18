"""Observador de d-pad/filtro: roda DENTRO do Kodi, sem tocar em nada.

Nao altera arquivos, nao abre janela e nao muda configuracao: apenas le as
infolabels oficiais e o Container da janela ativa (JSON-RPC interno, sem rede)
e escreve uma linha no kodi.log.

Uso no teste:
  F10                     -> imprime um SNAPSHOT do estado atual
  SMARTED_DPAD_TICK ...   -> linha automatica a cada mudanca de foco

Marcadores (lidos pelo CI):
  SMARTED_DPAD_SNAP <janela>|<controle_id>|<controle_label>|<folderpath>|<ordem>
  SMARTED_DPAD_ITEM <n>|<rotulo>          (um por item da lista, ate 40)
  SMARTED_DPAD_TICK <janela>|<controle_id>|<controle_label>
  SMARTED_DPAD_FIM
"""
import json
import time

import xbmc

DURACAO = 300          # segundos de observacao (o CI aperta as teclas)
PASSO = 0.25
MAX_ITENS = 40


def _info(rotulo):
    try:
        return (xbmc.getInfoLabel(rotulo) or '').strip()
    except Exception:
        return ''


def _rpc(method, params=None):
    try:
        resposta = xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}))
        return json.loads(resposta).get('result') or {}
    except Exception:
        return {}


def _log(mensagem):
    xbmc.log(mensagem, xbmc.LOGWARNING)


def linha_de_estado():
    janela = _rpc('GUI.GetProperties', {'properties': ['currentwindow']}).get('currentwindow', {})
    controle = _rpc('GUI.GetProperties', {'properties': ['currentcontrol']}).get('currentcontrol', {})
    return [
        str(janela.get('label', '')),
        str(controle.get('id', '')),
        str(controle.get('label', '')),
        _info('Container.FolderPath'),
        _info('Container.SortMethod'),
    ]


def snapshot():
    """Estado completo: janela, foco, pasta e os rotulos da lista."""
    partes = linha_de_estado()
    _log('SMARTED_DPAD_SNAP ' + '|'.join(partes))
    itens = _rpc('Container.GetItems', {'submenu': 'all'}).get('items') or []
    for indice, item in enumerate(itens[:MAX_ITENS]):
        rotulo = (item.get('label') or '').strip().replace('|', '/')
        _log('SMARTED_DPAD_ITEM %d|%s' % (indice, rotulo))
    _log('SMARTED_DPAD_NUM %d' % len(itens))


_log('SMARTED_DPAD_INICIO')
snapshot()
anterior = linha_de_estado()[:3]
fim = time.time() + DURACAO
while time.time() < fim and not xbmc.abortRequested:
    atual = linha_de_estado()[:3]
    if atual != anterior:
        anterior = atual
        _log('SMARTED_DPAD_TICK ' + '|'.join(atual))
    # O CI aperta F10 de novo para tirar novo snapshot; o proprio Kodi mata a
    # instancia anterior quando o script e chamado outra vez (mesmo addon).
    time.sleep(PASSO)
_log('SMARTED_DPAD_FIM')
