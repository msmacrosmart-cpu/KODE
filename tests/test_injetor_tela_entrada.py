# -*- coding: utf-8 -*-
"""Testa o injetor que aplica a tela do ZIP sobre um APK ja existente.

Usa um APK sintetico (sem Kodi, sem download): prova que apenas os 15 arquivos
do addon + o modulo tela_entrada.py entram, que so o service.py, o
addon-manifest.xml e os Font.xml das skins do projeto sao adaptados, que as
fontes do ZIP passam a existir e que o perfil semeado continua byte a byte
identico.
"""
import importlib.util
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INJETOR = ROOT / 'tools' / 'kodi' / 'injetar-tela-entrada.py'
ADDON = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome'
MODULO = 'assets/addons/service.smarted.bootstrap/tela_entrada.py'

MANIFEST = (b'<?xml version="1.0"?>\n<addons>\n'
            b'  <addon>skin.estuary</addon>\n'
            b'  <addon optional="true">service.smarted.bootstrap</addon>\n'
            b'</addons>\n')
SERVICE = b'''import threading
import xbmc
import xbmcvfs

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
FONT = b'''<?xml version="1.0" encoding="UTF-8"?>
<fonts>
  <fontset id="Default">
    <font><name>font13</name><filename>NotoSans-Regular.ttf</filename><size>30</size></font>
    <font><name>font16</name><filename>NotoSans-Regular.ttf</filename><size>36</size></font>
  </fontset>
</fonts>
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
            for skin in ('skin.novatv', 'skin.smartedtv.classic', 'skin.estuary'):
                z.writestr('assets/addons/%s/xml/Font.xml' % skin, FONT)
            z.writestr('assets/addons/skin.novatv/xml/Home.xml', b'<window/>')
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
            # 15 arquivos do ZIP + tela_entrada.py (modulo do servico)
            self.assertEqual(len(novos), 16)
            self.assertEqual([n for n in novos if not n.startswith(prefixo)], [MODULO])
            self.assertEqual(len([n for n in novos if n.startswith(prefixo)]), 15)
            self.assertEqual(sorted(n for n in a - d),
                             ['META-INF/CERT.RSA', 'META-INF/CERT.SF', 'META-INF/MANIFEST.MF'])
            alterados = sorted(n for n in a & d if antes.read(n) != depois.read(n))
            self.assertEqual(alterados, [
                'assets/addons/service.smarted.bootstrap/service.py',
                'assets/addons/skin.estuary/xml/Font.xml',
                'assets/addons/skin.novatv/xml/Font.xml',
                'assets/addons/skin.smartedtv.classic/xml/Font.xml',
                'assets/system/addon-manifest.xml'])
            # nenhuma outra tela / arquivo tocado
            self.assertEqual(antes.read('assets/addons/skin.novatv/xml/Home.xml'),
                             depois.read('assets/addons/skin.novatv/xml/Home.xml'))
            # perfil semeado intacto (o dex confere os hashes)
            self.assertEqual(
                antes.read('assets/smarted/profile/userdata/guisettings.xml'),
                depois.read('assets/smarted/profile/userdata/guisettings.xml'))
            # tela 100% identica ao ZIP
            for relativo in ('resources/skins/Default/1080i/DialogWelcome.xml',
                             'resources/skins/Default/media/qr_1.png',
                             'resources/skins/Default/media/qr_2.png',
                             'resources/skins/Default/media/welcome_background.png'):
                self.assertEqual(depois.read(prefixo + relativo),
                                 (ADDON / relativo).read_bytes())
            layout = ET.fromstring(depois.read(
                prefixo + 'resources/skins/Default/1080i/DialogWelcome.xml'))
            self.assertEqual(layout.tag, 'window')
            ET.fromstring(depois.read('assets/system/addon-manifest.xml'))

            servico = depois.read('assets/addons/service.smarted.bootstrap/service.py').decode()
            compile(servico, 'service.py', 'exec')
            self.assertIn('from tela_entrada import abrir_tela_entrada', servico)
            self.assertIn("name='welcome-entry'", servico)
            self.assertIn('abrir_tela_entrada', servico)
            modulo_tela = depois.read(MODULO).decode()
            compile(modulo_tela, 'tela_entrada.py', 'exec')
            self.assertIn('def abrir_tela_entrada(', modulo_tela)
            self.assertIn('RunScript("%s")', modulo_tela)

            # as 4 fontes que o layout do ZIP usa passam a existir nas skins
            for skin in ('skin.novatv', 'skin.smartedtv.classic', 'skin.estuary'):
                texto = depois.read('assets/addons/%s/xml/Font.xml' % skin).decode()
                ET.fromstring(texto)
                for fonte in ('font20', 'font22', 'font24', 'font30'):
                    self.assertIn('<name>%s</name>' % fonte, texto)
                # fontes que ja existiam continuam exatamente como estavam
                self.assertIn('<name>font13</name>', texto)
                self.assertIn('<name>font16</name>', texto)

    def test_recusa_apk_sem_servico_de_boot(self):
        with zipfile.ZipFile(self.base, 'w') as z:
            z.writestr('assets/system/addon-manifest.xml', MANIFEST)
            z.writestr('assets/smarted/profile/userdata/guisettings.xml', b'<settings/>')
        modulo = carregar()
        with self.assertRaises(SystemExit) as erro:
            modulo.main(['--apk', str(self.base), '--saida', str(self.saida)])
        self.assertIn('assets/addons/service.smarted.bootstrap/service.py',
                      str(erro.exception))

    def test_patch_fonts_preserva_o_resto(self):
        modulo = carregar()
        novo = modulo.patch_fonts(FONT)
        raiz = ET.fromstring(novo)
        nomes = [f.findtext('name') for f in raiz.iter('font')]
        self.assertEqual(nomes[:2], ['font13', 'font16'])
        self.assertEqual(sorted(set(nomes) & {'font20', 'font22', 'font24', 'font30'}),
                         ['font20', 'font22', 'font24', 'font30'])
        # idempotencia proibida: nao pode injetar duas vezes
        with self.assertRaises(SystemExit):
            modulo.patch_fonts(novo)

    def test_tamanhos_das_fontes_novas(self):
        modulo = carregar()
        self.assertEqual(modulo.FONTES_DA_TELA,
                         [('font20', 20), ('font22', 22), ('font24', 24), ('font30', 30)])
        texto = modulo.patch_fonts(FONT).decode()
        for nome, tamanho in modulo.FONTES_DA_TELA:
            bloco = re.search(r'<name>%s</name>.*?<size>(\d+)</size>' % nome, texto, re.S)
            self.assertIsNotNone(bloco)
            self.assertEqual(int(bloco.group(1)), tamanho)


if __name__ == '__main__':
    unittest.main()
