# -*- coding: utf-8 -*-
"""Trava os cards das duas fileiras da Home Classica/Aurora contra redesenho.

Estes hashes sao os da Home Clássica distribuida como skin.novatv nas versões
até a 1.0.86 (67974c2): cards 300x170 com anel de foco e titulo. Fonte, dados e
navegação não entram no hash — só a aparência do card.
"""
import hashlib
import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

HOME = Path(__file__).resolve().parents[1] / 'kodi/skin.estilo.personalizado/xml/Home.xml'
EXPECTED = {
    ('9201', 'itemlayout'): 'd8b773f055bf6c843f28e3d0ea929843f19a186f9cb80a889db43bd9f4b48716',
    ('9201', 'focusedlayout'): '9f7f0e267c6799e120c25566c1a7c1975f9922e5b1cb4e59eb3a2defe3df478d',
    ('9203', 'itemlayout'): 'd8b773f055bf6c843f28e3d0ea929843f19a186f9cb80a889db43bd9f4b48716',
    ('9203', 'focusedlayout'): '9f7f0e267c6799e120c25566c1a7c1975f9922e5b1cb4e59eb3a2defe3df478d',
}


def canonical(element):
    return [element.tag, sorted(element.attrib.items()), (element.text or '').strip(),
            [canonical(child) for child in element]]


class OriginalHomeDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(HOME).getroot()

    def test_cards_das_fileiras_da_home_original(self):
        for (ident, layout), expected in EXPECTED.items():
            with self.subTest(control=ident, layout=layout):
                node = self.root.find(".//control[@id='%s']/%s" % (ident, layout))
                self.assertIsNotNone(node)
                dados = json.dumps(canonical(node), ensure_ascii=False,
                                   separators=(',', ':')).encode()
                self.assertEqual(hashlib.sha256(dados).hexdigest(), expected)

    def test_geometria_da_home_original(self):
        # Lançamentos e Séries visíveis ao mesmo tempo, 570 e 822 de altura.
        for ident, topo in (('9201', '570'), ('9203', '822')):
            lista = self.root.find(".//control[@id='%s']" % ident)
            self.assertEqual((lista.findtext('top') or '').strip(), topo)
            self.assertEqual((lista.findtext('height') or '').strip(), '194')
        # Hero: selo LANÇAMENTO, título, metadados, plot e as ações.
        labels = [(e.text or '').strip() for e in self.root.iter('label')]
        self.assertIn('LANÇAMENTO', labels)
        self.assertIn('Assistir', labels)
        self.assertIn('Informações', labels)


if __name__ == '__main__':
    unittest.main()
