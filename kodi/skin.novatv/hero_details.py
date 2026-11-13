"""Show the current hero's full actual plot without changing playback."""
import xbmc
import xbmcgui


def main():
    title = xbmc.getInfoLabel('Container(9100).ListItem.Title')
    if not title:
        title = xbmc.getInfoLabel('Container(9100).ListItem.Label')
    plot = xbmc.getInfoLabel('Container(9100).ListItem.Plot')
    if title:
        xbmcgui.Dialog().textviewer(title, plot or 'Sinopse indisponível para este título.')
    else:
        xbmcgui.Dialog().notification('SMARTEDTV', 'Nenhum título disponível no destaque.')


if __name__ == '__main__':
    main()
