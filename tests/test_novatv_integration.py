import hashlib
import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import sys
import types
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIN = ROOT / 'kodi' / 'skin.novatv'
spec = importlib.util.spec_from_file_location('stage_profile', ROOT / 'tools/kodi/stage-profile.py')
stage_profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_profile)


class SkinContracts(unittest.TestCase):
    def test_xml_parses(self):
        xmls = list(SKIN.rglob('*.xml'))
        self.assertGreaterEqual(len(xmls), 94)
        for path in xmls:
            with self.subTest(path=path.relative_to(SKIN)):
                ET.parse(path)

    def test_settings_controls_match_kodi_21(self):
        types = {'2': 'label', '3': 'grouplist', '5': 'grouplist', '6': 'textbox',
                 '7': 'button', '8': 'radiobutton', '9': 'spincontrolex',
                 '10': 'button', '11': 'image', '12': 'edit', '13': 'sliderex',
                 '14': 'label', '15': 'colorbutton'}
        for name in ('SettingsCategory.xml', 'DialogAddonSettings.xml', 'DialogSettings.xml'):
            with self.subTest(window=name):
                root = ET.parse(SKIN / 'xml' / name).getroot()
                controls = [c for c in root.iter('control') if c.get('id')]
                ids = [c.get('id') for c in controls]
                self.assertEqual(len(ids), len(set(ids)))
                found = {c.get('id'): c for c in controls}
                for ident, expected in types.items():
                    self.assertEqual(found[ident].get('type'), expected, ident)
                for ident in ('3', '5'):
                    self.assertFalse(found[ident].findall('control'), 'Templates must not be in the dynamic list')
                if name == 'SettingsCategory.xml':
                    self.assertEqual(found['20'].findtext('onclick'), 'SettingsLevelChange')
                else:
                    for ident in ('28', '29', '30'):
                        self.assertEqual(found[ident].get('type'), 'button')

    def test_fallback_keyboard_uses_kodi_layout_ids(self):
        root = ET.parse(SKIN / 'xml' / 'DialogKeyboard.xml').getroot()
        ids = [int(c.get('id')) for c in root.iter('control') if (c.get('id') or '').isdigit()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({100 + row * 20 + col for row in range(4) for col in range(13)}.issubset(ids))
        self.assertTrue({8, 32, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312}.issubset(ids))

    def test_select_dialog_uses_kodi_control_types(self):
        root = ET.parse(SKIN / 'xml' / 'DialogSelect.xml').getroot()
        controls = {c.get('id'): c.get('type') for c in root.iter('control') if c.get('id')}
        self.assertEqual({key: controls[key] for key in ('1', '2', '3', '5', '6', '7', '8')},
                         {'1': 'label', '2': 'label', '3': 'list', '5': 'button',
                          '6': 'list', '7': 'button', '8': 'button'})

    def test_restricted_home_routes_and_unlock_sequence(self):
        home = ET.parse(SKIN / 'xml' / 'Home.xml').getroot()
        menu = home.find(".//control[@id='9000']/content")
        entries = [(i.findtext('label'), i.findtext('onclick'), i.findtext('visible')) for i in menu.findall('item')]
        self.assertEqual([x[0] for x in entries[:4]],
                         ['$LOCALIZE[31023]', '$LOCALIZE[31001]', '$LOCALIZE[31002]', '$LOCALIZE[31015]'])
        self.assertTrue(all('System.HasAddon(plugin.video.BrazucaPlay.Matrix)' in item[2] for item in entries[:3]))
        self.assertEqual(entries[3][1], 'ActivateWindow(Settings)')
        self.assertIn('plugin.video.smarted/?route=tv', entries[0][1])
        self.assertIn('plugin.video.smarted/?route=movies', entries[1][1])
        self.assertTrue(all('Skin.HasSetting(SmartedFullMode)' in (item[2] or '') for item in entries[4:]))
        logo = home.find(".//control[@id='8999']")
        actions = logo.findall('onclick')
        self.assertEqual(len(actions), 8)
        for step, action in enumerate(actions, 1):
            self.assertEqual(action.text, 'Skin.SetString(SmartedUnlock,%d)' % step)
            self.assertIn('!Skin.HasSetting(SmartedFullMode)', action.get('condition'))
        settings = ET.parse(SKIN / 'xml' / 'Settings.xml').getroot()
        actions = settings.findall('onunload')
        self.assertEqual([a.text for a in actions], ['Skin.SetString(SmartedUnlock,9)', 'Skin.SetBool(SmartedFullMode)'])
        self.assertTrue(all('Window.Next(Home)' in a.get('condition') for a in actions))

    def test_startup_advances_to_configured_kodi_window(self):
        root = ET.parse(SKIN / 'xml' / 'Startup.xml').getroot()
        self.assertEqual(root.findtext('onload'), 'ReplaceWindow($INFO[System.StartupWindow])')

    def test_main_settings_navigates_to_kodi_windows(self):
        root = ET.parse(SKIN / 'xml' / 'Settings.xml').getroot()
        menu = root.find(".//control[@id='9000']")
        self.assertEqual(root.findtext('defaultcontrol'), '9000')
        actions = {item.findtext('onclick') for item in menu.findall('./content/item')}
        for window in ('PlayerSettings', 'MediaSettings', 'ServiceSettings', 'InterfaceSettings',
                       'SystemSettings', 'AddonBrowser', 'Profiles'):
            self.assertIn('ActivateWindow(%s)' % window, actions)
        for language in ('resource.language.pt_br', 'resource.language.en_gb'):
            text = (SKIN / 'language' / language / 'strings.po').read_text(encoding='utf-8')
            self.assertIn('msgctxt "#31067"', text)

    def test_skin_palette(self):
        root = ET.parse(SKIN / 'colors/defaults.xml').getroot()
        colors = {c.get('name'): c.text.lower() for c in root.findall('color')}
        self.assertEqual({k: colors[k] for k in ('bg', 'panel', 'panel2', 'white', 'text', 'muted', 'accent')},
                         dict(bg='ff0d0d0d', panel='ff181818', panel2='ff262626', white='fff2f2f2',
                              text='ffd9d9d9', muted='ffa6a6a6', accent='fff2f2f2'))


class BrazucaRoutes(unittest.TestCase):
    def test_links_use_known_brazuca_modes_and_escape_hash(self):
        spec = importlib.util.spec_from_file_location('smarted_routes', ROOT / 'kodi/addons/plugin.video.smarted/routes.py')
        routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(routes)
        expected = {
            'TV ao vivo': (21, '#menu_canais'), 'Filmes': (27, '#filmes_menu'),
            'Séries': (27, '#series_menu'), 'Novelas': (25, '#novelas_menu'),
            'Animes': (22, '#animes_menu'), 'Doramas': (31, '#doramas_menu'),
            'Desenhos': (28, '#desenhos_menu'),
        }
        self.assertTrue(routes.items('series')[0][1].startswith(routes.SMARTED))
        self.assertEqual(routes.items('tv')[0][1], routes.brazuca(21, '#menu_canais'))
        self.assertEqual(routes.items('tv')[1][1], routes.smarted('search-channels'))
        entries = routes.items('root')[:2] + routes.items('series')[1:]
        for label, url in entries:
            with self.subTest(label=label):
                parsed = urlsplit(url)
                self.assertEqual(parsed.scheme, 'plugin')
                self.assertEqual(parsed.netloc, 'plugin.video.BrazucaPlay.Matrix')
                self.assertFalse(parsed.fragment)
                args = parse_qs(parsed.query, keep_blank_values=True)
                self.assertTrue(all(args.get(k) == [''] for k in ('name', 'iconimage', 'fanart', 'description')))
                mode, target = expected[label]
                self.assertEqual((int(args['mode'][0]), args['url'][0]), (mode, target))
        self.assertTrue(routes.items('root')[2][1].startswith(routes.SMARTED))
        self.assertEqual(routes.items('invalid'), [])

    def test_kodi_entrypoint_exposes_directories_and_handles_unknown_route(self):
        base = ROOT / 'kodi/addons/plugin.video.smarted'
        spec = importlib.util.spec_from_file_location('routes', base / 'routes.py')
        routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(routes)
        calls = []
        gui = types.SimpleNamespace(ListItem=lambda **kw: kw)
        plugin = types.SimpleNamespace(
            addDirectoryItem=lambda *a, **kw: calls.append(('item', a, kw)),
            endOfDirectory=lambda *a, **kw: calls.append(('end', a, kw)))
        spec = importlib.util.spec_from_file_location('smarted_main', base / 'default.py')
        main = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'routes': routes, 'xbmcgui': gui, 'xbmcplugin': plugin}):
            spec.loader.exec_module(main)
            with patch.object(sys, 'argv', ['plugin://plugin.video.smarted/', '42', '?route=series']):
                main.main()
            self.assertEqual(len([c for c in calls if c[0] == 'item']), 6)
            self.assertTrue(all(c[2]['isFolder'] for c in calls if c[0] == 'item'))
            self.assertTrue(calls[-1][2]['succeeded'])
            calls.clear()
            with patch.object(sys, 'argv', ['plugin://plugin.video.smarted/', '42', '?route=unknown']):
                main.main()
            self.assertEqual(len(calls), 1)
            self.assertFalse(calls[0][2]['succeeded'])


class BackupStage(unittest.TestCase):
    def make_zip(self, root, entries):
        path = root / 'backup.zip'
        with ZipFile(path, 'w') as z:
            for name, data in entries:
                z.writestr(name, data)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_stages_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup, sha = self.make_zip(root, [('files/.kodi/userdata/file.xml', b'profile')])
            dest = root / 'private'
            stage_profile.stage(backup, dest, sha)
            self.assertEqual((dest / 'userdata/file.xml').read_bytes(), b'profile')
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
            with self.assertRaises(FileExistsError):
                stage_profile.stage(backup, dest, sha)
            self.assertEqual((dest / 'userdata/file.xml').read_bytes(), b'profile')

    def test_unsafe_paths_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('files/.kodi/../evil', '/files/.kodi/evil', 'files/.kodi/..\\evil', 'elsewhere/a'):
                with self.subTest(name=name):
                    backup, sha = self.make_zip(root, [(name, b'bad')])
                    with self.assertRaises(ValueError):
                        stage_profile.stage(backup, root / 'dest', sha)
                    self.assertFalse((root / 'dest').exists())
                    self.assertFalse((root / 'evil').exists())

    def test_wrong_hash_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            link = ZipInfo('files/.kodi/link')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            backup, sha = self.make_zip(root, [(link, b'target')])
            with self.assertRaises(ValueError):
                stage_profile.stage(backup, root / 'dest', '0' * 64)
            with self.assertRaises(ValueError):
                stage_profile.stage(backup, root / 'dest', sha)
            self.assertFalse((root / 'dest').exists())


class BridgeApkStaging(unittest.TestCase):
    def test_bridge_staging_preserves_other_assets_and_refuses_overwrite(self):
        spec = importlib.util.spec_from_file_location('bridge_stage', ROOT / 'tools/kodi/stage-smarted-bridge.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            decoded = Path(tmp)
            (decoded / 'assets/addons').mkdir(parents=True)
            system = decoded / 'assets/system'
            system.mkdir(parents=True)
            manifest = system / 'addon-manifest.xml'
            manifest.write_text('<addons><addon>original</addon></addons>')
            module.stage(decoded)
            root = ET.parse(manifest).getroot()
            self.assertEqual([x.text for x in root], ['original', 'plugin.video.smarted'])
            bridge = decoded / 'assets/addons/plugin.video.smarted'
            self.assertEqual((bridge / 'default.py').read_bytes(), (ROOT / 'kodi/addons/plugin.video.smarted/default.py').read_bytes())
            self.assertFalse(list(bridge.rglob('*.pyc')))
            with self.assertRaises(ValueError):
                module.stage(decoded)
            self.assertEqual(len(ET.parse(manifest).getroot()), 2)

    def test_bridge_staging_rejects_existing_manifest_entry(self):
        spec = importlib.util.spec_from_file_location('bridge_stage2', ROOT / 'tools/kodi/stage-smarted-bridge.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            decoded = Path(tmp)
            (decoded / 'assets/addons').mkdir(parents=True)
            system = decoded / 'assets/system'
            system.mkdir(parents=True)
            (system / 'addon-manifest.xml').write_text('<addons><addon>plugin.video.smarted</addon></addons>')
            with self.assertRaises(ValueError):
                module.stage(decoded)
            self.assertFalse((decoded / 'assets/addons/plugin.video.smarted').exists())


if __name__ == '__main__':
    unittest.main()
