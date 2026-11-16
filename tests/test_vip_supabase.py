# -*- coding: utf-8 -*-
"""Validação de código: site, Edge Function do Supabase e tabela do painel.

O teste roda o ``vip.py`` de verdade com um Kodi de mentira: só a rede é
trocada por respostas prontas. O que fica travado:

  * a ordem das tentativas (site → Supabase → tabela);
  * a leitura das respostas (``{…}`` e a linha ``[{…}]`` do PostgREST);
  * os prazos: código de TESTE (10 minutos) e MENSAL (30 dias);
  * o ``vip.json`` que o Java lê para desligar os anúncios.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'vip.py'


def carregar_vip(respostas, tabela=None, supabase=('https://projeto.supabase.co', 'eyJhbGciOiJIUzI1NiJ9.anon.assinatura')):
    """Importa vip.py com Kodi falso; ``respostas`` mapeia URL → objeto JSON."""
    temporario = tempfile.mkdtemp(prefix='smarted-vip-')
    chamadas = []

    fake_xbmc = types.ModuleType('xbmc')
    for nivel in ('LOGDEBUG', 'LOGINFO', 'LOGWARNING', 'LOGERROR'):
        setattr(fake_xbmc, nivel, 10)
    fake_xbmc.log = lambda *a, **k: None
    fake_xbmc.getInfoLabel = lambda label: 'teste'
    fake_xbmc.executebuiltin = lambda b: chamadas.append(b)

    fake_vfs = types.ModuleType('xbmcvfs')
    fake_vfs.translatePath = lambda caminho: (
        temporario if 'profile' in caminho else temporario)
    fake_vfs.exists = os.path.exists
    fake_vfs.mkdirs = lambda caminho: os.makedirs(caminho, exist_ok=True)

    fake_addon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def getAddonInfo(self, chave):
            return 'service.smarted.bootstrap' if chave == 'id' else '1.0.83'

    fake_addon.Addon = Addon

    antigos = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs', 'xbmcaddon')}
    sys.modules.update({'xbmc': fake_xbmc, 'xbmcvfs': fake_vfs, 'xbmcaddon': fake_addon})
    try:
        spec = importlib.util.spec_from_file_location('vip_teste', VIP)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    finally:
        for nome, valor in antigos.items():
            if valor is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = valor

    modulo._pasta_teste = temporario

    def fake_post(url, corpo, chave=''):
        chamadas.append(('POST', url, chave, corpo))
        if url in respostas:
            return respostas[url]
        raise OSError('404 nao e API')

    def fake_get(url, chave=''):
        chamadas.append(('GET', url, chave, None))
        if tabela is not None:
            return tabela
        raise OSError('sem tabela')

    modulo._post = fake_post
    modulo._get = fake_get
    os.makedirs(os.path.join(temporario, 'addon_data', 'service.smarted.bootstrap'),
                exist_ok=True)
    if supabase:
        with open(os.path.join(temporario, 'addon_data', 'service.smarted.bootstrap',
                               'supabase.txt'), 'w', encoding='utf-8') as saida:
            saida.write('%s\n%s\n' % supabase)
    return modulo, chamadas


class ValidacaoTest(unittest.TestCase):
    def setUp(self):
        self.limpar = []

    def tearDown(self):
        for pasta in self.limpar:
            shutil.rmtree(pasta, ignore_errors=True)

    def carregar(self, *args, **kwargs):
        modulo, chamadas = carregar_vip(*args, **kwargs)
        self.limpar.append(modulo._pasta_teste)
        self.addCleanup(shutil.rmtree, modulo._pasta_teste, True)
        return modulo, chamadas

    def test_codigo_de_teste_10_minutos_no_site(self):
        modulo, _ = self.carregar({
            'https://smartedtv-vip.lovable.app/api/validar':
                {'valido': True, 'tipo': 'teste'},
        }, supabase=None)
        ok, mensagem = modulo.validar('TESTE-1234')
        self.assertTrue(ok, mensagem)
        dados = modulo.estado()
        self.assertTrue(dados['ativo'])
        self.assertIn('T', dados['expira'])          # data com hora
        self.assertTrue(modulo.ativa())
        limite = time.mktime(time.strptime(dados['expira'], '%Y-%m-%dT%H:%M:%SZ'))
        # ~10 minutos (o teste roda em UTC; margem de 2 min)
        self.assertLess(abs(limite - time.time()), 12 * 60)

    def test_codigo_mensal_30_dias_pela_edge_function(self):
        modulo, chamadas = self.carregar({
            'https://projeto.supabase.co/functions/v1/validar-codigo':
                {'ativo': True, 'dias': 30, 'mensagem': 'VIP liberado'},
        })
        ok, mensagem = modulo.validar('MENSAL-2026')
        self.assertTrue(ok, mensagem)
        dados = modulo.estado()
        dias = (time.mktime(time.strptime(dados['expira'], '%Y-%m-%dT%H:%M:%SZ'))
                - time.time()) / 86400.0
        self.assertGreater(dias, 29.5)
        self.assertLess(dias, 30.5)
        # a chave do Supabase foi junto nos cabeçalhos
        supabase = [c for c in chamadas if isinstance(c, tuple) and 'supabase.co' in c[1]]
        self.assertTrue(supabase)
        self.assertTrue(supabase[0][2])

    def test_codigo_na_tabela_do_painel(self):
        modulo, chamadas = self.carregar(
            {}, tabela=[{'codigo': 'PAINEL-777', 'usado': False, 'dias': 30}])
        ok, mensagem = modulo.validar('PAINEL-777')
        self.assertTrue(ok, mensagem)
        rotas = [c[1] for c in chamadas if isinstance(c, tuple)]
        self.assertTrue(any('rest/v1/codigos?codigo=eq.PAINEL-777' in r for r in rotas), rotas)

    def test_codigo_invalido_mostra_a_mensagem_do_servidor(self):
        modulo, _ = self.carregar({
            'https://smartedtv-vip.lovable.app/api/validar':
                {'valido': False, 'mensagem': 'Código não encontrado'},
        }, supabase=None)
        ok, mensagem = modulo.validar('XXX-0000')
        self.assertFalse(ok)
        self.assertIn('não encontrado', mensagem)
        self.assertFalse(modulo.ativa())

    def test_sem_servidor_nao_grava_nada(self):
        modulo, _ = self.carregar({}, supabase=None)
        ok, mensagem = modulo.validar('ABC-1234')
        self.assertFalse(ok)
        self.assertIn('servidor', mensagem)
        self.assertEqual(modulo.estado(), {})

    def test_prazo_expirado_desliga_o_vip(self):
        modulo, _ = self.carregar({}, supabase=None)
        self.assertFalse(modulo.dentro_do_prazo('2020-01-01T10:00:00Z'))
        self.assertTrue(modulo.dentro_do_prazo(modulo.em_instantes(600)))
        self.assertTrue(modulo.dentro_do_prazo('2999-12-31'))
        self.assertTrue(modulo.dentro_do_prazo(''))


class ArquivosDaPonteTest(unittest.TestCase):
    """O lado Java precisa ler o que o Python grava (e vice-versa)."""

    def test_formato_do_vip_json(self):
        texto = VIP.read_text(encoding='utf-8')
        self.assertIn("dados = {'ativo': True, 'codigo': codigo, 'expira': expira,", texto)
        licenca = (ROOT / 'smartedtv/tools/ads-java/Licenca.java.in').read_text(encoding='utf-8')
        self.assertIn('dentroDoPrazo', licenca)
        self.assertIn('yyyy-MM-dd', licenca)

    def test_ordem_das_tentativas(self):
        texto = VIP.read_text(encoding='utf-8')
        pos_site = texto.index('for rota in rotas():')
        pos_supabase = texto.index('for rota in funcoes:')
        pos_tabela = texto.index('rest/v1/codigos')
        self.assertLess(pos_site, pos_supabase)
        self.assertLess(pos_supabase, pos_tabela)


if __name__ == '__main__':
    unittest.main()


class RotaLembradaTest(unittest.TestCase):
    """A rota que funcionou é memorizada e compartilhada com o app Java."""

    def setUp(self):
        self.vip = Path('kodi/addons/service.smarted.bootstrap/vip.py').read_text(encoding='utf-8')
        self.jav = Path('smartedtv/tools/ads-java/Licenca.java.in').read_text(encoding='utf-8')
        self.sup = Path('smartedtv/tools/ads-java/Supabase.java.in').read_text(encoding='utf-8')

    def test_mesmo_nome_de_arquivo_dos_dois_lados(self):
        self.assertIn("ROTA_BOA = 'vip-endpoint-ok.txt'", self.vip)
        self.assertIn('ROTA_BOA = "vip-endpoint-ok.txt"', self.jav)
        self.assertIn('supabase-cache.txt', self.vip)
        self.assertIn('CACHE_KODI = "supabase-cache.txt"', self.sup)

    def test_python_lembra_a_rota_que_deu_certo(self):
        self.assertIn('def lembrar_rota(rota):', self.vip)
        self.assertIn('def _rota_lembrada():', self.vip)
        trecho = self.vip[self.vip.index('def rotas():'):]
        trecho = trecho[:trecho.index('def validar(')]
        self.assertIn('lembrada = _rota_lembrada()', trecho)
        self.assertIn('lista.append(lembrada)', trecho)
        self.assertIn('lembrar_rota(origem)', self.vip)

    def test_java_lembra_e_reaproveita(self):
        self.assertIn('private static void lembrarRota(Context contexto, String rota)', self.jav)
        self.assertIn('lembrarRota(contexto, usada);', self.jav)
        self.assertIn('rota que já funcionou', self.jav)

    def test_supabase_compartilhado_com_o_addon(self):
        self.assertIn('public static File pastaAddon(Context contexto)', self.sup)
        self.assertIn('addon_data', self.sup)
        self.assertIn('service.smarted.bootstrap', self.sup)

    def test_licenca_usa_a_mesma_pasta_do_addon(self):
        self.assertIn('public static File pastaAddon(Context contexto)', self.jav)
        self.assertIn('addon_data', self.jav)
