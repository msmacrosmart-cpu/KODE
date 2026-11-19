# -*- coding: utf-8 -*-
"""Diagnostico da tag VAST do app, passo a passo, com O MODULO REAL.

Le ``ads_vast.VAST_TAG_PADRAO``, pede a tag, escolhe o criativo, abre o
arquivo de video do anuncio e faz o caminho de exibicao com player falso (so
para ver se o player receberia a URL). Cada passo sai em uma linha ``::notice::``
para o dono do app ver onde parou.

Uso:  python3 tools/kodi/diag-vast-tag.py            (tag padrao do modulo)
      python3 tools/kodi/diag-vast-tag.py URL        (outra tag)
"""
from __future__ import print_function

import importlib.util
import os
import sys
import types
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULO = os.path.join(RAIZ, 'kodi', 'addons', 'service.smarted.bootstrap',
                      'ads_vast.py')


def aviso(texto):
    limpo = ' '.join(str(texto).replace('\r', ' ').replace('\n', ' ').split())
    print('::notice::' + limpo[:900])


def _xbmc_falso():
    """Kodi minimo: sem aparelho, sem player de verdade, sem rede interna."""
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
    xbmc.getInfoLabel = lambda _s: ''
    xbmc.getCondVisibility = lambda _s: False
    xbmc.executebuiltin = lambda *a, **k: None
    xbmc.log = lambda *a, **k: None
    xbmc.Player = lambda *a, **k: types.SimpleNamespace(
        isPlaying=lambda: False, isPlayingVideo=lambda: False,
        getPlayingFile=lambda: '', getTime=lambda: 0.0, getTotalTime=lambda: 0.0)
    sys.modules['xbmc'] = xbmc


def carregar(caminho=MODULO):
    spec = importlib.util.spec_from_file_location('ads_vast_diag', caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def diagnosticar(tag=None, modulo=None):
    """Devolve (ok, recibo/dict). Sem rede aqui isto reporta e para."""
    _xbmc_falso()
    vast = modulo or carregar()
    tag = (tag or vast.VAST_TAG_PADRAO or '').strip()
    aviso('tag = %s' % tag)
    if not tag:
        aviso('FALHOU: sem tag')
        return False, {'motivo': 'sem-tag'}
    dados = vast.baixar(tag)
    aviso('resposta: %s bytes' % (len(dados) if dados else 0))
    if not dados:
        return False, {'motivo': 'tag-sem-resposta'}
    anuncio = vast.escolher_anuncio(dados, 1080)
    if not anuncio:
        aviso('FALHOU: escolher_anuncio=None (VAST sem criativo legivel)')
        return False, {'motivo': 'vast-sem-criativo'}
    aviso('criativo = %s' % anuncio['url'][:140])
    aviso('tipo=%s duracao=%ss skip=%ss impressoes=%d' % (
        anuncio['tipo'], anuncio['duracao'], anuncio['tempo_skip'],
        len(anuncio['impressao'])))
    aviso('eventos = %s' % sorted(k for k, v in anuncio['eventos'].items() if v))
    try:
        pedido = urllib.request.Request(anuncio['url'],
                                        headers={'User-Agent': 'SMARTEDTV/VAST'})
        resposta = urllib.request.urlopen(pedido, timeout=30)
        try:
            cabeca = resposta.read(4096)
            aviso('arquivo do anuncio: http=%s tipo=%s bytes=%d' % (
                resposta.status, resposta.headers.get('Content-Type'),
                len(cabeca)))
        finally:
            resposta.close()
    except Exception as erro:
        aviso('arquivo do anuncio NAO abriu: %r' % (erro,))
        return False, {'motivo': 'criativo-inacessivel'}
    recebido = {}

    def tocar_falso(url, log=None):
        recebido['url'] = url
        aviso('player receberia = %s' % url[:140])
        return True

    recibo = vast.exibir(tag=tag, altura_tela=1080, baixar_tag=vast.baixar,
                         dormir=lambda _s: None, tocar=tocar_falso)
    aviso('recibo = %s' % vast.resumo(recibo))
    return bool(recebido.get('url')), recibo


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ok, recibo = diagnosticar(argv[0] if argv else None)
    if not ok:
        aviso('RESULTADO: caminho NAO chegou ao player (%s)'
              % recibo.get('motivo', '?'))
        return 1
    aviso('RESULTADO: caminho completo ate o player (anuncio real, nao simulado)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
