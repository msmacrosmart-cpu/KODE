# -*- coding: utf-8 -*-
"""Testa o injetor que aplica a tela do pacote sobre um APK ja existente.

Usa um APK sintetico (sem Kodi, sem download): prova que apenas os arquivos do
addon entram, que so o ``Startup.xml`` das skins, o ``Font.xml`` das skins
(quando faltam fontes wfNN) e o ``addon-manifest.xml`` sao alterados, e que o
perfil semeado continua byte a byte identico.
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
KEYMAP = 'assets/system/keymaps/zzz-smartedtv-voltar.xml'

MANIFEST = (b'<?xml version="1.0"?>\n<addons>\n'
            b'  <addon>skin.estuary</addon>\n'
            b'  <addon optional="true">service.smarted.bootstrap</addon>\n'
            b'</addons>\n')
STARTUP = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
           b'<window>\n'
           b'\t<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>\n'
           b'\t<controls />\n'
           b'</window>\n')
# Font.xml sintetico: declara as fontes classicas da skin (font10/12/13/14) e,
# opcionalmente, a wf13 — so para provar que o injetor nao repete uma fonte que
# a skin ja tem.
_FONTES_BASE = ('<font><name>%s</name><filename>NotoSans-Regular.ttf</filename>'
                '<size>30</size></font>\n')


def _font(*nomes):
    corpo = ''.join(_FONTES_BASE % n for n in nomes)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<fonts>\n'
            '  <fontset id="Default">\n    ' + corpo +
            '  </fontset>\n</fonts>\n').encode()


FONT = _font('font10', 'font12', 'font13', 'font14', 'wf13')
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
        modulo = self._injetar()
        with zipfile.ZipFile(self.base) as antes, zipfile.ZipFile(self.saida) as depois:
            a, d = set(antes.namelist()), set(depois.namelist())
            novos = sorted(n for n in d - a if not n.startswith('META-INF/'))
            # addon da tela + keymap + smart_ads.py (o vip.py do base e substituido)
            self.assertGreaterEqual(len(novos),
                                    len(modulo.arquivos_do_addon()) + 2)
            fora = [n for n in novos if not n.startswith(PREFIXO)]
            self.assertIn(KEYMAP, fora)
            self.assertIn('assets/addons/service.smarted.bootstrap/smart_ads.py', fora)
            for nome in fora:
                self.assertTrue(
                    nome in (KEYMAP,
                             'assets/addons/service.smarted.bootstrap/smart_ads.py')
                    or nome.endswith('/fonts/NotoSans-Regular.ttf'), nome)
            self.assertTrue(all(n.startswith(PREFIXO) or n in (
                KEYMAP, 'assets/addons/service.smarted.bootstrap/smart_ads.py')
                or n.endswith('/fonts/NotoSans-Regular.ttf') for n in novos), novos)
            self.assertEqual(sorted(n for n in a - d),
                             ['META-INF/CERT.RSA', 'META-INF/CERT.SF',
                              'META-INF/MANIFEST.MF'])
            alterados = sorted(n for n in a & d if antes.read(n) != depois.read(n))
            self.assertEqual(alterados, sorted(
                ['assets/system/addon-manifest.xml'] +
                ['assets/addons/%s/xml/Startup.xml' % s for s in SKINS] +
                ['assets/addons/%s/xml/Font.xml' % s for s in SKINS] +
                ['assets/addons/service.smarted.bootstrap/vip.py']))
            # nada mais foi tocado (Home, servico, dex, perfil)
            for nome in ('assets/addons/skin.novatv/xml/Home.xml',
                         'assets/addons/service.smarted.bootstrap/service.py',
                         'classes.dex', 'resources.arsc'):
                self.assertEqual(antes.read(nome), depois.read(nome), nome)
            for nome, resumo in self.perfil.items():
                self.assertEqual(
                    hashlib.sha256(depois.read(nome)).hexdigest(), resumo, nome)
            # a tela vai como esta no repositorio (gerada do pacote)
            for relativo in ('resources/skins/Default/1080i/DialogWelcome.xml',
                             'resources/skins/Default/media/bg.png',
                             'resources/skins/Default/media/qr_checkout.png',
                             'resources/skins/Default/media/qr_apk.png',
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
                # o seguro e um processo do proprio addon; o Startup.xml NAO
                # troca de janela (era o que deixava tela preta na v7)
                self.assertIn('RunScript(script.smartedtv.welcome,seguro=1)',
                              acoes[1])
                self.assertEqual(texto.count('ReplaceWindow'), 0)
                # o comando original sumiu: nao ha salto direto para a Home
                self.assertNotIn(
                    '<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>',
                    texto)

    def test_voltar_na_home_reabre_a_tela(self):
        self._injetar()
        with zipfile.ZipFile(self.saida) as z:
            self.assertIn(KEYMAP, z.namelist())
            raiz = ET.fromstring(z.read(KEYMAP))
            # so a Home e tocada: video, listas e dialogos continuam iguais
            self.assertEqual([e.tag for e in raiz], ['Home'])
            casa = raiz.find('Home')
            acoes = {(e.text or '').strip() for e in casa.iter()
                     if e is not casa and e.tag not in ('keyboard', 'remote')}
            self.assertEqual(acoes,
                             {'RunScript(script.smartedtv.welcome,voltar)'})
            teclas = [e.tag for e in casa.find('keyboard')]
            # KEYCODE_BACK do Android chega ao Kodi como XBMCK_BACKSPACE
            self.assertIn('backspace', teclas)
            self.assertIn('escape', teclas)
            self.assertEqual([e.tag for e in casa.find('remote')], ['back'])
            # os keymaps do app nao foram alterados
            with zipfile.ZipFile(self.base) as antes:
                do_app = [n for n in antes.namelist()
                          if n.startswith('assets/system/keymaps/')]
                for nome in do_app:
                    self.assertEqual(antes.read(nome), z.read(nome), nome)
            # e o nosso entra por ultimo na ordem alfabetica (o ultimo vence)
            do_sistema = sorted(n for n in z.namelist()
                                if re.fullmatch(r'assets/system/keymaps/[^/]+\.xml', n))
            self.assertEqual(do_sistema[-1], KEYMAP)

    def test_keymap_com_outra_janela_e_recusado(self):
        modulo = carregar()
        quebrado = (b'<keymap><Home><keyboard><backspace>RunScript('
                    b'script.smartedtv.welcome,voltar)</backspace></keyboard>'
                    b'</Home><Videos><keyboard><backspace>Back</backspace>'
                    b'</keyboard></Videos></keymap>')
        with self.assertRaises(SystemExit):
            modulo.validar_keymap(quebrado)

    def test_keymap_sem_backspace_e_recusado(self):
        modulo = carregar()
        quebrado = (b'<keymap><Home><keyboard><escape>RunScript('
                    b'script.smartedtv.welcome,voltar)</escape></keyboard>'
                    b'</Home></keymap>')
        with self.assertRaises(SystemExit):
            modulo.validar_keymap(quebrado)

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
            # a skin.estuary (que nao tinha wf13) ganha a fonte com o tamanho
            # certo, e as outras nao repetem a que ja existia
            texto = z.read('assets/addons/skin.estuary/xml/Font.xml').decode()
            self.assertIn('<name>wf13</name>', texto)
            bloco = re.search(r'<name>wf13</name>\s*<filename>(\S+)</filename>'
                              r'\s*<size>(\d+)</size>', texto)
            self.assertEqual(bloco.group(1), 'NotoSans-Regular.ttf')
            self.assertEqual(int(bloco.group(2)), 13)
            texto = z.read('assets/addons/skin.novatv/xml/Font.xml').decode()
            self.assertEqual(texto.count('<name>wf13</name>'), 1)

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
        esperadas = [nome for nome, _ in modulo.fontes_da_tela() if nome != 'wf13']
        self.assertEqual(adicionadas, esperadas)
        raiz = ET.fromstring(novo)
        nomes = [f.findtext('name') for f in raiz.iter('font')]
        self.assertEqual(nomes[:5], ['font10', 'font12', 'font13', 'font14',
                                     'wf13'])
        self.assertEqual(len(nomes), 5 + len(esperadas))
        for nome, tamanho in modulo.fontes_da_tela():
            if nome == 'wf13':
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
                         [nome for nome, _ in modulo.fontes_da_tela()])
        self.assertEqual(novo.decode().count('<name>wf13</name>'), 1)

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
