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

Modo projetor (imagem preta com audio)
-------------------------------------
Alguns projetores Android anunciam MediaCodec, mas o caminho
``MediaCodec (Surface)`` entrega audio sem quadro nenhum (tela preta). Nesses
aparelhos o boot troca para MediaCodec sem Surface e desliga o ajuste
automatico de taxa de quadros, que tambem apaga a imagem em projetores que
renegociam HDMI. A deteccao e conservadora: so pelo nome do aparelho
(projetor/projector e marcas conhecidas); TVs, boxes e sticks continuam com o
caminho rapido com Surface. Tudo com leitura de volta e sem derrubar o boot se
o Kodi recusar uma opcao.

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

# Projetor/Android TV com saida HDMI que apaga a imagem no decoder Surface.
VIDEO_SETTINGS_PROJETOR = {
    'videoplayer.usemediacodecsurface': False,  # Surface: audio sem imagem
    'videoplayer.usemediacodec': True,          # MediaCodec sem Surface
    'videoplayer.adjustrefreshrate': 0,         # nao renegocia HDMI ao abrir canal
}

# Nomes que identificam projetores (System.FriendlyName). Sem acento/minusculo.
PROJETOR_MARCAS = (
    'projetor', 'projector', 'cinebeam', 'the freestyle', 'freestyle',
    'xgimi', 'wanbo', 'byintek', 'magcubic', 'salange', 'yaber', 'vankyo',
    'nebula', 'anker', 'benq', 'epson', 'viewsonic', 'optoma', 'vivitek',
    'pico', 'dlp', 'led projector', 'smart projector', 'home projector',
)

# --- advancedsettings.xml ---------------------------------------------------
# Projetor com 1-2 GB de RAM: os mesmos 256 MB de cache deixam o aparelho
# sem memoria para os addons e a Home (o Kodi passa a "carregar" para sempre e
# pode ficar preto). Cache menor = perfil que carrega.
CACHE_SETTINGS_PROJETOR = {
    'filecache.buffermode': 4,
    'filecache.memorysize': 96,
    'filecache.readfactor': 600,
    'filecache.chunksize': 262144,
}

ADVANCED_TEMPLATE = """<!-- {marker}: cache agressivo para streams do Brazuca Play -->"
<advancedsettings version="1.0">
    <cache>
        <buffermode>4</buffermode>
        <memorysize>{memorysize}</memorysize>
        <readfactor>{readfactor}</readfactor>
    </cache>
    <network>
        <curlclienttimeout>20</curlclienttimeout>
        <curllowspeedtime>30</curllowspeedtime>
    </network>
</advancedsettings>
"""

# Projetor/box/stick com pouca RAM (1-2 GB): 256 MB de cache deixa o aparelho
# sem memoria para os addons e para a Home - a interface passa a "carregar
# para sempre" e o player engasga. O mesmo numero do perfil de projetor vale
# aqui, no arquivo que o Kodi le ANTES de subir os addons.
ADVANCED_CACHE_PROJETOR = (96 * 1024 * 1024, '6.0')


def _sem_acento(texto):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', texto or '')
                   if not unicodedata.combining(c)).lower()


def eh_projetor(nome_dispositivo):
    """True para projetores Android conhecidos (nao confunde TV/box/stick)."""
    nome = _sem_acento(nome_dispositivo)
    return any(marca in nome for marca in PROJETOR_MARCAS)


def video_settings(nome_dispositivo=''):
    """Perfil de video: Surface para TV/box/stick, sem Surface para projetor."""
    if eh_projetor(nome_dispositivo):
        return dict(VIDEO_SETTINGS_PROJETOR)
    return dict(VIDEO_SETTINGS)


def perfil_ja_aprendido():
    """O aparelho ja provou que precisa de MediaCodec sem Surface?

    Quem decide isso e o vigia de TV ao vivo (``ao_vivo.py``): quando o canal
    abre sem nenhum quadro, ele desliga o Surface e grava a marca. Aqui a marca
    e lida no boot para o perfil COMECAR certo, em vez de o aparelho repetir a
    tela preta a cada abertura do app. Ler arquivo local; nao depende de rede.
    """
    try:
        import ao_vivo
        return bool(ao_vivo.fallback_ligado())
    except Exception:
        return False


def advanced_path(home):
    return os.path.join(home, 'userdata', ADVANCEDSETTINGS)


def write_advancedsettings(home, log=None, nome_dispositivo=''):
    """Escreve o advancedsettings.xml otimizado (nunca sobrescreve o do usuário).

    O cache acompanha o aparelho: TV/box/stick/celular com RAM suficiente usam
    256 MB; projetor (e aparelho que ja provou precisar do perfil leve) usa
    96 MB, para nao ficar sem memoria para a Home e para os addons.
    """
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
    cache_pequeno = eh_projetor(nome_dispositivo) or perfil_ja_aprendido()
    memorysize, readfactor = (ADVANCED_CACHE_PROJETOR if cache_pequeno
                              else (256 * 1024 * 1024, '10.0'))
    if log and cache_pequeno:
        log('advancedsettings: cache de %d MB (perfil do aparelho)'
            % (memorysize // (1024 * 1024)))
    body = ADVANCED_TEMPLATE.format(marker=MARKER, memorysize=memorysize,
                                    readfactor=readfactor)
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


def apply_settings(jsonrpc, log=None, nome_dispositivo=''):
    """Aplica cache + aceleração por hardware via JSON-RPC.

    Devolve ``(aplicados, falhas)``; nunca levanta exceção para não derrubar o
    boot por causa de um setting inexistente. Em projetor usa o perfil sem
    MediaCodec Surface (imagem preta com audio).
    """
    applied = []
    failed = []
    perfil = video_settings(nome_dispositivo)
    cache = CACHE_SETTINGS_PROJETOR if eh_projetor(nome_dispositivo) else CACHE_SETTINGS
    if log and cache is CACHE_SETTINGS_PROJETOR:
        log('cache: perfil de projetor (%d MB em vez de %d MB)'
            % (cache['filecache.memorysize'], CACHE_SETTINGS['filecache.memorysize']))
    if perfil_ja_aprendido() and perfil.get('videoplayer.usemediacodecsurface'):
        # Aprendido no proprio aparelho: canal ao vivo ficava sem imagem com
        # Surface. Ganha o mesmo perfil do projetor (sem Surface).
        perfil = dict(VIDEO_SETTINGS_PROJETOR)
        if log:
            log('video: perfil aprendido no aparelho (canal ao vivo sem '
                'imagem com Surface) -> sem MediaCodec Surface')
    if log:
        log('video: %s -> %s' % (
            'projetor (sem Surface)'
            if perfil.get('videoplayer.usemediacodecsurface') is False
            else 'padrao (MediaCodec Surface)', perfil))
    for setting, value in sorted(cache.items()) + sorted(perfil.items()):
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


def ensure_performance(home, jsonrpc, log=None, nome_dispositivo=''):
    """Roda as duas camadas e devolve o resumo usado nos testes/relatório."""
    wrote = write_advancedsettings(home, log, nome_dispositivo=nome_dispositivo)
    applied, failed = apply_settings(jsonrpc, log, nome_dispositivo=nome_dispositivo)
    return {'advancedsettings': wrote, 'applied': applied, 'failed': failed,
            'projetor': eh_projetor(nome_dispositivo)}
