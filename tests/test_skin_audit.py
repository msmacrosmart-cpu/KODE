"""Static contracts; these do not substitute for Kodi runtime checks."""
from collections import Counter
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SKIN = ROOT / 'kodi/skin.novatv'
BRIDGE = ROOT / 'kodi/addons/plugin.video.smarted'


class Audit(unittest.TestCase):
    def test_includes_static_textures_and_control_ids(self):
        roots = [(p, ET.parse(p).getroot()) for p in (SKIN / 'xml').glob('*.xml')]
        defined = {n.get('name') for _, r in roots for n in r.iter('include') if n.get('name')}
        for path, root in roots:
            ids = [n.get('id') for n in root.iter('control') if (n.get('id') or '').isdigit()]
            self.assertFalse([i for i, count in Counter(ids).items() if count > 1], str(path))
            for node in root.iter('include'):
                name = node.get('content') or (node.text or '').strip()
                if not node.get('name') and name:
                    self.assertIn(name, defined, str(path))
            for node in root.iter():
                text = (node.text or '').strip()
                if node.tag.startswith('texture') and text and text != '-' and '$' not in text:
                    self.assertTrue((SKIN / 'media' / text).is_file(), str(path) + ': ' + text)

    def test_hero_actions_and_removed_band(self):
        root = ET.parse(SKIN / 'xml/Home.xml').getroot()
        hero = root.find(".//control[@id='9100']")
        for name in ('itemlayout', 'focusedlayout'):
            self.assertNotIn('scrim_v.png', [x.text for x in hero.find(name).iter('texture')])
        actions = root.find(".//control[@id='9110']").findall('onclick')
        self.assertEqual(len(actions), 2)
        self.assertTrue(any('ActivateWindow(Videos,' in x.text and 'IsFolder' in x.get('condition') for x in actions))
        self.assertTrue(any('PlayMedia(' in x.text for x in actions))
        self.assertIn('hero_details.py', root.find(".//control[@id='9112']/onclick").text)

    def test_artwork_and_player_controls_exist(self):
        for name in ('tv', 'movies', 'series', 'doramas', 'animes', 'novelas', 'desenhos'):
            self.assertTrue((BRIDGE / 'resources/categories' / (name + '.png')).is_file())
        osd = ET.parse(SKIN / 'xml/VideoOSD.xml').getroot()
        controls = {x.get('id'): x for x in osd.iter('control') if x.get('id')}
        self.assertEqual(controls['87'].findtext('action'), 'seek')
        for ident in ('600', '601', '602', '603', '606', '607', '70046', '710', '711', '70044'):
            self.assertIsNotNone(controls[ident].find('onclick'), ident)
        bookmarks = ET.parse(SKIN / 'xml/VideoOSDBookmarks.xml').getroot()
        ids = {x.get('id') for x in bookmarks.iter('control')}
        self.assertTrue({'2','3','4','11'}.issubset(ids))


if __name__ == '__main__':
    unittest.main()
