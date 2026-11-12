# -*- coding: utf-8 -*-
"""Player: barra de progresso sem a bolinha branca (nib) e progresso preservado."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
XML = ROOT / 'kodi/skin.estilo.personalizado/xml'


class PlayerSemBolinhaTest(unittest.TestCase):
    def test_nib_do_player_e_transparente(self):
        for nome in ('DialogSeekBar.xml', 'Custom_1109_TopBarOverlay.xml'):
            texto = (XML / nome).read_text(encoding='utf-8')
            self.assertNotIn('<textureslidernib colordiffuse="pb_white">', texto, nome)
            self.assertNotIn('<textureslidernibfocus colordiffuse="pb_white">', texto, nome)
            self.assertIn('colordiffuse="00FFFFFF">osd/progress/nub_bar.png', texto, nome)
            # a barra de progresso continua la (controles de reproduzir/avancar/retroceder)
            self.assertIn('<control type="slider" id="401">', texto) if nome.startswith('DialogSeekBar') else None
            self.assertIn('<control type="progress">', texto)

    def test_progresso_fica_salvo_pelo_kodi(self):
        # PlayMedia simples: o Kodi aplica o bookmark de cada video (mesma URL)
        navegacao = (ROOT / 'kodi/addons/plugin.video.smarted/navigation.py').read_text(encoding='utf-8')
        self.assertIn("'PlayMedia(%s)'", navegacao)
        self.assertIn("'ActivateWindow(Videos,%s)'", navegacao)


if __name__ == '__main__':
    unittest.main()
