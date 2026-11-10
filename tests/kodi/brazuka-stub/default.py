"""Isolated routing fixture, never used as the real Brazuka add-on."""
import sys
from urllib.parse import parse_qs, unquote_plus
import xbmc
import xbmcgui
import xbmcplugin

args = parse_qs(sys.argv[2].lstrip('?'))
if args.get('mode') == ['27'] and args.get('url') == ['#series_menu']:
    xbmc.log('SMARTED_TEST_BRAZUCA_SERIES_OK', xbmc.LOGWARNING)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), 'plugin://plugin.video.BrazucaPlay.Matrix/?test=1',
                                xbmcgui.ListItem(label='Teste isolado'), isFolder=True)
    xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True, cacheToDisc=False)
elif args.get('mode') == ['6'] and unquote_plus(args.get('url', [''])[0]) == '#series_list=resolver1_tvshows=a+b%20c':
    xbmc.log('SMARTED_TEST_BRAZUCA_SEARCH_RESULT_OK', xbmc.LOGWARNING)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), 'plugin://plugin.video.BrazucaPlay.Matrix/?test=2',
                                xbmcgui.ListItem(label='Resultado sintético'), isFolder=True)
    xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True, cacheToDisc=False)
else:
    xbmc.log('SMARTED_TEST_BRAZUCA_UNEXPECTED_ROUTE', xbmc.LOGERROR)
    xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=False, cacheToDisc=False)
