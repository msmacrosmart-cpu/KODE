DIRS = {}
def addDirectoryItem(handle, url, li=None, isFolder=False, totalItems=0, listitem=None):
    li = li if li is not None else listitem
    DIRS.setdefault(handle, []).append((url, li.label if hasattr(li,'label') else str(li), isFolder))
    return True
def addDirectoryItems(handle, items, total=0):
    DIRS.setdefault(handle, []).extend([(i[0], i[1].label if hasattr(i[1],'label') else str(i[1]), i[2]) for i in items])
    return True
def endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True):
    DIRS.setdefault(handle, []).append(('__END__', succeeded, False))
def setResolvedUrl(handle, succeeded, li): pass
def setContent(handle, content): pass
def setPluginCategory(handle, category): pass
def addSortMethod(*a, **k): pass
def setSetting(*a, **k): pass
def getSetting(*a, **k): return ''
def addToPlaylist(*a, **k): pass
SORT_METHOD_NONE = 0
SORT_METHOD_UNSORTED = 40
SORT_METHOD_LABEL = 1
SORT_METHOD_TITLE = 2
SORT_METHOD_VIDEO_TITLE = 11
SORT_METHOD_DATE = 3
SORT_METHOD_GENRE = 16
SORT_METHOD_EPISODE = 23
SORT_METHOD_UNSORTED = 40
