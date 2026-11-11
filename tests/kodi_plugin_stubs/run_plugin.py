#!/usr/bin/env python3
"""Executa o plugin.video.BrazucaPlay.Matrix fora do Kodi.

Carrega o ``default.py`` real do plugin com stubs de ``xbmc*`` e os módulos que
o perfil entrega, para provar que o addon inicia e lista o menu principal.
Sem rede os itens continuam aparecendo (o menu é estático); falhas de rede
aparecem como notificação, não como exceção.

Uso: python3 run_plugin.py PERFIL [ARGS_DO_PLUGIN...]
Saída: linhas ``DIR <pasta> <label>`` e ``RUN OK`` / ``EXCEPTION ...``.
"""
import json
import os
import runpy
import sys
import traceback

STUBS = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ID = 'plugin.video.BrazucaPlay.Matrix'
MODULES = {
    'script.module.kodi-six': 'libs',
    'script.module.six': 'lib',
    'script.module.requests': 'lib',
    'script.module.simplejson': 'lib',
    'script.module.beautifulsoup4': 'lib',
    'script.module.soupsieve': 'lib',
    'script.module.urllib3': 'lib',
    'script.module.certifi': 'lib',
    'script.module.chardet': 'lib',
    'script.module.idna': 'lib',
}


def main():
    profile = os.path.abspath(sys.argv[1])
    addons = profile if os.path.basename(profile) == 'addons' else os.path.join(profile, 'addons')
    plugin = os.path.join(addons, PLUGIN_ID)
    if not os.path.isdir(plugin):
        print('EXCEPTION plugin ausente em %s' % plugin)
        return 2

    data_dir = os.path.join(profile, 'userdata', 'addon_data', PLUGIN_ID)
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    for path in [STUBS, plugin] + [os.path.join(addons, name, folder)
                                   for name, folder in MODULES.items()]:
        if os.path.isdir(path):
            sys.path.insert(0, path)

    # os stubs leem estes caminhos do ambiente
    os.environ['SMARTED_STUB_PLUGIN'] = plugin
    os.environ['SMARTED_STUB_ADDON_DATA'] = data_dir
    os.environ['SMARTED_STUB_HOME'] = profile

    sys.argv = ['plugin://%s/' % PLUGIN_ID, '1', '?'] + sys.argv[2:]
    status = 0
    try:
        runpy.run_path(os.path.join(plugin, 'default.py'), run_name='__main__')
    except SystemExit:
        pass
    except BaseException as error:
        print('EXCEPTION %s: %s' % (type(error).__name__, error))
        traceback.print_exc()
        status = 1

    import xbmcplugin
    import xbmcgui
    items = []
    for entry in xbmcplugin.DIRS.values():
        items.extend(entry)
    for url, label, is_folder in items:
        if url == '__END__':
            continue
        print('DIR %s %s' % (1 if is_folder else 0, json.dumps(label, ensure_ascii=False)))
    print('NOTIFICATIONS %d' % len(xbmcgui.NOTIFS))
    print('RUN OK' if status == 0 else 'RUN FAILED')
    return status


if __name__ == '__main__':
    sys.exit(main())
