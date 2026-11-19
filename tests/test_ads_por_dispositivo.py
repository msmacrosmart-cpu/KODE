# -*- coding: utf-8 -*-
"""Monetizacao por dispositivo + cor da tela de pastas.

Pedido do usuario nesta rodada:

* celular/tablet: AdMob como sempre foi (nada muda);
* TV, TV Box, projetor e Fire Stick: anuncio de video VAST (Google IMA) com
  D-pad e botao oficial de pular;
* tela de pastas/categorias: o bloco superior estava branco estourado e tem
  de voltar ao cinza do tema escuro, chegando ao APK.

O que estes testes garantem de fato:

1. a deteccao de dispositivo responde ``celular`` para telefone e
   ``tela-grande`` para TV/box/projetor/stick (com os sinais que o Kodi expoe);
2. celular continua disparando a activity AdMob que existe no APK;
3. tela grande NAO dispara a activity AdMob (era o que deixava o player preto
   no projetor) e devolve False enquanto o SDK IMA nao estiver compilado;
4. a tela de pastas (MyVideoNav) nao tem mais branco estourado e esta na lista
   de arquivos que o build leva para o APK.
"""
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
SKIN_NOVATV = ROOT / 'kodi' / 'skin.novatv' / 'xml'
SKIN_CLASSICA = ROOT / 'kodi' / 'skin.estilo.personalizado' / 'xml'


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class PlayerFalso(object):
    def __init__(self, *a, **k):
        pass

    def isPlaying(self):
        return False

    def isPlayingVideo(self):
        return False


class AdsFalso(object):
    """Kodi minimo com um 'aparelho' configuravel."""

    def __init__(self, condicoes=(), nomes=None, tela=1080):
        self.condicoes = set(condicoes)
        self.nomes = nomes or {}
        self.tela = tela
        self.builtins = []
        self.logs = []

    def getCondVisibility(self, consulta):
        return consulta in self.condicoes

    def getInfoLabel(self, rotulo):
        if rotulo == 'System.ScreenHeight':
            return str(self.tela)
        return self.nomes.get(rotulo, '')

    def executebuiltin(self, comando):
        self.builtins.append(comando)

    def log(self, mensagem, nivel=1):
        self.logs.append(mensagem)


class BaseAds(unittest.TestCase):
    def setUp(self):
        # 'variante' e 'smart_ads' tambem: o modulo os importa e, se ficarem no
        # sys.modules, o proximo teste herdaria o "aparelho" falso daqui.
        self.guardados = {n: sys.modules.get(n)
                          for n in ('xbmc', 'xbmcvfs', 'xbmcgui', 'variante',
                                    'smart_ads')}
        sys.path.insert(0, str(BOOTSTRAP))
        self.modulo = None

    def tearDown(self):
        sys.path.remove(str(BOOTSTRAP))
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def _como_tv(self, tv=True):
        """Faz a variante responder tv/mobile sem depender do aparelho.

        Em producao quem decide e o marcador gravado no APK (ou o sinal do
        Kodi). Aqui a variante e substituida para o teste ser deterministico.
        """
        if self.modulo is None:
            return
        self.modulo._variante = types.SimpleNamespace(
            e_tv=lambda: tv, e_mobile=lambda: not tv)

    def _carregar(self, kodi):
        xbmc = types.ModuleType('xbmc')
        xbmc.getCondVisibility = kodi.getCondVisibility
        xbmc.getInfoLabel = kodi.getInfoLabel
        xbmc.executebuiltin = kodi.executebuiltin
        xbmc.log = kodi.log
        xbmc.Player = PlayerFalso
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p
        vfs.exists = os.path.exists
        vfs.File = lambda *a, **k: types.SimpleNamespace(
            read=lambda *x: '', write=lambda *x: None, close=lambda: None)
        sys.modules['xbmcvfs'] = vfs
        self.modulo = carregar('smart_ads_perfil', BOOTSTRAP / 'smart_ads.py')
        return self.modulo


class DeteccaoTest(BaseAds):
    def test_android_tv_e_tela_grande(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.TV',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        self.assertEqual(modulo.perfil_dispositivo()[0], modulo.PERFIL_TELA_GRANDE)

    def test_celular_continua_adhoc_para_mobile(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.Mobile',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        self.assertEqual(modulo.perfil_dispositivo()[0], modulo.PERFIL_CELULAR)

    def test_nome_do_aparelho_decide_quando_o_kodi_nao_responde(self):
        for nome in ('XGIMI Projector', 'Fire TV Stick', 'TV Box Droidlogic',
                     'Wanbo Projector'):
            kodi = AdsFalso(condicoes={'System.Platform.Android'},
                            nomes={'System.FriendlyName': nome})
            modulo = self._carregar(kodi)
            self.assertEqual(modulo.perfil_dispositivo()[0],
                             modulo.PERFIL_TELA_GRANDE, nome)
        for nome in ('Samsung Galaxy S23', 'Xiaomi Redmi Note', 'Moto G'):
            kodi = AdsFalso(condicoes={'System.Platform.Android'},
                            nomes={'System.FriendlyName': nome})
            modulo = self._carregar(kodi)
            self.assertEqual(modulo.perfil_dispositivo()[0],
                             modulo.PERFIL_CELULAR, nome)

    def test_tela_hd_sem_sinal_vira_tela_grande(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android'}, tela=720)
        modulo = self._carregar(kodi)
        self.assertEqual(modulo.perfil_dispositivo()[0], modulo.PERFIL_TELA_GRANDE)

    def test_perfil_fica_visivel_na_janela(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.TV',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        modulo.publicar_perfil()
        self.assertTrue(any('smartedtv.perfil' in b for b in kodi.builtins),
                        kodi.builtins)


class RoteamentoTest(BaseAds):
    """Celular anuncia por AdMob; TV NAO usa AdMob.

    Rodada anterior pedia AdMob em todos os aparelhos. O usuario observou no
    projetor que o anuncio nao aparece: o Google Mobile Ads (AdMob) nao tem
    formato suportado em Android TV, e a activity abria pausando o video para
    voltar sem nada. Contrato agora:

    * celular: AdMob como sempre;
    * TV: so anuncio de video (VAST/IMA); sem o SDK compilado no APK nada e
      pedido, fica registrado no log o que falta e o video segue.
    """

    def test_celular_dispara_a_activity_admob_do_apk(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.Mobile',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        self._como_tv(False)
        self.assertTrue(modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL))
        envios = [b for b in kodi.builtins if b.startswith('StartAndroidActivity')]
        self.assertEqual(len(envios), 1, kodi.builtins)
        self.assertIn(modulo.ATIVIDADE_PREROLL, envios[0])

    def test_tv_nao_dispara_activity_admob(self):
        """AdMob nao tem formato para Android TV: nada e pedido."""
        kodi = AdsFalso(condicoes={'System.Platform.Android.TV',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        self._como_tv(True)
        self.assertFalse(modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL))
        self.assertFalse(modulo.tocar_anuncio(modulo.ATIVIDADE_ABERTURA))
        envios = [b for b in kodi.builtins if b.startswith('StartAndroidActivity')]
        self.assertEqual(envios, [], kodi.builtins)

    def test_tv_registra_o_que_falta_em_vez_de_simular(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.TV',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        self._como_tv(True)
        logs = []
        modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL, log=logs.append)
        texto = ' '.join(logs)
        self.assertIn('IMA', texto)
        self.assertIn('VAST', texto)

    def test_abertura_na_tv_nao_abre_admob(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.TV',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        self._como_tv(True)
        self.assertFalse(modulo.mostrar_abertura())
        self.assertEqual([b for b in kodi.builtins
                          if b.startswith('StartAndroidActivity')], [])

    def test_vast_nunca_e_simulado(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.TV',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        self.assertEqual((modulo.VAST_TAG_PADRAO or '').strip(), '',
                         'sem tag VAST nao se inventa uma')
        self.assertFalse(modulo.vast_disponivel())
        self.assertFalse(modulo.abrir_anuncio_vast(modulo.ATIVIDADE_PREROLL))
        self.assertEqual([b for b in kodi.builtins
                          if b.startswith('StartAndroidActivity')], [])

    def test_vip_continua_sem_anuncio_em_qualquer_perfil(self):
        kodi = AdsFalso(condicoes={'System.Platform.Android.Mobile',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        modulo.vip_ativo = lambda: True
        self.assertFalse(modulo.mostrar_preroll(chave='x', sessao=1))

    def test_video_com_video_tocando_nao_interrompe(self):
        """O caminho VAST nunca pausa o que ja esta tocando."""
        kodi = AdsFalso(condicoes={'System.Platform.Android.TV',
                                   'System.Platform.Android'})
        modulo = self._carregar(kodi)
        modulo.abrir_anuncio_vast(modulo.ATIVIDADE_PREROLL)
        self.assertEqual([b for b in kodi.builtins if 'Player' in b], [])


class TelaDePastasTest(unittest.TestCase):
    """Bloco branco estourado -> cinza do tema, e o build leva o arquivo."""

    ARQUIVOS = (SKIN_NOVATV / 'MyVideoNav.xml', SKIN_CLASSICA / 'MyVideoNav.xml')

    def test_lista_nao_usa_branco_estourado(self):
        for caminho in self.ARQUIVOS:
            texto = caminho.read_text()
            self.assertNotIn('colordiffuse="B3FFFFFF"', texto,
                             '%s: card da lista continua branco' % caminho.name)
            self.assertNotIn('<texture colordiffuse="FFFFFFFF" border="16">\n'
                             'pb_rounded.png', texto.replace('\t', ''))

    def test_lista_usa_o_cinza_do_tema(self):
        for caminho in self.ARQUIVOS:
            texto = caminho.read_text()
            self.assertIn('F2262626', texto,
                          '%s: card da lista sem o cinza do tema' % caminho.name)
            self.assertIn('FF3A3A3A', texto,
                          '%s: foco da lista sem o cinza do tema' % caminho.name)

    def test_as_duas_skins_continuam_iguais(self):
        self.assertEqual(self.ARQUIVOS[0].read_text(),
                         self.ARQUIVOS[1].read_text(),
                         'a skin espelho saiu do lugar')

    def test_build_injeta_myvideonav_no_apk(self):
        ferramenta = (ROOT / 'tools/kodi/atualizar-apk-v17.py').read_text()
        self.assertIn("'MyVideoNav.xml'", ferramenta,
                      'o APK nao receberia a tela de pastas corrigida')
        self.assertIn("'Home.xml'", ferramenta)


if __name__ == '__main__':
    unittest.main()
