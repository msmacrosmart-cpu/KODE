# -*- coding: utf-8 -*-
"""Rodada 15: pastas sem poster, menu lateral so texto, silencio e barra limpa."""
import pathlib
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
XML = ROOT / 'kodi/skin.estilo.personalizado/xml'


class AjustesFinaisTest(unittest.TestCase):
    def test_pastas_nao_usam_poster(self):
        texto = (XML / 'MyVideoNav.xml').read_text(encoding='utf-8')
        painel = texto[texto.index('<control type="panel" id="52">'):]
        # a arte do poster so aparece em item reproduzivel; pasta tem cartao proprio
        self.assertIn('<texture background="true">$VAR[ItemArt]</texture><visible>!ListItem.IsFolder</visible>', painel)
        self.assertIn('<visible>ListItem.IsFolder</visible>', painel)
        self.assertIn('icons/filemanager.png', painel)

    def test_menu_lateral_sem_icones(self):
        texto = (XML / 'MyVideoNav.xml').read_text(encoding='utf-8')
        self.assertNotIn('smarted_nav_icon_', texto)
        self.assertNotIn('<left>12</left><top>', texto)

    def test_navegacao_silenciosa(self):
        addon = ROOT / 'kodi/addons/resource.uisounds.silencio'
        raiz = ET.parse(addon / 'addon.xml').getroot()
        pontos = [e.get('point') for e in raiz.findall('extension')]
        self.assertIn('kodi.resource.uisounds', pontos)
        sons = ET.parse(addon / 'sounds.xml').getroot()
        self.assertEqual(sons.tag, 'sounds')
        self.assertEqual(list(sons), [])  # nenhum som definido
        servico = (ROOT / 'kodi/addons/service.smarted.bootstrap/service.py').read_text(encoding='utf-8')
        self.assertIn("lookandfeel.soundskin", servico)
        self.assertIn('resource.uisounds.silencio', servico)
        build = (ROOT / 'tools/kodi/build-release-apk.py').read_text(encoding='utf-8')
        self.assertIn('resource.uisounds.silencio', build)

    def test_home_sem_botao_de_addons(self):
        texto = (XML / 'Home.xml').read_text(encoding='utf-8')
        self.assertNotIn('ActivateWindow(10040)', texto)
        self.assertNotIn('icons/settings/addons.png', texto)
        for botao in ('9121', '9122', '9123'):  # busca, ajustes, sair
            self.assertIn('id="%s"' % botao, texto)


if __name__ == '__main__':
    unittest.main()
