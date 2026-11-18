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
                z.writestr('assets/addons/skin.novatv/addon.xml', b'antigo')
                z.writestr('assets/addons/skin.smartedtv.classic/addon.xml', b'antigo')
                z.writestr('assets/addons/skin.novatv/xml/Home.xml', b'antigo')
                z.writestr('assets/addons/skin.novatv/xml/DialogButtonMenu.xml',
                           b'antigo')
                z.writestr('lib/arm64-v8a/libkodi.so', b'a')
                z.writestr('lib/armeabi-v7a/libkodi.so', b'b')
            self.assertEqual(mod.main(['--apk', str(base), '--saida', str(saida)]), 0)
            with zipfile.ZipFile(saida) as z:
                nomes = z.namelist()
                for nome in ('assets/addons/skin.novatv/xml/Home.xml',
                             'assets/addons/skin.novatv/xml/DialogButtonMenu.xml'):
                    self.assertIn(nome, nomes)
                    origem = ROOT / 'kodi/skin.estilo.personalizado/xml' / Path(nome).name
                    self.assertEqual(z.read(nome), origem.read_bytes())
                # a Home Clássica inteira vai para as duas skins do APK
                fonte = ROOT / 'kodi/skin.estilo.personalizado'
                for skin in ('skin.novatv', 'skin.smartedtv.classic'):
                    self.assertEqual(z.read('assets/addons/%s/xml/Home.xml' % skin),
                                     (fonte / 'xml/Home.xml').read_bytes())
                    self.assertEqual(z.read('assets/addons/%s/media/pb_ring.png' % skin),
                                     (fonte / 'media/pb_ring.png').read_bytes())
                    addon_xml = z.read('assets/addons/%s/addon.xml' % skin)
                    self.assertIn(('id="%s"' % skin).encode(), addon_xml)

    def test_base_sem_a_skin_ativa_e_recusada(self):
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
                z.writestr('assets/addons/script.smartedtv.welcome/default.py', b'x')
                z.writestr('assets/addons/service.smarted.bootstrap/service.py', b'x')
                z.writestr('lib/arm64-v8a/libkodi.so', b'a')
                z.writestr('lib/armeabi-v7a/libkodi.so', b'b')
            with self.assertRaises(SystemExit):
                mod.main(['--apk', str(base), '--saida', str(saida)])

    def test_startup_ganha_home_de_seguranca_que_a_tela_cancela(self):
        spec = importlib.util.spec_from_file_location('atualizar_v17', SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        original = (b'<window><onload>ReplaceWindow(Home)</onload></window>')
        novo = mod.patch_startup(original)
        self.assertIn(b'smartedtv_entrada,', novo)
        self.assertIn(b'smartedtv_home_seguro,', novo)
        self.assertIn(b'ActivateWindow(Home)', novo)
        # A janela de boot desenha a espera: startup vazio = tela preta.
        self.assertIn(b'<label>Carregando</label>', novo)
        self.assertEqual(novo.count(b'<controls'), 1)
        self.assertNotIn(b'ReplaceWindow', novo)
        # Uma Startup que ja tem a tela recebe apenas o alarme de seguranca.
        com_tela = (b'<window><onload>RunScript(script.smartedtv.welcome,seguro=1)'
                    b'</onload></window>')
        novo = mod.patch_startup(com_tela)
        self.assertIn(b'smartedtv_home_seguro,', novo)
        self.assertEqual(novo.count(b'smartedtv_home_seguro,'), 1)
        self.assertEqual(novo.count(b'smartedtv_entrada,'), 1)
        self.assertEqual(novo.count(b'seguro=1'), 1)
        # idempotente: o mesmo XML passado de novo nao muda nada
        self.assertEqual(mod.patch_startup(novo), novo)
        source = (ROOT / 'kodi/addons/script.smartedtv.welcome/default.py').read_text()
        self.assertIn('CancelAlarm(smartedtv_home_seguro,silent)', source)


if __name__ == '__main__':
    unittest.main()
