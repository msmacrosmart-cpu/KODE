#!/usr/bin/env python3
"""Valida o manifesto decodificado pelo SDK e as ABIs reais do APK assinado."""
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ANDROID = '{http://schemas.android.com/apk/res/android}'
ABIS = {'armeabi-v7a': (1, 40), 'arm64-v8a': (2, 183)}  # ELF class, e_machine


def _classe_dex(nome):
    import re
    achado = re.fullmatch(r'classes(\d*)\.dex', nome)
    return None if not achado else int(achado.group(1) or 1)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_manifest(root, name, code):
    app = root.find('application')
    sdk = root.find('uses-sdk')
    require(root.get('package') == 'smartedtv.full' and app is not None, 'pacote inesperado')
    require((root.get(ANDROID+'versionName'), root.get(ANDROID+'versionCode')) == (name, code), 'versão incorreta')
    require(sdk is not None and sdk.get(ANDROID+'minSdkVersion') == '26' and
            sdk.get(ANDROID+'targetSdkVersion') == '34' and sdk.get(ANDROID+'maxSdkVersion') is None, 'SDK incorreto')
    require(not root.get('split') and root.find('uses-split') is None, 'não é um APK standalone')
    for flag in ('debuggable', 'testOnly', 'isSplitRequired'):
        require(app.get(ANDROID+flag, 'false') == 'false', flag)
    features = {f.get(ANDROID+'name'): f.get(ANDROID+'required', 'true') for f in root.findall('uses-feature')}
    for feature in ('android.hardware.touchscreen', 'android.software.leanback', 'android.hardware.type.television'):
        require(features.get(feature) == 'false', 'feature deve ser opcional: '+feature)
    require(all(req == 'false' for feat, req in features.items() if (feat or '').startswith('android.hardware.touchscreen')), 'multitoque obrigatório')
    cats = set()
    for activity in app.findall('activity') + app.findall('activity-alias'):
        if activity.get(ANDROID+'exported') != 'true' or activity.get(ANDROID+'enabled') == 'false':
            continue
        for filt in activity.findall('intent-filter'):
            if any(a.get(ANDROID+'name') == 'android.intent.action.MAIN' for a in filt.findall('action')):
                cats.update(c.get(ANDROID+'name') for c in filt.findall('category'))
    require(app.get(ANDROID+'banner') and {'android.intent.category.'+c for c in ('LAUNCHER','LEANBACK_LAUNCHER')} <= cats,
            'launcher celular, launcher TV ou banner ausente')


def verify_apk(base, final, bridge=None):
    def code_files(z):
        return {n for n in z.namelist() if n.startswith('lib/') or re.fullmatch(r'classes\d*\.dex|resources\.arsc', n)}

    with ZipFile(base) as before, ZipFile(final) as apk:
        names = apk.namelist()
        require(len(names) == len(set(names)) and apk.testzip() is None, 'ZIP duplicado ou corrompido')
        require(apk.getinfo('resources.arsc').compress_type == ZIP_STORED, 'resources.arsc comprimido')
        require({n.split('/')[1] for n in names if n.startswith('lib/')} == ABIS.keys(), 'conjunto de ABIs incorreto')
        # O único Dex aceito a mais é UM classesN.dex novo (a ponte do anúncio,
        # compilada do fonte). Kodi, libs e o resto do código continuam iguais.
        antigos = code_files(before)
        novos = code_files(apk)
        extras = novos - antigos
        require(antigos <= novos, 'sumiu código da v22')
        if extras:
            antigos_dex = sorted(_classe_dex(n) for n in antigos if n.endswith('.dex'))
            numeros = sorted(_classe_dex(n) for n in extras if n.endswith('.dex'))
            require(len(extras) == 1 and numeros == [max(antigos_dex) + 1] and
                    extras == {'classes%d.dex' % numeros[0]}, 'Dex extra inesperado: %s' % extras)
        for path in code_files(apk):
            contents = apk.read(path)
            require(contents == before.read(path), 'código diferente da base: '+path)
            if path.startswith('lib/') and path.endswith('.so'):
                abi = path.split('/')[1]
                require(contents[:4] == b'\x7fELF' and contents[5] == 1 and
                        (contents[4], struct.unpack_from('<H', contents, 18)[0]) == ABIS[abi], 'ELF incompatível: '+path)
        if bridge is not None:
            novo = sorted(extras)[0]
            require(apk.read(novo) == bridge.read_bytes(),
                    'a ponte compilada não é o Dex novo do APK')
            print('ponte do anúncio: %s (%d B)' % (novo, len(bridge.read_bytes())))
        for abi in ABIS:
            require(f'lib/{abi}/libkodi.so' in names, 'motor ausente: '+abi)
            print(abi, sum(n.startswith(f'lib/{abi}/') and n.endswith('.so') for n in names), 'bibliotecas verificadas')
        for layout in ('DialogWelcome.xml', 'DialogWelcomeTV.xml'):
            require('assets/addons/script.smartedtv.welcome/resources/skins/Default/1080i/'+layout in names, layout)


if __name__ == '__main__':
    base, apk, xml, name, code = sys.argv[1:6]
    verify_manifest(ET.parse(xml).getroot(), name, code)
    verify_apk(Path(base), Path(apk), Path(sys.argv[6]) if len(sys.argv) > 6 else None)
    print(f'smartedtv.full {name} ({code}), API 26+, APK standalone, LAUNCHER + LEANBACK_LAUNCHER; '
          'Dex do Kodi e libs intactos; só a ponte do anúncio é Dex novo.')
