#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Troca o dex do bootstrap (classes3.dex) por um recompilado do repositorio.

O `classes4.dex` (codigo do app) NAO pode ser tocado: trocar bytes nele deixa o
ART recusar o arquivo e o app morre com
``NoClassDefFoundError: Lsmartedtv/full/XBMCJsonRPC`` (experimento A x D x C no
emulador). O bootstrap do splash, porem, e um dex separado (classes3.dex, ~10 kB,
o que `home-carrossel-emulator.yml` tambem recompila) e pode ser regerado a partir
de `tools/android/src/org/smartedtv/bootstrap/*.java`. Assim o pin do perfil novo
entra por compilacao, como manda o ART, sem tocar em codigo do app.
"""
import os
import shutil
import subprocess
import sys
import zipfile

FONTE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'android', 'src', 'org', 'smartedtv', 'bootstrap')
DEX_DO_BOOTSTRAP = 'classes3.dex'


def compilar(destino):
    """javac + d8: devolve o caminho do classes.dex gerado."""
    sdk = os.environ.get('ANDROID_HOME')
    if not sdk:
        raise SystemExit('ANDROID_HOME nao definido')
    jar = subprocess.run(['bash', '-c', 'find %s/platforms -name android.jar | sort -V | tail -1' % sdk],
                         capture_output=True, text=True, check=True).stdout.strip()
    ferramentas = subprocess.run(
        ['bash', '-c', 'find %s/build-tools -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1' % sdk],
        capture_output=True, text=True, check=True).stdout.strip()
    classes = os.path.join(destino, 'classes')
    dex = os.path.join(destino, 'dex')
    os.makedirs(classes, exist_ok=True)
    os.makedirs(dex, exist_ok=True)
    fontes = sorted(os.path.join(FONTE, f) for f in os.listdir(FONTE) if f.endswith('.java'))
    subprocess.run(['javac', '-source', '8', '-target', '8', '-classpath', jar,
                    '-d', classes] + fontes, check=True)
    achados = []
    for raiz, _, arquivos in os.walk(classes):
        achados.extend(os.path.join(raiz, a) for a in arquivos if a.endswith('.class'))
    subprocess.run([os.path.join(ferramentas, 'd8'), '--min-api', '21', '--lib', jar,
                    '--output', dex] + sorted(achados), check=True)
    return os.path.join(dex, 'classes.dex')


def trocar(apk_entrada, apk_saida, dex_compilado):
    with zipfile.ZipFile(apk_entrada) as z, \
            zipfile.ZipFile(apk_saida, 'w', allowZip64=True) as saida:
        if DEX_DO_BOOTSTRAP not in z.namelist():
            raise SystemExit('APK sem %s' % DEX_DO_BOOTSTRAP)
        novo = open(dex_compilado, 'rb').read()
        for item in z.infolist():
            if item.is_dir():
                continue
            dados = novo if item.filename == DEX_DO_BOOTSTRAP else z.read(item)
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            info.comment = item.comment
            saida.writestr(info, dados)
    print('bootstrap recompilado no %s (%d bytes)' % (DEX_DO_BOOTSTRAP, len(novo)))


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    trabalho = argv[3]
    if os.path.isdir(trabalho):
        shutil.rmtree(trabalho)
    os.makedirs(trabalho)
    trocar(argv[1], argv[2], compilar(trabalho))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
