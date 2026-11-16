# -*- coding: utf-8 -*-
"""Testa o injetor que aplica a tela do ZIP sobre um APK ja existente.

Usa um APK sintetico (sem Kodi, sem download): prova que apenas os 15 arquivos
do addon entram, que so o ``Startup.xml`` das skins, o ``Font.xml`` das skins
(quando faltam fontes) e o ``addon-manifest.xml`` sao alterados, e que o perfil
semeado continua byte a byte identico.
"""
import hashlib
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
PREFIXO = 'assets/addons/script.smartedtv.welcome/'
SKINS = ('skin.novatv', 'skin.smartedtv.classic', 'skin.estuary')

MANIFEST = (b'<?xml version="1.0"?>\n<addons>\n'
            b'  <addon>skin.estuary</addon>\n'
            b'  <addon optional="true">service.smarted.bootstrap</addon>\n'
            b'</addons>\n')
STARTUP = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
           b'<window>\n'
           b'\t<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>\n'
           b'\t<controls />\n'
           b'</window>\n')
# Font.xml sintetico: declara as fontes classicas que o layout do ZIP usa
# (font10/12/13/14) e, opcionalmente, font16 — que falta na skin.estuary do app.
_FONTES_BASE = ('<font><name>%s</name><filename>NotoSans-Regular.ttf</filename>'
                '<size>30</size></font>\n')


def _font(*nomes):
    corpo = ''.join(_FONTES_BASE % n for n in nomes)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<fonts>\n'
            '  <fontset id="Default">\n    ' + corpo +
            '  </fontset>\n</fonts>\n').encode()


FONT = _font('font10', 'font12', 'font13', 'font14', 'font16')
FONT_SEM_16 = _font('font10', 'font12', 'font13', 'font14')
VIP = (b'# -*- coding: utf-8 -*-\n'
       b'def validar(codigo):\n    return (False, "sem rede")\n')


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
        self.perfil = {}
        with zipfile.ZipFile(self.base, 'w') as z:
            z.writestr('AndroidManifest.xml', b'BINARIO')
            z.writestr('classes.dex', b'dex\n035\0')
            z.writestr('resources.arsc', b'ARSC', compress_type=zipfile.ZIP_STORED)
            z.writestr('assets/system/addon-manifest.xml', MANIFEST)
            z.writestr('assets/addons/service.smarted.bootstrap/service.py', b'# servico\n')
            z.writestr('assets/addons/service.smarted.bootstrap/vip.py', VIP)
            for skin in SKINS:
                z.writestr('assets/addons/%s/xml/Startup.xml' % skin, STARTUP)
                z.writestr('assets/addons/%s/xml/Font.xml' % skin,
                           FONT_SEM_16 if skin == 'skin.estuary' else FONT)
            z.writestr('assets/addons/skin.novatv/xml/Home.xml', b'<window/>')
            for nome, dados in (
                    ('assets/smarted/profile/userdata/guisettings.xml', b'<settings/>'),
                    ('assets/smarted/profile/userdata/Database/Addons33.db',
                     b'SQLite format 3\0')):
                z.writestr(nome, dados)
                self.perfil[nome] = hashlib.sha256(dados).hexdigest()
            z.writestr('assets/smarted/profile-manifest.txt',
                       b'hash\t11\tuserdata/guisettings.xml')
            z.writestr('META-INF/MANIFEST.MF', b'Manifest-Version: 1.0')
            z.writestr('META-INF/CERT.RSA', b'assinatura antiga')
            z.writestr('META-INF/CERT.SF', b'resumo antigo')

    def _injetar(self):
        modulo = carregar()
        self.assertEqual(
            modulo.main(['--apk', str(self.base), '--saida', str(self.saida)]), 0)
        return modulo

    def test_injeta_apenas_a_tela(self):
        self._injetar()
        with zipfile.ZipFile(self.base) as antes, zipfile.ZipFile(self.saida) as depois:
            a, d = set(antes.namelist()), set(depois.namelist())
            novos = sorted(n for n in d - a if not n.startswith('META-INF/'))
            self.assertEqual(len(novos), 15)
            self.assertTrue(all(n.startswith(PREFIXO) for n in novos), novos)
            self.assertEqual(sorted(n for n in a - d),
                             ['META-INF/CERT.RSA', 'META-INF/CERT.SF',
                              'META-INF/MANIFEST.MF'])
            alterados = sorted(n for n in a & d if antes.read(n) != depois.read(n))
            self.assertEqual(alterados, sorted(
                ['assets/system/addon-manifest.xml'] +
                ['assets/addons/%s/xml/Startup.xml' % s for s in SKINS] +
                ['assets/addons/%s/xml/Font.xml' % s for s in SKINS]))
            # nada mais foi tocado (Home, servico, dex, perfil)
            for nome in ('assets/addons/skin.novatv/xml/Home.xml',
                         'assets/addons/service.smarted.bootstrap/service.py',
                         'classes.dex', 'resources.arsc'):
                self.assertEqual(antes.read(nome), depois.read(nome), nome)
            for nome, resumo in self.perfil.items():
                self.assertEqual(
                    hashlib.sha256(depois.read(nome)).hexdigest(), resumo, nome)
            # a tela e byte a byte a do ZIP
            for relativo in ('resources/skins/Default/1080i/DialogWelcome.xml',
                             'resources/skins/Default/media/qr_1.png',
                             'resources/skins/Default/media/qr_2.png',
                             'resources/skins/Default/media/welcome_background.png',
                             'default.py', 'addon.xml'):
                self.assertEqual(depois.read(PREFIXO + relativo),
                                 (ADDON / relativo).read_bytes(), relativo)

    def test_startup_abre_a_tela_antes_da_home(self):
        self._injetar()
        with zipfile.ZipFile(self.saida) as z:
            for skin in SKINS:
                texto = z.read('assets/addons/%s/xml/Startup.xml' % skin).decode()
                raiz = ET.fromstring(texto.encode())
                acoes = [e.text.strip() for e in raiz.findall('onload')]
                self.assertEqual(len(acoes), 2, acoes)
                self.assertIn('RunScript(script.smartedtv.welcome)', acoes[0])
                self.assertIn('smartedtv_entrada,', acoes[0])
                # Home so pelo seguro, e depois do disparo
                self.assertIn('ReplaceWindow', acoes[1])
                self.assertIn('smartedtv_entrada_seguro', acoes[1])
                self.assertEqual(texto.count('ReplaceWindow'), 1)
                # o comando original sumiu: nao ha salto direto para a Home
                self.assertNotIn(
                    '<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>',
                    texto)

    def test_addon_registrado_como_optional_igual_aos_outros(self):
        self._injetar()
        with zipfile.ZipFile(self.saida) as z:
            manifest = z.read('assets/system/addon-manifest.xml').decode()
            ET.fromstring(manifest.encode())
            self.assertIn(
                '  <addon optional="true">script.smartedtv.welcome</addon>',
                manifest)
            # nao pode ser obrigatorio: um addon obrigatorio que falhe derruba o
            # Kodi inteiro (CAddonMgr::Init devolve LOGFATAL)
            self.assertNotIn('  <addon>script.smartedtv.welcome</addon>', manifest)

    def test_fontes_do_layout_passam_a_existir(self):
        self._injetar()
        with zipfile.ZipFile(self.saida) as z:
            layout = ET.fromstring(z.read(
                PREFIXO + 'resources/skins/Default/1080i/DialogWelcome.xml'))
            usadas = {f.text.strip() for f in layout.iter('font') if f.text}
            for skin in SKINS:
                texto = z.read('assets/addons/%s/xml/Font.xml' % skin).decode()
                ET.fromstring(texto.encode())
                for fonte in usadas:
                    self.assertIn('<name>%s</name>' % fonte, texto, (skin, fonte))
                self.assertIn('<name>font13</name>', texto)
            # a skin.estuary (que nao tinha font16) ganha a fonte
            texto = z.read('assets/addons/skin.estuary/xml/Font.xml').decode()
            self.assertIn('<name>font16</name>', texto)

    def test_recusa_apk_ja_injetado(self):
        self._injetar()
        modulo = carregar()
        with self.assertRaises(SystemExit):
            modulo.main(['--apk', str(self.saida), '--saida',
                         str(Path(self.tmp.name) / 'outro.apk')])

    def test_recusa_apk_sem_servico_de_boot(self):
        with zipfile.ZipFile(self.base, 'w') as z:
            z.writestr('assets/system/addon-manifest.xml', MANIFEST)
            z.writestr('assets/smarted/profile/userdata/guisettings.xml',
                       b'<settings/>')
        modulo = carregar()
        with self.assertRaises(SystemExit) as erro:
            modulo.main(['--apk', str(self.base), '--saida', str(self.saida)])
        self.assertIn('assets/addons/service.smarted.bootstrap/',
                      str(erro.exception))

    def test_patch_fonts_preserva_o_resto(self):
        modulo = carregar()
        novo, adicionadas = modulo.patch_fonts(FONT)
        self.assertEqual(adicionadas, ['font20', 'font22', 'font24', 'font30'])
        raiz = ET.fromstring(novo)
        nomes = [f.findtext('name') for f in raiz.iter('font')]
        self.assertEqual(nomes[:5], ['font10', 'font12', 'font13', 'font14',
                                     'font16'])
        self.assertEqual(len(nomes), 9)
        for nome, tamanho in modulo.FONTES_DA_TELA:
            if nome == 'font16':
                continue
            self.assertIn(nome, nomes)
            bloco = re.search(r'<name>%s</name>.*?<size>(\d+)</size>' % nome,
                              novo.decode(), re.S)
            self.assertEqual(int(bloco.group(1)), tamanho)
        # idempotencia proibida: nao pode injetar duas vezes
        with self.assertRaises(SystemExit):
            modulo.patch_fonts(novo)

    def test_patch_fonts_so_adiciona_o_que_falta(self):
        modulo = carregar()
        novo, adicionadas = modulo.patch_fonts(FONT_SEM_16)
        self.assertEqual(adicionadas,
                         ['font16', 'font20', 'font22', 'font24', 'font30'])
        self.assertEqual(novo.decode().count('<name>font16</name>'), 1)

    def test_startup_com_duas_acoes_e_aceito_e_sem_home_e_recusado(self):
        modulo = carregar()
        novo = modulo.patch_startup(STARTUP)
        self.assertIn(b'smartedtv_entrada,', novo)
        # um Startup.xml com Home solta nao pode passar
        ruim = (b'<window><onload>AlarmClock(smartedtv_entrada,'
                b'RunScript(script.smartedtv.welcome),00:00:00,silent)</onload>'
                b'<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>'
                b'</window>')
        with self.assertRaises(SystemExit):
            modulo.validar_publicacao(ruim)


if __name__ == '__main__':
    unittest.main()
