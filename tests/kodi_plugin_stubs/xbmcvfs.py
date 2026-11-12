import os, shutil
HOME = os.environ.get('SMARTED_STUB_HOME', '/tmp/kodi')
def _translate(p):
    if p in ('special://home', 'special://home/'):
        return HOME
    if p in ('special://profile', 'special://profile/'):
        return os.path.join(HOME, 'userdata')
    if p in ('special://temp', 'special://temp/'):
        return os.path.join(HOME, 'temp')
    if p in ('special://xbmc', 'special://xbmc/'):
        return os.environ.get('SMARTED_STUB_XBMC', '/tmp/kodi/xbmc')
    return (p.replace('special://home/', HOME + '/')
             .replace('special://profile/', HOME + '/userdata/')
             .replace('special://xbmc/', os.environ.get('SMARTED_STUB_XBMC', '/tmp/kodi/xbmc') + '/')
             .replace('special://temp/', HOME + '/temp/'))
def translatePath(p):
    return _translate(p)
def exists(p):
    return os.path.exists(translatePath(p))
def mkdir(p):
    try:
        os.makedirs(translatePath(p), exist_ok=True); return True
    except Exception: return False
def mkdirs(p): return mkdir(p)
def delete(p):
    try: os.remove(translatePath(p)); return True
    except Exception: return False
def rmdir(p, force=False):
    try: shutil.rmtree(translatePath(p), ignore_errors=True); return True
    except Exception: return False
def rename(a, b):
    try: os.rename(translatePath(a), translatePath(b)); return True
    except Exception: return False
def copy(a, b):
    try: shutil.copy(translatePath(a), translatePath(b)); return True
    except Exception: return False
def listdir(p):
    d = translatePath(p)
    try:
        names = os.listdir(d)
        return [n for n in names if os.path.isdir(os.path.join(d,n))], [n for n in names if os.path.isfile(os.path.join(d,n))]
    except Exception: return [], []
def File(p):
    return File(p)
class File(object):
    def __init__(self, p, mode='r'):
        self.p = translatePath(p); self.mode = mode; self.f = None
    def open(self):
        try:
            self.f = open(self.p, 'rb' if 'b' in self.mode else 'r'); return True
        except Exception: return False
    def read(self, n=-1):
        try: return self.f.read(n)
        except Exception: return b'' if 'b' in self.mode else ''
    def readBytes(self, n=-1): return b''
    def write(self, d):
        if not self.f: self.f = open(self.p, 'w'); 
        self.f.write(d); return True
    def close(self): 
        if self.f: self.f.close()
    def size(self):
        try: return os.path.getsize(self.p)
        except Exception: return 0
