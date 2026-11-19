# -*- coding: utf-8 -*-
"""VIP: o prazo contratado e respeitado ao segundo, e os anuncios voltam.

Dois defeitos reais encontrados aqui (com o modulo rodando, nao por leitura):

1. ``_gravar_licenca`` gravava ``expira_em`` (ISO com hora) tambem dentro de
   ``expira``. Quem lia ``expira`` esperava DATA e recebia data+hora.
2. ``ativa()`` decidia apenas por ``expira`` (o DIA). Com isso uma licenca que
   venceu as 18:38 continuava liberada ate as 23:59 do mesmo dia - o cliente
   ganhava horas de graca e o anuncio nao voltava na hora certa.

A correcao usa o instante exato (``expira_em``) quando ele existe e mantem a
data pura em ``expira``. Estes testes travam o comportamento.
"""
import importlib.util
import json
import os
import sys
import tempfile
import time
import types
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, 'kodi', 'addons', 'service.smarted.bootstrap')
sys.path.insert(0, ADDON)


def _iso(segundos_da_agora):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ',
                         time.gmtime(time.time() + segundos_da_agora))


class Base(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.perfil = os.path.join(self.home, 'userdata')
        self.pasta = os.path.join(self.perfil, 'addon_data',
                                  'service.smarted.bootstrap')
        os.makedirs(self.pasta, exist_ok=True)
        self.guardados = {n: sys.modules.get(n)
                          for n in ('xbmc', 'xbmcaddon', 'xbmcvfs', 'xbmcgui')}
        self.logs = []
        self._instalar()
        self.vip = self._carregar()

    def tearDown(self):
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def _instalar(self):
        logs = self.logs
        xbmc = types.ModuleType('xbmc')
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        xbmc.log = lambda msg, nivel=1: logs.append(msg)
        xbmc.executebuiltin = lambda *a, **k: None
        xbmc.getInfoLabel = lambda _s: ''
        xbmc.getCondVisibility = lambda _s: False
        sys.modules['xbmc'] = xbmc
        addon = types.ModuleType('xbmcaddon')
        addon.Addon = lambda *a, **k: types.SimpleNamespace(
            getAddonInfo=lambda c: {'id': 'service.smarted.bootstrap',
                                    'path': ADDON}.get(c, ''),
            getSetting=lambda _c: '')
        sys.modules['xbmcaddon'] = addon
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p.replace('special://home', self.home) \
            .replace('special://profile', self.perfil)
        vfs.exists = os.path.exists
        sys.modules['xbmcvfs'] = vfs
        gui = types.ModuleType('xbmcgui')
        gui.Dialog = lambda *a, **k: types.SimpleNamespace(
            ok=lambda *a, **k: None, notification=lambda *a, **k: None,
            yesno=lambda *a, **k: False, select=lambda *a, **k: 0,
            input=lambda *a, **k: '')
        gui.NOTIFICATION_INFO = gui.NOTIFICATION_WARNING = \
            gui.NOTIFICATION_ERROR = 0
        sys.modules['xbmcgui'] = gui

    def _carregar(self):
        spec = importlib.util.spec_from_file_location(
            'vip_prazo_%d' % time.time_ns(), os.path.join(ADDON, 'vip.py'))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo

    def _servidor(self, corpo, status=200):
        def post(url, dados, timeout, cookie=''):
            return status, {}, json.dumps(corpo), 'http'
        self.vip._post_json = post


class PrazoDoContratoTest(Base):
    def test_ativa_grava_data_pura_e_instante_exato(self):
        self._servidor({'active': True, 'expiresAt': _iso(30 * 86400)})
        ok, _msg = self.vip.validar('ABCD-1234-EFGH-5678')
        self.assertTrue(ok)
        dados = self.vip.estado()
        self.assertEqual(len(dados['expira']), 10, dados)
        self.assertIn('T', dados['expira_em'])
        self.assertTrue(self.vip.ativa())

    def test_licenca_vencida_ha_uma_hora_ja_nao_esta_ativa(self):
        """Era o defeito: vencida as 18:38, seguia ativa ate 23:59."""
        self.vip._gravar_licenca('ABCD-1234-EFGH-5678', _iso(-3600), 'teste')
        self.assertFalse(self.vip.ativa())

    def test_licenca_que_vence_em_dois_minutos_ainda_esta_ativa(self):
        self.vip._gravar_licenca('ABCD-1234-EFGH-5678', _iso(120), 'teste')
        self.assertTrue(self.vip.ativa())

    def test_prazo_contratado_nao_e_arredondado_para_o_dia(self):
        """Plano de 1 hora termina em 1 hora, nao no fim do dia."""
        self._servidor({'active': True, 'expiresAt': _iso(3600)})
        self.assertTrue(self.vip.validar('PLANO-HORA')[0])
        dados = self.vip.estado()
        self.assertEqual(dados['expira'], time.strftime('%Y-%m-%d'),
                         'data do dia do vencimento')
        hora = dados['expira_em']
        self.assertEqual(self.vip.dentro_do_prazo(hora), True)
        # e o instante gravado e o que o servidor mandou (nao "fim do dia")
        self.assertTrue(hora.endswith('Z'))

    def test_licenca_antiga_sem_instante_usa_a_data(self):
        """vip.json de versao anterior (so ``expira``) continua funcionando."""
        caminho = self.vip.VIP_JSON
        hoje = time.strftime('%Y-%m-%d')
        with open(caminho, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps({'ativo': True, 'expira': hoje,
                                     'codigo_hash': 'x'}))
        self.assertTrue(self.vip.ativa())
        with open(caminho, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps({'ativo': True,
                                     'expira': time.strftime(
                                         '%Y-%m-%d', time.gmtime(time.time() - 86400)),
                                     'codigo_hash': 'x'}))
        self.assertFalse(self.vip.ativa())

    def test_codigo_recusado_nao_grava_licenca(self):
        self._servidor({'active': False, 'message': 'Código não encontrado'}, 404)
        ok, msg = self.vip.validar('XXXX-0000')
        self.assertFalse(ok)
        self.assertEqual(self.vip.estado(), {})
        self.assertIn('não é válido', msg)


class VipDesligaAnunciosTest(Base):
    """VIP ativo = nenhum anuncio; vencido = regra normal volta."""

    def _smart(self):
        # smart_ads herda de xbmc.Player: aqui ele precisa ser CLASSE.
        class _Player(object):
            def __init__(self, *a, **k):
                pass

            def isPlayingVideo(self):
                return False

            def isPlaying(self):
                return False

        sys.modules['xbmc'].Player = _Player
        # o modulo de licenca DESTE teste (nao outro ja importado)
        sys.modules['vip'] = self.vip
        spec = importlib.util.spec_from_file_location(
            'smart_ads_vip_%d' % time.time_ns(),
            os.path.join(ADDON, 'smart_ads.py'))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo

    def test_vip_ativo_bloqueia_o_anuncio(self):
        self.vip._gravar_licenca('ABCD-1234-EFGH-5678', _iso(30 * 86400), 'teste')
        smart = self._smart()
        self.assertTrue(smart.vip_ativo())
        self.assertFalse(smart.mostrar_preroll(log=self.logs.append,
                                               chave='canal-1', sessao=1))

    def test_vip_vencido_volta_a_pedir_anuncio(self):
        self.vip._gravar_licenca('ABCD-1234-EFGH-5678', _iso(-60), 'teste')
        smart = self._smart()
        self.assertFalse(smart.vip_ativo(), 'licenca vencida nao isenta anuncio')
        pedidos = []
        smart.tocar_anuncio_com_aviso = lambda *a, **k: pedidos.append(a) or True
        smart.mostrar_preroll(log=self.logs.append, chave='canal-2', sessao=2)
        self.assertTrue(pedidos, 'com a licenca vencida o anuncio e pedido')


if __name__ == '__main__':
    unittest.main()
