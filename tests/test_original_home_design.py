"""Lock the supplied NovaTV hero and row card layouts against redesign.

Hashes were calculated from skin.novatv.zip SHA-256
86b9808741bdc00f498dd7d83192518251a455b034eb667e90442e4182df1acb.
Whitespace, the Home data sources and navigation are not part of these hashes.
"""
import hashlib
import json
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET

HOME = Path(__file__).resolve().parents[1] / 'kodi/skin.novatv/xml/Home.xml'
EXPECTED = {
    ('9100','itemlayout'): 'cc2972ee413050f8b6f1e7f4dbb8d780840763e0ccbaf9adc08fc034d517a29c',
    ('9100','focusedlayout'): '3af01ef5c0474b953f2187aedbf6dd052e5e8cd1402124133eef6ff6c831302f',
    ('9200','itemlayout'): 'dd8f347c2e70b5c45065654bc1fa2d1fd382f2b5bfb4f712849c579f2f0a3477',
    ('9200','focusedlayout'): 'd517bd256b12fef6e19bc509183ddbef6d6f20e27726b2ebd4df35f630e92296',
    ('9210','itemlayout'): '3877b5233f8da889136afb4db201a4f87dec6fba9dfd5ba2c0c9a9aab3d7b3c8',
    ('9210','focusedlayout'): 'ca60938ffdc42c4bc565f59f234eeb22488329a7c492d0a331a2395c36b56990',
    ('9220','itemlayout'): 'dd8f347c2e70b5c45065654bc1fa2d1fd382f2b5bfb4f712849c579f2f0a3477',
    ('9220','focusedlayout'): 'd517bd256b12fef6e19bc509183ddbef6d6f20e27726b2ebd4df35f630e92296',
    ('9230','itemlayout'): '3877b5233f8da889136afb4db201a4f87dec6fba9dfd5ba2c0c9a9aab3d7b3c8',
    ('9230','focusedlayout'): 'ca60938ffdc42c4bc565f59f234eeb22488329a7c492d0a331a2395c36b56990',
}


def canonical(element):
    return [element.tag, sorted(element.attrib.items()), (element.text or '').strip(),
            [canonical(child) for child in element]]


class OriginalHomeDesignTest(unittest.TestCase):
    def test_original_card_appearances(self):
        root=ET.parse(HOME).getroot()
        for (ident, layout), expected in EXPECTED.items():
            with self.subTest(control=ident,layout=layout):
                node=root.find(".//control[@id='%s']/%s" % (ident,layout))
                self.assertIsNotNone(node)
                data=json.dumps(canonical(node),ensure_ascii=False,separators=(',',':')).encode()
                self.assertEqual(hashlib.sha256(data).hexdigest(),expected)

if __name__=='__main__': unittest.main()
