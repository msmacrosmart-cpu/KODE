# -*- coding: utf-8 -*-
"""TV: VMAP (playlist de anuncios do Ad Manager) tem de virar anuncio.

Diagnostico que motivou estes testes: a tag de TESTE que o "Testar anuncio"
usava era ``external/vmap/single_ad_samples``. O corpus ``vmap`` devolve
``<vmap:VMAP><vmap:AdBreak><vmap:AdTagURI>`` - nao um ``<VAST><Ad><InLine>``.
O leitor so entendia VAST, entao o recibo saia ``vast-sem-criativo`` e nenhum
anuncio tocava, mesmo com rede e player bons. Uma tag VMAP do dono do app
(entrega padrao do Ad Manager) tinha o mesmo destino.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADS = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'


def _carregar():
    """Carrega ads_vast com stubs do Kodi (fora do aparelho nao ha xbmc)."""
    import importlib.util
    import sys
    import types

    guardados = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs', 'xbmcaddon')}
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
    xbmc.getInfoLabel = lambda _s: ''
    xbmc.getCondVisibility = lambda _s: False
    xbmc.executebuiltin = lambda *a, **k: None
    xbmc.log = lambda *a, **k: None
    xbmc.Player = lambda *a, **k: types.SimpleNamespace(
        isPlaying=lambda: False, isPlayingVideo=lambda: False,
        getPlayingFile=lambda: '', getTime=lambda: 0.0,
        getTotalTime=lambda: 0.0)
    sys.modules['xbmc'] = xbmc
    vfs = types.ModuleType('xbmcvfs')
    vfs.exists = lambda _p: False
    vfs.translatePath = lambda p: p
    sys.modules['xbmcvfs'] = vfs
    addon = types.ModuleType('xbmcaddon')
    addon.Addon = lambda *a, **k: types.SimpleNamespace(
        getSetting=lambda _k: '', getAddonInfo=lambda _k: '')
    sys.modules['xbmcaddon'] = addon
    spec = importlib.util.spec_from_file_location('ads_vast_vmap',
                                                  ADS / 'ads_vast.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    for nome, antigo in guardados.items():
        if antigo is None:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = antigo
    return modulo


VMAP = '''<?xml version="1.0" encoding="UTF-8"?>
<vmap:VMAP xmlns:vmap="http://www.iab.net/videosuite/vmap" version="1.0">
  <vmap:AdBreak timeOffset="start" breakType="linear" breakId="1">
    <vmap:AdSource allowMultipleAds="false" followRedirects="true">
      <vmap:AdTagURI templateType="vast3"><![CDATA[https://ads.test/vast]]></vmap:AdTagURI>
    </vmap:AdSource>
  </vmap:AdBreak>
</vmap:VMAP>'''


class VmapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vast = _carregar()

    def test_le_o_adbreak_do_vmap(self):
        self.assertEqual(self.vast.tag_do_vmap(VMAP), 'https://ads.test/vast')

    def test_vast_nao_e_confundido_com_vmap(self):
        vast = ('<VAST version="3.0"><Ad><InLine><AdSystem>x</AdSystem>'
                '</InLine></Ad></VAST>')
        self.assertEqual(self.vast.tag_do_vmap(vast), '')

    def test_vmap_sem_adtaguri_nao_quebra(self):
        self.assertEqual(self.vast.tag_do_vmap('<vmap:VMAP/>'), '')

    def test_xml_quebrado_nao_quebra(self):
        self.assertEqual(self.vast.tag_do_vmap('<vmap:VMAP'), '')
        self.assertEqual(self.vast.tag_do_vmap(None), '')

    def test_o_caminho_de_exibicao_segue_o_vmap(self):
        """exibir() tem de seguir a tag do VMAP e chegar ao criativo."""
        pedidos = []
        recibo = self.vast.exibir(
            tag='https://ads.test/vmap',
            baixar_tag=lambda url: (pedidos.append(url) or
                                    (VMAP if url.endswith('/vmap')
                                     else '<VAST version="3.0"/>')),
            tocar=lambda url, log=None: False,
            dormir=lambda s: None)
        self.assertEqual(pedidos, ['https://ads.test/vmap',
                                   'https://ads.test/vast'])
        # VAST vazio: o caminho tem de terminar sem anuncio, nao levantar
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'vast-sem-criativo')

    def test_tag_de_teste_devolve_vast_nao_vmap(self):
        """A tag de teste do Google tem de pedir VAST.

        ``.../vmap/single_ad_samples`` devolve VMAP; ``.../single_ad_samples``
        devolve o VAST de anuncio unico que este leitor entende.
        """
        tag = self.vast.tag_de_teste()
        self.assertIn('pubads.g.doubleclick.net', tag)
        self.assertIn('output=vast', tag)
        self.assertNotIn('/vmap/', tag,
                         'a tag de teste voltou a pedir VMAP (nao tem <Ad>)')


if __name__ == '__main__':
    unittest.main()
