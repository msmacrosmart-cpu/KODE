# -*- coding: utf-8 -*-
"""O log do Kodi no aparelho: leitura e limpeza de addon quebrado no perfil.

Duas provas que faltavam:

1. ``tools/kodi/analisar-kodi-log.py`` precisa achar no log REAL as linhas que
   o Kodi escreve quando a tela de um addon falha ("Add-on com erro",
   "Failed to load addon", "Unable to load addon"). Sem isso, "o log esta
   limpo" e so ausencia de leitura.
2. ``service.limpar_addons_quebrados`` precisa apagar do perfil do aparelho o
   addon sem codigo (pasta sem ``addon.xml``, ``library`` ausente, addon de
   terceiro cujo zip sumiu) e NAO tocar em addon sadio.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

LOG_SUJO = u"""2026-11-18 19:02:11.001 T:1234   ERROR: ADDON: CAddonMgr::GetAddon: Failed to load addon: plugin.video.youtube
2026-11-18 19:02:11.002 T:1234   ERROR: Load: Unable to load addon plugin.program.openwizard
2026-11-18 19:02:12.000 T:1234   ERROR: CGUIControlFactory: failed to load include
2026-11-18 19:02:13.000 T:1234   ERROR: Previous line repeats 1 times. Add-on com erro
2026-11-18 19:02:14.000 T:1234   ERROR: service.smarted.bootstrap: Traceback (most recent call last)
2026-11-18 19:02:15.000 T:1234  NOTICE: Starting Kodi (21.3)
"""

LOG_LIMPO = u"""2026-11-18 19:02:15.000 T:1234  NOTICE: Starting Kodi (21.3)
2026-11-18 19:02:20.000 T:1234  NOTICE: smarted: pronto apos 1 tentativa(s)
2026-11-18 19:02:21.000 T:1234  NOTICE: skin=skin.novatv (alterada=False, instalada=False)
"""


def _ferramenta():
    spec = importlib.util.spec_from_file_location(
        'analisar_kodi_log', RAIZ / 'tools' / 'kodi' / 'analisar-kodi-log.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class AnaliseDoLogTest(unittest.TestCase):
    def setUp(self):
        self.f = _ferramenta()

    def test_acha_os_addons_com_erro_pelo_nome(self):
        r = self.f.analisar(LOG_SUJO)
        self.assertIn('plugin.video.youtube', r['addons'])
        self.assertIn('plugin.program.openwizard', r['addons'])

    def test_acha_falha_de_servico(self):
        r = self.f.analisar(LOG_SUJO)
        self.assertTrue(r['servico'])

    def test_acha_falha_de_home(self):
        r = self.f.analisar(LOG_SUJO)
        self.assertTrue(r['home'])

    def test_log_de_app_saudavel_nao_rende_defeito(self):
        r = self.f.analisar(LOG_LIMPO)
        self.assertEqual([], self.f.defeitos(r))
        self.assertFalse(r['addons'])

    def test_exigir_limpo_reprova_log_com_addon_com_erro(self):
        arquivo = os.path.join(tempfile.mkdtemp(), 'kodi.log')
        with open(arquivo, 'w') as saida:
            saida.write(LOG_SUJO)
        codigo = self.f.main(['analisar', arquivo, '--exigir-limpo'])
        self.assertEqual(1, codigo)
        shutil.rmtree(os.path.dirname(arquivo), ignore_errors=True)

    def test_exigir_limpo_aprova_log_saudavel(self):
        arquivo = os.path.join(tempfile.mkdtemp(), 'kodi.log')
        with open(arquivo, 'w') as saida:
            saida.write(LOG_LIMPO)
        codigo = self.f.main(['analisar', arquivo, '--exigir-limpo'])
        self.assertEqual(0, codigo)
        shutil.rmtree(os.path.dirname(arquivo), ignore_errors=True)


class ServicoDoAparelho(object):
    """Carrega o service.py real com os modulos do APK fingidos."""

    def __init__(self):
        self.home = tempfile.mkdtemp()
        addons = os.path.join(self.home, '.kodi', 'addons')
        os.makedirs(addons)

        def criar(nome, addon_xml=None, arquivos=()):
            pasta = os.path.join(addons, nome)
            os.makedirs(pasta)
            if addon_xml is not None:
                with open(os.path.join(pasta, 'addon.xml'), 'w') as saida:
                    saida.write(addon_xml)
            for arquivo in arquivos:
                destino = os.path.join(pasta, arquivo)
                if not os.path.isdir(os.path.dirname(destino)):
                    os.makedirs(os.path.dirname(destino))
                with open(destino, 'w') as saida:
                    saida.write('# ok\n')
            return pasta

        # sadio: addon.xml + default.py
        criar('plugin.video.bom',
              '<addon id="plugin.video.bom"><extension library="default.py"/></addon>',
              ['default.py'])
        # addon.xml aponta uma biblioteca que nao existe
        criar('plugin.video.semlib',
              '<addon id="plugin.video.semlib"><extension library="default.py"/></addon>')
        # pasta sem addon.xml
        criar('plugin.program.resto', None, ['lixo.txt'])
        # terceiro conhecido, mesmo completo, nao e desta entrega
        criar('plugin.video.youtube',
              '<addon id="plugin.video.youtube"><extension library="default.py"/></addon>',
              ['default.py'])
        # pasta que nao e addon e que mora dentro de addons/ (zips do reparo)
        os.makedirs(os.path.join(addons, 'packages'))
        with open(os.path.join(addons, 'packages', 'x.zip'), 'w') as saida:
            saida.write('zip')
        self.addons = addons
        self.modulo = self._carregar()

    def _carregar(self):
        spec = importlib.util.spec_from_file_location(
            'simular_servico_perfil', RAIZ / 'tools' / 'kodi' / 'simular-servico.py')
        ferramenta = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ferramenta)
        ok, dados = ferramenta.simular(str(RAIZ / 'kodi' / 'addons' /
                                            'service.smarted.bootstrap'))
        assert ok, dados.get('traceback')
        service = sys.modules['service']
        raiz = os.path.join(self.home, '.kodi')

        def traduzir(caminho):
            # special://home/addons -> <home>/.kodi/addons (como no aparelho)
            return (caminho.replace('special://home', raiz)
                    .replace('special:\\home', raiz))
        service.xbmc.translatePath = traduzir
        return service

    def limpar(self):
        shutil.rmtree(self.home, ignore_errors=True)


class LimpezaNoPerfilTest(unittest.TestCase):
    def setUp(self):
        self.aparelho = ServicoDoAparelho()

    def tearDown(self):
        self.aparelho.limpar()

    def test_apaga_addon_sem_codigo_e_preserva_o_sadio(self):
        registros = []
        removidos = self.aparelho.modulo.limpar_addons_quebrados(registros.append)
        # "plugin.program.resto" (pasta sem addon.xml) NAO sai: a heuristica
        # apagou addons do motor do Kodi no APK e derrubou o CAddonMgr.
        self.assertEqual(['plugin.video.semlib', 'plugin.video.youtube'],
                         removidos)
        restantes = sorted(os.listdir(self.aparelho.addons))
        self.assertEqual(['packages', 'plugin.program.resto', 'plugin.video.bom'],
                         restantes,
                         'packages (zips do reparo) e pasta solta ficam: '
                         'a heuristica de pasta sem addon.xml derrubava o motor')
        self.assertTrue(any('retirados do perfil' in linha for linha in registros),
                        'a remocao precisa ficar registrada no log')

    def test_roda_duas_vezes_sem_quebrar(self):
        self.aparelho.modulo.limpar_addons_quebrados()
        self.assertEqual([], self.aparelho.modulo.limpar_addons_quebrados())


if __name__ == '__main__':
    unittest.main()
