# -*- coding: utf-8 -*-
"""O APK rapido precisa MANTER os XMLs de skin que substitui.

Regressao real: o laco dava `continue` depois de trocar Home.xml/ShutdownMenu,
o arquivo era lido mas nunca gravado no zip de saida.
"""
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools' / 'kodi' / 'atualizar-apk-v17.py'


class AtualizarApkTest(unittest.TestCase):
    def test_xmls_de_skin_continuam_no_apk_de_saida(self):
        spec = importlib.util.spec_from_file_location('atualizar_v17', SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as pasta:
            base = Path(pasta) / 'base.apk'
            saida = Path(pasta) / 'saida.apk'
            with zipfile.ZipFile(base, 'w') as z:
                z.writestr('AndroidManifest.xml', b'x')
                z.writestr('classes.dex', b'x')
                z.writestr('assets/system/addon-manifest.xml', b'x')
                z.writestr('assets/addons/script.smartedtv.welcome/default.py', b'antigo')
                z.writestr('assets/addons/service.smarted.bootstrap/service.py',
                           b'antigo')
                z.writestr('assets/addons/skin.novatv/xml/Home.xml', b'antigo')
                z.writestr('assets/addons/skin.novatv/xml/ShutdownMenu.xml', b'antigo')
                z.writestr('lib/arm64-v8a/libkodi.so', b'a')
                z.writestr('lib/armeabi-v7a/libkodi.so', b'b')
            self.assertEqual(mod.main(['--apk', str(base), '--saida', str(saida)]), 0)
            with zipfile.ZipFile(saida) as z:
                nomes = z.namelist()
                for nome in ('assets/addons/skin.novatv/xml/Home.xml',
                             'assets/addons/skin.novatv/xml/ShutdownMenu.xml'):
                    self.assertIn(nome, nomes)
                    origem = ROOT / 'kodi' / nome.replace('assets/addons/', '')
                    self.assertEqual(z.read(nome), origem.read_bytes())


if __name__ == '__main__':
    unittest.main()
