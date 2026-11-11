#!/usr/bin/env python3
"""Executa um diretório do plugin.video.BrazucaPlay.Matrix fora do Kodi.

Mesmo contrato do harness de testes (`tests/kodi_plugin_stubs/run_plugin.py`),
mas com uma diferença importante para simular o Kodi de verdade: o
``xbmc.Monitor`` aborta em seguida, então o padrão ``monitor_switch()`` do
add-on (que dorme esperando o player) não trava a simulação. Sem isso o
processo ficaria preso em ``while not monitor.waitForAbort(3)``.

Uso:
    python3 tools/kodi/kodi_plugin_runner.py PERFIL 'mode=27&url=%23filmes_menu'

Saída: JSON com os itens do diretório (label, folder, url) e o status.
"""
import json
import os
import runpy
import sys

STUBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                     'tests', 'kodi_plugin_stubs')
STUBS = os.path.abspath(STUBS)
PLUGIN_ID = 'plugin.video.BrazucaPlay.Matrix'
MODULES = {
    'script.module.kodi-six': 'libs', 'script.module.six': 'lib',
    'script.module.requests': 'lib', 'script.module.simplejson': 'lib',
    'script.module.beautifulsoup4': 'lib', 'script.module.soupsieve': 'lib',
    'script.module.urllib3': 'lib', 'script.module.certifi': 'lib',
    'script.module.chardet': 'lib', 'script.module.idna': 'lib',
}


def main(argv):
    if len(argv) < 3:
        print(json.dumps({'error': 'uso: kodi_plugin_runner.py PERFIL QUERY'}))
        return 2
    profile = os.path.abspath(argv[1])
    query = argv[2]
    addons = os.path.join(profile, 'addons')
    plugin = os.path.join(addons, PLUGIN_ID)
    if not os.path.isdir(plugin):
        print(json.dumps({'error': 'plugin ausente em %s' % plugin, 'items': []}))
        return 2
    data_dir = os.path.join(profile, 'userdata', 'addon_data', PLUGIN_ID)
    os.makedirs(data_dir, exist_ok=True)

    for path in [STUBS, plugin] + [os.path.join(addons, name, folder)
                                   for name, folder in MODULES.items()]:
        if os.path.isdir(path):
            sys.path.insert(0, path)

    os.environ['SMARTED_STUB_PLUGIN'] = plugin
    os.environ['SMARTED_STUB_ADDON_DATA'] = data_dir
    os.environ['SMARTED_STUB_HOME'] = profile

    import xbmc

    original = xbmc.Monitor

    class AbortNowMonitor(original):
        """Como o Kodi quando o usuário sai da janela: aborta na hora."""

        def waitForAbort(self, timeout=0):
            return True

    xbmc.Monitor = AbortNowMonitor

    if not query.startswith('?'):
        query = '?' + query
    sys.argv = ['plugin://%s/' % PLUGIN_ID, '1', query]

    error = None
    try:
        runpy.run_path(os.path.join(plugin, 'default.py'), run_name='__main__')
    except SystemExit:
        pass
    except BaseException as exc:  # noqa: BLE001 - queremos reportar qualquer falha
        error = '%s: %s' % (type(exc).__name__, exc)

    import xbmcgui
    import xbmcplugin

    items, seen = [], set()
    for entries in xbmcplugin.DIRS.values():
        for url, label, is_folder in entries:
            if url == '__END__':
                continue
            key = (url, label)
            if key in seen:
                continue
            seen.add(key)
            items.append({'label': label, 'url': url, 'folder': bool(is_folder)})

    print(json.dumps({
        'query': query,
        'items': items,
        'count': len(items),
        'notifications': len(getattr(xbmcgui, 'NOTIFS', []) or []),
        'error': error,
    }, ensure_ascii=False))
    return 1 if error else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
