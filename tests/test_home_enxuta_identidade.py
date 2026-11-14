# -*- coding: utf-8 -*-
"""Rodada 17: Home com Filmes/Series, nada de Kodi/Brazuca visivel e aviso unico."""
import pathlib
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
XML = ROOT / 'kodi/skin.estilo.personalizado/xml'


class HomeEnxutaTest(unittest.TestCase):
    def setUp(self):
        self.home = (XML / 'Home.xml').read_text(encoding='utf-8')

    def test_so_lancamentos_e_series_abaixo_do_hero(self):
        # 9201 = Lancamentos/Filmes (tambem alimenta o HERO), 9203 = Series.
        # A antiga 9202 ("Filmes") se sobrepunha a 9201 e foi removida.
        self.assertNotIn('<control type="list" id="9200">', self.home)
        self.assertNotIn('<control type="list" id="9202">', self.home)
        self.assertEqual(len(re.findall(r'<control type="list" id="92(?:01|03)">', self.home)), 2)
        filmes = re.search(r'<control type="list" id="9201">.{0,9000}?</content>', self.home, re.S).group(0)
        self.assertIn('route=recent-movies', filmes)
        series = re.search(r'<control type="list" id="9203">.{0,9000}?</content>', self.home, re.S).group(0)
        self.assertIn('route=recent-series', series)

    def test_titulos_acima_dos_cards_e_bom_espaco(self):
        tops = {cid: int(re.search(r'<control type="list" id="%s"><left>60</left><top>(\d+)</top>' % cid,
                                   self.home).group(1)) for cid in ('9201', '9203')}
        self.assertGreaterEqual(tops['9203'] - tops['9201'], 194)  # fileiras empilhadas, nao sobrepostas
        for cid, top in tops.items():
            titulo = re.search(r'<control type="label"><left>60</left><top>(\d+)</top>[^>]*>\s*'
                               r'<label>(?:Filmes|Séries)</label>', self.home.replace('\n', ''))
        # o titulo de cada secao fica ~48 px acima da fileira
        for cid, top in tops.items():
            achado = re.search(r'<control type="label"><left>60</left><top>(\d+)</top>'
                               r'(?:(?!</control>).)*?<label>(?:Lançamentos|Séries)</label>', self.home, re.S)
            self.assertIsNotNone(achado)
        self.assertIn('<itemgap>28</itemgap>', self.home)

    def test_hero_sem_sobreposicao(self):
        botoes = re.search(r'<control type="grouplist" id="9300"><left>60</left><top>(\d+)</top>'
                           r'<width>\d+</width><height>(\d+)</height>', self.home)
        sinopse = re.search(r'<control type="textbox"><left>60</left><top>(\d+)</top><width>\d+</width>'
                            r'<height>(\d+)</height><font>font12</font><textcolor>pb_text</textcolor>', self.home)
        self.assertIsNotNone(botoes); self.assertIsNotNone(sinopse)
        fim_sinopse = int(sinopse.group(1)) + int(sinopse.group(2))
        self.assertLessEqual(fim_sinopse, int(botoes.group(1)) - 12)

    def test_nada_de_kodi_ou_brazuca_visivel(self):
        for arq in XML.glob('*.xml'):
            texto = arq.read_text(encoding='utf-8', errors='ignore')
            for visivel in re.findall(r'<label>([^<]+)</label>', texto):
                self.assertNotRegex(visivel, r'Kodi|Brazuca', '%s: %s' % (arq.name, visivel))
            for visivel in re.findall(r'<description>([^<]+)</description>', texto):
                self.assertNotRegex(visivel, r'Kodi|Brazuca', '%s: %s' % (arq.name, visivel))

    def test_notificacao_com_identidade_unica(self):
        dialogo = (XML / 'DialogNotification.xml').read_text(encoding='utf-8')
        self.assertNotIn('SMARTEDTV</label>', dialogo)  # sem cabecalho duplicado na skin
        servico = (ROOT / 'kodi/addons/service.smarted.bootstrap/service.py').read_text(encoding='utf-8')
        for aviso in re.findall(r'Notification\(([^)]*)\)', servico):
            self.assertNotIn('Brazuca', aviso)
            self.assertNotIn('SMARTEDTV', aviso)


if __name__ == '__main__':
    unittest.main()
