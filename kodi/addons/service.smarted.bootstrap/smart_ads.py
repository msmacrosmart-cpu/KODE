# -*- coding: utf-8 -*-
"""Anuncios do AdMob disparados pelo Kodi (ponte nativa StartAndroidActivity).

O Kodi do APK e um binario pronto: o SDK do AdMob nao pode ser injetado nele sem
recompilar o Kodi inteiro. Por isso o anuncio e exibido pelo app
``org.smartedtv.ads`` (pasta ``android/smarted-ads``), assinado com a mesma
chave da linha, e o Kodi o abre por um builtin nativo:

    StartAndroidActivity(smartedtv.full,,,,,,,,org.smartedtv.ads.PreRollActivity)

ATENCAO a ordem dos parametros do builtin (Kodi v20+):

    StartAndroidActivity(package, intent, dataType, dataURI, flags, extras,
                         action, category, className)

O className e o NONO parametro, nao o segundo. Passar a classe em segundo lugar
faz o Kodi montar um intent com action = nome da classe e sem componente — o
Android nao acha ninguem e a tela de anuncio nunca abre (foi exatamente o bug
que deixou os anuncios "sem preencher": na verdade nem eram pedidos).

Dois gatilhos:

1. ABERTURA — uma unica vez, poucos segundos depois de a Home carregar
   (bloco ca-app-pub-2066014755407744/4214378379);
2. PRE-ROLL — sempre que um canal, filme ou serie comeca a tocar
   (bloco ca-app-pub-2066014755407744/3572039686). A tela do anuncio cobre o
   player enquanto o buffer acontece atras.

Nada aqui pode quebrar a reproducao: se o app de anuncios nao estiver
instalado, se o Kodi nao for Android ou se o builtin falhar, o video segue
normalmente.
"""
from __future__ import absolute_import, unicode_literals

import os
import time

import xbmc
import xbmcvfs

# PACKAGE = applicationId do app de anuncios (android/smarted-ads/app-id.txt).
# Precisa ser um pacote proprio: org.xbmc.kodi e o pacote do Kodi e o Android
# nao aceita dois apps com o mesmo nome — um sobrescreveria o outro.
# As CLASSES continuam no namespace org.smartedtv.ads (o applicationId nao muda
# o nome das classes): e por isso que a ponte leva pacote e classe separados.
PACKAGE = 'smartedtv.full'
ATIVIDADE_ABERTURA = 'org.smartedtv.ads.AppOpenActivity'
ATIVIDADE_PREROLL = 'org.smartedtv.ads.PreRollActivity'

# marcas para o relatorio do boot
MARKER = 'smartedtv-ads-v1'

# quanto esperar a Home desenhar antes do pop-up de abertura
ABERTURA_DELAY = 6

# dois anuncios em sequencia (zapping, proximo episodio) atrapalham: intervalo
# minimo entre pre-rolls. Ajuste aqui se quiser mais ou menos frequencia.
PREROLL_INTERVALO = 120


def _marker_path():
    try:
        perfil = xbmcvfs.translatePath('special://profile')
    except Exception:
        return None
    return os.path.join(perfil, 'addon_data', 'service.smarted.bootstrap',
                        'ads-abertura.txt')


def abertura_ja_mostrada():
    caminho = _marker_path()
    if not caminho:
        return False
    try:
        return xbmcvfs.exists(caminho)
    except Exception:
        return False


def marcar_abertura(quando=None):
    caminho = _marker_path()
    if not caminho:
        return False
    try:
        pasta = os.path.dirname(caminho)
        if pasta and not os.path.isdir(pasta):
            os.makedirs(pasta)
        with open(caminho, 'w') as arquivo:
            arquivo.write('abertura mostrada em %s\n'
                          % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(quando)))
        return True
    except Exception:
        return False


def android():
    """So tenta a ponte nativa quando o Kodi esta rodando no Android."""
    try:
        return bool(xbmc.getCondVisibility('System.Platform.Android'))
    except Exception:
        return False


def builtin_para(atividade, package=None):
    """Builtin com os 9 parametros na ordem do Kodi (className e o ultimo).

    Campos vazios no meio sao obrigatorios: o parser do builtin separa por
    virgula e as posicoes precisam ser respeitadas.
    """
    campos = [package or PACKAGE] + [''] * 7 + [atividade]
    return 'StartAndroidActivity(%s)' % ','.join(campos)


def tocar_anuncio(atividade, log=None):
    """Abre a tela de anuncio do app SMARTEDTV Ads. Devolve True se disparou."""
    if not android():
        if log:
            log('[SmartAds] ignorado (nao e Android)')
        return False
    builtin = builtin_para(atividade)
    try:
        xbmc.executebuiltin(builtin)
    except Exception as erro:
        if log:
            log('[SmartAds] %s falhou (%s)' % (builtin, erro), xbmc.LOGWARNING)
        return False
    if log:
        # este e o log que aparece no kodi.log quando o disparo acontece
        log('[SmartAds] disparando %s -> %s/%s'
            % (builtin, PACKAGE, atividade))
    return True


def mostrar_preroll(log=None, intervalo=PREROLL_INTERVALO, agora=None):
    """Video pre-roll antes de canal/filme/serie (respeita o intervalo)."""
    agora = time.time() if agora is None else agora
    if agora - globals().get('_ultimo_preroll', 0.0) < intervalo:
        return False
    disparou = tocar_anuncio(ATIVIDADE_PREROLL, log)
    if disparou:
        globals()['_ultimo_preroll'] = agora
    return disparou


def mostrar_abertura(log=None):
    """Pop-up de abertura: exatamente uma vez por instalacao."""
    if abertura_ja_mostrada():
        if log:
            log('[SmartAds] abertura ja exibida nesta instalacao')
        return False
    if not tocar_anuncio(ATIVIDADE_ABERTURA, log):
        return False
    marcar_abertura()
    if log:
        log('[SmartAds] pop-up de abertura disparado (uma vez por instalacao)')
    return True


def abertura_depois_do_boot(monitor, log=None):
    """Espera a Home aparecer e mostra o pop-up (roda em thread propria)."""
    try:
        if monitor.waitForAbort(ABERTURA_DELAY):
            return False
    except Exception:
        time.sleep(ABERTURA_DELAY)
    try:
        if xbmc.Player().isPlayingVideo():
            if log:
                log('[SmartAds] abertura adiada (video ja em reproducao)')
            return False
    except Exception:
        pass
    return mostrar_abertura(log)


def _e_video(player):
    try:
        return bool(player.isPlayingVideo())
    except Exception:
        return False


# Dentro do Kodi isto e xbmc.Player; fora dele (testes, PC sem Kodi) vira
# object, para o modulo poder ser importado em qualquer lugar.
_BasePlayer = getattr(xbmc, 'Player', object)


class MonitorPreRoll(_BasePlayer):
    """Escuta o inicio de QUALQUER stream e chama o pre-roll.

    Vale para canal de TV, filme e serie, venha do Brazuca ou de outro addon:
    o gancho e o proprio xbmc.Player, nao a rota do addon.
    """

    def __init__(self, log=None, intervalo=PREROLL_INTERVALO):
        if _BasePlayer is not object:
            _BasePlayer.__init__(self)
        self.log = log
        self.intervalo = intervalo

    def onPlay(self, **kwargs):  # Kodi chama no inicio do stream (buffer incluso)
        self._talvez_mostrar()

    def onAVStarted(self):
        # alguns streams so disparam aqui; o intervalo evita anuncio duplicado
        self._talvez_mostrar()

    def _talvez_mostrar(self):
        try:
            if not _e_video(self):
                return
            mostrar_preroll(self.log, self.intervalo)
        except Exception as erro:  # nunca derrubar o servico por causa do anuncio
            if self.log:
                self.log('[SmartAds] pre-roll falhou (%s)' % erro, xbmc.LOGWARNING)


_monitor = None


def iniciar_monitor(log=None, intervalo=PREROLL_INTERVALO):
    """Liga o gancho de reproducao uma vez por sessao."""
    global _monitor
    if _monitor is not None or not android():
        return _monitor
    try:
        _monitor = MonitorPreRoll(log, intervalo)
        if log:
            log('[SmartAds] gancho de pre-roll ligado (%s, minimo %d s entre anuncios)'
                % (MARKER, intervalo))
    except Exception as erro:
        if log:
            log('[SmartAds] nao foi possivel ligar o pre-roll (%s)' % erro, xbmc.LOGWARNING)
        _monitor = None
    return _monitor


def monitor():
    return _monitor
