# -*- coding: utf-8 -*-
"""Rodada 15: pastas sem poster, menu lateral so texto, silencio e barra limpa."""
import pathlib
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
XML = ROOT / 'kodi/skin.estilo.personalizado/xml'


class AjustesFinaisTest(unittest.TestCase):
    def test_pastas_nao_usam_poster(self):
        # a tela final (com video) e a unica que entra na grade; a intermediaria
        # fica na lista vertical, e os filtros so existem na grade
        plugin = (ROOT / 'kodi/addons/plugin.video.smarted/default.py').read_text(encoding='utf-8')
        # rodada 18: VOD voltou para a lista original (sem grade) e os filtros
        # aparecem na lista, nunca na TV ao vivo
        self.assertIn("Container.SetViewMode(50)", plugin)
        texto = (XML / 'MyVideoNav.xml').read_text(encoding='utf-8')
        self.assertNotIn('id="52"', texto)
        filtros = texto[texto.index('<control type="grouplist" id="9060">'):]
        self.assertIn('<visible>Control.IsVisible(50) + !String.Contains(Container.FolderPath,tv=1)</visible>',
                      filtros)
        self.assertEqual(filtros.count('route=pasta'), 6)

    def test_menu_lateral_sem_icones(self):
        texto = (XML / 'MyVideoNav.xml').read_text(encoding='utf-8')
        trilha = texto[texto.index('<control type="grouplist" id="9000">'):
                       texto.index('<control type="grouplist" id="9050">')]
        self.assertNotIn('smarted_nav_icon_', texto)
        self.assertNotIn('type="image"', trilha)

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
