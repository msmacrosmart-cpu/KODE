#!/usr/bin/env python3
"""Valida o manifesto decodificado pelo SDK e as ABIs reais do APK assinado."""
import hashlib
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
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


def _mutf8_u16(dados):
    out, i, n = [], 0, len(dados)
    while i < n:
        b0 = dados[i]
        if (b0 & 0x80) == 0:
            out.append(b0); i += 1
        elif (b0 & 0xE0) == 0xC0 and i + 1 < n:
            out.append(((b0 & 0x1F) << 6) | (dados[i + 1] & 0x3F)); i += 2
        elif (b0 & 0xF0) == 0xE0 and i + 2 < n:
            out.append(((b0 & 0x0F) << 12) | ((dados[i + 1] & 0x3F) << 6) | (dados[i + 2] & 0x3F)); i += 3
        else:
            out.append(b0); i += 1
    return tuple(out)


def verificar_classes4_dex(base_dex, novo_dex, base_manifest, novo_manifest):
    if novo_dex == base_dex:
        return
    require(len(novo_dex) == len(base_dex) and novo_dex.startswith(b'dex\n'), 'classes4.dex inválido')
    adler = zlib.adler32(memoryview(novo_dex)[12:]) & 0xFFFFFFFF
    require(struct.unpack_from('<I', novo_dex, 8)[0] == adler, 'classes4.dex: Adler-32 incorreto')
    require(novo_dex[12:32] == hashlib.sha1(memoryview(novo_dex)[32:]).digest(), 'classes4.dex: SHA-1 incorreto')
    count, table_off = struct.unpack_from('<II', novo_dex, 56)
    anterior = None
    for idx in range(count):
        off = struct.unpack_from('<I', novo_dex, table_off + 4 * idx)[0]
        pos = off
        while novo_dex[pos] & 0x80:
            pos += 1
        pos += 1
        fim = novo_dex.index(0, pos)
        atual = _mutf8_u16(novo_dex[pos:fim])
        require(anterior is None or anterior < atual, f'classes4.dex: string_ids fora de ordem em {idx}')
        anterior = atual
    pin_antigo = hashlib.sha256(base_manifest).hexdigest().encode('ascii')
    pin_novo = hashlib.sha256(novo_manifest).hexdigest().encode('ascii')
    require(pin_novo in novo_dex, 'classes4.dex: pin do manifesto ausente')
    reconstituido = novo_dex.replace(pin_novo, pin_antigo, 1)
    require(reconstituido[32:] == base_dex[32:], 'classes4.dex alterado além do pin do manifesto')


def verify_apk(base, final):
    def code_files(z):
        return {n for n in z.namelist() if n.startswith('lib/') or re.fullmatch(r'classes\d*\.dex|resources\.arsc', n)}

    with ZipFile(base) as before, ZipFile(final) as apk:
        names = apk.namelist()
        require(len(names) == len(set(names)) and apk.testzip() is None, 'ZIP duplicado ou corrompido')
        require(not any('plugin.video.youtube' in n or 'plugin.audio.mp3streams' in n for n in names),
                'YouTube ou MP3 Streams presente no APK')
        require(apk.getinfo('resources.arsc').compress_type == ZIP_STORED, 'resources.arsc comprimido')
        require({n.split('/')[1] for n in names if n.startswith('lib/')} == ABIS.keys(), 'conjunto de ABIs incorreto')
        require(code_files(before) == code_files(apk), 'sumiu código da v22')
        for path in code_files(apk):
            contents = apk.read(path)
            if path == 'classes4.dex' and 'assets/smarted/profile-manifest.txt' in names:
                verificar_classes4_dex(
                    before.read(path), contents,
                    before.read('assets/smarted/profile-manifest.txt'),
                    apk.read('assets/smarted/profile-manifest.txt'),
                )
            else:
                require(contents == before.read(path), 'código diferente da base: '+path)
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
