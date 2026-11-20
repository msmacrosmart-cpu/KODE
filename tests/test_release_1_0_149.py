# -*- coding: utf-8 -*-
"""Suíte objetiva da release 1.0.149 — exatamente 3 testes por funcionalidade:

1. Validação do código VIP (erro no último dígito seguido do código certo +
   aceitação em maiúsculas e minúsculas);
2. Remoção exclusiva de YouTube e MP3 Streams mantendo todos os demais addons
   e preservando a integridade binária de classes4.dex / skins;
3. 2º vídeo com anúncio sem congelar (MP4 prioritário, RepeatOff, worker thread
   e watchdog de travamento);
4. TV ao vivo com anúncios igual aos filmes/séries (sem player parado de 30s e
   sem sair do canal mesmo quando o proxy LAN temporário do Brazuca fecha).
"""
import hashlib
import importlib.util
import io
import json
import os
import shutil
import socket
import sqlite3
import struct
import sys
import tempfile
import time
import types
import unittest
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
WELCOME = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome' / 'default.py'
EMPACTADOR = ROOT / 'tools' / 'kodi' / 'atualizar-apk-v17.py'
VERIFICADOR = ROOT / 'smartedtv' / 'release' / 'verify.py'


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _string_encoder_brazuca(texto):
    return ''.join('%' + hex(ord(c))[2:] for c in texto)


VAST_MIX_WEBM_MP4 = '''<?xml version="1.0" encoding="UTF-8"?>
<VAST version="3.0">
  <Ad id="ad-mix">
    <InLine>
      <AdSystem>Hilltop</AdSystem>
      <AdTitle>Spot</AdTitle>
      <Impression><![CDATA[https://ads.exemplo/imp]]></Impression>
      <Creatives>
        <Creative id="c1">
          <Linear>
            <Duration>00:00:30</Duration>
            <TrackingEvents>
              <Tracking event="start"><![CDATA[https://ads.exemplo/start]]></Tracking>
              <Tracking event="complete"><![CDATA[https://ads.exemplo/complete]]></Tracking>
            </TrackingEvents>
            <MediaFiles>
              <MediaFile type="video/webm" width="1920" height="1080">
                <![CDATA[https://ads.exemplo/congelava-1080.webm]]>
              </MediaFile>
              <MediaFile type="video/mp4" width="1280" height="720">
                <![CDATA[https://ads.exemplo/estavel-720.mp4]]>
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>
'''


def _criar_dex_sintetico(strings_ordenadas):
    """Gera um arquivo DEX mínimo válido com string_ids ordenados, SHA-1 e Adler-32."""
    # Formato DEX: header de 112 bytes + string_ids + string_data
    itens_dados = []
    for s in strings_ordenadas:
        raw = s.encode('ascii')
        assert len(raw) < 128
        itens_dados.append(bytes([len(raw)]) + raw + b'\x00')
    n = len(strings_ordenadas)
    header_size = 0x70
    table_off = header_size
    data_off = table_off + 4 * n
    offsets = []
    cursor = data_off
    bloco_dados = bytearray()
    for item in itens_dados:
        offsets.append(cursor)
        bloco_dados.extend(item)
        cursor += len(item)
    total_size = cursor
    dex = bytearray(header_size)
    dex[0:8] = b'dex\n035\x00'
    struct.pack_into('<I', dex, 32, total_size)
    struct.pack_into('<I', dex, 36, header_size)
    struct.pack_into('<I', dex, 40, 0x12345678)
    struct.pack_into('<II', dex, 56, n, table_off)
    tabela = b''.join(struct.pack('<I', off) for off in offsets)
    corpo = bytes(dex) + tabela + bytes(bloco_dados)
    mutavel = bytearray(corpo)
    mutavel[12:32] = hashlib.sha1(memoryview(mutavel)[32:]).digest()
    adler = zlib.adler32(memoryview(mutavel)[12:]) & 0xFFFFFFFF
    struct.pack_into('<I', mutavel, 8, adler)
    return bytes(mutavel)


# ===========================================================================
# 1. VALIDAÇÃO DO CÓDIGO VIP (3 testes)
# ===========================================================================
class VipValidacaoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='smarted-vip149-')
        self.salvos = {k: sys.modules.get(k)
                       for k in ('xbmc', 'xbmcvfs', 'xbmcgui', 'xbmcaddon', 'vip')}
        self._props = {}
        xbmc = types.ModuleType('xbmc')
        xbmc.log = lambda *a, **k: None
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        xbmc.getCondVisibility = lambda _c: False
        xbmc.executebuiltin = lambda _c: None
        sys.modules['xbmc'] = xbmc

        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p.replace('special://profile', self.tmp).replace('special://home', self.tmp)
        vfs.exists = os.path.exists
        vfs.mkdirs = lambda p: os.makedirs(p, exist_ok=True)
        sys.modules['xbmcvfs'] = vfs

        props = self._props

        class FakeWindow(object):
            def __init__(self, *_a, **_k):
                pass

            def getProperty(self, k):
                return props.get(k, '')

            def setProperty(self, k, v):
                props[k] = str(v)

            def clearProperty(self, k):
                props.pop(k, None)

        class FakeWindowXMLDialog(object):
            def __init__(self, *_a, **_k):
                self._p = {}

            def setProperty(self, k, v):
                self._p[k] = str(v)

            def getProperty(self, k):
                return self._p.get(k, '')

            def clearProperty(self, k):
                self._p.pop(k, None)

            def close(self):
                pass

        gui = types.ModuleType('xbmcgui')
        gui.Window = FakeWindow
        gui.WindowXMLDialog = FakeWindowXMLDialog
        gui.ACTION_NAV_BACK = 92
        gui.ACTION_PREVIOUS_MENU = 10
        gui.Dialog = lambda *a, **k: types.SimpleNamespace(
            ok=lambda *x, **y: None,
            notification=lambda *x, **y: None,
            input=lambda *x, **y: '',
        )
        sys.modules['xbmcgui'] = gui

        addon = types.ModuleType('xbmcaddon')
        addon.Addon = lambda *a, **k: types.SimpleNamespace(
            getAddonInfo=lambda ch: self.tmp if ch in ('path', 'profile') else '1.0.149',
            getSetting=lambda _k: '',
            setSetting=lambda *_a: None,
        )
        sys.modules['xbmcaddon'] = addon

        if str(BOOTSTRAP) not in sys.path:
            sys.path.insert(0, str(BOOTSTRAP))
        self.vip = _carregar('vip_149', BOOTSTRAP / 'vip.py')
        sys.modules['vip'] = self.vip

    def tearDown(self):
        if str(BOOTSTRAP) in sys.path:
            sys.path.remove(str(BOOTSTRAP))
        for k, mod in self.salvos.items():
            if mod is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = mod
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_ultimo_numero_errado_depois_certo_aprova_sem_contaminar_cookie_nem_ui(self):
        """Reproduz exatamente o relato do usuário:
        1ª tentativa com último dígito trocado falha (404 com Set-Cookie sujo);
        2ª tentativa com o último dígito correto aprova imediatamente."""
        chamadas = []

        def servidor_realista(url, payload, cookie=None, timeout=12):
            chamadas.append((payload.get('code'), cookie))
            # Se um cookie sujo da tentativa errada tivesse sido salvo, o backend
            # bloquearia; além disso testamos também o retry sem cookie!
            if cookie == 'cookie-tentativa-errada':
                return (403, {'Set-Cookie': 'smartedtv_device=cookie-tentativa-errada; Path=/'},
                        json.dumps({'valid': False, 'message': 'Sessão bloqueada por tentativa inválida'}), url)
            if payload.get('code') == 'SMTV-2026-9998':
                return (404, {'Set-Cookie': 'smartedtv_device=cookie-tentativa-errada; Path=/'},
                        json.dumps({'active': False, 'message': 'Código não encontrado'}), url)
            if payload.get('code') == 'SMTV-2026-9999':
                return (200, {'Set-Cookie': 'smartedtv_device=cookie-valido-ok; Path=/'},
                        json.dumps({'valid': True, 'active': True, 'plan': 'mensal',
                                    'expires_at': '2027-01-15T00:00:00Z'}), url)
            return (404, {}, json.dumps({'active': False}), url)

        self.vip._post_json = servidor_realista

        # 1ª tentativa: último dígito errado ('8' em vez de '9')
        ok1, msg1 = self.vip.validar('SMTV-2026-9998')
        self.assertFalse(ok1)
        self.assertFalse(os.path.exists(self.vip._COOKIE),
                         'Erro 4xx NUNCA pode gravar device-cookie.txt')

        # Mesmo que já existisse cookie velho/preso no disco de versão anterior,
        # a 2ª tentativa com o número certo refaz sem cookie e aprova!
        os.makedirs(os.path.dirname(self.vip._COOKIE), exist_ok=True)
        with open(self.vip._COOKIE, 'w', encoding='utf-8') as f:
            f.write('cookie-tentativa-errada')

        ok2, msg2 = self.vip.validar('SMTV-2026-9999')
        self.assertTrue(ok2, msg2)
        self.assertTrue(self.vip.ativa())
        with open(self.vip._COOKIE, encoding='utf-8') as f:
            self.assertEqual(f.read().strip(), 'cookie-valido-ok')

        # Também valida a UI (DialogWelcome): após código recusado, clicar em
        # Ativar abre o teclado para corrigir o dígito em vez de reenviar o errado!
        welcome = _carregar('welcome_149', WELCOME)
        janela = welcome.WelcomeDialog('DialogWelcomeTV.xml', self.tmp, 'Default', '1080i')
        texto_campo = ['SMTV-2026-9998']
        foco = [311]
        janela.getControl = lambda cid: types.SimpleNamespace(
            getText=lambda: texto_campo[0],
            setText=lambda novo: texto_campo.__setitem__(0, novo),
        ) if cid == 310 else types.SimpleNamespace(setLabel=lambda *_: None)
        janela.setFocusId = lambda cid: foco.__setitem__(0, cid)
        janela._status = lambda *a, **k: None
        teclado_entradas = iter(['SMTV-2026-9999'])
        sys.modules['xbmcgui'].INPUT_ALPHANUM = 0
        sys.modules['xbmcgui'].Dialog = lambda *a, **k: types.SimpleNamespace(
            input=lambda *_a, **_k: next(teclado_entradas, ''),
            ok=lambda *_a, **_k: None,
            notification=lambda *_a, **_k: None,
        )
        # 1º clique em 311: rejeita 9998; ao fechar o diálogo (955), foco vai para 310!
        janela._ativar_codigo()
        janela.onClick(955)
        self.assertEqual(foco[0], 310)
        self.assertEqual(janela._codigo_recusado, 'SMTV-2026-9998')
        # 2º clique em 311 ainda com 9998 no campo: abre o teclado, recebe 9999 e aprova!
        janela._ativar_codigo()
        self.assertEqual(janela._codigo_recusado, '')
        self.assertEqual(janela.getProperty('welcome_status_action'), 'home')

    def test_2_codigo_funciona_em_maiusculas_e_minusculas_com_hifens_e_espacos(self):
        """Mesmo que o cliente receba em MAIÚSCULO, digitar em minúsculas
        (ou misturado, com espaços/travessão Unicode) funciona igual antes."""
        recebidos = []

        def servidor(url, payload, cookie=None, timeout=12):
            recebidos.append(payload.get('code'))
            if payload.get('code') == 'VIP9-ABCD-2026':
                return (200, {'Set-Cookie': 'smartedtv_device=dev1; Path=/'},
                        json.dumps({'valid': True, 'active': True,
                                    'expires_at': '2027-06-01T00:00:00Z'}), url)
            return (404, {}, json.dumps({'valid': False, 'message': 'Código inválido'}), url)

        self.vip._post_json = servidor
        for entrada in ('VIP9-ABCD-2026', 'vip9-abcd-2026', '  Vip9 – abcd — 2026\u200b '):
            if os.path.exists(self.vip.VIP_JSON):
                os.remove(self.vip.VIP_JSON)
            ok, msg = self.vip.validar(entrada)
            self.assertTrue(ok, f'Falhou para entrada {entrada!r}: {msg}')
            self.assertTrue(self.vip.ativa())
        self.assertTrue(all(c == 'VIP9-ABCD-2026' for c in recebidos), recebidos)

    def test_3_codigo_customizado_minusculo_no_banco_e_codigo_invalido_recusado(self):
        """Se um código customizado estiver gravado em minúsculo no banco, o
        fallback tenta lowercase; e código inexistente continua recusado."""
        def servidor(url, payload, cookie=None, timeout=12):
            if payload.get('code') == 'cliente-vip-77':
                return (200, {}, json.dumps({'valid': True, 'active': True,
                                             'expires_at': '2027-03-01T00:00:00Z'}), url)
            return (404, {}, json.dumps({'active': False, 'message': 'Código não encontrado'}), url)

        self.vip._post_json = servidor
        ok_invalido, msg_invalido = self.vip.validar('XXXX-0000')
        self.assertFalse(ok_invalido)
        self.assertIn('não é válido', msg_invalido)
        self.assertEqual(self.vip.estado(), {})

        ok_custom, msg_custom = self.vip.validar('Cliente-Vip-77')
        self.assertTrue(ok_custom, msg_custom)
        self.assertTrue(self.vip.ativa())


# ===========================================================================
# 2. REMOÇÃO EXCLUSIVA DE YOUTUBE E MP3 STREAMS (3 testes)
# ===========================================================================
class RemocaoYoutubeMp3StreamsTest(unittest.TestCase):
    def _criar_addons_db_bytes(self):
        fd, caminho = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        try:
            con = sqlite3.connect(caminho)
            con.executescript('''
                CREATE TABLE installed (addonID TEXT, enabled INTEGER, origin TEXT);
                CREATE TABLE addons (addonID TEXT, name TEXT);
                CREATE TABLE addonlinkrepo (idRepo INTEGER, idAddon INTEGER);
                CREATE TABLE repo (id INTEGER, addonID TEXT);
                CREATE TABLE package (addonID TEXT, filename TEXT);
                INSERT INTO installed VALUES ('plugin.video.youtube', 1, 'b29c3024-88f1-4a7a-9799-a086f9b623b9');
                INSERT INTO installed VALUES ('plugin.audio.mp3streams', 1, 'b29c3024-88f1-4a7a-9799-a086f9b623b9');
                INSERT INTO installed VALUES ('plugin.video.BrazucaPlay.Matrix', 1, '');
                INSERT INTO installed VALUES ('plugin.video.elementum', 1, '');
                INSERT INTO addons VALUES ('plugin.video.youtube', 'YouTube');
                INSERT INTO addons VALUES ('plugin.audio.mp3streams', 'MP3 Streams');
                INSERT INTO addons VALUES ('plugin.video.BrazucaPlay.Matrix', 'Brazuca Play');
                INSERT INTO addons VALUES ('plugin.video.elementum', 'Elementum');
                INSERT INTO package VALUES ('plugin.video.youtube', 'plugin.video.youtube-7.0.zip');
                INSERT INTO package VALUES ('plugin.audio.mp3streams', 'plugin.audio.mp3streams-1.0.zip');
            ''')
            con.commit()
            con.close()
            return Path(caminho).read_bytes()
        finally:
            if os.path.exists(caminho):
                os.remove(caminho)

    def test_1_empacotador_e_verify_removem_youtube_e_mp3streams_mantendo_dex_e_demais_addons(self):
        """atualizar-apk-v17.py expurga YouTube e MP3 Streams do perfil e do banco,
        recalcula o pin SHA-256 de profile-manifest.txt preservando a ordem de
        string_ids do classes4.dex, e passa na validação completa de verify.py."""
        atu = _carregar('atu_149', EMPACTADOR)
        ver = _carregar('ver_149', VERIFICADOR)

        db_sujo = self._criar_addons_db_bytes()
        arquivos_perfil = {
            'addons/plugin.video.youtube/addon.xml': b'<addon id="plugin.video.youtube"/>',
            'addons/plugin.audio.mp3streams/addon.xml': b'<addon id="plugin.audio.mp3streams"/>',
            'addons/plugin.video.BrazucaPlay.Matrix/addon.xml': b'<addon id="plugin.video.BrazucaPlay.Matrix"/>',
            'addons/plugin.video.elementum/addon.xml': b'<addon id="plugin.video.elementum"/>',
            'userdata/addon_data/plugin.video.youtube/settings.xml': b'<settings/>',
            'userdata/addon_data/plugin.audio.mp3streams/settings.xml': b'<settings/>',
            'userdata/Database/Addons33.db': db_sujo,
        }
        # Pelo menos 12 entradas no manifesto para permutação rápida de prefixo
        for idx in range(12):
            arquivos_perfil[f'userdata/extra_{idx:02d}.xml'] = f'<x i="{idx}"/>'.encode('utf-8')

        linhas_manifesto = []
        for rel in sorted(arquivos_perfil):
            b = arquivos_perfil[rel]
            linhas_manifesto.append(f'{hashlib.sha256(b).hexdigest()}\t{len(b)}\t{rel}\n')
        base_manifest = ''.join(linhas_manifesto).encode('utf-8')
        pin_base = hashlib.sha256(base_manifest).hexdigest()

        # Strings vizinhas reais de classes4.dex ('10' < pin_base < ': ')
        strings = sorted(['0', '10', pin_base, ': ', 'ProfileDirectorySeed', 'org/smartedtv'])
        base_dex = _criar_dex_sintetico(strings)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('classes4.dex', base_dex)
            zf.writestr('assets/smarted/profile-manifest.txt', base_manifest)
            for rel, b in arquivos_perfil.items():
                zf.writestr(f'assets/smarted/profile/{rel}', b)
        buf.seek(0)

        with zipfile.ZipFile(buf, 'r') as origem:
            excluidos, modificados = atu.preparar_perfil_limpo(origem)

        self.assertIn('assets/smarted/profile/addons/plugin.video.youtube/addon.xml', excluidos)
        self.assertIn('assets/smarted/profile/addons/plugin.audio.mp3streams/addon.xml', excluidos)
        self.assertNotIn('assets/smarted/profile/addons/plugin.video.BrazucaPlay.Matrix/addon.xml', excluidos)
        self.assertNotIn('assets/smarted/profile/addons/plugin.video.elementum/addon.xml', excluidos)

        novo_manifest = modificados['assets/smarted/profile-manifest.txt']
        novo_dex = modificados['classes4.dex']
        self.assertNotIn(b'plugin.video.youtube', novo_manifest)
        self.assertNotIn(b'plugin.audio.mp3streams', novo_manifest)
        self.assertIn(b'plugin.video.BrazucaPlay.Matrix', novo_manifest)
        self.assertIn(b'plugin.video.elementum', novo_manifest)

        # Valida integridade binária do classes4.dex com a mesma função do CI!
        ver.verificar_classes4_dex(base_dex, novo_dex, base_manifest, novo_manifest)

        # Confirma que Addons33.db ficou sem youtube/mp3streams mas manteve Brazuca e Elementum
        fd, db_limpo_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        try:
            Path(db_limpo_path).write_bytes(modificados['assets/smarted/profile/userdata/Database/Addons33.db'])
            con = sqlite3.connect(db_limpo_path)
            ids_inst = {r[0] for r in con.execute('SELECT addonID FROM installed')}
            con.close()
            self.assertNotIn('plugin.video.youtube', ids_inst)
            self.assertNotIn('plugin.audio.mp3streams', ids_inst)
            self.assertEqual(ids_inst, {'plugin.video.BrazucaPlay.Matrix', 'plugin.video.elementum'})
        finally:
            os.remove(db_limpo_path)

    def test_2_bootstrap_service_desativa_e_expurga_youtube_e_mp3streams_no_upgrade(self):
        """Em aparelhos que atualizarem por cima de versão anterior, service.py
        desativa via JSON-RPC e apaga pastas, pacotes e registros SQLite apenas
        de YouTube e MP3 Streams, preservando Brazuca e Elementum."""
        tmp = tempfile.mkdtemp(prefix='smarted-svc149-')
        salvos = {k: sys.modules.get(k) for k in ('xbmc', 'xbmcvfs', 'xbmcgui', 'xbmcaddon')}
        try:
            rpcs = []
            xbmc = types.ModuleType('xbmc')
            xbmc.log = lambda *a, **k: None
            xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
            xbmc.executebuiltin = lambda _c: None
            xbmc.getCondVisibility = lambda _c: False
            xbmc.executeJSONRPC = lambda p: (rpcs.append(json.loads(p)) or '{"result":"OK"}')
            xbmc.Monitor = object
            xbmc.Player = object
            sys.modules['xbmc'] = xbmc

            vfs = types.ModuleType('xbmcvfs')
            vfs.translatePath = lambda p: (
                p.replace('special://home/', tmp + '/')
                 .replace('special://home', tmp)
                 .replace('special://profile/', tmp + '/userdata/')
                 .replace('special://profile', tmp + '/userdata')
            )
            vfs.exists = os.path.exists
            sys.modules['xbmcvfs'] = vfs
            sys.modules['xbmcgui'] = types.SimpleNamespace(Dialog=lambda: None)
            sys.modules['xbmcaddon'] = types.SimpleNamespace(
                Addon=lambda *a, **k: types.SimpleNamespace(
                    getAddonInfo=lambda ch: 'service.smarted.bootstrap' if ch == 'id' else tmp,
                    getSetting=lambda _k: '',
                )
            )

            for pasta in (
                'addons/plugin.video.youtube',
                'addons/plugin.audio.mp3streams',
                'addons/plugin.video.BrazucaPlay.Matrix',
                'addons/plugin.video.elementum',
                'addons/packages',
                'userdata/addon_data/plugin.video.youtube',
                'userdata/Database',
            ):
                os.makedirs(os.path.join(tmp, pasta), exist_ok=True)
            Path(tmp, 'addons/packages/plugin.video.youtube-7.0.zip').write_bytes(b'zip')
            Path(tmp, 'userdata/Database/Addons33.db').write_bytes(self._criar_addons_db_bytes())

            if str(BOOTSTRAP) not in sys.path:
                sys.path.insert(0, str(BOOTSTRAP))
            svc = _carregar('svc_149', BOOTSTRAP / 'service.py')
            svc.limpar_repositorios_de_terceiros()

            self.assertFalse(os.path.exists(os.path.join(tmp, 'addons/plugin.video.youtube')))
            self.assertFalse(os.path.exists(os.path.join(tmp, 'addons/plugin.audio.mp3streams')))
            self.assertFalse(os.path.exists(os.path.join(tmp, 'addons/packages/plugin.video.youtube-7.0.zip')))
            self.assertTrue(os.path.exists(os.path.join(tmp, 'addons/plugin.video.BrazucaPlay.Matrix')))
            self.assertTrue(os.path.exists(os.path.join(tmp, 'addons/plugin.video.elementum')))
            desabilitados = [r['params']['addonid'] for r in rpcs
                             if r.get('method') == 'Addons.SetAddonEnabled']
            self.assertIn('plugin.video.youtube', desabilitados)
            self.assertIn('plugin.audio.mp3streams', desabilitados)

            con = sqlite3.connect(os.path.join(tmp, 'userdata/Database/Addons33.db'))
            restantes = {r[0] for r in con.execute('SELECT addonID FROM installed')}
            con.close()
            self.assertEqual(restantes, {'plugin.video.BrazucaPlay.Matrix', 'plugin.video.elementum'})
        finally:
            for k, mod in salvos.items():
                if mod is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = mod
            shutil.rmtree(tmp, ignore_errors=True)

    def test_3_skins_espelhadas_sem_atalho_instalador_youtube_e_sem_regressao_nav(self):
        """As duas skins permanecem idênticas, sem InstallAddon(plugin.video.youtube),
        e preservam intactos Home.xml e MyVideoNav.xml da 1.0.148."""
        for arq in ('Custom_1107_SearchDialog.xml', 'Home.xml', 'MyVideoNav.xml'):
            c1 = (ROOT / 'kodi/skin.estilo.personalizado/xml' / arq).read_text(encoding='utf-8')
            c2 = (ROOT / 'kodi/skin.novatv/xml' / arq).read_text(encoding='utf-8')
            self.assertEqual(c1, c2, f'Divergência entre skins em {arq}')
            ET.fromstring(c1)
        busca = (ROOT / 'kodi/skin.novatv/xml/Custom_1107_SearchDialog.xml').read_text(encoding='utf-8')
        self.assertNotIn('InstallAddon(plugin.video.youtube)', busca)


# ===========================================================================
# 3. 2º VÍDEO COM ANÚNCIO SEM CONGELAR A TELA (3 testes)
# ===========================================================================
class SegundoVideoSemCongelarTest(unittest.TestCase):
    def setUp(self):
        self.salvos = {k: sys.modules.get(k)
                       for k in ('xbmc', 'xbmcvfs', 'xbmcaddon', 'xbmcgui',
                                 'ads_vast', 'ads_regra', 'variante', 'ao_vivo', 'smart_ads')}
        self._instalar_kodi()

    def tearDown(self):
        if str(BOOTSTRAP) in sys.path:
            sys.path.remove(str(BOOTSTRAP))
        for k, mod in self.salvos.items():
            if mod is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = mod

    def _instalar_kodi(self):
        st = {
            'tocando': False,
            'arquivo': '',
            'posicao': 0.0,
            'total': 0.0,
            'repeat': 'Off',
            'janela': 'Home',
            'relogio': 1000.0,
            'builtins': [],
            'seeks': [],
            'congelar_url': set(),
            'condicoes': {'System.Platform.Android', 'System.Platform.Android.TV'},
            'info': {'Player.Filenameandpath': ''},
        }
        self.st = st

        class FakePlayer(object):
            def __init__(self, *a, **k):
                pass

            def isPlayingVideo(self):
                return st['tocando']

            def getPlayingFile(self):
                return st['arquivo']

            def getTime(self):
                return st['posicao']

            def getTotalTime(self):
                return st['total']

            def seekTime(self, s):
                st['posicao'] = float(s)
                st['seeks'].append(float(s))

        def executebuiltin(cmd):
            st['builtins'].append(cmd)
            if cmd == 'PlayerControl(RepeatOff)':
                st['repeat'] = 'Off'
            elif cmd == 'PlayerControl(RepeatOne)':
                st['repeat'] = 'One'
            elif cmd == 'ActivateWindow(fullscreenvideo)':
                st['janela'] = 'fullscreenvideo'
            elif cmd.startswith('PlayMedia('):
                url = cmd.split('"', 2)[1]
                # Se WebM fosse escolhido na TV Box, congelaria!
                if url.endswith('.webm'):
                    st['congelar_url'].add(url)
                st['arquivo'] = url
                st['tocando'] = True
                st['posicao'] = 0.0 if url in st['congelar_url'] else 1.0
                st['total'] = 30.0 if 'ads.exemplo' in url else 5400.0
                st['janela'] = 'fullscreenvideo'

        def getCondVisibility(c):
            if c == 'Window.IsActive(fullscreenvideo)':
                return st['janela'] == 'fullscreenvideo'
            return c in st['condicoes']

        def executeJSONRPC(pedido):
            dados = json.loads(pedido)
            m = dados.get('method')
            if m == 'Player.GetActivePlayers':
                return json.dumps({'result': [{'playerid': 1, 'type': 'video'}] if st['tocando'] else []})
            if m == 'Player.Seek':
                alvo = float(dados['params']['value']['seconds'])
                st['posicao'] = alvo
                st['seeks'].append(alvo)
            return json.dumps({'result': 'OK'})

        xbmc = types.ModuleType('xbmc')
        xbmc.Player = FakePlayer
        xbmc.executebuiltin = executebuiltin
        xbmc.getCondVisibility = getCondVisibility
        xbmc.getInfoLabel = lambda r: st['info'].get(r, '')
        xbmc.executeJSONRPC = executeJSONRPC
        xbmc.log = lambda *a, **k: None
        xbmc.sleep = lambda _ms: None
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc
        sys.modules['xbmcvfs'] = types.SimpleNamespace(
            translatePath=lambda p: p, exists=lambda _p: False)
        sys.modules['xbmcaddon'] = types.SimpleNamespace(
            Addon=lambda *a, **k: types.SimpleNamespace(
                getSetting=lambda _k: '', getAddonInfo=lambda _k: 'service.smarted.bootstrap'))
        sys.modules['xbmcgui'] = types.SimpleNamespace(
            Dialog=lambda: types.SimpleNamespace(ok=lambda *a, **k: None, notification=lambda *a, **k: None))
        if str(BOOTSTRAP) not in sys.path:
            sys.path.insert(0, str(BOOTSTRAP))

    def test_1_dois_videos_seguidos_com_anuncio_priorizam_mp4_desligam_repeat_e_retomam(self):
        """1º filme com anúncio + 2º filme com anúncio: escolhe MP4 (nunca WebM),
        desliga RepeatOne antes do anúncio e devolve ambos os filmes em tela cheia."""
        vast = _carregar('vast_v2_1', BOOTSTRAP / 'ads_vast.py')
        sys.modules['ads_vast'] = vast
        vast._agora = lambda: self.st['relogio']
        vast.disparar = lambda _u: 0

        def dormir(_s):
            self.st['relogio'] += 1.0
            if self.st['tocando'] and self.st['arquivo'] not in self.st['congelar_url']:
                self.st['posicao'] += 8.0

        # 1º vídeo com anúncio
        self.st.update({'tocando': True, 'arquivo': 'https://cdn.exemplo/filme-1.mp4',
                        'posicao': 35.0, 'total': 5400.0, 'repeat': 'One', 'janela': 'fullscreenvideo'})
        r1 = vast.exibir_e_devolver(
            tag='https://ads.exemplo/vast',
            baixar_tag=lambda _u: VAST_MIX_WEBM_MP4.encode('utf-8'),
            dormir=dormir,
        )
        self.assertTrue(r1['exibido'])
        self.assertTrue(r1.get('conteudo_devolvido'))
        self.assertEqual(self.st['repeat'], 'Off')
        self.assertEqual(self.st['arquivo'], 'https://cdn.exemplo/filme-1.mp4')
        self.assertEqual(self.st['janela'], 'fullscreenvideo')

        # 2º vídeo com anúncio (após intervalo de 2 min)
        self.st.update({'tocando': True, 'arquivo': 'https://cdn.exemplo/filme-2.mp4',
                        'posicao': 90.0, 'total': 5400.0, 'janela': 'fullscreenvideo'})
        r2 = vast.exibir_e_devolver(
            tag='https://ads.exemplo/vast',
            baixar_tag=lambda _u: VAST_MIX_WEBM_MP4.encode('utf-8'),
            dormir=dormir,
        )
        self.assertTrue(r2['exibido'])
        self.assertTrue(r2.get('conteudo_devolvido'))
        self.assertEqual(self.st['arquivo'], 'https://cdn.exemplo/filme-2.mp4')
        self.assertEqual(self.st['janela'], 'fullscreenvideo')
        self.assertIn(90.0, self.st['seeks'])
        self.assertFalse(any('.webm' in b for b in self.st['builtins']),
                         'Nunca deve escolher WebM quando há MP4 compatível')

    def test_2_watchdog_destrava_segundo_anuncio_congelado_em_6s(self):
        """Se o servidor VAST mandar um criativo corrompido que trava o quadro
        no 2º anúncio, o watchdog corta em ~6s e devolve o 2º filme na hora."""
        vast = _carregar('vast_v2_2', BOOTSTRAP / 'ads_vast.py')
        sys.modules['ads_vast'] = vast
        vast._agora = lambda: self.st['relogio']
        vast.disparar = lambda _u: 0
        self.st['congelar_url'].add('https://ads.exemplo/estavel-720.mp4')
        self.st.update({'tocando': True, 'arquivo': 'https://cdn.exemplo/segundo-filme.mp4',
                        'posicao': 64.0, 'total': 3600.0, 'janela': 'fullscreenvideo'})

        def dormir(_s):
            self.st['relogio'] += 1.0
            if self.st['tocando'] and self.st['arquivo'] not in self.st['congelar_url']:
                self.st['posicao'] += 5.0

        inicio = self.st['relogio']
        recibo = vast.exibir_e_devolver(
            tag='https://ads.exemplo/vast',
            baixar_tag=lambda _u: VAST_MIX_WEBM_MP4.encode('utf-8'),
            dormir=dormir,
        )
        duracao_gasta = self.st['relogio'] - inicio
        self.assertTrue(recibo.get('conteudo_devolvido'))
        self.assertLessEqual(recibo['segundos'], 8.0,
                             f'Anúncio travado não pode prender por 30s (levou {duracao_gasta}s)')
        self.assertEqual(self.st['arquivo'], 'https://cdn.exemplo/segundo-filme.mp4')
        self.assertEqual(self.st['janela'], 'fullscreenvideo')

    def test_3_monitor_preroll_roda_vast_em_worker_thread_sem_bloquear_onavstarted(self):
        """No Android TV real, _disparar não bloqueia a thread de callback do Kodi
        e protege contra reentrância na volta do 2º vídeo."""
        vast = _carregar('vast_v2_3', BOOTSTRAP / 'ads_vast.py')
        sys.modules['ads_vast'] = vast
        smart_ads = _carregar('smart_ads_v2_3', BOOTSTRAP / 'smart_ads.py')
        smart_ads.e_tv = lambda: True
        smart_ads.android = lambda: True

        terminou = []

        def anuncio_lento(_ativ, _log=None, _uri=''):
            time.sleep(0.12)
            terminou.append(True)
            return True

        smart_ads.abrir_anuncio = anuncio_lento
        self.st.update({'tocando': True, 'arquivo': 'https://cdn.exemplo/ep2.mp4',
                        'posicao': 5.0, 'total': 1800.0, 'janela': 'fullscreenvideo'})
        monitor = smart_ads.MonitorPreRoll()
        t0 = time.monotonic()
        disparou = monitor._disparar(smart_ads.ATIVIDADE_PREROLL, None)
        dt = time.monotonic() - t0
        self.assertTrue(disparou)
        self.assertLess(dt, 0.06, 'onAVStarted não pode ficar bloqueado esperando o anúncio')
        # Enquanto a worker thread está rodando, novo disparo é bloqueado (_em_vast=True)
        self.assertFalse(monitor._disparar(smart_ads.ATIVIDADE_PREROLL, None))
        time.sleep(0.20)
        self.assertEqual(terminou, [True])
        self.assertFalse(monitor._em_vast)
        self.assertGreater(monitor._ate_ignorar_volta_vast, time.monotonic())


# ===========================================================================
# 4. TV AO VIVO COM ANÚNCIOS SEM PLAYER DE 30S PARADO E SEM SAIR DO CANAL (3 testes)
# ===========================================================================
class TvAoVivoComAnunciosTest(unittest.TestCase):
    def setUp(self):
        self.salvos = {k: sys.modules.get(k)
                       for k in ('xbmc', 'xbmcvfs', 'xbmcaddon', 'xbmcgui',
                                 'ads_vast', 'ao_vivo', 'ad_return')}
        # Escolhe uma porta local garantidamente FECHADA para simular o proxy
        # temporário do Brazuca (codec.py) que encerra ao abrir o anúncio
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        self.porta_morta = s.getsockname()[1]
        s.close()

        self.url_stream_real = (
            'http://s.apkwuv.xyz/live/demopadexchange/demopad/globo_sp.m3u8'
            '|User-Agent=Dalvik/2.1.0&Referer=https%3A%2F%2Fexemplo.tv%2F'
        )
        # Formato EXATO do Brazuca Play (codec.URL_PROXY + string_encoder(url)) em IP LAN
        self.url_proxy_brazuca = (
            f'http://127.0.0.1:{self.porta_morta}/?url='
            + _string_encoder_brazuca(self.url_stream_real)
        )
        self._instalar_kodi_ao_vivo()

    def tearDown(self):
        if str(BOOTSTRAP) in sys.path:
            sys.path.remove(str(BOOTSTRAP))
        for k, mod in self.salvos.items():
            if mod is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = mod

    def _instalar_kodi_ao_vivo(self):
        porta_morta = self.porta_morta
        st = {
            'tocando': True,
            'arquivo': self.url_proxy_brazuca,
            'posicao': 12.0,
            'total': 30.0,  # janela deslizante HLS ao vivo frequentemente informa 30s!
            'janela': 'fullscreenvideo',
            'relogio': 500.0,
            'builtins': [],
            'seeks': [],
            'anuncio_parado_30s': False,
            'abriu_menu_opcoes': False,
        }
        self.st = st

        class FakePlayer(object):
            def __init__(self, *a, **k):
                pass

            def isPlayingVideo(self):
                return st['tocando']

            def getPlayingFile(self):
                return st['arquivo']

            def getTime(self):
                return st['posicao']

            def getTotalTime(self):
                return st['total']

            def seekTime(self, s):
                st['seeks'].append(float(s))

        def executebuiltin(cmd):
            st['builtins'].append(cmd)
            if cmd == 'ActivateWindow(fullscreenvideo)':
                st['janela'] = 'fullscreenvideo'
            elif cmd.startswith('PlayMedia('):
                alvo = cmd.split('"', 2)[1]
                # Se tentar reabrir mode=11 do Brazuca, abriria diálogo de opções!
                if 'mode=11' in alvo:
                    st['abriu_menu_opcoes'] = True
                    st['tocando'] = False
                    return
                # Se tentar reabrir o proxy morto do Brazuca, falha e sai do canal!
                if f':{porta_morta}/' in alvo:
                    st['tocando'] = False
                    st['arquivo'] = ''
                    st['janela'] = 'MyVideoNav'
                    return
                st['arquivo'] = alvo
                st['tocando'] = True
                st['janela'] = 'fullscreenvideo'
                if 'ads.exemplo' in alvo:
                    st['posicao'] = 0.0 if st['anuncio_parado_30s'] else 1.0
                    st['total'] = 30.0
                else:
                    st['posicao'] = 2.0
                    st['total'] = 30.0

        def getCondVisibility(c):
            if c == 'Window.IsActive(fullscreenvideo)':
                return st['janela'] == 'fullscreenvideo'
            return False

        def getInfoLabel(r):
            if r in ('Player.Filenameandpath', 'Player.FilenameAndPath'):
                return 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=11&name=Globo&url=ch1'
            return ''

        def executeJSONRPC(pedido):
            dados = json.loads(pedido)
            if dados.get('method') == 'Player.Seek':
                st['seeks'].append(float(dados['params']['value']['seconds']))
            if dados.get('method') == 'Player.GetActivePlayers':
                return json.dumps({'result': [{'playerid': 1, 'type': 'video'}] if st['tocando'] else []})
            return json.dumps({'result': 'OK'})

        xbmc = types.ModuleType('xbmc')
        xbmc.Player = FakePlayer
        xbmc.executebuiltin = executebuiltin
        xbmc.getCondVisibility = getCondVisibility
        xbmc.getInfoLabel = getInfoLabel
        xbmc.executeJSONRPC = executeJSONRPC
        xbmc.log = lambda *a, **k: None
        xbmc.sleep = lambda _ms: None
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        sys.modules['xbmc'] = xbmc
        sys.modules['xbmcvfs'] = types.SimpleNamespace(
            translatePath=lambda p: p, exists=lambda _p: False)
        sys.modules['xbmcaddon'] = types.SimpleNamespace(
            Addon=lambda *a, **k: types.SimpleNamespace(
                getSetting=lambda _k: '', getAddonInfo=lambda _k: 'service.smarted.bootstrap'))
        sys.modules['xbmcgui'] = types.SimpleNamespace(
            Dialog=lambda: types.SimpleNamespace(ok=lambda *a, **k: None, notification=lambda *a, **k: None))
        if str(BOOTSTRAP) not in sys.path:
            sys.path.insert(0, str(BOOTSTRAP))

    def test_1_tv_ao_vivo_reproduz_anuncio_e_retorna_ao_canal_pela_url_real_sem_sair(self):
        """Canal ao vivo do Brazuca (proxy LAN + string_encoder): reproduz o
        anúncio igual a filmes/séries e volta ao canal usando a URL real
        decodificada (com headers preservados), sem seek e sem sair do canal."""
        ao_vivo = _carregar('ao_vivo_tv1', BOOTSTRAP / 'ao_vivo.py')
        sys.modules['ao_vivo'] = ao_vivo
        vast = _carregar('vast_tv1', BOOTSTRAP / 'ads_vast.py')
        sys.modules['ads_vast'] = vast
        vast._agora = lambda: self.st['relogio']
        vast.disparar = lambda _u: 0

        self.assertTrue(ao_vivo.eh_ao_vivo(self.url_proxy_brazuca))
        estado = vast.estado_do_conteudo()
        self.assertTrue(estado['ao_vivo'])
        self.assertEqual(estado['url_real'], self.url_stream_real)

        def dormir(_s):
            self.st['relogio'] += 1.0
            if self.st['tocando']:
                self.st['posicao'] += 8.0

        recibo = vast.exibir_e_devolver(
            tag='https://ads.exemplo/vast',
            baixar_tag=lambda _u: VAST_MIX_WEBM_MP4.encode('utf-8'),
            dormir=dormir,
        )
        self.assertTrue(recibo['exibido'])
        self.assertTrue(recibo.get('conteudo_devolvido'))
        self.assertTrue(self.st['tocando'], 'O canal ao vivo não pode fechar após o anúncio')
        self.assertEqual(self.st['arquivo'], self.url_stream_real)
        self.assertEqual(self.st['janela'], 'fullscreenvideo')
        self.assertEqual(self.st['seeks'], [], 'TV ao vivo nunca recebe Seek')
        self.assertFalse(self.st['abriu_menu_opcoes'],
                         'Não pode reabrir mode=11 pedindo ESCOLHA UMA OPÇÃO de novo')

    def test_2_tv_ao_vivo_nao_fica_presa_em_player_vazio_de_30s_e_volta_ao_canal(self):
        """Se o criativo de 30s travar em 0.0s na TV ao vivo, não fica 30s parado
        sem fazer nada: corta em ~6s e devolve o canal ao vivo funcionando."""
        ao_vivo = _carregar('ao_vivo_tv2', BOOTSTRAP / 'ao_vivo.py')
        sys.modules['ao_vivo'] = ao_vivo
        vast = _carregar('vast_tv2', BOOTSTRAP / 'ads_vast.py')
        sys.modules['ads_vast'] = vast
        vast._agora = lambda: self.st['relogio']
        vast.disparar = lambda _u: 0
        self.st['anuncio_parado_30s'] = True

        def dormir(_s):
            self.st['relogio'] += 1.0
            if self.st['tocando'] and 'ads.exemplo' not in self.st['arquivo']:
                self.st['posicao'] += 2.0

        recibo = vast.exibir_e_devolver(
            tag='https://ads.exemplo/vast',
            baixar_tag=lambda _u: VAST_MIX_WEBM_MP4.encode('utf-8'),
            dormir=dormir,
        )
        self.assertLessEqual(recibo['segundos'], 8.0)
        self.assertTrue(recibo.get('conteudo_devolvido'))
        self.assertTrue(self.st['tocando'])
        self.assertEqual(self.st['arquivo'], self.url_stream_real)
        self.assertEqual(self.st['janela'], 'fullscreenvideo')

    def test_3_ao_vivo_tocar_de_novo_no_fluxo_mobile_tambem_usa_url_real_quando_proxy_fecha(self):
        """No celular (AdMob + ad_return), quando o proxy LAN de TV ao vivo cai
        durante o anúncio, ao_vivo._tocar_de_novo reabre a URL real sem sair."""
        ao_vivo = _carregar('ao_vivo_tv3', BOOTSTRAP / 'ao_vivo.py')
        sys.modules['ao_vivo'] = ao_vivo
        self.st['tocando'] = False
        self.st['arquivo'] = ''
        ok = ao_vivo._tocar_de_novo(self.url_proxy_brazuca)
        self.assertTrue(ok)
        self.assertTrue(self.st['tocando'])
        self.assertEqual(self.st['arquivo'], self.url_stream_real)


if __name__ == '__main__':
    unittest.main()
