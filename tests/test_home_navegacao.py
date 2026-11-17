# -*- coding: utf-8 -*-
"""Home ativa (skin.novatv): HERO -> grades e grades -> HERO no D-pad."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'kodi' / 'skin.novatv' / 'xml' / 'Home.xml'


class HomeNavegacaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raiz = ET.parse(HOME).getroot()

    def controle(self, ident):
        achado = self.raiz.find(".//control[@id='%s']" % ident)
        self.assertIsNotNone(achado, 'controle %s ausente' % ident)
        return achado

    def test_defaultcontrol_continua_na_barra_superior(self):
        self.assertEqual(self.raiz.findtext('defaultcontrol'), '9000')

    def test_hero_desce_para_a_primeira_grade(self):
        hero = self.controle('9100')
        descidas = [(c.text or '').strip() for c in hero.findall('ondown')]
        self.assertTrue(any('9500' in d for d in descidas), descidas)
        self.assertTrue(any('hide_widgets' in (c.get('condition') or '')
                            for c in hero.findall('ondown')
                            if (c.text or '').strip() == '9500'), descidas)
        # fallback quando as grades estao escondidas: botoes do HERO
        self.assertIn('9110', descidas)
        self.assertIn('9000', [(c.text or '').strip()
                               for c in hero.findall('onup')])

    def test_grades_sobem_para_o_hero(self):
        grades = self.controle('9500')
        subidas = grades.findall('onup')
        self.assertTrue(any((c.text or '').strip() == '9100' and
                            'hide_hero' in (c.get('condition') or '')
                            for c in subidas), [c.text for c in subidas])
        self.assertIn('9000', [(c.text or '').strip() for c in subidas])

    def test_botoes_do_hero_sobem_para_o_hero(self):
        for ident in ('9110', '9111', '9112'):
            self.assertEqual((self.controle(ident).findtext('onup') or '').strip(),
                             '9100', ident)

    def test_primeira_grade_nao_foi_deslocada(self):
        grades = self.controle('9500')
        self.assertEqual((grades.findtext('top') or '').strip(), '650')
        self.assertEqual((grades.findtext('height') or '').strip(), '430')


if __name__ == '__main__':
    unittest.main()
