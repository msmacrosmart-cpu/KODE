# -*- coding: utf-8 -*-
"""Otimizações de reprodução para o Brazuca Play (aplicadas no boot).

Duas camadas, ambas nativas e idempotentes:

* ``userdata/advancedsettings.xml`` — cache de **entrada rápida**: buffer curto
  (50 MB) e leitura acelerada (20x), para o player abrir no primeiro trecho em
  vez de esperar encher um buffer grande, e timeouts de rede curtos. É escrito **no perfil do
  usuário** (nunca em ``assets/smarted/profile/``, que é validado por hash pelo
  dex do launcher) e o Kodi aplica na inicialização seguinte.
* ``Settings.SetSettingValue`` via JSON-RPC — as mesmas otimizações de cache da
  interface (``filecache.*``) e a aceleração por hardware do Android
  (``videoplayer.usemediacodecsurface`` / ``videoplayer.usemediacodec``), que
  valem imediatamente e não exigem reiniciar o app.

Nada é inventado: os ids abaixo existem em ``system/settings/settings.xml`` do
Kodi 21 (Omega) e os valores respeitam as listas de opções aceitas
(``filecachememorysizes`` = 16..1024 MB, ``filecachereadfactors`` = 110..5000,
``filecachechunksizes`` = 256 B..1 MB).
"""
from __future__ import absolute_import, unicode_literals

import os

ADVANCEDSETTINGS = 'advancedsettings.xml'
MARKER = 'smartedtv-performance-v2'

# --- interface Settings (JSON-RPC) -----------------------------------------
# Buffer CURTO de proposito: o player comeca a tocar assim que os primeiros
# trechos chegam. Buffer grande (256 MB) segurava a abertura por 10-20 s em
# conexoes medias — o Kodi so libera o video depois de encher o cache.
CACHE_SETTINGS = {
    'filecache.buffermode': 1,        # 1 = cache somente streams da internet
    # 48 MB: o menor valor "cheio" da lista do Kodi a partir de 50 MB. O
    # advancedsettings.xml abaixo manda 50 MB (52428800 bytes) e vale no boot,
    # que e o que segura o primeiro frame.
    'filecache.memorysize': 48,
    'filecache.readfactor': 2000,     # 20x (le os trechos 20x mais rapido que o bitrate)
    'filecache.chunksize': 524288,    # 512 KB por leitura
}

VIDEO_SETTINGS = {
    'videoplayer.usemediacodecsurface': True,   # MediaCodec (Surface) do Android
    'videoplayer.usemediacodec': True,          # decodificador MediaCodec nativo
    # Sem troca de modo de video ao abrir o player: cada ajuste de Hz custa
    # 1-3 s de tela preta antes do primeiro frame.
    'videoplayer.adjustrefreshrate': 0,
}

# --- advancedsettings.xml ---------------------------------------------------
ADVANCED_TEMPLATE = """<!-- {marker}: partida rapida do player (buffer curto + leitura 20x) -->
<advancedsettings version="1.0">
    <cache>
        <!-- 1 = cache apenas de streams da internet (nao segura arquivo local) -->
        <buffermode>1</buffermode>
        <!-- 50 MB: enche rapido e libera o primeiro frame -->
        <memorysize>52428800</memorysize>
        <!-- 20x o bitrate: sem esperar o buffer grande -->
        <readfactor>20.0</readfactor>
    </cache>
    <network>
        <!-- handshake da CDN nao pode segurar o play por 30 s -->
        <curlclienttimeout>15</curlclienttimeout>
        <curllowspeedtime>20</curllowspeedtime>
    </network>
</advancedsettings>
"""


def advanced_path(home):
    return os.path.join(home, 'userdata', ADVANCEDSETTINGS)


def write_advancedsettings(home, log=None):
    """Escreve o advancedsettings.xml otimizado (nunca sobrescreve o do usuário)."""
    path = advanced_path(home)
    if os.path.isfile(path):
        try:
            with open(path) as handle:
                current = handle.read()
        except Exception:
            current = ''
        if MARKER not in current:
            if log:
                log('advancedsettings.xml do usuário preservado')
            return False
    body = ADVANCED_TEMPLATE.format(marker=MARKER)
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    temp = path + '.tmp'
    with open(temp, 'w') as handle:
        handle.write(body)
    os.replace(temp, path)
    if log:
        log('advancedsettings.xml otimizado gravado em %s' % path)
    return True


def apply_settings(jsonrpc, log=None):
    """Aplica cache + aceleração por hardware via JSON-RPC.

    Devolve ``(aplicados, falhas)``; nunca levanta exceção para não derrubar o
    boot por causa de um setting inexistente.
    """
    applied = []
    failed = []
    for setting, value in sorted(CACHE_SETTINGS.items()) + sorted(VIDEO_SETTINGS.items()):
        try:
            response = jsonrpc('Settings.SetSettingValue', {'setting': setting, 'value': value})
            if response.get('error'):
                failed.append(setting)
                if log:
                    log('setting %s recusado: %s' % (setting, response['error']))
                continue
            check = jsonrpc('Settings.GetSettingValue', {'setting': setting})
            current = (check.get('result') or {}).get('value', '<sem resposta>')
            if str(current).lower() in (str(value).lower(), str(int(value)) if isinstance(value, bool) else str(value)):
                applied.append(setting)
            else:
                failed.append(setting)
                if log:
                    log('setting %s não confirmou (ficou %s)' % (setting, current))
        except Exception as error:  # nunca derrubar o boot
            failed.append(setting)
            if log:
                log('setting %s falhou: %s' % (setting, error))
    if log:
        log('performance: %d aplicados, %d recusados' % (len(applied), len(failed)))
    return applied, failed


def ensure_performance(home, jsonrpc, log=None):
    """Roda as duas camadas e devolve o resumo usado nos testes/relatório."""
    wrote = write_advancedsettings(home, log)
    applied, failed = apply_settings(jsonrpc, log)
    return {'advancedsettings': wrote, 'applied': applied, 'failed': failed}
