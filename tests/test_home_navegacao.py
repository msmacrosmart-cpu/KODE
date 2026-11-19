# -*- coding: utf-8 -*-
"""Home ativa (skin.novatv = Classica/Aurora): HERO -> Lancamentos/Series e volta."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'kodi' / 'skin.novatv' / 'xml' / 'Home.xml'
ACOES = ('9000', '9121', '9122', '9123', '9201', '9203', '9300', '9301', '9302',
         '9303')


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

    def test_hero_desce_para_as_fileiras_visiveis(self):
        hero = self.controle('9300')
        descidas = [(c.text or '').strip() for c in hero.findall('ondown')]
        self.assertIn('9201', descidas)
        self.assertIn('9203', descidas)
        self.assertNotIn('9202', descidas, '9202 nao existe na Aurora')

    def test_fileiras_sobem_para_as_acoes_do_hero(self):
        for ident in ('9201', '9203'):
            subidas = [(c.text or '').strip() for c in self.controle(ident).findall('onup')]
            self.assertIn('9300', subidas, ident)

    def test_acoes_do_hero_sobem_para_a_barra(self):
        for ident in ('9301', '9302', '9303'):
            self.assertEqual((self.controle(ident).findtext('onup') or '').strip(),
                             '9300', ident)

    def test_lancamentos_e_series_ficam_lado_a_lado_no_grafo(self):
        self.assertEqual((self.controle('9201').findtext('top') or '').strip(), '570')
        self.assertEqual((self.controle('9203').findtext('top') or '').strip(), '822')
        descidas = [(e.text or '').strip() for e in self.controle('9201').findall('ondown')]
        self.assertIn('9203', descidas)
        subidas = [(e.text or '').strip() for e in self.controle('9203').findall('onup')]
        self.assertIn('9300', subidas)
        # 9203 NAO sobe para 9201: subir tem de sair da fileira e ir para o
        # hero (9300). O 9203 -> 9201 veio da troca de 873542f por d91326f e
        # era um dos tres <onup> incondicionais que deixavam o primeiro vencer
        # por acidente (e travavam o foco quando o hero estava oculto).
        # A subida da fileira de baixo para a de cima NAO e perdida: e feita
        # pelo hero (9300), que fica entre elas.
        self.assertNotIn('9201', subidas)

    def test_nenhum_alvo_de_dpad_aponta_para_controle_inexistente(self):
        ids = {c.get('id') for c in self.raiz.iter('control') if c.get('id')}
        for tag in ('onup', 'ondown', 'onleft', 'onright', 'defaultcontrol', 'onclick'):
            for elemento in self.raiz.iter(tag):
                valor = (elemento.text or '').strip()
                if valor.isdigit() and tag != 'onclick':
                    self.assertIn(valor, ids, '%s -> %s ausente' % (tag, valor))

    def test_ids_nao_se_repetem(self):
        vistos = {}
        for elemento in self.raiz.iter('control'):
            ident = elemento.get('id')
            if ident:
                vistos[ident] = vistos.get(ident, 0) + 1
        repetidos = {k: v for k, v in vistos.items() if v > 1}
        self.assertEqual(repetidos, {})


if __name__ == '__main__':
    unittest.main()
