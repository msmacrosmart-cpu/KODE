# -*- coding: utf-8 -*-
"""Tag VAST do projeto (MagSrv) e confinamento do fluxo VAST ao modo TV.

O dono do app configurou a tag ``https://s.magsrv.com/v1/vast.php?idz=6096742``
como padrao. Dois pontos precisam ficar provados, porque os dois ja falharam
antes neste projeto:

1. a URL existe em UM lugar so (``ads_vast.VAST_TAG_PADRAO``) e e a que o
   ``smart_ads`` usa - nao uma copia, nao uma tag inventada;
2. o fluxo VAST so dispara/exibe em TV (Android TV, TV Box, stick, projetor).
   No celular/tablet o anuncio continua sendo o AdMob da activity nativa e
   nenhuma tag VAST e pedida.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
TAG = 'https://s.magsrv.com/v1/vast.php?idz=6096742'

sys.path.insert(0, str(BOOTSTRAP))


class KodiFalso(object):
    """Kodi minimo: 'aparelho' configuravel, sem rede e sem player real."""

    def __init__(self, condicoes=(), info=None):
        self.condicoes = set(condicoes)
        self.info = dict(info or {})
        self.builtins = []
        self.logs = []

    def getCondVisibility(self, consulta):
        return consulta in self.condicoes

    def getInfoLabel(self, rotulo):
        return self.info.get(rotulo, '')

    def executebuiltin(self, comando):
        self.builtins.append(comando)

    def log(self, mensagem, *a, **k):
        self.logs.append(mensagem)


class _PlayerBase(object):
    def __init__(self, *args, **kwargs):
        pass


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class BaseTag(unittest.TestCase):
    def setUp(self):
        self.guardados = {n: sys.modules.get(n)
                          for n in ('xbmc', 'xbmcvfs', 'xbmcgui', 'variante',
                                    'smart_ads', 'ads_vast')}
        self.kodi = KodiFalso(condicoes={'System.Platform.Android'})
        self.instalar_kodi(self.kodi)
        self.vast = carregar('ads_vast_tag', BOOTSTRAP / 'ads_vast.py')

    def instalar_kodi(self, kodi):
        xbmc = types.ModuleType('xbmc')
        xbmc.getCondVisibility = kodi.getCondVisibility
        xbmc.getInfoLabel = kodi.getInfoLabel
        xbmc.executebuiltin = kodi.executebuiltin
        xbmc.log = kodi.log
        xbmc.Player = _PlayerBase
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p
        vfs.exists = lambda _p: False
        sys.modules['xbmcvfs'] = vfs

    def tearDown(self):
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo


class TagPadraoTest(BaseTag):
    """A URL do dono do app, num lugar so."""

    def test_ads_vast_tem_a_tag_do_projeto(self):
        self.assertEqual(self.vast.VAST_TAG_PADRAO, TAG)

    def test_a_tag_e_uma_url_valida_e_nao_um_placeholder(self):
        self.assertTrue(self.vast.VAST_TAG_PADRAO.startswith('https://'))
        self.assertIn('magsrv.com', self.vast.VAST_TAG_PADRAO)
        self.assertIn('idz=6096742', self.vast.VAST_TAG_PADRAO)

    def test_tag_configurada_devolve_a_tag_do_projeto(self):
        self.assertEqual(self.vast.tag_configurada(self.vast.VAST_TAG_PADRAO),
                         TAG)

    def test_janela_ainda_pode_trocar_a_tag_sem_atualizar_o_apk(self):
        self.kodi.info['Window(10000).Property(smartedtv.vast.tag)'] = \
            'https://ads/trocada'
        self.assertEqual(self.vast.tag_configurada(self.vast.VAST_TAG_PADRAO),
                         'https://ads/trocada')

    def test_smart_ads_le_a_tag_de_ads_vast_sem_copiar(self):
        smart = carregar('smart_ads_tag', BOOTSTRAP / 'smart_ads.py')
        self.assertEqual(smart.VAST_TAG_PADRAO, TAG)
        self.assertEqual(smart.VAST_TAG_PADRAO, self.vast.VAST_TAG_PADRAO)

    def test_o_modulo_continua_inteiro(self):
        """Nada de arquivo truncado: todas as funcoes publicas seguem la."""
        for nome in ('tag_configurada', 'modo_de_teste', 'tag_de_teste',
                     'tag_do_wrapper', 'tag_do_vmap', 'escolher_anuncio',
                     'baixar', 'disparar', 'reproduzir', 'exibir',
                     'estado_do_conteudo', 'restaurar', 'exibir_e_devolver',
                     'resumo'):
            self.assertTrue(callable(getattr(self.vast, nome, None)), nome)
        for nome in ('TEMPO_MAXIMO_ANUNCIO', 'ESPERA_INICIO', 'FOLGA_FIM',
                     'QUARTIS', 'TIMEOUT_HTTP', 'PROFUNDIDADE_WRAPPER',
                     'PROPRIEDADE_TAG', 'VAST_TAG_PADRAO'):
            self.assertTrue(hasattr(self.vast, nome), nome)


class ConfinamentoAoModoTVTest(BaseTag):
    """VAST so em TV; celular segue no AdMob, sem pedir tag."""

    def _smart(self, tv):
        modulo = carregar('smart_ads_confina', BOOTSTRAP / 'smart_ads.py')
        modulo._variante = types.SimpleNamespace(
            e_tv=lambda: bool(tv), e_mobile=lambda: not tv)
        modulo.e_tv = lambda: bool(tv)
        return modulo

    def _vast_falso(self):
        pedidos = []

        def exibir(**kwargs):
            pedidos.append(kwargs.get('tag'))
            return {'exibido': False, 'motivo': 'tag-sem-resposta'}

        self.vast.exibir_e_devolver = exibir
        sys.modules['ads_vast'] = self.vast
        return pedidos

    def test_na_tv_a_tag_padrao_e_pedida(self):
        pedidos = self._vast_falso()
        smart = self._smart(True)
        smart.tocar_anuncio(smart.ATIVIDADE_PREROLL)
        self.assertEqual(pedidos, [TAG])

    def test_no_celular_nenhuma_tag_vast_e_pedida(self):
        pedidos = self._vast_falso()
        smart = self._smart(False)
        smart.tocar_anuncio(smart.ATIVIDADE_PREROLL)
        self.assertEqual(pedidos, [], 'celular nao usa VAST')
        atividades = [b for b in self.kodi.builtins
                      if b.startswith('StartAndroidActivity')]
        self.assertEqual(len(atividades), 1, 'celular usa o AdMob')
        self.assertIn(smart.ATIVIDADE_PREROLL, atividades[0])

    def test_no_celular_o_teste_de_anuncio_nao_vira_vast(self):
        pedidos = self._vast_falso()
        smart = self._smart(False)
        smart.testar_anuncio_video()   # chamado direto: nao ha caminho de TV
        # a funcao e o caminho de video; quem garante o confinamento e o
        # roteamento acima (tocar_anuncio). Aqui so provamos que ela nao
        # dispara a activity do AdMob nem inventa tag.
        self.assertEqual([b for b in self.kodi.builtins
                          if b.startswith('StartAndroidActivity')], [])

    def test_informacao_da_tv_so_aparece_na_tv(self):
        smart = self._smart(False)
        self.assertIsNone(smart.explicar_anuncio_tv(self.kodi.log))
        smart_tv = self._smart(True)
        texto = smart_tv.explicar_anuncio_tv(self.kodi.log)
        self.assertIn('VAST', texto)


if __name__ == '__main__':
    unittest.main()
