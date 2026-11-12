# -*- coding: utf-8 -*-
"""Otimizações de reprodução para o Brazuca Play (aplicadas no boot).

Duas camadas, ambas nativas e idempotentes:

* ``userdata/advancedsettings.xml`` — cache de arquivo agressivo em memória e
  timeouts de rede mais tolerantes a CDNs lentas. É escrito **no perfil do
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
MARKER = 'smartedtv-performance-v1'

# --- interface Settings (JSON-RPC) -----------------------------------------
CACHE_SETTINGS = {
    'filecache.buffermode': 4,        # 4 = cache para todos os arquivos/streams
    'filecache.memorysize': 256,      # MB
    'filecache.readfactor': 1000,     # 10x
    'filecache.chunksize': 524288,    # 512 KB
}

VIDEO_SETTINGS = {
    'videoplayer.usemediacodecsurface': True,   # MediaCodec (Surface) do Android
    'videoplayer.usemediacodec': True,          # decodificador MediaCodec nativo
}

# --- advancedsettings.xml ---------------------------------------------------
ADVANCED_TEMPLATE = """<!-- {marker}: cache agressivo para streams do Brazuca Play -->
<advancedsettings version="1.0">
    <cache>
        <buffermode>4</buffermode>
        <memorysize>268435456</memorysize>
        <readfactor>10.0</readfactor>
    </cache>
    <network>
        <curlclienttimeout>20</curlclienttimeout>
        <curllowspeedtime>30</curllowspeedtime>
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
