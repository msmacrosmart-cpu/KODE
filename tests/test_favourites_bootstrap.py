"""Favoritos nativos e instalação do Brazuca Play no boot.

Requisitos do usuário (2026-11-11):

* o Brazuca Play tem que estar instalado/habilitado **quando o app abre**, sem
  precisar entrar antes em uma opção de vídeo;
* os atalhos (TV ao vivo, Filmes, Séries, Animes, Novelas, Desenhos, Doramas)
  precisam estar nos **favoritos do Kodi** (nativos), e não só em telas da skin;
* precisa existir um caminho nativo para navegar nos addons (fallback).
"""
from pathlib import Path
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi/addons/service.smarted.bootstrap'
SKIN = ROOT / 'kodi/skin.estilo.personalizado'
XML = SKIN / 'xml'

sys.path.insert(0, str(BOOTSTRAP))
import favourites  # noqa: E402


class FavouritesModuleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / 'userdata').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def path(self):
        return self.home / 'userdata' / 'favourites.xml'

    def test_cria_os_atalhos_do_brazuca_play(self):
        added = favourites.ensure_favourites(str(self.home))
        self.assertEqual(len(added), len(favourites.SHORTCUTS))
        root = ET.parse(self.path()).getroot()
        self.assertEqual(root.tag, 'favourites')
        names = [node.get('name') for node in root]
        self.assertEqual(names, ['TV ao vivo', 'Filmes', 'Séries',
                                 'Canais (pastas)', 'Filmes (pastas)', 'Séries (pastas)',
                                 'Novelas', 'Animes', 'Desenhos', 'Doramas'])

    def test_primeiros_atalhos_apontam_para_os_favoritos_sincronizados(self):
        """Os tres atalhos principais leem favorites.json do addon (mode 15)."""
        favourites.ensure_favourites(str(self.home))
        root = ET.parse(self.path()).getroot()
        esperado = {'TV ao vivo': 'canais', 'Filmes': 'filmes', 'Séries': 'series'}
        for node in list(root)[:3]:
            nome = node.get('name')
            self.assertIn(nome, esperado)
            self.assertIn('mode=15', node.text or '', nome)
            self.assertIn('url=%s' % esperado[nome], node.text or '', nome)

    def test_atalhos_abrem_o_plugin_com_icone_e_fanart(self):
        favourites.ensure_favourites(str(self.home))
        for node in ET.parse(self.path()).getroot():
            action = node.text or ''
            self.assertIn('ActivateWindow(10025,', action)
            self.assertIn('plugin.video.BrazucaPlay.Matrix/?mode=', action)
            self.assertIn('iconimage=', action)
            self.assertIn('fanart=', action)

    def test_idempotente(self):
        favourites.ensure_favourites(str(self.home))
        first = self.path().read_text()
        self.assertEqual(favourites.ensure_favourites(str(self.home)), [])
        self.assertEqual(self.path().read_text(), first)

    def test_preserva_favoritos_do_usuario(self):
        (self.path()).write_text(
            '<favourites>\n'
            '    <favourite name="Meu canal" thumb="x.png">'
            'PlayMedia("http://exemplo/a.m3u8")</favourite>\n'
            '</favourites>\n')
        favourites.ensure_favourites(str(self.home))
        root = ET.parse(self.path()).getroot()
        names = [node.get('name') for node in root]
        self.assertEqual(names[0], 'Meu canal')
        self.assertEqual(len(root), 1 + len(favourites.SHORTCUTS))

    def test_nao_duplica_atalho_que_ja_existe(self):
        action = favourites.shortcut_action('Filmes', 15, 'filmes')
        (self.path()).write_text(
            '<favourites>\n    <favourite name="Filmes">%s</favourite>\n</favourites>\n'
            % action.replace('&', '&amp;'))
        added = favourites.ensure_favourites(str(self.home))
        self.assertNotIn('Filmes', added)
        self.assertEqual(len(ET.parse(self.path()).getroot()), len(favourites.SHORTCUTS))

    def test_arquivo_corrompido_e_recriado(self):
        self.path().write_text('lixo que nao e xml')
        added = favourites.ensure_favourites(str(self.home))
        self.assertEqual(len(added), len(favourites.SHORTCUTS))
        self.assertEqual(len(ET.parse(self.path()).getroot()), len(favourites.SHORTCUTS))


class BootServiceTest(unittest.TestCase):
    def setUp(self):
        self.source = (BOOTSTRAP / 'service.py').read_text()

    def test_repara_antes_de_esperar_o_usuario_abrir_algo(self):
        self.assertIn('def repair_until_ready(', self.source)
        self.assertIn('REPAIR_ATTEMPTS', self.source)
        main = self.source[self.source.index('def main():'):]
        self.assertIn('repair_until_ready(monitor)', main)

    def test_grava_favoritos_no_boot(self):
        main = self.source[self.source.index('def main()'):]
        self.assertIn('write_favourites()', main)
        self.assertIn('ensure_favourites', self.source)

    def test_avisa_o_usuario_no_boot(self):
        self.assertIn('Preparando o conteudo', self.source)
        self.assertIn('Conteudo pronto para usar', self.source)
        # nenhuma notificacao cita o addon nem repete "SMARTED"
        for aviso in re.findall(r'Notification\(([^)]*)\)', self.source):
            self.assertNotIn('Brazuca', aviso)
            self.assertNotIn('SMARTEDTV', aviso)
        self.assertIn("Notification(SMARTED,", self.source)

    def test_check_py_restaura_atalhos_sob_demanda(self):
        source = (BOOTSTRAP / 'check.py').read_text()
        self.assertIn('favoritos', source)
        self.assertIn('restore_favourites', source)


class SkinShortcutsTest(unittest.TestCase):
    def setUp(self):
        self.home = (XML / 'Home.xml').read_text(encoding='utf-8')

    def test_home_tem_favoritos(self):
        self.assertIn('id="9019"', self.home)
        self.assertIn('ActivateWindow(10060)', self.home)

    def test_home_sem_botao_de_addons(self):
        # pedido do usuario (rodada 15): a barra redonda tem so Busca, Ajustes
        # e Sair - gerenciar addons sai da tela inicial.
        self.assertNotIn('id="9124"', self.home)
        self.assertNotIn('ActivateWindow(10040)', self.home)

    def test_ajustes_tem_favoritos_addons_e_restaurar(self):
        settings = (XML / 'Settings.xml').read_text(encoding='utf-8')
        self.assertIn('<label>Favoritos</label>', settings)
        self.assertIn('<label>Add-ons de vídeo</label>', settings)
        self.assertIn('RunScript(service.smarted.bootstrap,favoritos)', settings)
        self.assertIn('ActivateWindow(10040)', settings)

    def test_icones_dos_novos_itens_existem(self):
        for name in ('favourites.png', 'refresh.png'):
            self.assertTrue((SKIN / 'media/icons/settings' / name).is_file(), name)

    def test_nome_da_skin_e_smartedtv(self):
        addon = ET.parse(SKIN / 'addon.xml').getroot()
        self.assertEqual(addon.get('name'), 'SMARTEDTV')
        for path in XML.glob('*.xml'):
            self.assertNotIn('NOVA TV', path.read_text(encoding='utf-8'), path.name)


if __name__ == '__main__':
    unittest.main()


class PerformanceTest(unittest.TestCase):
    """advancedsettings.xml + aceleração por hardware aplicados no boot."""

    def setUp(self):
        sys.path.insert(0, str(BOOTSTRAP))
        import performance
        self.performance = performance
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / 'userdata').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def fake_jsonrpc(self, store, reject=()):
        def rpc(method, params=None):
            params = params or {}
            setting = params.get('setting')
            if method == 'Settings.SetSettingValue':
                if setting in reject:
                    return {'error': {'message': 'recusado'}}
                store[setting] = params.get('value')
                return {'result': 'OK'}
            if method == 'Settings.GetSettingValue':
                return {'result': {'value': store.get(setting)}}
            return {}
        return rpc

    def test_grava_advancedsettings_com_cache(self):
        wrote = self.performance.write_advancedsettings(str(self.home))
        self.assertTrue(wrote)
        body = (self.home / 'userdata' / 'advancedsettings.xml').read_text()
        self.assertIn('<buffermode>4</buffermode>', body)
        self.assertIn('<memorysize>268435456</memorysize>', body)
        self.assertIn(self.performance.MARKER, body)

    def test_preserva_advancedsettings_do_usuario(self):
        path = self.home / 'userdata' / 'advancedsettings.xml'
        path.write_text('<advancedsettings><loglevel>1</loglevel></advancedsettings>')
        self.assertFalse(self.performance.write_advancedsettings(str(self.home)))
        self.assertIn('loglevel', path.read_text())

    def test_nao_reescreve_o_proprio_arquivo(self):
        self.performance.write_advancedsettings(str(self.home))
        first = (self.home / 'userdata' / 'advancedsettings.xml').read_text()
        self.performance.write_advancedsettings(str(self.home))
        self.assertEqual(first, (self.home / 'userdata' / 'advancedsettings.xml').read_text())

    def test_aplica_cache_e_hardware(self):
        store = {}
        applied, failed = self.performance.apply_settings(self.fake_jsonrpc(store))
        self.assertEqual(failed, [])
        self.assertIn('filecache.memorysize', applied)
        self.assertIn('videoplayer.usemediacodecsurface', applied)
        self.assertEqual(store['filecache.buffermode'], 4)
        self.assertTrue(store['videoplayer.usemediacodec'])
        self.assertTrue(store['videoplayer.usemediacodecsurface'])

    def test_projetor_desliga_surface_para_nao_ficar_com_imagem_preta(self):
        store = {}
        applied, failed = self.performance.apply_settings(
            self.fake_jsonrpc(store), nome_dispositivo='XGIMI Halo+ Projector')
        self.assertEqual(failed, [])
        self.assertIn('videoplayer.usemediacodecsurface', applied)
        self.assertFalse(store['videoplayer.usemediacodecsurface'])
        self.assertTrue(store['videoplayer.usemediacodec'])
        self.assertEqual(store['videoplayer.adjustrefreshrate'], 0)

    def test_tv_box_continua_com_surface(self):
        store = {}
        self.performance.apply_settings(self.fake_jsonrpc(store),
                                         nome_dispositivo='Samsung Smart TV')
        self.assertTrue(store['videoplayer.usemediacodecsurface'])

    def test_deteccao_de_projetor_nao_confunde_tv(self):
        for nome in ('Projetor Wanbo X1', 'Android Projector', 'LG CineBeam',
                     'Anker Nebula Capsule', 'Epson EH-TW5650'):
            self.assertTrue(self.performance.eh_projetor(nome), nome)
        for nome in ('Samsung Smart TV', 'Mi Box S', 'Fire TV Stick',
                     'Chromecast with Google TV', 'Celular Galaxy S23'):
            self.assertFalse(self.performance.eh_projetor(nome), nome)

    def test_setting_recusado_nao_derruba_o_boot(self):
        store = {}
        applied, failed = self.performance.apply_settings(
            self.fake_jsonrpc(store, reject=('filecache.chunksize',)))
        self.assertEqual(failed, ['filecache.chunksize'])
        self.assertIn('filecache.readfactor', applied)

    def test_valores_respeitam_as_opcoes_do_kodi(self):
        self.assertIn(self.performance.CACHE_SETTINGS['filecache.memorysize'],
                      (16, 20, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024))
        self.assertIn(self.performance.CACHE_SETTINGS['filecache.readfactor'],
                      (0, 110, 125, 150, 175, 200, 250, 300, 400, 500, 700, 1000, 1500, 2000, 3000, 5000))
        self.assertIn(self.performance.CACHE_SETTINGS['filecache.chunksize'],
                      (256, 512, 1024, 2 * 1024, 4 * 1024, 8 * 1024, 16 * 1024, 32 * 1024,
                       64 * 1024, 128 * 1024, 256 * 1024, 512 * 1024, 1024 * 1024))
        self.assertEqual(self.performance.CACHE_SETTINGS['filecache.buffermode'], 4)

    def test_servico_aplica_no_boot(self):
        source = (BOOTSTRAP / 'service.py').read_text()
        main = source[source.index('def main():'):]
        self.assertIn('apply_performance()', main)
        self.assertIn('ensure_performance', source)
        self.assertIn('System.FriendlyName', source)

    def test_servico_recupera_boot_sem_janela(self):
        source = (BOOTSTRAP / 'service.py').read_text()
        self.assertIn('def garantir_interface_inicial', source)
        self.assertIn("name='boot-interface'", source)
        self.assertIn('RunScript(script.smartedtv.welcome)', source)

    def test_addon_do_servico_tem_uma_unica_extensao_de_script(self):
        raiz = ET.parse(BOOTSTRAP / 'addon.xml').getroot()
        scripts = [e for e in raiz.findall('extension')
                   if e.get('point') == 'xbmc.python.script']
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0].get('library'), 'check.py')
        self.assertEqual(raiz.get('version'), '1.0.9')

    def test_addon_do_servico_declara_xml_1_0_e_um_script_existente(self):
        texto = (BOOTSTRAP / 'addon.xml').read_text()
        self.assertTrue(texto.startswith('<?xml version="1.0"'))
        self.assertNotIn('version="1.1"', texto)
        raiz = ET.parse(BOOTSTRAP / 'addon.xml').getroot()
        for extensao in raiz.findall('extension'):
            biblioteca = extensao.get('library')
            if biblioteca:
                self.assertTrue((BOOTSTRAP / biblioteca).is_file(), biblioteca)

    def test_servico_remove_estagios_temporarios_de_seed(self):
        source = (BOOTSTRAP / 'service.py').read_text()
        self.assertIn('def limpar_estagios_de_seed', source)
        self.assertIn("nome.startswith('.smarted-seed-')", source)
        self.assertIn('limpar_estagios_de_seed()', source)

    def test_servico_habilita_os_addons_do_app_antes_da_interface(self):
        source = (BOOTSTRAP / 'service.py').read_text()
        self.assertIn('CORE_ADDONS', source)
        self.assertIn('enable_addons(CORE_ADDONS)', source)
        for addon in ('script.smartedtv.welcome', 'service.smarted.bootstrap',
                      'plugin.video.smarted'):
            self.assertIn(addon, source)

    def test_servico_liga_os_anuncios_e_limpa_marcas_no_boot(self):
        source = (BOOTSTRAP / 'service.py').read_text()
        self.assertIn('smart_ads.iniciar_monitor(log)', source)
        self.assertIn('smart_ads.abertura_depois_do_boot', source)
        self.assertIn('limpar_estado_interface()', source)
