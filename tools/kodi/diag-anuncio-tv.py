# -*- coding: utf-8 -*-
"""Diagnostico de anuncio da TV, rodando DENTRO do aparelho (via adb shell).

Responde, com o app instalado: o aparelho e tratado como TV? a tag VAST do
projeto existe no addon? a tag responde? o criativo existe? Diz o veredito e
o que falta. Nao altera nada: so le e registra.

Uso (no AVD/TV, com o APK instalado):
    adb shell "python3 /data/local/tmp/diag-anuncio-tv.py"
"""
from __future__ import print_function

import os
import sys


def aviso(texto):
    limpo = ' '.join(str(texto).replace('\r', ' ').replace('\n', ' ').split())
    print('::notice::' + limpo[:900])


def _achar_addons():
    """Pastas onde o addon pode estar (Kodi do sistema ou do perfil do app)."""
    return (
        '/sdcard/Android/data/smartedtv.full/files/.kodi/addons',
        '/sdcard/Android/data/smartedtv.tv/files/.kodi/addons',
        '/data/data/smartedtv.full/files/.kodi/addons',
        '/sdcard/.kodi/addons',
    )


def _addon():
    for base in _achar_addons():
        pasta = os.path.join(base, 'service.smarted.bootstrap')
        if os.path.isdir(pasta):
            return pasta
    return ''


def diagnosticar(pasta=None):
    """Devolve (eh_tv, tag_ok, motivo)."""
    pasta = pasta or _addon()
    if not pasta:
        aviso('addon: NAO encontrado em %s' % (_achar_addons(),))
        return False, False, 'addon-ausente'
    aviso('addon: %s' % pasta)
    sys.path.insert(0, pasta)
    import importlib
    try:
        variante = importlib.import_module('variante')
    except Exception as erro:
        aviso('variante: falhou (%r)' % (erro,))
        return False, False, 'variante-falhou'
    try:
        tv = bool(variante.e_tv())
    except Exception as erro:
        aviso('e_tv falhou (%r)' % (erro,))
        tv = False
    aviso('e_tv=%s (marcador=%s)' % (tv, getattr(variante, 'MARCADOR', '?')))
    try:
        vast = importlib.import_module('ads_vast')
    except Exception as erro:
        aviso('ads_vast: falhou (%r)' % (erro,))
        return tv, False, 'ads_vast-falhou'
    tag = (vast.VAST_TAG_PADRAO or '').strip()
    aviso('tag padrao = %s' % tag)
    if not tag:
        return tv, False, 'sem-tag'
    dados = vast.baixar(tag)
    aviso('tag respondeu: %s bytes' % (len(dados) if dados else 0))
    if not dados:
        return tv, False, 'tag-sem-resposta'
    anuncio = vast.escolher_anuncio(dados, 1080)
    if not anuncio:
        return tv, False, 'vast-sem-criativo'
    aviso('criativo: %s (%s, %ss)' % (anuncio['url'][:110], anuncio.get('tipo'),
                                      anuncio.get('duracao')))
    return tv, True, 'pronto'


def main():
    tv, tag_ok, motivo = diagnosticar()
    if not tv:
        aviso('VEREDITO: este aparelho NAO e tratado como TV; o anuncio aqui e '
              'o AdMob (celular). No modo TV o anuncio e video (VAST).')
        return 0
    if not tag_ok:
        aviso('VEREDITO: TV, mas o fluxo VAST nao chegaria ao player (%s)' % motivo)
        return 1
    aviso('VEREDITO: TV com tag VAST valida e criativo legivel (%s)' % motivo)
    return 0


if __name__ == '__main__':
    sys.exit(main())
