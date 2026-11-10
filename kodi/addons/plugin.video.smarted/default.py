"""Kodi directory bridge; does not collect or fabricate catalogue data."""
import sys
from urllib.parse import parse_qs

import xbmcgui
import xbmcplugin

from routes import items


def main():
    handle = int(sys.argv[1])
    params = parse_qs(sys.argv[2].lstrip('?'), keep_blank_values=True)
    route = params.get('route', ['root'])[0]
    entries = items(route)
    if not entries:
        xbmcplugin.endOfDirectory(handle, succeeded=False, cacheToDisc=False)
        return
    for label, url in entries:
        item = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(handle, url, item, isFolder=True)
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


if __name__ == '__main__':
    main()
