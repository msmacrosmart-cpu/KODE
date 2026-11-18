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
            # Ids dentro de <include name=...> são modelos: o Kodi renumera por
            # instância e a skin Clássica usa o mesmo 799 em dois botões de toque
            # mutuamente exclusivos. A duplicata proibida é entre controles reais.
            modelos = {id(n) for inc in root.iter('include') if inc.get('name')
                       for n in inc.iter('control')}
            # Só controles focáveis disputam o D-pad; imagens/labels aninhadas
            # com o mesmo id (inclusive NumItems) não são foco.
            ids = [n.get('id') for n in root.iter('control')
                   if (n.get('id') or '').isdigit() and id(n) not in modelos
                   and n.get('type') in ('button', 'radiobutton', 'grouplist', 'list',
                                         'edit', 'spinbox', 'panel', 'textbox')]
            self.assertFalse([i for i, count in Counter(ids).items() if count > 1], str(path))
            for node in root.iter('include'):
                name = node.get('content') or (node.text or '').strip()
                if not node.get('name') and name and '$' not in name:
                    self.assertIn(name, defined, str(path))
            for node in root.iter():
                text = (node.text or '').strip()
                if node.tag.startswith('texture') and text and text != '-' and '$' not in text:
                    if text.startswith('special://'):
                        continue  # resolve no Kodi instalado, não na skin
                    self.assertTrue((SKIN / 'media' / text).is_file(), str(path) + ': ' + text)

    def test_hero_actions_e_fanart(self):
        """Home Classica/Aurora: hero pela fileira 9201, acoes em 9300."""
        root = ET.parse(SKIN / 'xml/Home.xml').getroot()
        self.assertIsNotNone(root.find(".//control[@id='9201']"))
        acoes = root.find(".//control[@id='9300']")
        botoes = {c.get('id'): c for c in acoes.findall('control')}
        self.assertIn('PlayMedia(', botoes['9301'].findtext('onclick'))
        self.assertIn('Trailer', botoes['9302'].findtext('onclick'))
        info = ' '.join(e.text or '' for e in botoes['9303'].findall('onclick'))
        self.assertIn('Action(Info)', info)
        # o fundo do hero e o fanart do item (nunca uma imagem fixa da skin)
        textos = [x.text or '' for x in root.iter('texture')]
        self.assertTrue(any('Container(9201).ListItem.Art(fanart)' in t for t in textos))

    def test_artwork_e_controles_do_player_existem(self):
        # A Home Clássica usa as janelas/OSD dela; a checagem de arte por
        # categoria valia para a skin removida. Aqui: arte das fileiras + OSD.
        home = ET.parse(SKIN / 'xml/Home.xml').getroot()
        self.assertTrue(home.find(".//control[@id='9201']/itemlayout"))
        osd = ET.parse(SKIN / 'xml/VideoOSD.xml').getroot()
        controls = {x.get('id'): x for x in osd.iter('control') if x.get('id')}
        for ident in ('600', '601', '602', '603'):
            self.assertIsNotNone(controls.get(ident), ident)
        for name in ('tv', 'movies', 'series', 'doramas', 'animes', 'novelas', 'desenhos'):
            self.assertTrue((BRIDGE / 'resources/categories' / (name + '.png')).is_file())
        self.assertIn('87', controls)
        # OSD da Clássica: a barra de progresso e os botões do player existem
        ids = {x.get('id') for x in osd.iter('control')}
        self.assertTrue(ids & {'600', '601', '602', '603', '604', '605'},
                        'barra/botões do OSD ausentes')


if __name__ == '__main__':
    unittest.main()
