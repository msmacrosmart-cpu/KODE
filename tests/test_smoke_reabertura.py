# -*- coding: utf-8 -*-
"""O smoke do emulador tem de testar reabertura (tela preta / app saindo).

Sem isso o pipeline publicava um APK que abria preto e ninguém percebia: o
teste antigo só abria o app uma vez por launcher.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / 'smartedtv/release/install-smoke.sh'


class SmokeReaberturaTest(unittest.TestCase):
    def setUp(self):
        self.texto = SMOKE.read_text(encoding='utf-8')

    def test_reabre_o_app_varias_vezes(self):
        self.assertIn('for ciclo in 1 2 3', self.texto)
        self.assertIn('am force-stop', self.texto)

    def test_falha_se_o_processo_morrer(self):
        self.assertIn('o processo morreu', self.texto)
        self.assertIn('pidof "$pkg"', self.texto)

    def test_falha_se_a_tela_ficar_preta(self):
        self.assertIn('tela_preto', self.texto)
        self.assertIn('ImageStat', self.texto)
        self.assertIn('brilho medio', self.texto)

    def test_nao_mexe_no_workflow(self):
        """A ordem do pipeline continua a mesma; só o script do smoke muda."""
        workflow = (ROOT / '.github/workflows/smartedtv-universal.yml').read_text(
            encoding='utf-8')
        self.assertIn('bash smartedtv/release/install-smoke.sh', workflow)


if __name__ == '__main__':
    unittest.main()
