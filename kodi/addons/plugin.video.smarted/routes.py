"""Real entry points provided by Brazuca Play 2.1.4.

No catalogue data is embedded here. Deeper navigation and playback remain the
responsibility of the installed Brazuca add-on.
"""
from urllib.parse import urlencode

BRAZUCA = 'plugin://plugin.video.BrazucaPlay.Matrix/'
SMARTED = 'plugin://plugin.video.smarted/'


def brazuca(mode, url):
    return BRAZUCA + '?' + urlencode({'url': url, 'mode': mode})


def smarted(route):
    return SMARTED + '?' + urlencode({'route': route})


def items(route):
    if route == 'root':
        return [
            ('TV ao vivo', brazuca(21, '#menu_canais')),
            ('Filmes', brazuca(27, '#filmes_menu')),
            ('Séries', smarted('series')),
        ]
    if route == 'series':
        return [
            ('Séries', brazuca(27, '#series_menu')),
            ('Novelas', brazuca(25, '#novelas_menu')),
            ('Animes', brazuca(22, '#animes_menu')),
            ('Doramas', brazuca(31, '#doramas_menu')),
            ('Desenhos', brazuca(28, '#desenhos_menu')),
        ]
    return []
