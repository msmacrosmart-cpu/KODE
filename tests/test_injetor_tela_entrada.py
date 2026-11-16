# -*- coding: utf-8 -*-
"""Testa o injetor que aplica a tela do ZIP sobre um APK ja existente.

Usa um APK sintetico (sem Kodi, sem download): prova que apenas os 15 arquivos
do addon entram, que so service.py e addon-manifest.xml sao adaptados e que o
perfil semeado continua byte a byte identico.
"""
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INJETOR = ROOT / 'tools' / 'kodi' / 'injetar-tela-entrada.py'
ADDON = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome'

MANIFEST = (b'<?xml version="1.0"?>\n<addons>\n'
            b'  <addon>skin.estuary</addon>\n'
            b'  <addon optional="true">service.smarted.bootstrap</addon>\n'
            b'</addons>\n')
SERVICE = b'''import threading
import xbmc

def log(m, level=1):
    pass

def enable_addons(ids):
    return []

def main():
    monitor = xbmc.Monitor()
    return monitor

if __name__ == '__main__':
    main()
'''


def carregar():
    spec = importlib.util.spec_from_file_location('injetor_tela', INJETOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class InjetorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'atual.apk'
        self.saida = Path(self.tmp.name) / 'bruto.apk'
        with zipfile.ZipFile(self.base, 'w') as z:
            z.writestr('AndroidManifest.xml', b'BINARIO')
            z.writestr('classes.dex', b'dex\n035\0')
            z.writestr('resources.arsc', b'ARSC', compress_type=zipfile.ZIP_STORED)
            z.writestr('assets/system/addon-manifest.xml', MANIFEST)
            z.writestr('assets/addons/service.smarted.bootstrap/service.py', SERVICE)
            z.writestr('assets/smarted/profile/userdata/guisettings.xml', b'<settings/>')
            z.writestr('assets/smarted/profile-manifest.txt', b'hash\t11\tuserdata/guisettings.xml')
            z.writestr('META-INF/MANIFEST.MF', b'Manifest-Version: 1.0')
            z.writestr('META-INF/CERT.RSA', b'assinatura antiga')
            z.writestr('META-INF/CERT.SF', b'resumo antigo')

    def test_injeta_apenas_a_tela(self):
        modulo = carregar()
        self.assertEqual(modulo.main(['--apk', str(self.base), '--saida', str(self.saida)]), 0)
        prefixo = 'assets/addons/script.smartedtv.welcome/'
        with zipfile.ZipFile(self.base) as antes, zipfile.ZipFile(self.saida) as depois:
            a, d = set(antes.namelist()), set(depois.namelist())
            novos = sorted(n for n in d - a if not n.startswith('META-INF/'))
            self.assertEqual(len(novos), 15)
            self.assertTrue(all(n.startswith(prefixo) for n in novos))
            self.assertEqual(sorted(n for n in a - d),
                             ['META-INF/CERT.RSA', 'META-INF/CERT.SF', 'META-INF/MANIFEST.MF'])
            alterados = sorted(n for n in a & d if antes.read(n) != depois.read(n))
            self.assertEqual(alterados,
                             ['assets/addons/service.smarted.bootstrap/service.py',
                              'assets/system/addon-manifest.xml'])
            # perfil semeado intacto (o dex confere os hashes)
            self.assertEqual(
                antes.read('assets/smarted/profile/userdata/guisettings.xml'),
                depois.read('assets/smarted/profile/userdata/guisettings.xml'))
            # tela 100% identica ao ZIP
            self.assertEqual(
                depois.read(prefixo + 'resources/skins/Default/1080i/DialogWelcome.xml'),
                (ADDON / 'resources/skins/Default/1080i/DialogWelcome.xml').read_bytes())
            self.assertEqual(
                depois.read(prefixo + 'resources/skins/Default/media/qr_1.png'),
                (ADDON / 'resources/skins/Default/media/qr_1.png').read_bytes())
            self.assertEqual(
                depois.read(prefixo + 'resources/skins/Default/media/qr_2.png'),
                (ADDON / 'resources/skins/Default/media/qr_2.png').read_bytes())
            ET.fromstring(depois.read(prefixo + 'resources/skins/Default/1080i/DialogWelcome.xml'))
            ET.fromstring(depois.read('assets/system/addon-manifest.xml'))
            servico = depois.read('assets/addons/service.smarted.bootstrap/service.py').decode()
            compile(servico, 'service.py', 'exec')
            self.assertIn("'RunScript(%s)' % WELCOME_ADDON", servico)
            self.assertIn("name='welcome-entry'", servico)
            self.assertIn('def abrir_tela_entrada(', servico)

    def test_recusa_apk_sem_servico_de_boot(self):
        with zipfile.ZipFile(self.base, 'w') as z:
            z.writestr('assets/system/addon-manifest.xml', MANIFEST)
            z.writestr('assets/smarted/profile/userdata/guisettings.xml', b'<settings/>')
        modulo = carregar()
        with self.assertRaises(SystemExit) as erro:
            modulo.main(['--apk', str(self.base), '--saida', str(self.saida)])
        self.assertIn('ponto de entrada nao localizado', str(erro.exception))


if __name__ == '__main__':
    unittest.main()
