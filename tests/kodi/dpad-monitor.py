"""Observador do d-pad: roda DENTRO do Kodi e NAO age na interface.

Antes o proprio script abria janelas e apertava setas; o bootstrap do app
reimpoe a Home nos primeiros segundos e as duas coisas brigavam, entao a prova
acusava falha sem haver defeito. Agora:

* quem aperta as teclas e o CI (adb), como um controle remoto de verdade;
* este script so LE: janela atual, controle com foco (``Control.HasFocus``,
  que e condicao, nao infolabel) e os rotulos da lista, uma linha por leitura.

Marcadores lidos pelo CI:
  SMARTED_DPAD_SNAP <janela>|<controle>|<n_itens>|<rotulo_item_0>|...
  SMARTED_DPAD_INICIO / SMARTED_DPAD_FIM
"""
import os
import time
import xml.etree.ElementTree as ET

import xbmc
import xbmcvfs

DURACAO = 600
PASSO = 0.4
MAX_ROTULOS = 6

XML_DA_JANELA = {
    'home': ('Home.xml',),
    'vídeos': ('MyVideoNav.xml',), 'videos': ('MyVideoNav.xml',),
    'ajustes': ('Settings.xml',), 'settings': ('Settings.xml',),
}
XML_PADRAO = ('MyVideoNav.xml', 'Home.xml', 'Settings.xml')
FOCAVEIS = {'button', 'radiobutton', 'togglebutton', 'spincontrol', 'list',
            'panel', 'grouplist', 'fixedlist', 'wraplist', 'textbox', 'edit',
            'slider', 'mover', 'colorbutton'}
_CACHE = {}


def _log(mensagem):
    xbmc.log(mensagem, xbmc.LOGWARNING)


def _info(rotulo):
    try:
        return (xbmc.getInfoLabel(rotulo) or '').strip()
    except Exception:
        return ''


def _cond(expressao):
    try:
        return bool(xbmc.getCondVisibility(expressao))
    except Exception:
        return False


def janela():
    return _info('System.CurrentWindow')


def ids_da_janela():
    """Ids focaveis declarados nos XMLs da janela atual (cacheado)."""
    chave = janela().lower()
    if chave in _CACHE:
        return _CACHE[chave]
    nomes = XML_DA_JANELA.get(chave, XML_PADRAO)
    bases = []
    for especial in ('special://home/addons', 'special://xbmc/addons'):
        try:
            bases.append(xbmcvfs.translatePath(especial))
        except Exception:
            pass
    vistos = []
    for skin in ('skin.estilo.personalizado', 'skin.novatv'):
        for nome in nomes:
            caminho = ''
            for base in bases:
                tentativa = os.path.join(base, skin, 'xml', nome)
                if os.path.exists(tentativa):
                    caminho = tentativa
                    break
            if not caminho:
                continue
            try:
                raiz = ET.parse(caminho).getroot()
            except Exception as erro:
                _log('SMARTED_DPAD_ERRO_XML %s: %s' % (caminho, erro))
                continue
            for controle in raiz.iter('control'):
                cid = controle.get('id')
                if controle.get('type') in FOCAVEIS and cid and cid not in vistos:
                    vistos.append(cid)
    _CACHE[chave] = vistos
    _log('SMARTED_DPAD_IDS (%s, %d)' % (chave, len(vistos)))
    return vistos


def foco():
    for cid in ids_da_janela():
        if _cond('Control.HasFocus(%s)' % cid):
            return cid
    return '?'


def itens():
    rotulos = []
    for indice in range(MAX_ROTULOS):
        valor = _info('ListItemAbsolute(%d).Label' % indice)
        if not valor:
            break
        rotulos.append(valor.replace('|', '/'))
    return rotulos


# Arquivo proprio: o kodi.log e ROTACIONADO quando o app reinicia o Kodi e a
# leitura por ele voltava vazia (a prova lia zero linhas e acusava defeito).
try:
    ARQUIVO = xbmcvfs.translatePath('special://temp/dpad-observador.log')
except Exception:
    ARQUIVO = '/sdcard/dpad-observador.log'


def _gravar(linha):
    _log(linha)
    try:
        with open(ARQUIVO, 'a', encoding='utf-8') as fluxo:
            fluxo.write(linha + '\n')
    except Exception:
        pass


_gravar('SMARTED_DPAD_INICIO arquivo=%s' % ARQUIVO)
fim = time.time() + DURACAO
while time.time() < fim and not xbmc.abortRequested:
    _gravar('SMARTED_DPAD_SNAP %s|%s|%d|%s'
            % (janela(), foco(), len(itens()), '|'.join(itens())))
    time.sleep(PASSO)
_gravar('SMARTED_DPAD_FIM')
