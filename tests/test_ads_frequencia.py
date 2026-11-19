# -*- coding: utf-8 -*-
"""Regra de frequencia dos anuncios (pedido do usuario).

O que estes testes garantem, item por item do pedido:

1. anuncio SO na troca de conteudo (canal, filme, episodio);
2. depois de um anuncio CONCLUIDO ou PULADO, 2 minutos sem anuncio;
3. dentro dos 2 minutos, outros conteudos abrem normalmente (sem anuncio);
4. passados os 2 minutos, o proximo conteudo pode receber anuncio;
5. anuncio que falha/nao existe/nao abre NUNCA bloqueia nem consome o
   intervalo (a proxima troca tenta de novo);
6. conteudo que ja comecou nao e interrompido (a resposta negativa e imediata);
7. VIP continua sem anuncio em qualquer perfil;
8. a regra e centralizada: todos os gatilhos passam pelo MESMO estado, entao
   nao existe anuncio duplicado por eventos diferentes;
9. o estado sobrevive a reinicio do servico (o Android mata o processo em TV
   box/stick com pouca RAM) - se ficasse so em memoria, o intervalo de 2
   minutos seria esquecido e o anuncio voltaria na primeira troca.
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'

INTERVALO = 120


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class KodiFalso(object):
    def __init__(self):
        self.perfil = tempfile.mkdtemp()
        self.condicoes = set()
        self.builtins = []
        self.logs = []

    def getCondVisibility(self, consulta):
        return consulta in self.condicoes

    def getInfoLabel(self, rotulo):
        return ''

    def executebuiltin(self, comando):
        self.builtins.append(comando)

    def log(self, mensagem, nivel=1):
        self.logs.append(mensagem)


class BaseRegra(unittest.TestCase):
    def setUp(self):
        self.guardados = {n: sys.modules.get(n)
                          for n in ('xbmc', 'xbmcvfs', 'xbmcgui')}
        self.kodi = KodiFalso()
        sys.path.insert(0, str(BOOTSTRAP))
        xbmc = types.ModuleType('xbmc')
        xbmc.getCondVisibility = self.kodi.getCondVisibility
        xbmc.getInfoLabel = self.kodi.getInfoLabel
        xbmc.executebuiltin = self.kodi.executebuiltin
        xbmc.log = self.kodi.log
        xbmc.Player = object
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: (self.kodi.perfil if p.startswith(
            'special://profile') else p)
        vfs.exists = os.path.exists
        sys.modules['xbmcvfs'] = vfs
        sys.modules.pop('ads_regra', None)
        self.regra = carregar('ads_regra_teste', BOOTSTRAP / 'ads_regra.py')

    def tearDown(self):
        sys.path.remove(str(BOOTSTRAP))
        sys.modules.pop('ads_regra', None)
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo


class FrequenciaTest(BaseRegra):
    def test_sem_anuncio_anterior_libera(self):
        pode, motivo = self.regra.pode_anunciar('canal:A', agora=1000.0)
        self.assertTrue(pode, motivo)

    def test_dois_minutos_depois_de_concluido(self):
        """O intervalo conta do FIM do anuncio (concluido ou pulado)."""
        t0 = 1000.0
        self.assertTrue(self.regra.pode_anunciar('canal:A', agora=t0)[0])
        self.regra.registrar_anuncio('canal:A', t0)
        # anuncio exibido por 20 s (concluido ou pulado)
        self.assertTrue(self.regra.concluir_anuncio(t0 + 20))
        # 10 s depois do fim: ainda bloqueado
        self.assertFalse(self.regra.pode_anunciar('canal:B', agora=t0 + 30)[0])
        # 119 s depois do fim: ainda bloqueado
        self.assertFalse(self.regra.pode_anunciar('canal:B', agora=t0 + 139)[0])
        # 121 s depois do fim: libera
        self.assertTrue(self.regra.pode_anunciar('canal:B', agora=t0 + 141)[0])

    def test_trocas_dentro_da_janela_nao_levam_anuncio(self):
        """Canal -> filme -> episodio dentro de 2 min: nenhum anuncio."""
        t0 = 1000.0
        self.regra.registrar_anuncio('canal:A', t0)
        self.regra.concluir_anuncio(t0 + 15)
        for i, chave in enumerate(('filme:B', 'serie:C:S01E02', 'canal:D')):
            pode, motivo = self.regra.pode_anunciar(chave, agora=t0 + 20 + i * 5)
            self.assertFalse(pode, '%s nao deveria anunciar (%s)' % (chave, motivo))
            self.assertIn('intervalo', motivo)

    def test_mesmo_conteudo_nao_e_troca(self):
        t0 = 1000.0
        self.regra.registrar_anuncio('canal:A', t0)
        self.regra.concluir_anuncio(t0 + 10)
        # muito depois dos 2 min, mas e o MESMO conteudo que ja foi anunciado
        pode, motivo = self.regra.pode_anunciar('canal:A', agora=t0 + 500)
        self.assertFalse(pode, motivo)
        # a razao exata e "esta troca ja tentou": o mesmo conteudo nao ganha
        # um segundo anuncio mesmo depois dos 2 minutos.
        self.assertIn('ja tentou', motivo)
        self.assertFalse(self.regra.pode_anunciar('canal:A',
                                                 agora=t0 + 10000)[0])

    def test_chave_diferencia_canal_filme_e_episodio(self):
        canal1 = self.regra.chave_do_conteudo('http://iptv/1.m3u8', 'Canal 1')
        canal2 = self.regra.chave_do_conteudo('http://iptv/1.m3u8', 'Canal 2')
        filme = self.regra.chave_do_conteudo('http://vod/filme.mkv')
        ep1 = self.regra.chave_do_conteudo('http://vod/serie/s01e01.mkv')
        ep2 = self.regra.chave_do_conteudo('http://vod/serie/s01e02.mkv')
        self.assertEqual(len({canal1, canal2, filme, ep1, ep2}), 5)
        # o mesmo conteudo, chamado duas vezes, da a mesma chave
        self.assertEqual(ep1, self.regra.chave_do_conteudo(
            'http://vod/serie/s01e01.mkv', ''))

    def test_falha_do_anuncio_nao_consome_o_intervalo(self):
        """Anuncio que nao abriu: a proxima troca pode tentar de novo."""
        t0 = 1000.0
        self.regra.registrar_anuncio('canal:A', t0)
        self.regra.cancelar_anuncio('canal:A')
        pode, motivo = self.regra.pode_anunciar('canal:B', agora=t0 + 5)
        self.assertTrue(pode, motivo)
        self.assertFalse(self.regra.ultimo_anuncio(t0 + 5))

    def test_estado_sobrevive_a_reinicio_do_servico(self):
        """O Android mata o processo em TV box/stick: a janela continua valendo."""
        t0 = 1000.0
        self.regra.registrar_anuncio('canal:A', t0)
        self.regra.concluir_anuncio(t0 + 10)
        # novo "processo": modulo recarregado, mesmo profile em disco
        sys.modules.pop('ads_regra', None)
        nova = carregar('ads_regra_teste2', BOOTSTRAP / 'ads_regra.py')
        self.assertFalse(nova.pode_anunciar('canal:B', agora=t0 + 30)[0])
        self.assertTrue(nova.pode_anunciar('canal:B', agora=t0 + 200)[0])
        # e o arquivo fica onde o app procura
        self.assertTrue(os.path.isfile(os.path.join(
            self.kodi.perfil, 'addon_data', 'service.smarted.bootstrap',
            'ads-regra.json')))

    def test_relogio_para_tras_nao_prende_o_anuncio(self):
        """Ajuste de hora/NTP no aparelho nao pode bloquear para sempre.

        Um instante no futuro e lixo de relogio: e descartado. Tratar como
        "acabou de mostrar" renovaria o intervalo a cada consulta e o aparelho
        ficaria sem anuncio nenhum; descartar libera na hora e o problema se
        corrige sozinho no proximo anuncio de verdade.
        """
        agora = 5000.0
        self.regra.registrar_anuncio('canal:A', agora + 3600)   # futuro
        pode, motivo = self.regra.pode_anunciar('canal:B', agora=agora)
        self.assertTrue(pode, motivo)
        # e o lixo nao fica no arquivo
        sys.modules.pop('ads_regra', None)
        nova = carregar('ads_regra_teste3', BOOTSTRAP / 'ads_regra.py')
        self.assertFalse(nova.ultimo_anuncio(agora))

    def test_arquivo_corrompido_nao_quebra_nada(self):
        pasta = os.path.join(self.kodi.perfil, 'addon_data',
                             'service.smarted.bootstrap')
        os.makedirs(pasta)
        with open(os.path.join(pasta, 'ads-regra.json'), 'w') as handle:
            handle.write('{isto nao e json')
        pode, _motivo = self.regra.pode_anunciar('canal:A', agora=1000.0)
        self.assertTrue(pode, 'perfil corrompido nao pode travar o anuncio')


class UmAnuncioPorConteudoTest(BaseRegra):
    """Regra adicional: um anuncio por conteudo por sessao de reproducao.

    Mesmo que os 2 minutos tenham passado, nada de novo enquanto o usuario
    continuar no mesmo conteudo. Reiniciar, pausar, retomar, reconectar ou
    recarregar o mesmo conteudo NAO e troca de conteudo.
    """

    def setUp(self):
        BaseRegra.setUp(self)
        self.regra.registrar_anuncio('canal:A', 1000.0)
        self.regra.concluir_anuncio(1010.0)

    def test_mesmo_conteudo_nunca_ganha_o_segundo_anuncio(self):
        # muito depois dos 2 minutos, e ainda no mesmo conteudo
        for agora in (1010.0, 1200.0, 5000.0, 86400.0):
            pode, motivo = self.regra.pode_anunciar('canal:A', agora=agora)
            self.assertFalse(pode, '%s s: %s' % (agora, motivo))

    def test_recarregar_reconectar_nao_abre_bilhete_novo(self):
        self.assertFalse(self.regra.abrir_troca('canal:A'))
        self.assertFalse(self.regra.pode_anunciar('canal:A', agora=9999.0)[0])

    def test_reabrir_o_mesmo_conteudo_nao_autoriza_outro_anuncio(self):
        """Regra 3: recarregar/reconectar parar e voltar NAO e troca.

        Mesmo que a sessao de reproducao tenha terminado (PARAR) e passado
        muito mais que os 2 minutos, o mesmo conteudo nao recebe outro anuncio.
        """
        self.regra.encerrar_conteudo()
        self.assertTrue(self.regra.abrir_troca('canal:A'))
        pode, motivo = self.regra.pode_anunciar('canal:A', agora=9999.0)
        self.assertFalse(pode, motivo)
        self.assertIn('ja recebeu', motivo)

    def test_conteudo_diferente_depois_de_parar_e_liberado(self):
        """Troca REAL de conteudo (outro canal/filme) continua podendo."""
        self.regra.encerrar_conteudo()
        self.assertTrue(self.regra.abrir_troca('filme:Z'))
        pode, motivo = self.regra.pode_anunciar('filme:Z', agora=9999.0)
        self.assertTrue(pode, motivo)

    def test_parar_dentro_dos_2_minutos_nao_libera(self):
        """Outro conteudo, mas dentro da janela: o intervalo bloqueia."""
        self.regra.encerrar_conteudo()
        self.assertTrue(self.regra.abrir_troca('canal:Z'))
        pode, motivo = self.regra.pode_anunciar('canal:Z', agora=1050.0)
        self.assertFalse(pode, motivo)
        self.assertIn('intervalo', motivo)

    def test_troca_real_depois_do_intervalo_libera(self):
        self.regra.encerrar_conteudo()
        self.assertTrue(self.regra.abrir_troca('filme:B'))
        self.assertTrue(self.regra.pode_anunciar('filme:B', agora=1200.0)[0])
        # e so o primeiro conteudo novo: o seguinte ja esta no intervalo
        self.regra.registrar_anuncio('filme:B', 1200.0)
        self.regra.concluir_anuncio(1215.0)
        self.regra.encerrar_conteudo()
        self.assertTrue(self.regra.abrir_troca('serie:C:S01E01'))
        self.assertFalse(self.regra.pode_anunciar('serie:C:S01E01',
                                                 agora=1300.0)[0])

    def test_uma_tentativa_por_troca_mesmo_falhando(self):
        """Anuncio que falhou nao e tentado de novo dentro da mesma troca."""
        self.regra.encerrar_conteudo()
        self.regra.registrar_anuncio('filme:B', 5000.0)
        self.regra.cancelar_anuncio('filme:B')       # nao abriu
        self.assertFalse(self.regra.pode_anunciar('filme:B', agora=5001.0)[0])
        # a proxima TROCA de conteudo pode tentar (uma tentativa por troca)
        self.regra.encerrar_conteudo()
        self.regra.abrir_troca('filme:C')
        self.assertTrue(self.regra.pode_anunciar('filme:C', agora=5002.0)[0])


class IntegracaoSmartAdsTest(BaseRegra):
    """A regra e usada pelo gatilho real (uma unica porta de entrada)."""

    def setUp(self):
        BaseRegra.setUp(self)
        self.smart = carregar('smart_ads_regra', BOOTSTRAP / 'smart_ads.py')
        self.smart.vip_ativo = lambda: False
        self.disparos = []

    def _disparar(self, atividade, log=None):
        self.disparos.append(atividade)
        return True

    def test_anuncio_a_cada_video_nao_acontece_mais(self):
        """O defeito relatado: a cada video aparecia anuncio."""
        t = 1000.0
        resultados = []
        for i in range(6):
            resultados.append(self.smart.mostrar_preroll(
                caminho='http://vod/filme-%d.mkv' % i, sessao=i,
                disparar=self._disparar, agora=t + i * 5))
        # so o primeiro dispara; os outros 5 (em 25 s) nao
        self.assertEqual(resultados, [True, False, False, False, False, False])
        self.assertEqual(len(self.disparos), 1)

    def test_dois_minutos_depois_volta_a_anunciar(self):
        self.assertTrue(self.smart.mostrar_preroll(
            caminho='http://vod/a.mkv', sessao=1, disparar=self._disparar,
            agora=1000.0))
        self.assertFalse(self.smart.mostrar_preroll(
            caminho='http://vod/b.mkv', sessao=2, disparar=self._disparar,
            agora=1050.0))
        self.assertTrue(self.smart.mostrar_preroll(
            caminho='http://vod/c.mkv', sessao=3, disparar=self._disparar,
            agora=1000.0 + INTERVALO + 5))

    def test_vip_nunca_recebe_anuncio(self):
        self.smart.vip_ativo = lambda: True
        for i in range(3):
            self.assertFalse(self.smart.mostrar_preroll(
                caminho='http://vod/filme-%d.mkv' % i, sessao=i,
                disparar=self._disparar, agora=1000.0 + i * 1000))
        self.assertEqual(self.disparos, [])

    def test_falha_nao_trava_e_nao_consome(self):
        """Sem inventario/SDK: devolve False na hora e nada fica bloqueado."""
        def falhar(atividade, log=None):
            self.disparos.append(atividade)
            return False
        self.assertFalse(self.smart.mostrar_preroll(
            caminho='http://vod/a.mkv', sessao=1, disparar=falhar,
            agora=1000.0))
        # a proxima troca tenta de novo (o intervalo nao foi consumido)
        self.assertTrue(self.smart.mostrar_preroll(
            caminho='http://vod/b.mkv', sessao=2, disparar=self._disparar,
            agora=1005.0))

    def test_mesmo_inicio_nao_duplica_anuncio(self):
        """onPlayBackStarted + onAVStarted do MESMO stream = um anuncio."""
        self.assertTrue(self.smart.mostrar_preroll(
            caminho='http://vod/a.mkv', sessao=7, disparar=self._disparar,
            agora=1000.0))
        self.assertFalse(self.smart.mostrar_preroll(
            caminho='http://vod/a.mkv', sessao=7, disparar=self._disparar,
            agora=1002.0))
        self.assertEqual(len(self.disparos), 1)

    def test_teste_dos_ajustes_nao_consome_o_intervalo(self):
        self.smart.mostrar_preroll(forcar=True, disparar=self._disparar,
                                   agora=1000.0)
        # depois do teste, a primeira troca real ainda pode anunciar
        self.assertTrue(self.smart.mostrar_preroll(
            caminho='http://vod/a.mkv', sessao=1, disparar=self._disparar,
            agora=1001.0))


if __name__ == '__main__':
    unittest.main()
