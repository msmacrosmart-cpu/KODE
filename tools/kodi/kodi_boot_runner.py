#!/usr/bin/env python3
"""Roda a sequência de boot do service.smarted.bootstrap num perfil, sem Kodi.

Executa exatamente as mesmas funções que ``service.main()`` chama, na mesma
ordem (reparo → UpdateLocalAddons → habilitação → favoritos → performance →
skin/nós da Home), mas para antes do laço infinito do serviço. O JSONRPС é
substituído por um stub que responde como o Kodi de um perfil já montado.

Uso:
    python3 tools/kodi/kodi_boot_runner.py PERFIL
"""
import json
import os
import sys


def main(argv):
    if len(argv) < 2:
        print(json.dumps({'error': 'uso: kodi_boot_runner.py PERFIL'}))
        return 2
    profile = os.path.abspath(argv[1])
    here = os.path.dirname(os.path.abspath(__file__))
    stubs = os.path.abspath(os.path.join(here, '..', '..', 'tests', 'kodi_plugin_stubs'))
    bootstrap = os.path.abspath(os.path.join(here, '..', '..', 'kodi', 'addons',
                                             'service.smarted.bootstrap'))
    if not os.path.isdir(profile):
        print(json.dumps({'error': 'perfil inexistente: %s' % profile}))
        return 2

    os.environ['SMARTED_STUB_HOME'] = profile
    os.environ['SMARTED_STUB_ADDON_DATA'] = os.path.join(profile, 'userdata', 'addon_data',
                                                         'plugin.video.BrazucaPlay.Matrix')
    os.environ['SMARTED_STUB_PLUGIN'] = os.path.join(profile, 'addons',
                                                     'plugin.video.BrazucaPlay.Matrix')
    for path in (stubs, bootstrap):
        sys.path.insert(0, path)

    import xbmc

    calls = []

    def executeJSONRPC(request):
        payload = json.loads(request)
        method = payload.get('method', '')
        calls.append(method)
        if method == 'Addons.GetAddons':
            return json.dumps({'result': {'addons': [], 'limits': {'start': 0, 'end': 0, 'total': 0}},
                               'id': 1})
        if method == 'Settings.GetSettingValue':
            return json.dumps({'result': {'value': ''}, 'id': 1})
        return json.dumps({'result': 'OK', 'id': 1})

    xbmc.executeJSONRPC = executeJSONRPC

    import xbmcaddon

    class BootstrapAddon(object):
        """O addon é um add-on de sistema (assets/addons do APK); aqui apontamos
        para o pacote do repositório, que é o mesmo conteúdo que vai no APK."""

        def __init__(self, id=None):
            self.id = id or 'service.smarted.bootstrap'

        def getAddonInfo(self, key):
            return {
                'path': bootstrap, 'id': self.id, 'name': 'SMARTED-TV Bootstrap',
                'version': '1.0.4',
                'profile': os.path.join(profile, 'userdata', 'addon_data', self.id),
            }.get(key, '')

        def getSetting(self, key):
            return ''

        def setSetting(self, key, value):
            return None

        def getLocalizedString(self, key):
            return ''

    xbmcaddon.Addon = BootstrapAddon

    import xbmcvfs

    report = {'error': None, 'jsonrpc': calls}
    try:
        import service

        monitor = xbmc.Monitor()
        repair_report, attempts = service.repair_until_ready(monitor)
        report['repair_ok'] = bool(repair_report and repair_report['ok'])
        report['repair_attempts'] = attempts
        report['required'] = list(repair_report['required']) if repair_report else []
        xbmc.executebuiltin('UpdateLocalAddons()')
        failed = service.enable_addons(report['required'])
        report['enable_failed'] = failed

        added = service.write_favourites()
        report['favourites_added'] = list(added or [])
        fav_path = os.path.join(profile, 'userdata', 'favourites.xml')
        if os.path.isfile(fav_path):
            import xml.etree.ElementTree as ET
            report['favourites_total'] = len(list(ET.parse(fav_path).getroot()))

        performance = service.apply_performance()
        report['performance_applied'] = list(performance.get('applied', []))

        home = xbmcvfs.translatePath('special://home')
        addons_dir = os.path.join(home, 'addons')
        skin = service.ensure_skin(home, log=service.log)
        report['skin'] = skin
        nodes = service.ensure_home_nodes(
            service.home_xml_candidates(addons_dir),
            os.path.join(home, 'userdata', 'favourites.xml'),
            log=service.log)
        report['home_nodes'] = nodes
    except BaseException as exc:  # noqa: BLE001
        import traceback
        report['error'] = '%s: %s' % (type(exc).__name__, exc)
        report['traceback'] = traceback.format_exc()

    report['xbmc_log'] = list(getattr(xbmc, 'LOG', []))[-40:]
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report['error'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
