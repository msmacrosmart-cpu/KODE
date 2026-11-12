import sys
ITEMS = []
NOTIFS = []
DIALOGS = []
class ListItem(object):
    def __init__(self, label='', label2='', iconImage='', thumbnailImage='', path=''):
        self.label = label; self.path = path
        self.info = {}; self.props = {}
        self._art = {}
    def setLabel(self, v): self.label = v
    def getLabel(self): return self.label
    def setLabel2(self, v): self.label2 = v
    def setArt(self, d): self._art.update(d or {})
    def setArtwork(self, a, b=None): pass
    def setIconImage(self, v): pass
    def setThumbnailImage(self, v): pass
    def setInfo(self, t, d): self.info.update(d or {})
    def setProperty(self, k, v): self.props[k] = v
    def setProperty(self, k, v): self.props[k] = v
    def getProperty(self, k): return self.props.get(k, '')
    def setContentLookup(self, v): pass
    def setPath(self, v): self.path = v
    def getPath(self): return self.path
    def addContextMenuItems(self, *a, **k): pass
    def setMimeType(self, v): pass
    def setSubtitles(self, v): pass
    def isSelected(self): return False
    def getVideoInfoTag(self): return VideoInfoTag()
    def getMusicInfoTag(self): return MusicInfoTag()
    def setCast(self, v): pass
    def setUniqueIDs(self, *a, **k): pass
    def setAvailableFanart(self, *a, **k): pass
def Dialog():
    return Dialog()
class Dialog(object):
    def notification(self, *a, **k): NOTIFS.append(a)
    def ok(self, *a, **k): DIALOGS.append(('ok', a)); return True
    def yesno(self, *a, **k): DIALOGS.append(('yesno', a)); return False
    def select(self, *a, **k): DIALOGS.append(('select', a)); return 0
    def textviewer(self, *a, **k): DIALOGS.append(('textviewer', a))
    def input(self, *a, **k): return ''
    def numeric(self, *a, **k): return 0
    def multiselect(self, *a, **k): return []
    def browse(self, *a, **k): return ''
    def iscanceled(self): return False
    def close(self): pass
class DialogProgress(object):
    def create(self, *a, **k): pass
    def update(self, *a, **k): pass
    def iscanceled(self): return False
    def close(self): pass
class DialogProgressBG(object):
    def create(self, *a, **k): pass
    def update(self, *a, **k): pass
    def close(self): pass
class Window(object):
    def __init__(self, *a, **k): pass
    def setProperty(self, k, v): pass
    def getProperty(self, k): return ''
    def clearProperties(self): pass
    def setProperty(self, k, v): pass
    def doModal(self): pass
    def close(self): pass
class WindowXML(Window): pass
class WindowDialog(Window): pass
class DialogXML(Window): pass
class DialogSelect(object):
    def __init__(self, *a, **k): pass
    def doModal(self): pass
    def getSelectedItem(self): return None
class DialogText(object): pass
class DialogBusy(object): pass
class Control(object): pass
class ControlButton(Control): pass
class ControlImage(Control): pass
class ControlLabel(Control): pass
class ControlList(Control): pass
class ControlTextBox(Control): pass
def getCurrentWindowId(): return 10025
def getCurrentWindowDialogId(): return 9999

class VideoInfoTag(object):
    def __init__(self):
        self._d = {}
    def setTitle(self, v): self._d['title'] = v
    def setOriginalTitle(self, v): pass
    def setMediaType(self, v): self._d['mediatype'] = v
    def setPlot(self, v): self._d['plot'] = v
    def setPlotOutline(self, v): pass
    def setGenres(self, v): self._d['genres'] = v
    def setGenre(self, v): self._d['genre'] = v
    def setDateAdded(self, v): self._d['dateadded'] = v
    def setYear(self, v): self._d['year'] = v
    def setRating(self, *a, **k): pass
    def setVotes(self, *a, **k): pass
    def setCast(self, v): pass
    def setDirectors(self, v): pass
    def setWriters(self, v): pass
    def setDuration(self, v): pass
    def setSeason(self, v): pass
    def setEpisode(self, v): pass
    def setTvShowTitle(self, v): pass
    def setTagline(self, v): pass
    def setTrailer(self, v): pass
    def setIMDBNumber(self, v): pass
    def setUniqueID(self, *a, **k): pass
    def setUniqueIDs(self, *a, **k): pass
    def setSortTitle(self, v): pass
    def setCountries(self, v): pass
    def setStudios(self, v): pass
    def setPremiered(self, v): pass
    def setMpaa(self, v): pass
    def setPath(self, v): pass
    def setFileNameAndPath(self, v): pass
    def addSeason(self, *a, **k): pass
    def addEpisode(self, *a, **k): pass
    def addStreamDetails(self, *a, **k): pass
class MusicInfoTag(object):
    def setTitle(self, v): pass
