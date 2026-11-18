# -*- coding: utf-8 -*-
"""skin.novatv é o espelho da skin Clássica/Aurora: nada pode divergir.

O APK da 1.0.92 usa ``skin.novatv`` como skin ativa. A Home desejada é a da
Clássica (67974c2); para o pacote não voltar a mostrar outra Home, os arquivos
publicados têm de ser exatamente os da fonte.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTE = ROOT / 'kodi' / 'skin.estilo.personalizado'
ESPELHO = ROOT / 'kodi' / 'skin.novatv'
PASTAS = ('xml', 'media', 'fonts', 'colors', 'playlists', 'resources', 'language', 'extras')


def arquivos(base):
    return {p.relative_to(base).as_posix(): p.read_bytes()
            for pasta in PASTAS if (base / pasta).is_dir()
            for p in (base / pasta).rglob('*') if p.is_file()}


class EspelhoDaClassicaTest(unittest.TestCase):
    def test_arquivos_identicos(self):
        fonte, espelho = arquivos(FONTE), arquivos(ESPELHO)
        self.assertTrue(fonte, 'skin fonte vazia')
        self.assertEqual(sorted(set(fonte) - set(espelho)), [], 'faltam no espelho')
        self.assertEqual(sorted(set(espelho) - set(fonte)), [], 'sobrando no espelho')
        diferentes = [n for n in fonte if fonte[n] != espelho.get(n)]
        self.assertEqual(diferentes, [], 'arquivos diferentes')

    def test_toda_fonte_citada_existe_na_skin(self):
        # Kodi não cai para o fontset Default sozinho se o .ttf citado faltar:
        # a tela de entrada (wfNN) e a Home (font12/font13) usam estas fontes.
        import xml.etree.ElementTree as ET
        for base in (FONTE, ESPELHO):
            raiz = ET.parse(base / 'xml' / 'Font.xml').getroot()
            citadas = {(f.findtext('filename') or '').strip() for f in raiz.iter('font')}
            faltando = sorted(n for n in citadas
                              if n and not (base / 'fonts' / n).is_file())
            self.assertEqual(faltando, [], str(base))

    def test_home_espelhada_e_a_classica(self):
        # A Home da foto (67974c2) + os ajustes de navegação desta entrega.
        home = (ESPELHO / 'xml' / 'Home.xml').read_bytes()
        self.assertEqual(home, (FONTE / 'xml' / 'Home.xml').read_bytes())
        import xml.etree.ElementTree as ET
        raiz = ET.fromstring(home)
        self.assertEqual((raiz.find(".//control[@id='9201']/top").text or '').strip(), '570')
        self.assertEqual((raiz.find(".//control[@id='9203']/top").text or '').strip(), '822')


if __name__ == '__main__':
    unittest.main()
