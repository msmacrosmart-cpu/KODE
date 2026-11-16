# -*- coding: utf-8 -*-
"""Abertura da tela de entrada entregue no ZIP (script.smartedtv.welcome).

Este modulo pertence ao servico de boot que ja existe (service.smarted.bootstrap)
e NAO cria interface nenhuma: ele apenas executa o ``default.py`` do addon
``script.smartedtv.welcome`` (os 15 arquivos do ZIP, sem alteracao visual) e
confirma que a janela realmente carregou.

Por que nao usar ``RunScript(script.smartedtv.welcome)`` sozinho:

* no Kodi Omega 21 o ``RunScript(addonid)`` resolve o addon somente quando ele
  esta habilitado no ``Addons33.db`` (``OnlyEnabled::CHOICE_YES``); em perfis que
  o cliente ja tinha, um addon novo pode ficar registrado como desabilitado e o
  comando e ignorado sem nenhum aviso;
* o addon da tela e opcional no ``addon-manifest.xml``; a sincronizacao do banco
  so forca ``enabled=1`` para addons de sistema obrigatorios.

Por isso a tela e carregada diretamente do arquivo (import + ``open_welcome()``)
no proprio interpretador do servico, com ``RunScript`` por caminho como plano B.
"""
from __future__ import absolute_import, unicode_literals

import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

WELCOME_ADDON = 'script.smartedtv.welcome'
WELCOME_SCRIPT = 'default.py'
WELCOME_MARCA = 'smartedtv.welcome.ativa'
WELCOME_TENTATIVAS = 20
WELCOME_ESPERA = 1
WELCOME_ABERTURA_TENTATIVAS = 3
WELCOME_LOG = 'smarted-tela-entrada.log'

_LOGGER = None


def registrar(mensagem, nivel=None):
    """Registra no log do Kodi e em userdata/smarted-tela-entrada.log."""
    nivel = xbmc.LOGINFO if nivel is None else nivel
    if _LOGGER is not None:
        try:
            _LOGGER('tela de entrada: %s' % mensagem, nivel)
        except Exception:
            pass
    try:
        xbmc.log('[%s] %s' % (WELCOME_ADDON, mensagem), nivel)
    except Exception:
        pass
    try:
        arquivo_log = os.path.join(xbmcvfs.translatePath('special://home'),
                                   'userdata', WELCOME_LOG)
        pasta = os.path.dirname(arquivo_log)
        if pasta and not os.path.isdir(pasta):
            os.makedirs(pasta)
        with open(arquivo_log, 'a') as arquivo:
            arquivo.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), mensagem))
    except Exception:
        pass


def caminho_da_tela():
    """Caminho absoluto do default.py da tela, sem depender do banco de addons."""
    candidatos = []
    for raiz in ('special://xbmc/addons/', 'special://home/addons/'):
        try:
            candidatos.append(os.path.join(
                xbmcvfs.translatePath(raiz + WELCOME_ADDON), WELCOME_SCRIPT))
        except Exception:
            continue
    try:
        candidatos.append(os.path.join(
            xbmcvfs.translatePath(
                xbmcaddon.Addon(WELCOME_ADDON).getAddonInfo('path')),
            WELCOME_SCRIPT))
    except Exception:
        pass

    for candidato in candidatos:
        caminho = os.path.normpath(candidato)
        try:
            if xbmcvfs.exists(caminho):
                return caminho
        except Exception:
            if os.path.isfile(caminho):
                return caminho
    registrar('default.py nao encontrado; candidatos: %r' % candidatos,
              xbmc.LOGERROR)
    return None


def janela_ativa():
    """Confirma que a tela carregou (propriedade marcada no onInit do dialogo)."""
    try:
        return xbmc.getInfoLabel(
            'Window(10000).Property(%s)' % WELCOME_MARCA) == '1'
    except Exception:
        return False


def executar_no_servico(caminho):
    """Carrega o default.py do ZIP e chama open_welcome() neste interpretador."""
    import importlib.util

    spec = importlib.util.spec_from_file_location('smartedtv_welcome_runtime',
                                                  caminho)
    if spec is None or spec.loader is None:
        raise RuntimeError('nao foi possivel carregar %s' % caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.open_welcome()


def abrir_tela_entrada(monitor, logger=None):
    """Abre a tela do ZIP uma unica vez por inicializacao do SMARTEDTV.

    O dialogo e independente: aparece na frente da interface principal, sem
    substitui-la, e devolve o controle a ela quando o usuario conclui uma acao
    ou pressiona Voltar. Nenhum fluxo novo de negocio e criado aqui.
    """
    global _LOGGER
    _LOGGER = logger

    # 1) sem a Home ativa nao existe janela para receber o dialogo
    pronto = False
    for _tentativa in range(WELCOME_TENTATIVAS):
        if monitor.abortRequested():
            return
        if xbmc.getCondVisibility('Window.IsActive(10000)'):
            pronto = True
            break
        if monitor.waitForAbort(WELCOME_ESPERA):
            return
    if not pronto:
        registrar('Home (janela 10000) nao ficou ativa; tela nao exibida',
                  xbmc.LOGERROR)
        return

    # 2) localiza os arquivos do ZIP (addons de sistema do APK)
    caminho = None
    for _tentativa in range(WELCOME_TENTATIVAS):
        if monitor.abortRequested():
            return
        caminho = caminho_da_tela()
        if caminho:
            break
        try:
            xbmc.executebuiltin('UpdateLocalAddons()')
        except Exception:
            pass
        if monitor.waitForAbort(WELCOME_ESPERA):
            return
    if not caminho:
        return
    registrar('abrindo a tela a partir de %s' % caminho)

    try:
        xbmc.executebuiltin('ClearProperty(%s,10000)' % WELCOME_MARCA)
    except Exception:
        pass

    # 3) metodo principal: abrir no proprio interpretador do servico
    for tentativa in range(WELCOME_ABERTURA_TENTATIVAS):
        if monitor.abortRequested():
            return
        try:
            executar_no_servico(caminho)
        except Exception as erro:
            registrar('falha ao abrir no servico: %s' % erro, xbmc.LOGERROR)
        if janela_ativa():
            registrar('tela exibida e fechada pelo usuario')
            return
        registrar('tentativa %d nao confirmou a janela' % (tentativa + 1),
                  xbmc.LOGWARNING)

        # 4) plano B: RunScript pelo caminho do arquivo (nao pelo id do addon)
        try:
            xbmc.executebuiltin('RunScript("%s")' % caminho)
        except Exception as erro:
            registrar('RunScript falhou: %s' % erro, xbmc.LOGERROR)
        for _ in range(10):
            if monitor.waitForAbort(1):
                return
            if janela_ativa():
                registrar('tela exibida via RunScript')
                return
    registrar('janela nao confirmada; a interface principal segue normal',
              xbmc.LOGERROR)
