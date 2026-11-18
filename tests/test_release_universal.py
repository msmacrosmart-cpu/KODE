"""Contratos de instalação e regressão do editor de manifesto sobre AXML real."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / 'tools/kodi/ajustar-versao-apk.py'
spec = importlib.util.spec_from_file_location('verificar_universal', ROOT / 'smartedtv/release/verify.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
A = verify.ANDROID
SAMPLE = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="smartedtv.full"
 android:versionName="1.0.87" android:versionCode="2103073">
 <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34"/>
 <uses-feature android:name="android.hardware.touchscreen" android:required="false"/>
 <uses-feature android:name="android.hardware.type.television" android:required="false"/>
 <uses-feature android:name="android.software.leanback" android:required="false"/>
 <application android:banner="@android:drawable/ic_dialog_info" android:label="Versão">
  <activity android:name=".Splash" android:exported="true"><intent-filter>
   <action android:name="android.intent.action.MAIN"/>
   <category android:name="android.intent.category.LAUNCHER"/>
   <category android:name="android.intent.category.LEANBACK_LAUNCHER"/>
  </intent-filter></activity>
  <meta-data android:name="outro" android:value="2103073"/>
 </application></manifest>'''


class Contrato(unittest.TestCase):
    def test_manifesto_celular_e_tv(self):
        verify.verify_manifest(ET.fromstring(SAMPLE), '1.0.87', '2103073')

    def test_piso_de_api_continua_21(self):
        """Regressao da 1.0.92: elevar o minSdk para 26 recusa Android 7/Fire OS 6.

        A v21 (minSdk 21) instalou no aparelho do relato; o APK tem de manter
        esse piso. O teste olha o verificador e o build, nao so o manifesto.
        """
        self.assertEqual(verify.MIN_SDK, '21')
        build = (ROOT / 'smartedtv/release/build.sh').read_text()
        self.assertIn('--min-sdk 21', build)
        self.assertNotIn('--min-sdk 26', build)
        # minSdk 21 e aceito; 26 nao e mais o unico valor valido
        raiz = ET.fromstring(SAMPLE)
        verify.verify_manifest(raiz, '1.0.87', '2103073')
        raiz = ET.fromstring(SAMPLE.replace('minSdkVersion="21"', 'minSdkVersion="23"'))
        with self.assertRaises(ValueError):
            verify.verify_manifest(raiz, '1.0.87', '2103073')

    def test_recusa_filtros_de_instalacao(self):
        for xpath, attr, val in (('.', 'split', 'config.arm64_v8a'),
                                 ('uses-sdk', A+'minSdkVersion', '26'),
                                 ('uses-feature', A+'required', 'true'),
                                 ('application', A+'testOnly', 'true'),
                                 ('application', A+'isSplitRequired', 'true'),
                                 ('.//activity', A+'exported', 'false'),
                                 ('.//action', A+'name', 'android.intent.action.VIEW')):
            with self.subTest(attr=attr):
                root = ET.fromstring(SAMPLE)
                root.find(xpath).set(attr, val)
                with self.assertRaises(ValueError):
                    verify.verify_manifest(root, '1.0.87', '2103073')

    def test_manifesto_binario_pode_crescer_sem_trocar_outros_inteiros(self):
        sdk = Path(os.environ.get('ANDROID_HOME', '/nonexistent'))
        aapt = Path(os.environ.get('AAPT2', sdk/'build-tools/35.0.0/aapt2'))
        jar = Path(os.environ.get('ANDROID_JAR', sdk/'platforms/android-34/android.jar'))
        if not aapt.is_file() or not jar.is_file():
            self.skipTest('teste de integração requer AAPT2 e ANDROID_JAR')
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            xml = SAMPLE.replace('<application ', '<application android:debuggable="true" ')
            (work/'AndroidManifest.xml').write_text(xml)
            original, final = work/'base.apk', work/'novo.apk'
            subprocess.run([aapt, 'link', '-I', jar, '--manifest', work/'AndroidManifest.xml', '-o', original], check=True)
            cmd = [sys.executable, EDITOR, original, final, '--de', '1.0.87', '--de-codigo', '2103073',
                   '--para', '1.0.100', '--para-codigo', '2103086', '--min-sdk']
            self.assertNotEqual(subprocess.run(cmd+['19'], capture_output=True).returncode, 0)
            subprocess.run(cmd+['21'], check=True, capture_output=True)
            tree = subprocess.check_output([aapt, 'dump', 'xmltree', '--file', 'AndroidManifest.xml', final], text=True)
            self.assertRegex(tree, r'versionName\([^)]*\)="1\.0\.100"')
            self.assertRegex(tree, r'minSdkVersion\([^)]*\)=21')
            self.assertRegex(tree, r'versionCode\([^)]*\)=2103086')
            self.assertRegex(tree, r':value\([^)]*\)=2103073')
            self.assertRegex(tree, r'debuggable\([^)]*\)=false')
            self.assertIn('Versão', tree)
            with ZipFile(original) as before, ZipFile(final) as after:
                self.assertEqual(before.read('resources.arsc'), after.read('resources.arsc'))
