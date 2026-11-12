import os
# Caminhos definidos por run_plugin.py (perfil informado na linha de comando)
ADDON_PATH = os.environ.get('SMARTED_STUB_PLUGIN',
                            '/tmp/prof/plugin.video.BrazucaPlay.Matrix')
ADDON_DATA = os.environ.get('SMARTED_STUB_ADDON_DATA',
                            '/tmp/kodi/userdata/addon_data/plugin.video.BrazucaPlay.Matrix')
SETTINGS = {}
class Addon(object):
    def __init__(self, id=None):
        self.id = id or 'plugin.video.BrazucaPlay.Matrix'
    def getAddonInfo(self, k):
        m = {'path': ADDON_PATH, 'id': self.id, 'name': 'BrazucaPlay', 'version': '2.1.4',
             'profile': ADDON_DATA, 'icon': 'icon.png', 'fanart': 'fanart.jpg',
             'author': 'Brazuca', 'disclaimer': '', 'summary': '', 'description': '',
             'stars': '0', 'prebuilt': 'false', 'type': 'xbmc.python.pluginsource'}
        return m.get(k, '')
    def getLocalizedString(self, i): return ''
    def getSetting(self, k): return SETTINGS.get(k, 'true')
    def getSettingString(self, k): return SETTINGS.get(k, '')
    def getSettingBool(self, k): return SETTINGS.get(k, 'true') == 'true'
    def getSettingInt(self, k): return int(SETTINGS.get(k, '0') or 0)
    def setSetting(self, k, v): SETTINGS[k] = v
    def openSettings(self): pass
    def getVersions(self): return []
def get_addon_info(i):
    return Addon().getAddonInfo(i)
