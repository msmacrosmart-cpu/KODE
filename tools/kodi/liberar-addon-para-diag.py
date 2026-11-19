# -*- coding: utf-8 -*-
"""Torna o addon legivel pelo ``adb shell`` no AVD descartavel do CI.

So para o emulador: o Kodi do aparelho guarda o addon em
``/sdcard/Android/data/<pacote>/files/.kodi/addons``. O diagnostico de
anuncio da TV (``diag-anuncio-tv.py``) precisa LER esses .py; se a pasta
estiver 700 para o app, o shell nao le e o diagnostico "nao acha o addon".

Nao mexe em protecao nenhuma: as permissoes sao refeitas na PROXIMA
instalacao do APK, e o AVD e jogado fora no fim do job.
"""
from __future__ import print_function

import subprocess
import sys

PACOTES = ('smartedtv.full', 'smartedtv.tv')


def rodar(*comando):
    try:
        return subprocess.check_output(comando, stderr=subprocess.STDOUT).decode(
            'utf-8', 'replace')
    except Exception as erro:
        return 'ERRO %r' % (erro,)


def liberar(pacotes=PACOTES, shell=rodar):
    """Abre a leitura da pasta do addon nos pacotes indicados."""
    avisos = []
    for pacote in pacotes:
        base = '/sdcard/Android/data/%s/files/.kodi' % pacote
        existe = shell('adb', 'shell', 'test', '-d', base)
        if 'ERRO' in existe:
            avisos.append('%s: sem %s' % (pacote, base))
            continue
        for pasta in ('', '/addons', '/addons/service.smarted.bootstrap'):
            shell('adb', 'shell', 'chmod', '755', base + pasta)
        saida = shell('adb', 'shell', 'ls', base + '/addons/service.smarted.bootstrap/ads_vast.py')
        ok = 'ads_vast.py' in saida
        avisos.append('%s: addon %s' % (pacote, 'legivel' if ok else 'nao legivel'))
    return avisos


def main():
    for linha in liberar():
        print('::notice::liberar-addon: ' + linha)
    return 0


if __name__ == '__main__':
    sys.exit(main())
