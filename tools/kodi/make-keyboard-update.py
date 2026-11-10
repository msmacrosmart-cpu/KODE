#!/usr/bin/env python3
"""Prepare an unsigned keyboard test update from the exact published 1.0.15 APK.

Only the Android manifest version, libkodi, Android settings, and a new DEX are
changed. This is not proof of ABI compatibility or successful device operation.
"""
import hashlib
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

if len(sys.argv) != 5:
    raise SystemExit('Usage: make-keyboard-update.py OLD.apk CANDIDATE.apk keyboard.dex OUTPUT.apk')
old, candidate, dex, out = map(Path, sys.argv[1:])
def digest(data):
    return hashlib.sha256(data).hexdigest()
if digest(old.read_bytes()) != '1cb892b1103a3a42a2ed846825c93ae7075cccf9260b7b451d61c1b23ea827e0':
    raise SystemExit('Unexpected original APK')
if digest(candidate.read_bytes()) != 'f737dffe81c8ec9973f22ee24df4fd4cdc02de0cfe131a95d777635ae3998222':
    raise SystemExit('Unexpected compiled candidate')
dex_data = dex.read_bytes()
if not dex_data.startswith(b'dex\n') or b'XBMCNativeKeyboard' not in dex_data:
    raise SystemExit('Keyboard DEX is absent or invalid')
settings = 'assets/system/settings/android.xml'
lib = 'lib/arm64-v8a/libkodi.so'
with zipfile.ZipFile(old) as source, zipfile.ZipFile(candidate) as built:
    if 'classes2.dex' in source.namelist():
        raise SystemExit('Source unexpectedly contains a second DEX')
    manifest = source.read('AndroidManifest.xml')
    version_old, version_new = '1.0.15'.encode('utf-16le'), '1.0.16'.encode('utf-16le')
    code_old, code_new = struct.pack('<I', 2103001), struct.pack('<I', 2103002)
    if manifest.count(version_old) != 1 or manifest.count(code_old) != 1:
        raise SystemExit('Manifest version data is not unique')
    manifest = manifest.replace(version_old, version_new).replace(code_old, code_new)
    old_settings = source.read(settings)
    new_settings = built.read(settings)
    xml = ElementTree.fromstring(new_settings)
    setting = xml.find(".//setting[@id='input.androidusekodikeyboard']")
    if setting is None or setting.findtext('default') != 'false':
        raise SystemExit('Native keyboard is not enabled by default')
    insertion = '''    <category id="input">\n      <group id="3">\n        <!-- Desativado por padrão: utiliza o teclado do Android. -->\n        <setting id="input.androidusekodikeyboard" type="boolean" label="24162">\n          <level>1</level>\n          <default>false</default>\n          <control type="toggle" />\n        </setting>\n      </group>\n    </category>\n'''.encode('utf-8')
    if new_settings.count(insertion) != 1 or new_settings.replace(insertion, b'') != old_settings:
        raise SystemExit('Android settings changed beyond the keyboard setting')
    compiled_lib = built.read(lib)
    if b'XBMCNativeKeyboard' not in compiled_lib:
        raise SystemExit('Compiled native keyboard bridge absent')
    replacements = {'AndroidManifest.xml': manifest, settings: new_settings, lib: compiled_lib}
    sig = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
    with zipfile.ZipFile(out, 'w', allowZip64=True) as target:
        seen = set()
        for item in source.infolist():
            if item.is_dir() or sig.fullmatch(item.filename):
                continue
            if item.filename in seen:
                raise SystemExit('Duplicate ZIP member')
            seen.add(item.filename)
            target.writestr(item, replacements.get(item.filename, source.read(item.filename)))
        target.writestr('classes2.dex', dex_data, compress_type=zipfile.ZIP_DEFLATED)
print('Unsigned candidate constructed; version 1.0.16 / 2103002. Runtime remains untested.')
