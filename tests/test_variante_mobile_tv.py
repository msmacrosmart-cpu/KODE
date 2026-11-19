# -*- coding: utf-8 -*-
"""Separacao MOBILE x TV: uma unica decisao, duas consequencias.

O pedido do usuario nesta rodada:

* duas versoes no mesmo repositorio (celular e TV), com o maximo de codigo
  compartilhado - nada de duplicar o projeto;
* a versao MOBILE que ja funciona nao pode mudar de comportamento;
* a TV consulta SO a pasta ``SMARTEDTV-ON`` do Dropbox e o celular SO a
  ``SMARTEDTV-MOBILE``; nenhuma versao baixa o APK da outra;
* o botao de baixar/atualizar dentro do app respeita a mesma separacao.

Estes testes travam o contrato em ``variante.py`` (a unica fonte da verdade) e
em ``vip.py`` (quem usa essa decisao para achar o APK).
"""
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class KodiFalso(object):
    """Kodi minimo: condicoes, info labels e um "disco" para o marcador."""

    def __init__(self, condicoes=(), nomes=None, tela=1080):
        self.condicoes = set(condicoes)
        self.nomes = nomes or {}
        self.tela = tela
        self.logs = []
        self.builtins = []

    def getCondVisibility(self, consulta):
        return consulta in self.condicoes

    def getInfoLabel(self, rotulo):
        if rotulo == 'System.ScreenHeight':
            return str(self.tela)
        return self.nomes.get(rotulo, '')

    def log(self, mensagem, nivel=1):
        self.logs.append(mensagem)

    def executebuiltin(self, comando):
        self.builtins.append(comando)


class BaseVariante(unittest.TestCase):
    def setUp(self):
        self.guardados = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs')}
        self.arquivos = {}

    def tearDown(self):
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def carregar(self, kodi, marcador=None, traduzir=None):
        xbmc = types.ModuleType('xbmc')
        xbmc.getCondVisibility = kodi.getCondVisibility
        xbmc.getInfoLabel = kodi.getInfoLabel
        xbmc.log = kodi.log
        xbmc.executebuiltin = kodi.executebuiltin
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = traduzir or (lambda p: p)
        sys.modules['xbmcvfs'] = vfs
        modulo = carregar('variante_teste', BOOTSTRAP / 'variante.py')
        # O marcador e resolvido por variante_do_arquivo(); fixamos a leitura
        # para o teste nao depender do sistema de arquivos do runner.
        modulo.variante_do_arquivo = lambda: marcador
        return modulo


class MarcadorTest(BaseVariante):
    def test_marcador_do_apk_manda_mais_que_o_aparelho(self):
        kodi = KodiFalso(condicoes={'System.Platform.Android.Mobile'})
        modulo = self.carregar(kodi, marcador='tv')
        self.assertEqual(modulo.variante(), 'tv')
        self.assertTrue(modulo.e_tv())
        self.assertFalse(modulo.e_mobile())

    def test_marcador_mobile_vence_sinal_de_tv(self):
        kodi = KodiFalso(condicoes={'System.Platform.Android.TV'})
        modulo = self.carregar(kodi, marcador='mobile')
        self.assertEqual(modulo.variante(), 'mobile')

    def test_sem_marcador_android_tv_e_tv(self):
        kodi = KodiFalso(condicoes={'System.Platform.Android.TV',
                                    'System.Platform.Android'})
        modulo = self.carregar(kodi)
        self.assertEqual(modulo.variante(), 'tv')

    def test_sem_marcador_celular_continua_mobile(self):
        kodi = KodiFalso(condicoes={'System.Platform.Android.Mobile',
                                    'System.Platform.Android'})
        modulo = self.carregar(kodi)
        self.assertEqual(modulo.variante(), 'mobile')

    def test_duvida_cai_para_mobile(self):
        """A versao aprovada e a do celular: erro de deteccao nunca a troca."""
        kodi = KodiFalso()
        modulo = self.carregar(kodi)
        self.assertEqual(modulo.variante(), 'mobile')


class PastasTest(BaseVariante):
    def test_cada_versao_tem_a_sua_pasta(self):
        modulo = self.carregar(KodiFalso(), marcador='tv')
        self.assertEqual(modulo.pasta_dropbox(), 'SMARTEDTV-ON')
        self.assertEqual(modulo.pacote(), 'smartedtv.tv')
        modulo = self.carregar(KodiFalso(), marcador='mobile')
        self.assertEqual(modulo.pasta_dropbox(), 'SMARTEDTV-MOBILE')
        self.assertEqual(modulo.pacote(), 'smartedtv.full')

    def test_mobile_preserva_o_identificador_historico(self):
        modulo = self.carregar(KodiFalso(), marcador='mobile')
        self.assertEqual(modulo.PACOTE_MOBILE, 'smartedtv.full')


class VipTest(unittest.TestCase):
    """vip.py: link, pasta e recusa do APK da outra versao."""

    def setUp(self):
        self.guardados = {n: sys.modules.get(n)
                          for n in ('xbmc', 'xbmcvfs', 'xbmcaddon', 'xbmcgui',
                                    'variante')}

    def tearDown(self):
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def _vip(self, tv):
        xbmc = types.ModuleType('xbmc')
        xbmc.getCondVisibility = lambda c: False
        xbmc.getInfoLabel = lambda r: ''
        xbmc.log = lambda *a, **k: None
        xbmc.executebuiltin = lambda *a, **k: None
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p
        vfs.exists = os.path.exists
        sys.modules['xbmcvfs'] = vfs
        addon = types.ModuleType('xbmcaddon')

        class Addon(object):
            def __init__(self, *a, **k):
                pass

            def getAddonInfo(self, chave):
                return 'service.smarted.bootstrap'

            def getSetting(self, *a, **k):
                return ''

            def setSetting(self, *a, **k):
                pass

        addon.Addon = Addon
        sys.modules['xbmcaddon'] = addon
        gui = types.ModuleType('xbmcgui')
        gui.Dialog = lambda *a, **k: types.SimpleNamespace(
            ok=lambda *x, **y: None, notification=lambda *x, **y: None)
        sys.modules['xbmcgui'] = gui
        sys.modules['variante'] = types.SimpleNamespace(
            e_tv=lambda: tv, e_mobile=lambda: not tv,
            pacote=lambda: 'smartedtv.tv' if tv else 'smartedtv.full',
            pasta_dropbox=lambda: 'SMARTEDTV-ON' if tv else 'SMARTEDTV-MOBILE',
            resumo=lambda: 'teste')
        # vip.py importa smarted_release do proprio addon: colocar a pasta no
        # path SO durante o exec_module (o projeto nunca mexe em sys.path).
        salvos = dict(sys.modules)
        sys.path.insert(0, str(BOOTSTRAP))
        try:
            spec = importlib.util.spec_from_file_location('vip_teste',
                                                         BOOTSTRAP / 'vip.py')
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
        finally:
            sys.path.remove(str(BOOTSTRAP))
            for nome in set(sys.modules) - set(salvos):
                if nome in ('vip_teste', 'smarted_release'):
                    sys.modules.pop(nome, None)
        return modulo

    def test_mobile_usa_a_pasta_historica(self):
        vip = self._vip(False)
        self.assertFalse(vip.eh_tv())
        self.assertEqual(vip.pasta_nome(), 'SMARTEDTV-MOBILE')
        self.assertTrue(vip.dropbox_configurado())

    def test_tv_sem_pasta_nao_baixa_nada(self):
        vip = self._vip(True)
        self.assertTrue(vip.eh_tv())
        self.assertEqual(vip.pasta_nome(), 'SMARTEDTV-ON')
        self.assertFalse(vip.dropbox_configurado(),
                         'pasta da TV nao foi publicada: nao pode haver link')
        caminho, motivo = vip.resolver_apk_publicado()
        self.assertIsNone(caminho)
        self.assertEqual(motivo, 'pasta-nao-configurada')

    def test_tv_nao_cai_no_link_fixo_nem_no_github(self):
        vip = self._vip(True)
        self.assertEqual(vip.pastas_dropbox(), [])

    def test_mobile_continua_com_os_links_que_funcionam(self):
        vip = self._vip(False)
        self.assertTrue(vip.pastas_dropbox())
        self.assertIn('SMARTEDTV.apk', vip.APK_NOME)

    def test_recusa_apk_da_outra_versao(self):
        vip = self._vip(True)
        # pacote_do_apk le o marcador de dentro do zip; sem APK real, o
        # contrato e: None nunca aprova como "serve".
        self.assertFalse(vip.apk_serve_para_esta_versao('/nao/existe.apk'))


if __name__ == '__main__':
    unittest.main()
