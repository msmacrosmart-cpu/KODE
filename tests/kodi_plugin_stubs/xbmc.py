# Minimal Kodi stub for offline smoke tests
import os, sys, json
LOG = []
def log(msg, level=1):
    LOG.append(msg)
    sys.stderr.write('[xbmc.log] %s\n' % msg)
def executebuiltin(cmd, wait=False):
    log('executebuiltin: %s' % cmd)
def getCondVisibility(c):
    return False
def getInfoLabel(i):
    if i == 'System.BuildVersion':
        return '21.3 (21.3.0) Git:20251031-a3a448d-dirty'
    if i == 'System.BuildVersionShort':
        return '21.3'
    return ''
def getSkinDir():
    return 'skin.novatv'
def getAddonInfo(i):
    return '/tmp/prof/plugin.video.BrazucaPlay.Matrix'
def translatePath(p):
    home = os.environ.get('SMARTED_STUB_HOME', '/tmp/kodi')
    if p in ('special://home', 'special://home/'):
        return home
    if p in ('special://profile', 'special://profile/'):
        return os.path.join(home, 'userdata')
    return (p.replace('special://home/', home + '/')
             .replace('special://profile/', home + '/userdata/')
             .replace('special://xbmc/', os.environ.get('SMARTED_STUB_XBMC', '/tmp/kodi/xbmc') + '/'))
def getLanguage(*a, **k):
    return 'Portuguese'
def getLocalizedString(*a, **k):
    return ''
def sleep(ms):
    pass
class Monitor(object):
    def abortRequested(self): return False
    def waitForAbort(self, t=0): return False
def Player(*a, **k):
    return None
def PlayList(*a, **k):
    return None
def Keyboard(*a, **k):
    class K:
        def doModal(self): return None
        def getText(self): return ''
    return K()
LOGINFO = 1
LOGFATAL = 4
LOGERROR = 4
LOGWARNING = 2
LOGNONE = 0
def getRegion(*a, **k): return 'Brazil'
def getIPAddress(): return '127.0.0.1'
def getSkinDir(): return 'skin.novatv'
def getSupportedMedia(t): return ''
def setCondVisibility(*a, **k): pass
