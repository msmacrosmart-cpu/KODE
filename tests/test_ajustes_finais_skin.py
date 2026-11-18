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
        # rodada 19: navegacao nativa do addon de volta (o padrao que funcionava).
        # A grade e uma vista OPCIONAL (52); o padrao e a lista 50.
        texto = (XML / 'MyVideoNav.xml').read_text(encoding='utf-8')
        self.assertIn('<defaultcontrol always="true">50</defaultcontrol>', texto)
        self.assertIn('<views>50,51,52</views>', texto)
        filtros = texto[texto.index('<control type="grouplist" id="9060">'):]
        # A barra vale em qualquer vista (a janela abre na 50, mas a 52 tambem
        # usa filtro). O filtro em si NAO pode ser Container.SetSortMethod:
        # em diretorio de plugin o Kodi 21 so aplica metodo declarado pelo
        # addon, e a pasta do Brazuca declara apenas SortByNone - os botoes
        # chamavam um id inexistente e nada mudava.
        self.assertIn('<visible>!String.Contains(Container.FolderPath,mode=21)</visible>',
                      filtros)
        self.assertEqual(filtros.count('Container.SetSortMethod'), 0)
        for ordem in ('todos', 'az', 'za', 'adicionados', 'votados', 'recentes'):
            self.assertIn('route=ordenar&amp;ordem=%s' % ordem, filtros)

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
