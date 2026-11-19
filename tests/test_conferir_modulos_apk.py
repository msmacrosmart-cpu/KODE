# -*- coding: utf-8 -*-
"""O conferidor de modulos no APK tem de reprovar o APK incompleto.

Foi um APK assim (sem ads_regra.py) que chegou ao projetor e derrubou o
service.py no boot. O conferidor roda no CI antes de publicar; estes testes
garantem que ele realmente reprova o caso real, e nao que "sempre passa".
"""
import importlib.util
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'kodi' / 'conferir-modulos-no-apk.py'
PREFIXO = 'assets/addons/service.smarted.bootstrap/'


def _carregar():
    spec = importlib.util.spec_from_file_location('conferir_modulos', TOOL)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class ConferirModulosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _carregar()
        cls.modulos = cls.tool.modulos_do_injetor()

    def _apk(self, pasta, nomes):
        destino = pasta / 'teste.apk'
        with zipfile.ZipFile(destino, 'w') as z:
            for nome in nomes:
                z.writestr(PREFIXO + nome, b'# ' + nome.encode())
        return destino

    def test_lista_do_injetor_tem_os_modulos_do_bug(self):
        for esperado in ('ads_regra.py', 'ads_vast.py', 'repair.py',
                         'favourites.py', 'skin_setup.py'):
            self.assertIn(esperado, self.modulos)

    def test_apk_completo_passa(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            apk = self._apk(Path(tmp), self.modulos)
            presentes, faltando = self.tool.conferir(apk, self.modulos)
            self.assertEqual(faltando, [])
            self.assertEqual(len(presentes), len(self.modulos))

    def test_apk_sem_ads_regra_reprova(self):
        """O caso real: sem ads_regra.py o servico morre no import."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            sem = [m for m in self.modulos if m != 'ads_regra.py']
            apk = self._apk(Path(tmp), sem)
            _, faltando = self.tool.conferir(apk, self.modulos)
            self.assertEqual(faltando, ['ads_regra.py'])
            self.assertEqual(self.tool.main([str(apk)]), 1)

    def test_apk_completo_devolve_zero(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            apk = self._apk(Path(tmp), self.modulos)
            self.assertEqual(self.tool.main([str(apk)]), 0)


if __name__ == '__main__':
    unittest.main()
