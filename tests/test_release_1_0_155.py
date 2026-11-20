#!/usr/bin/env python3
"""Suite dedicada da v1.0.155: compatibilidade total TV Stick + TV Box
sem qualquer regressao em celular e projetor (base v1.0.154).
"""
import importlib.util
import os
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
BOOT = RAIZ / 'kodi' / 'addons' / 'service.smarted.bootstrap'


def _carregar_modulo(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, str(caminho))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


smarted_release = _carregar_modulo('smarted_release_155', BOOT / 'smarted_release.py')
variante = _carregar_modulo('variante_155', BOOT / 'variante.py')
ajustar_apk = _carregar_modulo('ajustar_versao_apk_155', RAIZ / 'tools' / 'kodi' / 'ajustar-versao-apk.py')
verify_mod = _carregar_modulo('smartedtv_verify_155', RAIZ / 'smartedtv' / 'release' / 'verify.py')


def _construir_axml_teste(features):
    """Monta um AndroidManifest binário AXML mínimo válido para testar uses-feature.

    ``features``: lista de tuplas ``(nome_feature, required_val)`` onde
    ``required_val`` pode ser ``True``, ``False`` ou ``None`` (atributo omitido).
    """
    ns_uri = ajustar_apk.ANDROID
    palavras = [
        'name',          # idx 0 -> 0x01010003
        'required',      # idx 1 -> 0x0101028e
        ns_uri,          # idx 2
        'manifest',      # idx 3
        'uses-feature',  # idx 4
    ]
    for feat, _ in features:
        if feat not in palavras:
            palavras.append(feat)

    blobs = []
    offsets = []
    pos = 0
    for s in palavras:
        offsets.append(pos)
        b = struct.pack('<H', len(s)) + s.encode('utf-16-le') + b'\x00\x00'
        blobs.append(b)
        pos += len(b)
    corpo_str = b''.join(blobs)
    while len(corpo_str) % 4:
        corpo_str += b'\x00'
    strings_start = 28 + 4 * len(palavras)
    pool_size = strings_start + len(corpo_str)
    pool = struct.pack(
        '<HHIIIIII',
        0x0001, 28, pool_size, len(palavras), 0, 0, strings_start, 0,
    ) + b''.join(struct.pack('<I', o) for o in offsets) + corpo_str

    res_ids = [0x01010003, 0x0101028e]
    res_chunk = struct.pack('<HHI', 0x0180, 8, 8 + 4 * len(res_ids)) + b''.join(
        struct.pack('<I', r) for r in res_ids
    )

    elem_chunks = []
    for feat, req in features:
        idx_feat = palavras.index(feat)
        attrs = [
            struct.pack(
                '<IIIHBBI',
                palavras.index(ns_uri), 0, idx_feat, 8, 0, 0x03, idx_feat,
            )
        ]
        if req is not None:
            attrs.append(struct.pack(
                '<IIIHBBI',
                palavras.index(ns_uri), 1, 0xFFFFFFFF, 8, 0, 0x12,
                0xFFFFFFFF if req else 0,
            ))
        bloco_attr = b''.join(attrs)
        tam_el = 36 + len(bloco_attr)
        el = struct.pack(
            '<HHIIIIIHHHHHH',
            0x0102, 16, tam_el, 1, 0xFFFFFFFF,
            0xFFFFFFFF, palavras.index('uses-feature'),
            20, 20, len(attrs), 0, 0, 0,
        ) + bloco_attr
        elem_chunks.append(el)

    corpo = pool + res_chunk + b''.join(elem_chunks)
    cab = struct.pack('<HHI', 0x0003, 8, 8 + len(corpo))
    return cab + corpo, palavras


class KodiStub:
    def __init__(self, condicoes=(), infos=None):
        self.condicoes = set(condicoes)
        self.infos = dict(infos or {})

    def getCondVisibility(self, cond):
        return cond in self.condicoes

    def getInfoLabel(self, chave):
        return self.infos.get(chave, '')


class Release10155Test(unittest.TestCase):
    def setUp(self):
        variante._CACHE_SISTEMA.clear()

    def tearDown(self):
        variante._CACHE_SISTEMA.clear()

    def test_versao_1_0_155(self):
        self.assertEqual(smarted_release.VERSION_NAME, '1.0.155')
        self.assertEqual(smarted_release.VERSION_CODE, 2103141)

    def test_axml_desliga_uses_feature_obrigatoria_e_omitida(self):
        manifesto, palavras = _construir_axml_teste([
            ('android.hardware.touchscreen', False),
            ('android.hardware.screen.landscape', True),
            ('android.hardware.faketouch', None),
        ])
        ajustado, alteradas = ajustar_apk.tornar_features_opcionais(manifesto)
        self.assertIn('android.hardware.screen.landscape', alteradas)
        self.assertIn('android.hardware.faketouch', alteradas)

        vistos = {}
        for inicio, tipo, _, tamanho in ajustar_apk._chunks_axml(ajustado):
            if tipo != 0x0102:
                continue
            passo = ajustar_apk._u16(ajustado, inicio + 26)
            base = inicio + 16 + ajustar_apk._u16(ajustado, inicio + 24)
            qtd = ajustar_apk._u16(ajustado, inicio + 28)
            nome_f, req_f = None, None
            for i in range(qtd):
                pos = base + i * passo
                atrib = palavras[ajustar_apk._u32(ajustado, pos + 4)]
                if atrib == 'name':
                    nome_f = palavras[ajustar_apk._u32(ajustado, pos + 16)]
                elif atrib == 'required':
                    req_f = ajustar_apk._u32(ajustado, pos + 16)
            vistos[nome_f] = req_f
        self.assertEqual(vistos, {
            'android.hardware.touchscreen': 0,
            'android.hardware.screen.landscape': 0,
            'android.hardware.faketouch': 0,
        })

    def test_verify_recusa_screen_landscape_obrigatorio(self):
        from tests.test_release_universal import SAMPLE
        root = ET.fromstring(SAMPLE)
        uf = ET.SubElement(root, 'uses-feature')
        uf.set('{http://schemas.android.com/apk/res/android}name', 'android.hardware.screen.landscape')
        with self.assertRaises(ValueError):
            verify_mod.verify_manifest(root, '1.0.87', '2103073')
        uf.set('{http://schemas.android.com/apk/res/android}required', 'false')
        verify_mod.verify_manifest(root, '1.0.87', '2103073')

    def test_tv_sticks_detectados_mesmo_com_friendlyname_kodi(self):
        cenarios_stick = [
            {'ro.product.manufacturer': 'Amazon', 'ro.product.model': 'AFTMM', 'ro.build.version.fireos': '7.6.6.9'},
            {'ro.product.manufacturer': 'Xiaomi', 'ro.product.model': 'MiTV-AESP0', 'ro.product.device': 'mistick'},
            {'ro.product.manufacturer': 'Intelbras', 'ro.product.model': 'Izy Play'},
            {'ro.product.manufacturer': 'Aquario', 'ro.product.model': 'STV-3000'},
        ]
        for props in cenarios_stick:
            with tempfile.TemporaryDirectory() as tmp:
                prop_path = os.path.join(tmp, 'build.prop')
                with open(prop_path, 'w', encoding='utf-8') as fh:
                    for k, v in props.items():
                        fh.write('%s=%s\n' % (k, v))
                kodi = KodiStub(
                    condicoes={'System.Platform.Android', 'System.Platform.Android.Mobile'},
                    infos={'System.FriendlyName': 'Kodi', 'System.ScreenHeight': '1080'},
                )
                with mock.patch.dict(sys.modules, {'xbmc': kodi}), \
                     mock.patch.object(variante, 'variante_do_arquivo', return_value=None), \
                     mock.patch.object(variante, '_PROP_ARQUIVOS_PADRAO', (prop_path,)), \
                     mock.patch.object(variante, '_PERM_PASTAS_PADRAO', ()):
                    variante._CACHE_SISTEMA.clear()
                    self.assertEqual(variante.variante(), 'tv', msg=str(props))
                    self.assertTrue(variante.e_tv())

    def test_tv_boxes_aosp_detectadas_sem_afetar_celular(self):
        cenarios_box = [
            {'ro.product.model': 'MXQ Pro 4K', 'ro.board.platform': 'gxbb'},
            {'ro.product.model': 'TX3 Mini', 'ro.hardware': 'amlogic'},
            {'ro.product.model': 'X96Q', 'ro.board.platform': 'sun50iw9p1'},
            {'ro.product.model': 'SmartBox', 'ro.build.characteristics': 'mbx,nosdcard'},
            {'ro.product.model': 'RK_BOX', 'ro.board.platform': 'rk322x'},
        ]
        for props in cenarios_box:
            with tempfile.TemporaryDirectory() as tmp:
                prop_path = os.path.join(tmp, 'build.prop')
                with open(prop_path, 'w', encoding='utf-8') as fh:
                    for k, v in props.items():
                        fh.write('%s=%s\n' % (k, v))
                kodi = KodiStub(
                    condicoes={'System.Platform.Android', 'System.Platform.Android.Mobile'},
                    infos={'System.FriendlyName': 'Kodi', 'System.ScreenHeight': '1080'},
                )
                with mock.patch.dict(sys.modules, {'xbmc': kodi}), \
                     mock.patch.object(variante, 'variante_do_arquivo', return_value=None), \
                     mock.patch.object(variante, '_PROP_ARQUIVOS_PADRAO', (prop_path,)), \
                     mock.patch.object(variante, '_PERM_PASTAS_PADRAO', ()):
                    variante._CACHE_SISTEMA.clear()
                    self.assertEqual(variante.variante(), 'tv', msg=str(props))

        celulares = [
            {'ro.product.manufacturer': 'samsung', 'ro.product.model': 'SM-A546E'},
            {'ro.product.manufacturer': 'motorola', 'ro.product.model': 'moto g84 5G'},
            {'ro.product.manufacturer': 'Xiaomi', 'ro.product.model': 'Redmi Note 13'},
        ]
        for props in celulares:
            with tempfile.TemporaryDirectory() as tmp:
                prop_path = os.path.join(tmp, 'build.prop')
                perm_dir = os.path.join(tmp, 'permissions')
                os.makedirs(perm_dir)
                open(os.path.join(perm_dir, 'android.hardware.touchscreen.xml'), 'w').close()
                with open(prop_path, 'w', encoding='utf-8') as fh:
                    for k, v in props.items():
                        fh.write('%s=%s\n' % (k, v))
                kodi = KodiStub(
                    condicoes={'System.Platform.Android', 'System.Platform.Android.Mobile'},
                    infos={'System.FriendlyName': 'Kodi', 'System.ScreenHeight': '1080'},
                )
                with mock.patch.dict(sys.modules, {'xbmc': kodi}), \
                     mock.patch.object(variante, 'variante_do_arquivo', return_value=None), \
                     mock.patch.object(variante, '_PROP_ARQUIVOS_PADRAO', (prop_path,)), \
                     mock.patch.object(variante, '_PERM_PASTAS_PADRAO', (perm_dir,)):
                    variante._CACHE_SISTEMA.clear()
                    self.assertEqual(variante.variante(), 'mobile', msg=str(props))

    def test_vip_github_aceita_smartedtv_apk_quando_universal_404(self):
        from tests.test_apk_nome_fixo import carregar_vip
        vip, _, _ = carregar_vip()
        vip._resolver_apk_pasta_dropbox = lambda: None
        vip.eh_tv = lambda: True

        def cabecalhos(url, **_):
            if url.endswith('/SMARTEDTV-universal.apk'):
                return (1024, 'not-found.html')
            if url.endswith('/SMARTEDTV.apk'):
                return (264844625, 'SMARTEDTV.apk')
            return (None, None)

        vip._cabecalhos_remotos = cabecalhos
        url, origem = vip.resolver_apk_publicado()
        self.assertEqual(origem, 'github')
        self.assertTrue(url.endswith('/SMARTEDTV.apk'))

    def test_keymaps_tv_stick_e_tv_box_validos(self):
        voltar = ET.parse(RAIZ / 'kodi' / 'keymaps' / 'smartedtv-voltar.xml').getroot()
        player = ET.parse(RAIZ / 'kodi' / 'keymaps' / 'smartedtv-player.xml').getroot()
        self.assertEqual([c.tag for c in voltar], ['Home'])
        self.assertIsNotNone(voltar.find('./Home/keyboard/nav_back'))
        self.assertIsNotNone(voltar.find('./Home/gamepad/B'))
        self.assertIsNotNone(player.find('./FullscreenVideo/keyboard/nav_back'))
        self.assertIsNotNone(player.find('./FullscreenLiveTV/keyboard/nav_back'))


if __name__ == '__main__':
    unittest.main()
