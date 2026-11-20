#!/usr/bin/env python3
"""Valida o manifesto decodificado pelo SDK e as ABIs reais do APK assinado."""
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ANDROID = '{http://schemas.android.com/apk/res/android}'
# Piso de API do Kodi 21.3 e da v21, que instalou no aparelho do usuario.
# Elevar isto (a 1.0.92 elevou para 26) recusa Android 7 e Fire OS 6.
MIN_SDK = '21'
ABIS = {'armeabi-v7a': (1, 40), 'arm64-v8a': (2, 183)}  # ELF class, e_machine


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_manifest(root, name, code):
    app = root.find('application')
    sdk = root.find('uses-sdk')
    require(root.get('package') == 'smartedtv.full' and app is not None, 'pacote inesperado')
    require((root.get(ANDROID+'versionName'), root.get(ANDROID+'versionCode')) == (name, code), 'versão incorreta')
    require(sdk is not None and sdk.get(ANDROID+'minSdkVersion') == MIN_SDK and
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


def verificar_skins(apk, names):
    """A Home entregue é a Clássica (a da foto) e a tela de entrada tem fonte."""
    for skin in ('skin.novatv', 'skin.smartedtv.classic'):
        home = apk.read('assets/addons/%s/xml/Home.xml' % skin)
        raiz = ET.fromstring(home)

        def topo(ident):
            return (raiz.find(".//control[@id='%s']/top" % ident).text or '').strip()

        require(topo('9201') == '570' and topo('9203') == '822' and topo('9300') == '460',
                '%s: Home não é a Clássica' % skin)
        require(any((e.text or '').strip() == 'LANÇAMENTO' for e in raiz.iter('label')),
                '%s: selo LANÇAMENTO ausente' % skin)
        require(any('Container(9201).ListItem.Art(fanart)' in (e.text or '')
                    for e in raiz.iter('texture')), '%s: hero sem fanart' % skin)
        fontes = apk.read('assets/addons/%s/xml/Font.xml' % skin).decode('utf-8')
        for estilo in ('wf13', 'wf17', 'wf42'):
            require('<name>%s</name>' % estilo in fontes, '%s sem %s' % (skin, estilo))
        require('assets/addons/%s/fonts/NotoSans-Regular.ttf' % skin in names,
                '%s sem a fonte da tela de entrada' % skin)
        print('skin ok: %s (Home Clássica + fontes)' % skin)


HEX64 = re.compile(rb'[0-9a-f]{64}')


def so_mudou_o_pin(novo, base):
    """Dex so pode diferir da base na string do pin do perfil (64 hex).

    O perfil embarcado sai sem os addons de terceiros (youtube, OpenWizard...),
    entao o sha256 de `assets/smarted/profile-manifest.txt` muda e o bootstrap
    precisa conferir o novo valor. O build troca o pin NO DEX; a regra de "dex
    identico a base" continua valendo para todo o resto.
    """
    if len(novo) != len(base):
        return False
    inicio = next((i for i, (a, b) in enumerate(zip(novo, base)) if a != b), None)
    if inicio is None:
        return True
    fim = len(novo) - next(i for i, (a, b) in enumerate(zip(novo[::-1], base[::-1]))
                           if a != b)
    return (any(m.start() <= inicio and fim <= m.end() for m in HEX64.finditer(base)) and
            any(m.start() <= inicio and fim <= m.end() for m in HEX64.finditer(novo)))


def verify_apk(base, final):
    def code_files(z):
        return {n for n in z.namelist() if n.startswith('lib/') or re.fullmatch(r'classes\d*\.dex|resources\.arsc', n)}

    with ZipFile(base) as before, ZipFile(final) as apk:
        names = apk.namelist()
        require(len(names) == len(set(names)) and apk.testzip() is None, 'ZIP duplicado ou corrompido')
        require(apk.getinfo('resources.arsc').compress_type == ZIP_STORED, 'resources.arsc comprimido')
        require({n.split('/')[1] for n in names if n.startswith('lib/')} == ABIS.keys(), 'conjunto de ABIs incorreto')
        require(code_files(before) == code_files(apk), 'sumiu código da v22')
        for path in code_files(apk):
            contents = apk.read(path)
            original = before.read(path)
            if contents != original:
                require(path.endswith('.dex') and so_mudou_o_pin(contents, original),
                        'código diferente da base: '+path)
                print('%s: so o pin do perfil mudou (permitido)' % path)
            if path.startswith('lib/') and path.endswith('.so'):
                abi = path.split('/')[1]
                require(contents[:4] == b'\x7fELF' and contents[5] == 1 and
                        (contents[4], struct.unpack_from('<H', contents, 18)[0]) == ABIS[abi], 'ELF incompatível: '+path)
        for abi in ABIS:
            require(f'lib/{abi}/libkodi.so' in names, 'motor ausente: '+abi)
            print(abi, sum(n.startswith(f'lib/{abi}/') and n.endswith('.so') for n in names), 'bibliotecas verificadas')
        verificar_skins(apk, names)
        for layout in ('DialogWelcome.xml', 'DialogWelcomeTV.xml'):
            require('assets/addons/script.smartedtv.welcome/resources/skins/Default/1080i/'+layout in names, layout)


if __name__ == '__main__':
    base, apk, xml, name, code = sys.argv[1:]
    verify_manifest(ET.parse(xml).getroot(), name, code)
    verify_apk(Path(base), Path(apk))
    print(f'smartedtv.full {name} ({code}), API 21+, APK standalone, LAUNCHER + LEANBACK_LAUNCHER; Dex e libs intactos.')
