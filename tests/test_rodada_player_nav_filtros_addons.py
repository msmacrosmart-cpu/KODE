# -*- coding: utf-8 -*-
"""Bateria objetiva (exatamente 3 testes por funcionalidade) para o build:

1. Player + Anuncio + Retomada em tela cheia (sem sair para 2o plano na Home e
   sem perder conexao com o filme/canal);
2. Navegacao D-pad da Home (barra superior 9000 tratada igual ao Hero 9300,
   ultima grade descendo para 9000 e subida completa);
3. Filtro de conteudos em MyVideoNav.xml acessivel pelo D-pad (IDs inteiros
   9061..9066 e ligacao ida/volta com listas 50/51/52 e lateral 9000);
4. Addons/Elementum preservados + DNS Cloudflare DoH + integridade do servico.
"""
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
SKINS = ('skin.estilo.personalizado', 'skin.novatv')

VAST_AMOSTRA = '''<?xml version="1.0" encoding="UTF-8"?>
<VAST version="3.0">
  <Ad id="ad-real">
    <InLine>
      <AdSystem>SMARTED</AdSystem>
      <AdTitle>PreRoll</AdTitle>
      <Impression><![CDATA[https://ads.exemplo/imp]]></Impression>
      <Creatives>
        <Creative id="c1">
          <Linear>
            <Duration>00:00:10</Duration>
            <TrackingEvents>
              <Tracking event="start"><![CDATA[https://ads.exemplo/start]]></Tracking>
              <Tracking event="complete"><![CDATA[https://ads.exemplo/complete]]></Tracking>
            </TrackingEvents>
            <MediaFiles>
              <MediaFile type="video/mp4" width="1280" height="720" bitrate="1000">
                <![CDATA[https://ads.exemplo/preroll-720.mp4]]>
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>
'''


def _carregar_modulo(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# FUNCIONALIDADE 1: Player + Anuncio + Retomada (3 testes)
# ===========================================================================
class PlayerAnuncioRetomadaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='smarted-player-')
        self.salvos = {
            k: sys.modules.get(k)
            for k in ('xbmc', 'xbmcvfs', 'xbmcaddon', 'xbmcgui',
                      'ads_vast', 'ads_regra', 'variante', 'ao_vivo',
                      'smart_ads', 'vip', 'smarted_release')
        }
        self._instalar_kodi_realista()

    def tearDown(self):
        if str(BOOTSTRAP) in sys.path:
            sys.path.remove(str(BOOTSTRAP))
        for nome, mod in self.salvos.items():
            if mod is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = mod
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _instalar_kodi_realista(self):
        """Simula fielmente o C++ do Kodi (PlayerBuiltins.cpp):
        PlayMedia(url, 1) fecha fullscreenvideo (noFullscreen=True -> Home)!
        PlayMedia(url) mantem/abre fullscreenvideo.
        """
        estado = {
            'tocando': True,
            'arquivo': 'https://cdn.exemplo/filme-conectado.mp4',
            'posicao': 42.0,
            'total': 5400.0,
            'janela': 'fullscreenvideo',
            'builtins': [],
            'historico_janelas': [],
            'condicoes': {'System.Platform.Android', 'System.Platform.Android.TV'},
            'info': {
                'System.ScreenHeight': '1080',
                'Player.Filenameandpath': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=1&url=movie123',
                'VideoPlayer.Title': 'Filme Teste',
            },
            'falhar_urls': set(),
            'relogio': 1000.0,
            'seeks': [],
        }
        self.estado = estado

        class FakePlayer(object):
            def __init__(self, *a, **kw):
                pass

            def isPlayingVideo(self):
                return estado['tocando']

            def isPlaying(self):
                return estado['tocando']

            def getPlayingFile(self):
                return estado['arquivo'] if estado['tocando'] else ''

            def getTime(self):
                return estado['posicao']

            def getTotalTime(self):
                return estado['total']

            def seekTime(self, seg):
                estado['posicao'] = float(seg)
                estado['seeks'].append(float(seg))

        def executebuiltin(cmd):
            estado['builtins'].append(cmd)
            if cmd.startswith('PlayMedia('):
                miolo = cmd[len('PlayMedia('):-1]
                # Se tiver ,1 fora das aspas -> noFullscreen=True (bug real!)
                partes = miolo.rsplit(',', 1)
                no_fullscreen = len(partes) == 2 and partes[1].strip() == '1'
                url = partes[0].strip().strip('"') if no_fullscreen else miolo.strip().strip('"')
                if url in estado['falhar_urls']:
                    estado['tocando'] = False
                    estado['arquivo'] = ''
                    return
                estado['tocando'] = True
                estado['arquivo'] = url
                estado['posicao'] = 1.0
                estado['total'] = 10.0 if 'preroll' in url else 5400.0
                if no_fullscreen:
                    # Comportamento real do Kodi C++: sai do fullscreen para Home!
                    estado['janela'] = 'Home'
                estado['historico_janelas'].append((url, estado['janela']))
            elif cmd == 'ActivateWindow(fullscreenvideo)':
                estado['janela'] = 'fullscreenvideo'
                estado['historico_janelas'].append(('fullscreen', estado['janela']))

        def getCondVisibility(cond):
            if cond == 'Window.IsActive(fullscreenvideo)':
                return estado['janela'] == 'fullscreenvideo'
            return cond in estado['condicoes']

        def getInfoLabel(rotulo):
            return estado['info'].get(rotulo, '')

        def executeJSONRPC(pedido):
            dados = json.loads(pedido)
            if dados.get('method') == 'Player.GetActivePlayers':
                if estado['tocando']:
                    return json.dumps({'result': [{'playerid': 1, 'type': 'video'}]})
                return json.dumps({'result': []})
            if dados.get('method') == 'Player.Seek':
                alvo = dados['params']['value']['seconds']
                estado['posicao'] = float(alvo)
                estado['seeks'].append(float(alvo))
            return json.dumps({'result': 'OK'})

        xbmc = types.ModuleType('xbmc')
        xbmc.Player = FakePlayer
        xbmc.executebuiltin = executebuiltin
        xbmc.getCondVisibility = getCondVisibility
        xbmc.getInfoLabel = getInfoLabel
        xbmc.executeJSONRPC = executeJSONRPC
        xbmc.log = lambda *a, **k: None
        xbmc.sleep = lambda ms: None
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc

        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p.replace('special://profile', self.tmp).replace('special://home', self.tmp)
        vfs.exists = os.path.exists
        vfs.mkdir = lambda p: os.makedirs(p, exist_ok=True)
        sys.modules['xbmcvfs'] = vfs

        addon = types.ModuleType('xbmcaddon')
        addon.Addon = lambda *a, **k: types.SimpleNamespace(
            getSetting=lambda _k: '',
            setSetting=lambda *_a: None,
            getAddonInfo=lambda k: 'service.smarted.bootstrap' if k == 'id' else self.tmp,
        )
        sys.modules['xbmcaddon'] = addon

        gui = types.ModuleType('xbmcgui')
        gui.Dialog = lambda *a, **k: types.SimpleNamespace(
            ok=lambda *x, **y: None, notification=lambda *x, **y: None)
        sys.modules['xbmcgui'] = gui

        sys.path.insert(0, str(BOOTSTRAP))

    def test_1_anuncio_e_filme_tocam_em_tela_cheia_nunca_em_segundo_plano_na_home(self):
        """Reproduz o relato exato do usuario: abrir filme -> anuncio -> filme.
        Nenhum PlayMedia pode levar ',1' (noFullscreen) e a janela permanece
        fullscreenvideo durante o anuncio e apos retomar o filme."""
        vast = _carregar_modulo('ads_vast_t1', BOOTSTRAP / 'ads_vast.py')
        sys.modules['ads_vast'] = vast
        vast._agora = lambda: self.estado['relogio']
        vast.disparar = lambda _urls: 0

        def dormir(_s):
            self.estado['relogio'] += 2.0
            if self.estado['tocando']:
                self.estado['posicao'] += 3.0

        recibo = vast.exibir_e_devolver(
            tag='https://ads.exemplo/vast',
            baixar_tag=lambda _u: VAST_AMOSTRA.encode('utf-8'),
            dormir=dormir,
        )
        self.assertTrue(recibo['exibido'])
        self.assertTrue(recibo.get('conteudo_devolvido'))
        for cmd in self.estado['builtins']:
            if cmd.startswith('PlayMedia('):
                self.assertFalse(cmd.endswith(',1)'),
                                 'PlayMedia com ,1 joga o video para 2o plano na Home: %s' % cmd)
        self.assertEqual(self.estado['janela'], 'fullscreenvideo')
        self.assertEqual(self.estado['arquivo'], 'https://cdn.exemplo/filme-conectado.mp4')
        self.assertIn(42.0, self.estado['seeks'])

    def test_2_reconexao_automatica_quando_stream_perde_conexao_no_anuncio(self):
        """Se a URL temporaria do CDN perder conexao ao ser interrompida pelo
        anuncio, restaurar() reconecta pela rota original plugin:// em tela cheia."""
        vast = _carregar_modulo('ads_vast_t2', BOOTSTRAP / 'ads_vast.py')
        sys.modules['ads_vast'] = vast
        vast._agora = lambda: self.estado['relogio']
        vast.disparar = lambda _urls: 0
        # URL temporaria falha na reabertura; plugin_path reconecta!
        self.estado['falhar_urls'].add('https://cdn.exemplo/filme-conectado.mp4')
        self.estado['janela'] = 'Home'

        def dormir(_s):
            self.estado['relogio'] += 2.0
            if self.estado['tocando']:
                self.estado['posicao'] += 3.0

        recibo = vast.exibir_e_devolver(
            tag='https://ads.exemplo/vast',
            baixar_tag=lambda _u: VAST_AMOSTRA.encode('utf-8'),
            dormir=dormir,
        )
        self.assertTrue(recibo['exibido'])
        self.assertTrue(recibo.get('conteudo_devolvido'))
        self.assertTrue(self.estado['tocando'])
        self.assertEqual(
            self.estado['arquivo'],
            'plugin://plugin.video.BrazucaPlay.Matrix/?mode=1&url=movie123',
        )
        self.assertEqual(self.estado['janela'], 'fullscreenvideo')

    def test_3_celular_720p_usa_admob_sem_vast_e_vip_sincroniza_prazo(self):
        """Celular HD+ 720p usa AdMob (nao VAST), abertura na TV nao toca som
        oculto na Home e VIP vencido grava ativo=false para sincronizar Java."""
        self.estado['condicoes'] = {'System.Platform.Android', 'System.Platform.Android.Mobile'}
        self.estado['info']['System.ScreenHeight'] = '720'
        self.estado['info']['System.FriendlyName'] = 'Moto G'
        variante = _carregar_modulo('variante_t3', BOOTSTRAP / 'variante.py')
        variante.variante_do_arquivo = lambda: None
        sys.modules['variante'] = variante
        self.assertEqual(variante.variante(), 'mobile')

        smart_ads = _carregar_modulo('smart_ads_t3', BOOTSTRAP / 'smart_ads.py')
        self.assertTrue(smart_ads.tocar_anuncio(smart_ads.ATIVIDADE_PREROLL))
        self.assertTrue(any('StartAndroidActivity' in b for b in self.estado['builtins']))

        # Na TV, abertura na Home NUNCA dispara VAST em segundo plano
        smart_ads.e_tv = lambda: True
        self.assertFalse(smart_ads.mostrar_abertura())

        # VIP vencido sincroniza "ativo": false no disco para o Java
        vip = _carregar_modulo('vip_t3', BOOTSTRAP / 'vip.py')
        os.makedirs(os.path.dirname(vip.VIP_JSON), exist_ok=True)
        with open(vip.VIP_JSON, 'w', encoding='utf-8') as f:
            json.dump({'ativo': True, 'expira': '2099-12-31',
                       'expira_em': '2020-01-01T00:00:00Z'}, f)
        self.assertFalse(vip.ativa())
        with open(vip.VIP_JSON, encoding='utf-8') as f:
            gravado = json.load(f)
        self.assertFalse(gravado['ativo'])


# ===========================================================================
# FUNCIONALIDADE 2: Navegacao D-pad da Home (3 testes)
# ===========================================================================
class HomeBarraHeroGradesTest(unittest.TestCase):
    def _raiz(self, skin):
        return ET.parse(ROOT / 'kodi' / skin / 'xml' / 'Home.xml').getroot()

    def test_1_barra_superior_tratada_igual_ao_hero_sem_filhos_presos(self):
        for skin in SKINS:
            raiz = self._raiz(skin)
            barra = raiz.find(".//control[@id='9000']")
            hero = raiz.find(".//control[@id='9300']")
            self.assertEqual(barra.get('type'), 'grouplist')
            self.assertEqual(hero.get('type'), 'grouplist')
            # Nenhum botao filho de 9000 ou 9300 pode prender <onup>/<ondown>
            for container in (barra, hero):
                for botao in container.findall('control'):
                    self.assertIsNone(botao.find('onup'),
                                      '%s: filho %s prende onup' % (skin, botao.get('id')))
                    self.assertIsNone(botao.find('ondown'),
                                      '%s: filho %s prende ondown' % (skin, botao.get('id')))
            # 9000 desce para 9300 e 9300 sobe direto para 9000
            self.assertIn('9300', [(e.text or '').strip() for e in barra.findall('ondown')])
            self.assertIn('9000', [(e.text or '').strip() for e in hero.findall('onup')])

    def test_2_ultima_grade_para_baixo_vai_para_barra_superior_e_nao_para_hero(self):
        for skin in SKINS:
            raiz = self._raiz(skin)
            pares = (('9203', '9000'), ('9220', '9000'),
                     ('9230', '9010'), ('9240', '9020'))
            for grade_id, barra_id in pares:
                grade = raiz.find(".//control[@id='%s']" % grade_id)
                descidas = [(e.text or '').strip() for e in grade.findall('ondown')]
                self.assertEqual(
                    descidas, [barra_id],
                    '%s: ultima grade %s deve descer para %s (estava %s)'
                    % (skin, grade_id, barra_id, descidas),
                )

    def test_3_subida_completa_grades_hero_barra_superior_e_topo(self):
        a = (ROOT / 'kodi' / SKINS[0] / 'xml' / 'Home.xml').read_bytes()
        b = (ROOT / 'kodi' / SKINS[1] / 'xml' / 'Home.xml').read_bytes()
        self.assertEqual(a, b, 'Home.xml divergiu entre as duas skins')
        raiz = self._raiz(SKINS[0])
        up_9203 = [(e.text or '').strip() for e in raiz.find(".//control[@id='9203']").findall('onup')]
        up_9201 = [(e.text or '').strip() for e in raiz.find(".//control[@id='9201']").findall('onup')]
        up_9300 = [(e.text or '').strip() for e in raiz.find(".//control[@id='9300']").findall('onup')]
        up_9000 = [(e.text or '').strip() for e in raiz.find(".//control[@id='9000']").findall('onup')]
        self.assertEqual(up_9203, ['9201', '9300', '9000'])
        self.assertEqual(up_9201, ['9300', '9000'])
        self.assertIn('9000', up_9300)
        self.assertEqual(up_9000, ['9121'])


# ===========================================================================
# FUNCIONALIDADE 3: Filtro de Conteudos acessivel no D-pad (3 testes)
# ===========================================================================
class FiltroConteudoDpadTest(unittest.TestCase):
    def _raiz(self, skin):
        return ET.parse(ROOT / 'kodi' / skin / 'xml' / 'MyVideoNav.xml').getroot()

    def test_1_botoes_do_filtro_tem_ids_inteiros_unicos_focaveis_no_kodi(self):
        for skin in SKINS:
            raiz = self._raiz(skin)
            barra = raiz.find(".//control[@id='9060']")
            self.assertIsNotNone(barra)
            botoes = barra.findall('control')
            self.assertEqual(len(botoes), 6)
            ids = [b.get('id') for b in botoes]
            self.assertTrue(all(i and i.isdigit() for i in ids),
                            '%s: IDs nao numericos quebram o D-pad no Kodi: %s' % (skin, ids))
            self.assertEqual(ids, ['9061', '9062', '9063', '9064', '9065', '9066'])

    def test_2_listas_e_grade_acessam_filtro_por_cima_e_por_baixo_e_voltam(self):
        for skin in SKINS:
            raiz = self._raiz(skin)
            barra = raiz.find(".//control[@id='9060']")
            descidas = [(e.text or '').strip() for e in barra.findall('ondown')]
            self.assertEqual(descidas, ['52', '51', '50'])
            self.assertEqual((barra.findtext('onleft') or '').strip(), '9000')
            self.assertEqual((barra.findtext('onup') or '').strip(), '9000')
            for vista in ('50', '51', '52'):
                ctrl = raiz.find(".//control[@id='%s']" % vista)
                self.assertIn('9060', [(e.text or '').strip() for e in ctrl.findall('onup')])
                self.assertIn('9060', [(e.text or '').strip() for e in ctrl.findall('ondown')])

    def test_3_barra_lateral_e_rodape_alcancam_grade_e_filtros(self):
        a = (ROOT / 'kodi' / SKINS[0] / 'xml' / 'MyVideoNav.xml').read_bytes()
        b = (ROOT / 'kodi' / SKINS[1] / 'xml' / 'MyVideoNav.xml').read_bytes()
        self.assertEqual(a, b, 'MyVideoNav.xml divergiu entre as duas skins')
        raiz = self._raiz(SKINS[0])
        for ident in ('9000', '9050'):
            ctrl = raiz.find(".//control[@id='%s']" % ident)
            direitas = [(e.text or '').strip() for e in ctrl.findall('onright')]
            self.assertEqual(direitas, ['52', '51', '50'])
        self.assertIn('9060', [(e.text or '').strip() for e in raiz.find(".//control[@id='9000']").findall('onup')])


# ===========================================================================
# FUNCIONALIDADE 4: Addons/Elementum + DNS Cloudflare + Servico (3 testes)
# ===========================================================================
class AddonsElementumDnsTest(unittest.TestCase):
    def setUp(self):
        self._mods_antes = dict(sys.modules)
        self._path_antes = list(sys.path)

    def tearDown(self):
        sys.path[:] = self._path_antes
        for k in list(sys.modules):
            if k not in self._mods_antes:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = self._mods_antes[k]

    def test_1_elementum_e_addon_dns_permanecem_intactos_na_limpeza(self):
        tmp = tempfile.mkdtemp(prefix='smarted-addons-')
        try:
            kodi = os.path.join(tmp, '.kodi')
            addons = os.path.join(kodi, 'addons')
            db_dir = os.path.join(kodi, 'userdata', 'Database')
            os.makedirs(addons)
            os.makedirs(db_dir)
            todos = (
                'repository.elementumorg', 'plugin.video.elementum',
                'script.elementum.burst', 'context.elementum', 'addon.dns',
                'plugin.video.BrazucaPlay.Matrix', 'repository.xbmc.org',
                'plugin.video.youtube', 'plugin.program.openwizard',
                'repository.redwizard',
            )
            for nome in todos:
                p = os.path.join(addons, nome)
                os.makedirs(p)
                with open(os.path.join(p, 'addon.xml'), 'w') as f:
                    f.write('<addon id="%s"><extension library="default.py"/></addon>' % nome)
                with open(os.path.join(p, 'default.py'), 'w') as f:
                    f.write('# ok\n')
            con = sqlite3.connect(os.path.join(db_dir, 'Addons33.db'))
            con.execute('CREATE TABLE repo (id INTEGER PRIMARY KEY, addonID TEXT)')
            con.execute('CREATE TABLE addonlinkrepo (id INTEGER, addonID TEXT)')
            for r in ('repository.elementumorg', 'repository.redwizard'):
                con.execute('INSERT INTO repo (addonID) VALUES (?)', (r,))
            con.commit()
            con.close()

            sim = _carregar_modulo('sim_srv', ROOT / 'tools' / 'kodi' / 'simular-servico.py')
            ok, dados = sim.simular(str(BOOTSTRAP))
            self.assertTrue(ok, dados.get('traceback'))
            srv = sys.modules['service']
            srv.xbmc.translatePath = lambda c: c.replace('special://home', kodi)
            srv.xbmcvfs.translatePath = lambda c: c.replace('special://home', kodi)
            srv.limpar_repositorios_de_terceiros(lambda *_a: None)
            restantes = set(os.listdir(addons))
            for preservado in ('repository.elementumorg', 'plugin.video.elementum',
                               'script.elementum.burst', 'context.elementum', 'addon.dns'):
                self.assertIn(preservado, restantes)
            for removido in ('plugin.video.youtube', 'plugin.program.openwizard',
                             'repository.redwizard'):
                self.assertNotIn(removido, restantes)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_2_dns_cloudflare_doh_gravado_em_xml_valido_e_jsonrpc(self):
        tmp = tempfile.mkdtemp(prefix='smarted-dns-')
        try:
            perf = _carregar_modulo('perf_dns', BOOTSTRAP / 'performance.py')
            chamadas = []

            def rpc(method, params=None):
                chamadas.append((method, params))
                if method == 'Settings.GetSettingValue':
                    return {'result': {'value': params.get('setting') and perf.CACHE_SETTINGS.get(params['setting'], True)}}
                return {'result': True}

            res = perf.ensure_performance(tmp, rpc, nome_dispositivo='Smart TV')
            self.assertTrue(res['advancedsettings'])
            self.assertTrue(res['doh_cloudflare'])
            xml_path = os.path.join(tmp, 'userdata', 'advancedsettings.xml')
            raiz = ET.parse(xml_path).getroot()
            self.assertEqual(raiz.findtext('./network/dnsoverhttps'),
                             'https://cloudflare-dns.com/dns-query')
            self.assertTrue(any(
                m == 'Settings.SetSettingValue'
                and p.get('setting') == 'network.dnsoverhttps'
                and p.get('value') == 'https://cloudflare-dns.com/dns-query'
                for m, p in chamadas
            ))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_3_servico_bootstrap_importa_limpo_com_todos_os_modulos(self):
        sim = _carregar_modulo('sim_srv2', ROOT / 'tools' / 'kodi' / 'simular-servico.py')
        ok, dados = sim.simular(str(BOOTSTRAP))
        self.assertTrue(ok, dados.get('traceback'))


if __name__ == '__main__':
    unittest.main()
