# -*- coding: utf-8 -*-
"""Ajuste de desempenho: cache do advancedsettings acompanha o aparelho.

Pedido do usuario: "se houver alguma configuracao pra melhorar o desempenho do
app e do player, teste 3 vezes, passando no teste, adicione ao app".

O que muda (e por que e seguro):

* o `advancedsettings.xml` (que o Kodi le ANTES de subir addons) passa a usar
  o mesmo perfil de memoria do resto do app: TV/box/stick/celular com RAM
  suficiente continuam com 256 MB; projetor - e aparelho que ja provou precisar
  do perfil leve - usa 96 MB. Antes o arquivo era fixo em 256 MB mesmo nesses
  aparelhos, e era ele que deixava a Home "carregando para sempre" com 1 GB de
  RAM (o proprio modulo documenta esse defeito para o projetor);
* nada muda em layout, nos valores aprovados de TV/box/stick, nem no
  advancedsettings do usuario (que continua preservado).

Este arquivo roda o mesmo conjunto de verificacoes TRES vezes (PASSADAS=3),
para cumprir a exigencia de "teste 3 vezes, passando, adicione".
"""
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
PASSADAS = 3

# Teto de cache do perfil leve (projetor/box com pouca RAM) e piso do perfil
# normal. Se algum dia alguem mexer nisso sem medir, o teste avisa.
CACHE_LEVE_MAXIMO = 128 * 1024 * 1024
CACHE_NORMAL = 256 * 1024 * 1024


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def carregar_performance():
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
    xbmc.getInfoLabel = lambda *a, **k: ''
    xbmc.getCondVisibility = lambda *a, **k: False
    xbmc.log = lambda *a, **k: None
    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: p
    xbmcvfs.exists = lambda p: False
    salvos = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs')}
    sys.modules.update(xbmc=xbmc, xbmcvfs=xbmcvfs)
    modulo = carregar('performance_desempenho', BOOTSTRAP / 'performance.py')
    modulo._salvos = salvos
    return modulo


class DesempenhoTest(unittest.TestCase):
    """O mesmo conjunto de verificacoes em 3 passadas independentes."""

    def setUp(self):
        self.performance = carregar_performance()

    def tearDown(self):
        for nome, antigo in self.performance._salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    # -- uma passada completa ------------------------------------------------
    def _uma_passada(self, passada):
        performance = self.performance
        pasta = tempfile.mkdtemp()

        # 1) TV/box/stick continuam com o cache que ja estava aprovado
        self.assertTrue(
            performance.write_advancedsettings(pasta, nome_dispositivo='Mi Box S'),
            'passada %d: TV box nao gravou' % passada)
        corpo = Path(pasta, 'userdata', 'advancedsettings.xml').read_text()
        self.assertIn('<memorysize>%d</memorysize>' % CACHE_NORMAL, corpo)
        self.assertIn('<readfactor>10.0</readfactor>', corpo)
        self.assertIn('<buffermode>4</buffermode>', corpo)
        self.assertIn(performance.MARKER, corpo)

        # 2) projetor/box de 1 GB: cache menor, para a Home caber na memoria
        outra = tempfile.mkdtemp()
        self.assertTrue(performance.write_advancedsettings(
            outra, nome_dispositivo='XGIMI Halo+ Projector'))
        leve = Path(outra, 'userdata', 'advancedsettings.xml').read_text()
        import re
        memorysize = int(re.search(r'<memorysize>(\d+)</memorysize>', leve).group(1))
        self.assertLessEqual(memorysize, CACHE_LEVE_MAXIMO)
        self.assertGreater(memorysize, 0)
        # o cache continua ligado para todos os streams: so o tamanho muda
        self.assertIn('<buffermode>4</buffermode>', leve)
        # nao perder as melhorias de rede que ja existiam
        self.assertIn('<curlclienttimeout>20</curlclienttimeout>', leve)

        # 3) advancedsettings do usuario NUNCA e sobrescrito
        terceira = tempfile.mkdtemp()
        arquivo = Path(terceira, 'userdata', 'advancedsettings.xml')
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text('<advancedsettings><loglevel>1</loglevel></advancedsettings>')
        self.assertFalse(performance.write_advancedsettings(
            terceira, nome_dispositivo='XGIMI Halo+ Projector'))
        self.assertIn('loglevel', arquivo.read_text())

        # 4) idempotente: rodar de novo nao muda o arquivo
        antes = Path(pasta, 'userdata', 'advancedsettings.xml').read_text()
        performance.write_advancedsettings(pasta, nome_dispositivo='Mi Box S')
        self.assertEqual(
            antes, Path(pasta, 'userdata', 'advancedsettings.xml').read_text())

        # 5) os settings do player continuam os mesmos que ja funcionavam
        store = {}

        def jsonrpc(metodo, params=None):
            if metodo == 'Settings.SetSettingValue':
                store[params['setting']] = params['value']
                return {}
            if metodo == 'Settings.GetSettingValue':
                return {'result': {'value': store.get(params['setting'])}}
            return {}

        aplicados, recusados = performance.apply_settings(
            jsonrpc, None, nome_dispositivo='Mi Box S')
        self.assertEqual(recusados, [])
        self.assertTrue(store['videoplayer.usemediacodecsurface'])
        self.assertTrue(store['videoplayer.usemediacodec'])
        self.assertEqual(store['filecache.buffermode'], 4)
        self.assertIn('filecache.memorysize', aplicados)

    def test_passada_1(self):
        self._uma_passada(1)

    def test_passada_2(self):
        self._uma_passada(2)

    def test_passada_3(self):
        self._uma_passada(3)

    def test_tres_passadas_seguidas_no_mesmo_aparelho(self):
        """Estabilidade: repetir 3x no mesmo perfil nao acumula nem regride."""
        pasta = tempfile.mkdtemp()
        corpos = []
        for _ in range(PASSADAS):
            self.performance.write_advancedsettings(
                pasta, nome_dispositivo='Fire TV Stick')
            corpos.append(Path(pasta, 'userdata', 'advancedsettings.xml').read_text())
        self.assertEqual(len(set(corpos)), 1, 'o arquivo mudou entre passadas')

    def test_servico_aplica_o_desempenho_no_boot_e_no_reparo(self):
        fonte = (BOOTSTRAP / 'service.py').read_text()
        main = fonte[fonte.index('def main():'):]
        self.assertIn('apply_performance()', main)
        # o preparo em segundo plano (que roda com a Home ja na tela) tambem
        preparo = fonte[fonte.index('def _preparar_em_segundo_plano('):]
        preparo = preparo[:preparo.index('def main()')]
        self.assertIn('apply_performance()', preparo)


if __name__ == '__main__':
    unittest.main()
