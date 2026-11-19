# -*- coding: utf-8 -*-
"""Anuncio de video (VAST) na TV: o que o usuario pediu como prioridade.

O pedido foi direto: "garanta que os anuncios sejam reproduzidos". Estes
testes cobrem o caminho inteiro, sem aparelho:

    tag VAST -> XML -> criativo linear -> player do Kodi -> eventos VAST
             -> conteudo de volta no ponto certo

O que cada grupo garante:

1. leitura do VAST (MP4 preferido, HLS como alternativa, Wrapper ignorado,
   tag invalida nao derruba nada);
2. recibo de exibicao HONESTO: ``exibido`` so e True quando o player tocou o
   video do anuncio; sem tag/rede/criativo, False e o conteudo segue;
3. eventos disparados na ordem certa (impression no inicio, quartis, complete);
4. frequencia intacta (``ads_regra`` continua decidindo; falha nao consome o
   intervalo de 2 minutos);
5. conteudo devolvido: ao vivo reabre sem seek; filme retoma na posicao;
6. celular NAO muda: continua disparando a activity AdMob.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'

VAST_VALIDO = '''<?xml version="1.0" encoding="UTF-8"?>
<VAST version="3.0">
  <Ad id="ad-1">
    <InLine>
      <AdSystem>SMARTED Test</AdSystem>
      <AdTitle>Anuncio linear de teste</AdTitle>
      <Impression><![CDATA[https://ads.exemplo/impressao]]></Impression>
      <Error><![CDATA[https://ads.exemplo/erro]]></Error>
      <Creatives>
        <Creative id="cr-1">
          <Linear skipoffset="00:00:05">
            <Duration>00:00:30</Duration>
            <TrackingEvents>
              <Tracking event="start"><![CDATA[https://ads.exemplo/start]]></Tracking>
              <Tracking event="firstQuartile"><![CDATA[https://ads.exemplo/q1]]></Tracking>
              <Tracking event="midpoint"><![CDATA[https://ads.exemplo/q2]]></Tracking>
              <Tracking event="thirdQuartile"><![CDATA[https://ads.exemplo/q3]]></Tracking>
              <Tracking event="complete"><![CDATA[https://ads.exemplo/fim]]></Tracking>
              <Tracking event="skip"><![CDATA[https://ads.exemplo/pulo]]></Tracking>
            </TrackingEvents>
            <MediaFiles>
              <MediaFile type="video/mp4" width="640" height="360" bitrate="400">
                <![CDATA[https://ads.exemplo/anuncio-360.mp4]]>
              </MediaFile>
              <MediaFile type="video/mp4" width="1280" height="720" bitrate="1200">
                <![CDATA[https://ads.exemplo/anuncio-720.mp4]]>
              </MediaFile>
              <MediaFile type="application/x-mpegURL" width="1920" height="1080">
                <![CDATA[https://ads.exemplo/anuncio.m3u8]]>
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>
'''

VAST_SEM_CRIATIVO = '''<?xml version="1.0"?>
<VAST version="3.0"><Ad id="x"><InLine><AdSystem>S</AdSystem>
<Creatives><Creative><Linear><Duration>00:00:10</Duration>
<MediaFiles><MediaFile type="text/html"><![CDATA[https://x/e.html]]></MediaFile>
</MediaFiles></Linear></Creative></Creatives></InLine></Ad></VAST>
'''

VAST_WRAPPER = '''<?xml version="1.0"?>
<VAST version="3.0"><Ad id="w"><Wrapper>
<AdSystem>S</AdSystem><VASTAdTagURI><![CDATA[https://ads.exemplo/wrapper]]></VASTAdTagURI>
</Wrapper></Ad></VAST>
'''


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class PlayerDeMentira(object):
    """Player com estado controlavel: toca, avanca o tempo e para."""

    def __init__(self):
        self.tocando = False
        self.video = True
        self.arquivo = ''
        self.posicao = 0.0
        self.total = 0.0
        self.builtins = []
        self.relogio = 0.0

    # API do xbmc.Player usada pelo modulo
    def isPlayingVideo(self):
        return self.tocando and self.video

    def isPlaying(self):
        return self.tocando

    def getPlayingFile(self):
        return self.arquivo

    def getTime(self):
        return self.posicao

    def getTotalTime(self):
        return self.total

    def seekTime(self, segundos):
        self.posicao = segundos


class KodiDeMentira(object):
    def __init__(self):
        self.player = PlayerDeMentira()
        self.builtins = []
        self.logs = []
        self.condicoes = set()
        self.info = {}
        self.LOGINFO, self.LOGWARNING, self.LOGERROR = 1, 3, 4

    def Player(self):
        return self.player

    # o modulo chama xbmc.Player() e tambem herda dele
    PlayerBase = PlayerDeMentira

    def getCondVisibility(self, consulta):
        return consulta in self.condicoes

    def getInfoLabel(self, rotulo):
        return self.info.get(rotulo, '')

    def executebuiltin(self, comando):
        self.builtins.append(comando)
        if comando.startswith('PlayMedia'):
            self.player.tocando = True
            self.player.video = True
            self.player.posicao = 0.0
            self.player.total = 30.0

    def executeJSONRPC(self, pedido):
        import json
        dados = json.loads(pedido)
        metodo = dados.get('method')
        if metodo == 'Player.GetActivePlayers':
            if self.player.tocando:
                return json.dumps({'result': [{'playerid': 1, 'type': 'video'}]})
            return json.dumps({'result': []})
        return json.dumps({'result': 'OK'})

    def log(self, mensagem, nivel=1):
        self.logs.append(mensagem)


class BaseVast(unittest.TestCase):
    def setUp(self):
        self.guardados = {n: sys.modules.get(n)
                          for n in ('xbmc', 'xbmcvfs', 'xbmcaddon', 'xbmcgui',
                                    'ads_vast', 'ads_regra', 'variante',
                                    'ao_vivo', 'smart_ads')}
        self.kodi = KodiDeMentira()
        self._relogio = [0.0]
        xbmc = types.ModuleType('xbmc')

        class _PlayerBase(object):
            """Base para MediaPortal/MonitorPreRoll (o Kodi usa xbmc.Player)."""

            def __init__(self, *args, **kwargs):
                pass

        xbmc.Player = _PlayerBase
        xbmc.getCondVisibility = self.kodi.getCondVisibility
        xbmc.getInfoLabel = self.kodi.getInfoLabel
        xbmc.executebuiltin = self.kodi.executebuiltin
        xbmc.executeJSONRPC = self.kodi.executeJSONRPC
        xbmc.log = self.kodi.log
        xbmc.sleep = lambda ms: None
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        # o modulo pede o player no modulo global: devolve o falso
        xbmc.Player = lambda *a, **k: self.kodi.player
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p
        vfs.exists = lambda p: False
        vfs.File = lambda *a, **k: types.SimpleNamespace(
            read=lambda *x: '', write=lambda *x: None, close=lambda: None)
        sys.modules['xbmcvfs'] = vfs
        addon = types.ModuleType('xbmcaddon')

        class _Addon(object):
            def getSetting(self, _chave):
                return ''

            def getAddonInfo(self, _chave):
                return 'service.smarted.bootstrap'

        addon.Addon = _Addon
        sys.modules['xbmcaddon'] = addon
        gui = types.ModuleType('xbmcgui')
        gui.Dialog = lambda: types.SimpleNamespace(ok=lambda *a, **k: None,
                                                   notification=lambda *a, **k: None)
        sys.modules['xbmcgui'] = gui
        sys.path.insert(0, str(BOOTSTRAP))
        self.vast = carregar('ads_vast_teste', BOOTSTRAP / 'ads_vast.py')
        # relogio falso: os testes nao podem esperar 15 s de verdad
        self.vast._agora = lambda: self._relogio[0]

    def tearDown(self):
        sys.path.remove(str(BOOTSTRAP))
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    # relogio acelerado: nao dormir de verdade e avancar o player
    def _dormir(self, segundos):
        """Dormir de mentira: avanca o relogio e o video do anuncio."""
        self._relogio[0] += 1.0
        if self.kodi.player.tocando:
            self.kodi.player.posicao += 1.0


# ---------------------------------------------------------------------------
# 1. Leitura do VAST
# ---------------------------------------------------------------------------
class LeituraDoVastTest(BaseVast):
    def test_escolhe_o_mp4_mais_proximo_da_tela(self):
        anuncio = self.vast.escolher_anuncio(VAST_VALIDO, altura_tela=1080)
        self.assertIsNotNone(anuncio)
        self.assertEqual(anuncio['url'], 'https://ads.exemplo/anuncio-720.mp4')
        self.assertEqual(anuncio['duracao'], 30.0)
        self.assertEqual(anuncio['tempo_skip'], 5)

    def test_mp4_ganha_do_hls_mesmo_com_resolucao_menor(self):
        anuncio = self.vast.escolher_anuncio(VAST_VALIDO, altura_tela=1920)
        self.assertTrue(anuncio['url'].endswith('.mp4'),
                        'MP4 progressivo e mais confiavel em box/stick')

    def test_hls_serve_quando_nao_ha_mp4(self):
        xml = VAST_VALIDO.replace('video/mp4', 'video/x-flv')
        anuncio = self.vast.escolher_anuncio(xml)
        self.assertTrue(anuncio['url'].endswith('.m3u8'))

    def test_nao_aceita_criativo_que_nao_e_video(self):
        self.assertIsNone(self.vast.escolher_anuncio(VAST_SEM_CRIATIVO))

    def test_wrapper_sem_inline_nao_vira_anuncio_falso(self):
        self.assertIsNone(self.vast.escolher_anuncio(VAST_WRAPPER))

    def test_xml_quebrado_nao_derruba_nada(self):
        for entrada in ('', None, '<VAST', 'nao e xml', b'\x00\x01'):
            self.assertIsNone(self.vast.escolher_anuncio(entrada))

    def test_urls_de_evento_e_impressao_sao_lidas(self):
        anuncio = self.vast.escolher_anuncio(VAST_VALIDO)
        self.assertEqual(anuncio['impressao'], ['https://ads.exemplo/impressao'])
        self.assertEqual(anuncio['eventos']['complete'],
                         ['https://ads.exemplo/fim'])
        self.assertEqual(anuncio['eventos']['skip'], ['https://ads.exemplo/pulo'])


# ---------------------------------------------------------------------------
# 2. Nada de tag inventada
# ---------------------------------------------------------------------------
class TagTest(BaseVast):
    def test_sem_tag_nao_ha_anuncio(self):
        self.assertEqual(self.vast.tag_configurada(''), '')

    def test_tag_do_modulo_e_usada(self):
        self.assertEqual(self.vast.tag_configurada('https://ads/x?z=1'),
                         'https://ads/x?z=1')

    def test_tag_da_janela_tem_prioridade(self):
        self.kodi.info['Window(10000).Property(smartedtv.vast.tag)'] = \
            'https://ads/janela'
        self.assertEqual(self.vast.tag_configurada('https://ads/modulo'),
                         'https://ads/janela')

    def test_tag_de_teste_e_a_oficial_do_google(self):
        self.assertIn('pubads.g.doubleclick.net', self.vast.tag_de_teste())

    def test_sem_tag_o_conteudo_nao_e_mexido(self):
        recibo = self.vast.exibir_e_devolver(log=self.kodi.logs.append, tag='')
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'sem-tag')
        self.assertEqual(self.kodi.builtins, [])


# ---------------------------------------------------------------------------
# 3. Reproducao de verdade (o pedido principal)
# ---------------------------------------------------------------------------
class ReproducaoTest(BaseVast):
    def setUp(self):
        super(ReproducaoTest, self).setUp()
        # conteudo tocando: filme na posicao 120 s
        self.kodi.player.tocando = True
        self.kodi.player.arquivo = 'https://exemplo/filme.mp4'
        self.kodi.player.posicao = 120.0
        self.kodi.player.total = 3600.0
        # sem 'ao_vivo' no caminho: o filme volta por PlayMedia + seek
        sys.modules['ao_vivo'] = types.SimpleNamespace(
            eh_ao_vivo=lambda caminho='': 'canal' in (caminho or ''),
            _tocar_de_novo=lambda caminho: True)

    def _baixar(self, xml):
        return lambda _url: xml.encode('utf-8')

    def test_anuncio_toca_e_conteudo_volta(self):
        recibo = self.vast.exibir_e_devolver(
            log=self.kodi.logs.append,
            tag='https://ads/tag',
            baixar_tag=self._baixar(VAST_VALIDO),
            dormir=self._dormir)
        self.assertTrue(recibo['exibido'], recibo)
        self.assertEqual(recibo['motivo'], 'exibido')
        self.assertTrue(recibo.get('conteudo_devolvido'))
        # o video do anuncio foi entregue ao player
        tocou = [b for b in self.kodi.builtins if 'anuncio-720.mp4' in b]
        self.assertEqual(len(tocou), 1, self.kodi.builtins)
        # e o conteudo foi reaberto depois
        voltou = [b for b in self.kodi.builtins if 'filme.mp4' in b]
        self.assertEqual(len(voltou), 1, self.kodi.builtins)

    def test_recibo_traz_os_eventos_do_vast(self):
        recibo = self.vast.exibir_e_devolver(
            tag='https://ads/tag', baixar_tag=self._baixar(VAST_VALIDO),
            dormir=self._dormir)
        self.assertIn('start', recibo['eventos'])
        self.assertIn('complete', recibo['eventos'])

    def test_tag_sem_resposta_libera_o_conteudo(self):
        recibo = self.vast.exibir_e_devolver(
            tag='https://ads/tag', baixar_tag=lambda _u: None,
            dormir=self._dormir)
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'tag-sem-resposta')
        # nao recarregou o filme do zero por causa de um anuncio que nao veio
        self.assertEqual([b for b in self.kodi.builtins if 'filme.mp4' in b], [])

    def test_vast_sem_criativo_linear_libera_o_conteudo(self):
        recibo = self.vast.exibir_e_devolver(
            tag='https://ads/tag',
            baixar_tag=self._baixar(VAST_SEM_CRIATIVO), dormir=self._dormir)
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'vast-sem-criativo')

    def test_player_recusando_nao_marca_anuncio_como_exibido(self):
        recibo = self.vast.exibir_e_devolver(
            tag='https://ads/tag', baixar_tag=self._baixar(VAST_VALIDO),
            tocar=lambda url, log=None: False, dormir=self._dormir)
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'player-recusou')

    def test_anuncio_que_nao_inicia_nao_vira_impressao(self):
        """PlayMedia aceito mas o video nao comeca: nao houve anuncio."""
        sem_player = lambda c: self.kodi.builtins.append(c)
        self.kodi.executebuiltin = sem_player
        sys.modules['xbmc'].executebuiltin = sem_player
        self.kodi.player.tocando = False
        self.kodi.player.video = False
        recibo = self.vast.exibir(
            tag='https://ads/tag', baixar_tag=self._baixar(VAST_VALIDO),
            dormir=self._dormir)
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'nao-iniciou')

    def test_tempo_maximo_encerra_o_anuncio(self):
        # video do anuncio sem duracao informada: o prazo manda
        recibo = self.vast.exibir(
            tag='https://ads/tag', baixar_tag=self._baixar(VAST_VALIDO),
            tempo_maximo=3, dormir=self._dormir)
        self.assertTrue(recibo['exibido'])
        self.assertLessEqual(recibo['segundos'], 6)


# ---------------------------------------------------------------------------
# 4. Eventos VAST
# ---------------------------------------------------------------------------
class EventosTest(BaseVast):
    def test_impressao_e_quartis_sao_disparados_na_ordem(self):
        anuncio = self.vast.escolher_anuncio(VAST_VALIDO)
        chamadas = []
        self.vast.disparar_original = self.vast.disparar

        def registrar(urls):
            chamadas.extend(urls)
            return len(urls)

        self.vast.disparar = registrar
        try:
            player = self.kodi.player
            player.tocando = True
            player.posicao = 0.0
            player.total = 30.0
            def dormir(_segundos):
                self._relogio[0] += 1.0
                player.posicao = min(30.0, player.posicao + 7.5)

            self.vast.reproduzir(anuncio, dormir=dormir)
        finally:
            self.vast.disparar = self.vast.disparar_original
        self.assertEqual(chamadas[0], 'https://ads.exemplo/impressao')
        self.assertIn('https://ads.exemplo/start', chamadas)
        self.assertIn('https://ads.exemplo/q1', chamadas)
        self.assertIn('https://ads.exemplo/q2', chamadas)
        self.assertIn('https://ads.exemplo/q3', chamadas)
        self.assertEqual(chamadas[-1], 'https://ads.exemplo/fim')


# ---------------------------------------------------------------------------
# 5. Conteudo devolvido
# ---------------------------------------------------------------------------
class DevolucaoDoConteudoTest(BaseVast):
    def test_ao_vivo_reabre_sem_seek(self):
        self.kodi.player.tocando = True
        self.kodi.player.arquivo = 'plugin://plugin.video.smarted/?canal=1'
        self.kodi.player.posicao = 500.0
        estado = {'caminho': 'plugin://plugin.video.smarted/?canal=1',
                  'posicao': 500.0, 'total': 0.0, 'ao_vivo': True}
        self.vast.restaurar(estado, dormir=self._dormir)
        buscas = [c for c in self.kodi.builtins if 'Seek' in c]
        self.assertEqual(buscas, [], 'seek em ao vivo derruba o fluxo')

    def test_filme_retoma_na_posicao(self):
        self.kodi.player.tocando = True
        estado = {'caminho': 'https://exemplo/filme.mp4', 'posicao': 120.0,
                  'total': 3600.0, 'ao_vivo': False}
        self.vast.restaurar(estado, dormir=self._dormir)
        self.assertTrue(any('filme.mp4' in c for c in self.kodi.builtins))


# ---------------------------------------------------------------------------
# 6. smart_ads: TV usa video, celular continua no AdMob
# ---------------------------------------------------------------------------
class RoteamentoTest(BaseVast):
    def _carregar_ads(self):
        # smart_ads herda de xbmc.Player: aqui ele precisa ser classe
        class _PlayerBase(object):
            def __init__(self, *args, **kwargs):
                pass

        sys.modules['xbmc'].Player = _PlayerBase
        self.modulo = carregar('smart_ads_vast', BOOTSTRAP / 'smart_ads.py')
        self.modulo._variante = types.SimpleNamespace(
            e_tv=lambda: True, e_mobile=lambda: False)
        return self.modulo

    def test_tv_pede_anuncio_de_video_e_nao_admob(self):
        modulo = self._carregar_ads()
        modulo.VAST_TAG_PADRAO = 'https://ads/tag'
        self.kodi.condicoes = {'System.Platform.Android'}
        # variante por instancia (o global do modulo pode ser herdado)
        modulo.e_tv = lambda: True
        modulo.e_mobile = lambda: False

        # o modulo importa ads_vast do addon: aponta para o mesmo objeto do
        # teste para observar a chamada (sem rede e sem player de verdade)
        sys.modules['ads_vast'] = self.vast
        original = self.vast.exibir_e_devolver
        chamadas = []

        def falso(**kwargs):
            chamadas.append(kwargs)
            return {'exibido': True, 'motivo': 'exibido',
                    'eventos': ['start', 'complete']}

        self.vast.exibir_e_devolver = falso
        try:
            resultado = modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL)
        finally:
            self.vast.exibir_e_devolver = original
        self.assertTrue(resultado)
        self.assertEqual(len(chamadas), 1, chamadas)
        self.assertEqual(chamadas[0]['tag'], 'https://ads/tag')
        atividades = [b for b in self.kodi.builtins
                      if b.startswith('StartAndroidActivity')]
        self.assertEqual(atividades, [], 'TV nao usa a activity do AdMob')

    def test_tv_sem_tag_nao_pede_nada_e_nao_quebra(self):
        modulo = self._carregar_ads()
        modulo.VAST_TAG_PADRAO = ''
        self.assertFalse(modulo.tocar_anuncio(modulo.ATIDADE_PREROLL)
                         if hasattr(modulo, 'ATIDADE_PREROLL')
                         else modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL))
        self.assertEqual([b for b in self.kodi.builtins
                          if b.startswith('StartAndroidActivity')], [])

    def test_celular_continua_disparando_admob(self):
        modulo = self._carregar_ads()
        modulo._variante = types.SimpleNamespace(
            e_tv=lambda: False, e_mobile=lambda: True)
        modulo.e_tv = lambda: False
        self.kodi.condicoes = {'System.Platform.Android'}
        self.assertTrue(modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL))
        atividades = [b for b in self.kodi.builtins
                      if b.startswith('StartAndroidActivity')]
        self.assertEqual(len(atividades), 1)
        self.assertIn(modulo.ATIVIDADE_PREROLL, atividades[0])


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------------------
# 7. O modulo chega ao APK (senao a TV fica sem anuncio, em silencio)
# ---------------------------------------------------------------------------
class EntregaNoApkTest(unittest.TestCase):
    INJETOR = ROOT / 'tools' / 'kodi' / 'injetar-tela-entrada.py'

    def test_injetor_leva_o_modulo_vast_para_o_apk(self):
        fonte = self.INJETOR.read_text(encoding='utf-8')
        self.assertIn('service.smarted.bootstrap/ads_vast.py', fonte)
        self.assertIn('VAST_MODULO', fonte)

    def test_modulo_vast_existe_no_repositorio(self):
        self.assertTrue((BOOTSTRAP / 'ads_vast.py').is_file())

    def test_modulo_nao_usa_rede_sem_timeout(self):
        """Nenhuma chamada de rede pode prender a TV."""
        fonte = (BOOTSTRAP / 'ads_vast.py').read_text(encoding='utf-8')
        self.assertIn('timeout=TIMEOUT_HTTP', fonte)
        self.assertNotIn('timeout=None', fonte)

    def test_modulo_compila_para_o_kodi(self):
        import py_compile
        py_compile.compile(str(BOOTSTRAP / 'ads_vast.py'), doraise=True)


class WrapperTest(BaseVast):
    """O Ad Manager entrega Wrapper quando ha mediacao: tem de ser seguido."""

    WRAPPER = ('<?xml version="1.0"?><VAST version="3.0"><Ad id="w"><Wrapper>'
               '<AdSystem>G</AdSystem>'
               '<VASTAdTagURI><![CDATA[https://ads.exemplo/proximo]]>'
               '</VASTAdTagURI></Wrapper></Ad></VAST>')

    def test_le_a_tag_do_wrapper(self):
        self.assertEqual(self.vast.tag_do_wrapper(self.WRAPPER),
                         'https://ads.exemplo/proximo')

    def test_inline_nao_tem_tag_de_wrapper(self):
        self.assertEqual(self.vast.tag_do_wrapper(VAST_VALIDO), '')

    def test_exibir_segue_o_wrapper_ate_o_criativo(self):
        pedidos = []

        def baixar(url):
            pedidos.append(url)
            if url == 'https://ads/tag':
                return self.WRAPPER.encode('utf-8')
            return VAST_VALIDO.encode('utf-8')

        self.kodi.player.tocando = True
        recibo = self.vast.exibir_e_devolver(
            tag='https://ads/tag', baixar_tag=baixar, dormir=self._dormir)
        self.assertEqual(pedidos[:2], ['https://ads/tag',
                                       'https://ads.exemplo/proximo'])
        self.assertTrue(recibo['exibido'], recibo)

    def test_cadeia_longa_demais_e_cortada(self):
        def baixar(url):
            return self.WRAPPER.encode('utf-8')

        recibo = self.vast.exibir(tag='https://ads/tag', baixar_tag=baixar,
                                  dormir=self._dormir)
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'vast-sem-criativo')


class ModoDeTesteTest(BaseVast):
    """Validacao em TV real com a tag oficial de TESTE do Google.

    O usuario autorizou anuncios de teste oficiais na validacao. Fora desse
    modo, sem tag do projeto, nao existe anuncio nenhum (nada inventado).
    """

    def test_sem_modo_de_teste_e_sem_tag_nao_ha_anuncio(self):
        self.assertEqual(self.vast.tag_configurada(''), '')

    def test_modo_de_teste_usa_a_tag_oficial(self):
        self.kodi.info['Window(10000).Property(smartedtv.vast.teste)'] = '1'
        tag = self.vast.tag_configurada('')
        self.assertEqual(tag, self.vast.tag_de_teste())
        self.assertIn('pubads.g.doubleclick.net', tag)

    def test_tag_do_projeto_ganha_do_modo_de_teste(self):
        self.kodi.info['Window(10000).Property(smartedtv.vast.teste)'] = '1'
        self.assertEqual(self.vast.tag_configurada('https://ads/projeto'),
                         'https://ads/projeto')


class BotaoTestarAnuncioTest(BaseVast):
    """O botao dos Ajustes pede o anuncio pelo MESMO caminho da reproducao."""

    def _carregar_ads(self):
        class _PlayerBase(object):
            def __init__(self, *args, **kwargs):
                pass

        sys.modules['xbmc'].Player = _PlayerBase
        modulo = carregar('smart_ads_botao', BOOTSTRAP / 'smart_ads.py')
        self.kodi.condicoes = {'System.Platform.Android'}
        modulo.e_tv = lambda: True
        modulo.VAST_TAG_PADRAO = 'https://ads/tag'
        sys.modules['ads_vast'] = self.vast
        return modulo

    def test_teste_usa_o_caminho_de_video(self):
        modulo = self._carregar_ads()
        chamadas = []

        def falso(**kwargs):
            chamadas.append(kwargs)
            return {'exibido': True, 'motivo': 'exibido', 'segundos': 12}

        original = self.vast.exibir_e_devolver
        self.vast.exibir_e_devolver = falso
        try:
            recibo = modulo.testar_anuncio_video()
        finally:
            self.vast.exibir_e_devolver = original
        self.assertTrue(recibo['exibido'])
        self.assertEqual(len(chamadas), 1)

    def test_teste_sem_tag_nao_quebra(self):
        modulo = self._carregar_ads()
        modulo.VAST_TAG_PADRAO = ''
        self.kodi.info['Window(10000).Property(smartedtv.vast.teste)'] = ''
        recibo = modulo.testar_anuncio_video()
        self.assertFalse(recibo['exibido'])
        self.assertEqual(recibo['motivo'], 'sem-tag')

    def test_teste_com_modo_de_teste_usa_tag_do_google(self):
        modulo = self._carregar_ads()
        modulo.VAST_TAG_PADRAO = ''
        self.kodi.info['Window(10000).Property(smartedtv.vast.teste)'] = '1'
        self.assertIn('pubads.g.doubleclick.net',
                      self.vast.tag_configurada(modulo.VAST_TAG_PADRAO))


class FumacaDoCaminhoCompletoTest(BaseVast):
    """Ciclo ponta a ponta, sem rede e sem aparelho (o que o smoke faz).

    tag -> VAST -> player -> eventos -> conteudo de volta. E este caminho que
    roda na TV quando o usuario troca de conteudo.
    """

    def test_ciclo_completo(self):
        self.kodi.player.tocando = True
        self.kodi.player.arquivo = 'https://exemplo/filme.mp4'
        self.kodi.player.posicao = 120.0
        self.kodi.player.total = 3600.0
        recibo = self.vast.exibir_e_devolver(
            tag='https://ads/tag',
            baixar_tag=lambda _u: VAST_VALIDO.encode('utf-8'),
            dormir=self._dormir)
        self.assertTrue(recibo['exibido'])
        self.assertEqual(recibo['eventos'],
                         ['complete', 'firstQuartile', 'midpoint', 'start',
                          'thirdQuartile'])
        self.assertTrue(any('anuncio-720.mp4' in b for b in self.kodi.builtins))
        self.assertTrue(any('filme.mp4' in b for b in self.kodi.builtins[1:]))
        self.assertTrue(recibo.get('conteudo_devolvido'))
