# -*- coding: utf-8 -*-
"""TV ao vivo: canal com som (ou mudo) e imagem preta.

O relato que este modulo atende: **so os canais de "TV ao vivo" ficam com tela
preta**; filmes e series tocam normal. Filme/serie, no Brazuca, e um arquivo
unico (MP4/HLS com duracao, buscavel). Canal ao vivo e um fluxo continuo sem
duracao, reaberto a cada troca.

Tres coisas quebram so no fluxo continuo:

1. **Retomada de posicao.** O retorno do anuncio (``ad_return``) devolvia o
   player para a posicao guardada com ``Player.Seek``. Em VOD isso e correto.
   Em canal ao vivo o ponto guardado fica FORA da janela disponivel: o Kodi
   busca no passado que nao existe mais e a tela fica preta (as vezes com som,
   as vezes sem nada) ate o usuario trocar de canal. Aqui a regra e explicita:
   **ao vivo nunca recebe seek**.
2. **Fluxo que nao volta sozinho.** Quando o player foi pausado pelo anuncio e
   o canal sai do ar naquele intervalo, o Kodi nao retoma: a janela do player
   fica sem quadro nenhum. Nesse caso a unica volta confiavel e reabrir o canal
   (PlayMedia do mesmo endereco) para entrar no ponto atual da transmissao.
3. **Decoder sem imagem.** ``videoplayer.usemediacodecsurface=true`` entrega
   audio e nenhum quadro em alguns chips com fluxo TS/MPEG-TS ao vivo (o
   mesmo defeito que o projetor tem com qualquer video). Como nao ha aparelho
   aqui para medir, o modulo **observa** o player: sem ``videowidth``/codec de
   video depois de abrir, desliga o Surface, reabre o canal uma unica vez e
   grava a escolha, para o proximo boot ja comecar no perfil que funcionou.

Nada aqui inventa dado: a deteccao usa o endereco que o player informa
(``.m3u8``/``.ts``/``mode=11`` do Brazuca) e os infolabels oficiais do Kodi
(``Player.Process(videowidth)``, ``videocodec``, ``VideoPlayer.Content(live)``).
"""
from __future__ import absolute_import, unicode_literals

import os
import time

import xbmc
import xbmcvfs

# Extensoes que este app entrega como canal continuo. ``.mpd`` NAO entra: no
# Brazuca ele e usado tambem para VOD com duracao.
EXTENSOES = ('.m3u8', '.m3u', '.ts', '.mpegts', '.m2ts')

# O addon abre canal pelo resolver dele (``mode=11`` = play do canal).
MODO_CANAL = 'mode=11'

# Espera para o player entregar o primeiro quadro antes de desconfiar.
ESPERA_PADRAO = 12.0
PASSO = 0.5

MARKER = 'smartedtv-ao-vivo-v1'
FALLBACK_ARQUIVO = 'ao-vivo-sem-surface.txt'


def _marker_path():
    """Caminho do arquivo de perfil aprendido (perfil real do Kodi).

    Exige caminho absoluto: em Kodi ``special://profile`` sempre resolve para
    um caminho real. Se nao resolver (teste fora do aparelho), nao se grava
    nada - marca em caminho relativo nao serve para nada.
    """
    try:
        perfil = xbmcvfs.translatePath('special://profile')
    except Exception:
        return None
    if not perfil or not os.path.isabs(perfil):
        return None
    return os.path.join(perfil, 'addon_data', 'service.smarted.bootstrap',
                        FALLBACK_ARQUIVO)


def _label(rotulo):
    try:
        return xbmc.getInfoLabel(rotulo) or ''
    except Exception:
        return ''


def eh_ao_vivo(caminho='', canal_pvr=None):
    """O que esta tocando e um canal continuo (ao vivo)?"""
    if canal_pvr is None:
        try:
            canal_pvr = bool(xbmc.getCondVisibility('VideoPlayer.Content(live)'))
        except Exception:
            canal_pvr = False
    if canal_pvr:
        return True
    endereco = (caminho or '').lower()
    if not endereco:
        return False
    if MODO_CANAL in endereco:
        return True
    if 'channel' in endereco or 'canal' in endereco or 'aovivo' in endereco:
        return True
    # tira a query antes de olhar a extensao: ``...?token=abc`` nao engana
    base = endereco.split('?', 1)[0]
    return any(base.endswith(ext) for ext in EXTENSOES)


def tem_imagem():
    """O player ja tem quadro de video (largura/codec informados)?"""
    for rotulo in ('Player.Process(videowidth)', 'VideoPlayer.VideoResolution'):
        valor = _label(rotulo).strip()
        if valor and valor not in ('0', '0x0'):
            return True
    for rotulo in ('Player.Process(videocodec)', 'VideoPlayer.VideoCodec'):
        if _label(rotulo).strip():
            return True
    return False


def tem_audio():
    for rotulo in ('Player.Process(audiocodec)', 'VideoPlayer.AudioCodec',
                   'Player.Process(audiosamplerate)'):
        if _label(rotulo).strip():
            return True
    return False


def fallback_ligado():
    """O perfil sem MediaCodec Surface ja foi escolhido neste aparelho?"""
    caminho = _marker_path()
    if not caminho:
        return False
    try:
        if not os.path.exists(caminho):
            return False
        with open(caminho) as arquivo:
            return MARKER in arquivo.read()
    except Exception:
        return False


def marcar_fallback(log=None):
    """Grava a escolha para o proximo boot (perfil ja testado no aparelho)."""
    caminho = _marker_path()
    if not caminho:
        return False
    try:
        pasta = os.path.dirname(caminho)
        if pasta and not os.path.isdir(pasta):
            os.makedirs(pasta)
        with open(caminho, 'w') as arquivo:
            arquivo.write('%s\nvideo: sem MediaCodec Surface (canal ao vivo '
                          'estava sem imagem)\n' % MARKER)
        if log:
            log('[AoVivo] perfil salvo: proximo boot sem MediaCodec Surface')
        return True
    except Exception as erro:
        if log:
            log('[AoVivo] nao consegui salvar o perfil (%s)' % erro,
                xbmc.LOGWARNING)
        return False


def aplicar_fallback(log=None):
    """Desliga MediaCodec Surface pelo JSON-RPC e confere a leitura."""
    import json

    def definir(setting, valor):
        pedido = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.SetSettingValue',
                  'params': {'setting': setting, 'value': valor}}
        try:
            resposta = json.loads(xbmc.executeJSONRPC(json.dumps(pedido)))
        except Exception:
            return False
        return 'error' not in resposta

    mudou = definir('videoplayer.usemediacodecsurface', False)
    definir('videoplayer.adjustrefreshrate', 0)  # nao renegocia HDMI no canal
    if log:
        log('[AoVivo] MediaCodec Surface %s' %
            ('desligado' if mudou else 'nao aceito pelo Kodi'), xbmc.LOGWARNING)
    return mudou


def _tocar_de_novo(caminho):
    """Reabre o canal pelo proprio player (entra no ponto atual da transmissao)."""
    if not caminho:
        return False
    try:
        xbmc.executebuiltin('PlayMedia("%s")' % caminho.replace('"', '%22'))
        return True
    except Exception:
        return False


def vigiar(player, caminho='', log=None, espera=ESPERA_PADRAO):
    """Confere a imagem de um canal; se nao houver, escolhe o perfil que funciona.

    Devolve ``'ok'`` (imagem apareceu), ``'reaberto'`` (fallback aplicado e
    canal reaberto), ``'ignorado'`` (nao e ao vivo / nao esta tocando) ou
    ``'sem-imagem'`` (sem Surface e ainda sem imagem: nada mais a fazer aqui,
    fica registrado no log para o proximo diagnostico).
    """
    caminho = caminho or ''
    if not caminho:
        try:
            caminho = player.getPlayingFile()
        except Exception:
            caminho = ''
    if not eh_ao_vivo(caminho):
        return 'ignorado'
    limite = time.time() + max(2.0, espera)
    viu_audio = False
    while time.time() < limite:
        try:
            if not player.isPlayingVideo():
                return 'ignorado'
        except Exception:
            return 'ignorado'
        if tem_imagem():
            if log:
                log('[AoVivo] imagem ok em %s' % caminho[-60:])
            return 'ok'
        viu_audio = viu_audio or tem_audio()
        time.sleep(PASSO)
    if log:
        log('[AoVivo] canal sem imagem depois de %.0fs (audio=%s): %s'
            % (espera, 'sim' if viu_audio else 'nao', caminho[-70:]),
            xbmc.LOGWARNING)
    if fallback_ligado():
        if log:
            log('[AoVivo] perfil sem Surface ja estava ativo: nada a reabrir',
                xbmc.LOGWARNING)
        return 'sem-imagem'
    aplicar_fallback(log)
    marcar_fallback(log)
    if _tocar_de_novo(caminho):
        if log:
            log('[AoVivo] canal reaberto com o perfil sem Surface')
        return 'reaberto'
    return 'sem-imagem'


def iniciar(player, caminho='', log=None, espera=ESPERA_PADRAO):
    """Roda ``vigiar`` numa thread, para nao travar o player nem o anuncio."""
    import threading
    def trabalho():
        try:
            vigiar(player, caminho, log, espera)
        except Exception as erro:  # nunca derrubar o servico
            if log:
                log('[AoVivo] vigia falhou (%s)' % type(erro).__name__,
                    xbmc.LOGWARNING)

    thread = threading.Thread(target=trabalho, name='ao-vivo-imagem',
                              daemon=True)
    thread.start()
    return thread
