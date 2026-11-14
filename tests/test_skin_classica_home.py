# -*- coding: utf-8 -*-
"""Skin classica SMARTEDTV 1.0.18 — fileiras da Home e paineis escuros.

Essas correcoes valem para a linha classica (a mesma familia da 1.0.47, sem
Bingie): a skin do repositorio e embarcada como skin.novatv, byte a byte igual
ao que ja esta dentro do APK 1.0.47.
"""
import pathlib
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIN = ROOT / 'kodi/skin.estilo.personalizado'
HOME = SKIN / 'xml/Home.xml'
NAV = SKIN / 'xml/MyVideoNav.xml'
ADDON = SKIN / 'addon.xml'
BUILD = ROOT / 'tools/kodi/build-release-apk.py'
FLUXO = ROOT / '.github/workflows/build-release-classica.yml'


def texto(controle, tag):
    return (controle.findtext(tag) or '').strip()


class HomeClassicaTest(unittest.TestCase):
    def setUp(self):
        self.raiz = ET.parse(HOME).getroot()
        self.listas = {c.get('id'): c for c in self.raiz.iter('control')
                       if c.get('type') == 'list' and c.get('id')}
        self.rotulos = {(c.findtext('label') or '').strip()
                        for c in self.raiz.iter('control') if c.get('type') == 'label'}

    def test_duas_fileiras_e_nenhuma_duplicada(self):
        # 9201 = Lancamentos/Filmes (alimenta o hero), 9203 = Series.
        # 9202 era a fileira "Filmes" que se sobrepunha a de lancamentos.
        self.assertIn('9201', self.listas)
        self.assertIn('9203', self.listas)
        self.assertNotIn('9202', self.listas)

    def test_fileiras_cabem_na_tela_com_respiro(self):
        topo1 = int(texto(self.listas['9201'], 'top'))
        alt1 = int(texto(self.listas['9201'], 'height'))
        topo2 = int(texto(self.listas['9203'], 'top'))
        alt2 = int(texto(self.listas['9203'], 'height'))
        self.assertEqual((topo1, alt1), (570, 194))
        self.assertEqual((topo2, alt2), (822, 194))
        respiro = topo2 - (topo1 + alt1)
        self.assertGreaterEqual(respiro, 20, 'fileiras coladas')
        self.assertLessEqual(topo2 + alt2, 1080, 'fileira de Series fora da tela')

    def test_conteudo_de_cada_fileira(self):
        self.assertIn('route=recent-movies', texto(self.listas['9201'], 'content'))
        self.assertIn('route=recent-series', texto(self.listas['9203'], 'content'))

    def test_rotulos_das_fileiras(self):
        self.assertIn('Lançamentos', self.rotulos)
        self.assertIn('Séries', self.rotulos)
        self.assertNotIn('Filmes', self.rotulos)

    def test_foco_liga_as_duas_fileiras(self):
        self.assertIn('<ondown>9203</ondown>', ET.tostring(self.listas['9201'], encoding='unicode'))
        self.assertIn('<onup>9201</onup>', ET.tostring(self.listas['9203'], encoding='unicode'))

    def test_hero_continua_ligado_na_fileira_de_cima(self):
        # o HERO (titulo, sinopse, fanart) le Container(9201)
        self.assertIn('Container(9201)', HOME.read_text(encoding='utf-8'))


class PainelDaListaTest(unittest.TestCase):
    def setUp(self):
        self.texto = NAV.read_text(encoding='utf-8')

    def test_nenhum_painel_branco_na_listagem(self):
        # pb_rounded.png e uma textura cinza-clara: tingida de branco virava painel claro
        self.assertNotIn('colordiffuse="B3FFFFFF" border="16">pb_rounded.png', self.texto)
        self.assertNotIn('colordiffuse="FFFFFFFF" border="16">pb_rounded.png', self.texto)

    def test_paineis_em_cinza_escuro(self):
        self.assertIn('colordiffuse="CC121212" border="16">pb_rounded.png', self.texto)
        self.assertIn('colordiffuse="FF1E1E1E" border="16">pb_rounded.png', self.texto)


class VersaoEBuildTest(unittest.TestCase):
    def test_skin_em_1_0_18(self):
        raiz = ET.parse(ADDON).getroot()
        self.assertEqual(raiz.get('id'), 'skin.estilo.personalizado')
        self.assertEqual(raiz.get('version'), '1.0.18')

    def test_script_de_build_tem_os_modos_da_linha_classica(self):
        script = BUILD.read_text(encoding='utf-8')
        for opcao in ('--skin-version', '--keep-bridge', '--no-classic-copy'):
            self.assertIn(opcao, script)

    def test_fluxo_classico_encadeia_as_versoes(self):
        # a linha classica anda sempre em cima da release anterior publicada
        fluxo = FLUXO.read_text(encoding='utf-8')
        self.assertIn('--from-version 1.0.59', fluxo)
        self.assertIn('5e3dc5c36be6b630ced417f2feab85af6507c2d00b7c2e86256f6491d08cf51b', fluxo)
        self.assertIn('v1.0.60-classica', fluxo)
        # 1.0.59 so reembarca o bootstrap: o resto do APK base fica intacto
        self.assertIn('--bridge-addons service.smarted.bootstrap', fluxo)


if __name__ == '__main__':
    unittest.main()
