#!/usr/bin/env python3
"""Gera o overlay SMARTEDTV para a skin BINGIE MOD.

O overlay nao recria a skin: troca o menu superior gerado pelo
script.skinshortcuts por uma barra fixa com as categorias de VOD do Brazuca Play
e neutraliza os widgets das bibliotecas legadas (Skin Helper Widgets, TMDb Helper
e playlists .xsp que a skin nao entrega), que eram a origem dos erros
"GetDirectory" no log.

Uso:
    python3 tools/kodi/bingie-overlay.py <pasta-da-skin-bingie> <pasta-do-overlay>
"""
import re
import sys
from pathlib import Path

BRAZUCA = 'plugin://plugin.video.BrazucaPlay.Matrix/?%s'
SMARTED = 'plugin://plugin.video.smarted/?%s'

# widget padrao da Home: rota do SMARTED que desce a arvore do addon ate o
# conteudo real da categoria (posteres/filmes que reproduzem)
CARROSSEL = SMARTED % 'route=carrossel&alvo=%s'
LANCAMENTOS = SMARTED % 'route=recent-movies'
SERIES_NOVAS = SMARTED % 'route=recent-series'

# rotas legadas que geravam erro no log (addons desligados/playlists ausentes)
LEGADOS = re.compile(
    r'plugin://script\.skin\.helper\.widgets/[^<\s"\']*'
    r'|plugin://plugin\.video\.themoviedb\.helper[^<\s"\']*'
    r'|special://skin/(?:playlists|extras/widgetplaylists)/[^<\s"\']*\.xsp')


def acao(mode, pasta, nome):
    """Acao nativa: abre a pasta real do add-on Brazuca Play."""
    return ('ActivateWindow(Videos, "%s", return)'
            % (BRAZUCA % 'mode=%s&url=%%23%s&name=%s&iconimage=DefaultFolder.png'
               '&fanart=DefaultFolder.png&description=Menu' % (mode, pasta, nome)))


# (rotulo, acao, widget principal, tipo de widget, widgets extras)
# Barra: TV ao vivo (sem carrossel de canais na Home) + VOD do Brazuca Play.
# Os carrosseis seguem a ordem pedida: Lancamentos, categoria e Favoritos.
MENU = [
    ('TV ao vivo', acao(21, 'menu_canais', 'TV%20ao%20vivo'), '', 'video', []),
    ('Filmes', acao(27, 'filmes_menu', 'Filmes'),
     LANCAMENTOS, 'movies', [CARROSSEL % 'filmes', SMARTED % 'route=favoritos-filmes']),
    ('Séries', acao(27, 'series_menu', 'S%C3%A9ries'),
     SERIES_NOVAS, 'tvshows', [CARROSSEL % 'series', SMARTED % 'route=favoritos-series']),
    ('Novelas', acao(25, 'novelas_menu', 'Novelas'),
     CARROSSEL % 'novelas', 'tvshows', [SMARTED % 'route=favoritos-novelas']),
    ('Animes', acao(22, 'animes_menu', 'Animes'),
     CARROSSEL % 'animes', 'tvshows', [SMARTED % 'route=favoritos-animes']),
    ('Doramas', acao(31, 'doramas_menu', 'Doramas'),
     CARROSSEL % 'doramas', 'tvshows', [SMARTED % 'route=favoritos-doramas']),
    ('Desenhos', acao(28, 'desenhos_menu', 'Desenhos'),
     CARROSSEL % 'desenhos', 'tvshows', [SMARTED % 'route=favoritos-desenhos']),
    ('Busca', 'ActivateWindow(1109,return)', '', 'video', []),
    ('Ajustes', 'ActivateWindow(Settings)', '', 'video', []),
    ('Sair', 'ActivateWindow(ShutdownMenu)', '', 'video', []),
]


def esc(valor):
    return (valor.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def item(indice, rotulo, acao_, widget, tipo, extras):
    linhas = ['\t\t<item id="%d">' % indice,
              '\t\t\t<property name="id">%d</property>' % indice,
              '\t\t\t<label>%s</label>' % esc(rotulo),
              '\t\t\t<label2>%s</label2>' % esc(rotulo),
              '\t\t\t<icon></icon>',
              '\t\t\t<thumb />',
              '\t\t\t<property name="labelID">%d</property>' % indice,
              '\t\t\t<property name="defaultID">%d</property>' % indice]
    if widget:
        linhas += ['\t\t\t<property name="widget">%s</property>' % esc(rotulo),
                   '\t\t\t<property name="widgetTarget">videos</property>',
                   '\t\t\t<property name="widgetType">%s</property>' % tipo,
                   '\t\t\t<property name="widgetPath">%s</property>' % esc(widget),
                   '\t\t\t<property name="widgetName">%s</property>' % esc(rotulo)]
        for pos, extra in enumerate(extras, start=1):
            linhas += ['\t\t\t<property name="widget.%d">%s</property>' % (pos, esc(rotulo)),
                       '\t\t\t<property name="widgetTarget.%d">videos</property>' % pos,
                       '\t\t\t<property name="widgetType.%d">%s</property>' % (pos, tipo),
                       '\t\t\t<property name="widgetPath.%d">%s</property>' % (pos, esc(extra)),
                       '\t\t\t<property name="widgetName.%d">%s</property>' % (pos, esc(rotulo))]
    linhas += ['\t\t\t<onclick>%s</onclick>' % esc(acao_),
               '\t\t\t<property name="path">%s</property>' % esc(acao_),
               '\t\t\t<property name="list">10025</property>',
               '\t\t\t<property name="group">mainmenu</property>',
               '\t\t\t<property name="hasSubmenu">False</property>',
               '\t\t</item>']
    return '\n'.join(linhas)


def bloco_menu():
    itens = '\n'.join(item(i, *entrada) for i, entrada in enumerate(MENU, start=1))
    return '\t<include name="skinshortcuts-mainmenu">\n' + itens + '\n\t</include>'


def limpar_widgets_legados(texto: str) -> str:
    """Troca widgets de addons legados/playlists ausentes pelos do SMARTED."""
    return LEGADOS.sub('plugin://plugin.video.smarted/?route=carrossel&amp;alvo=filmes', texto)


def gerar_includes(origem: Path) -> str:
    texto = origem.read_text(encoding='utf-8')
    padrao = re.compile(r'\t<include name="skinshortcuts-mainmenu">.*?\n\t</include>', re.S)
    if not padrao.search(texto):
        raise SystemExit('menu superior do skinshortcuts nao encontrado em %s' % origem)
    texto = padrao.sub(lambda _: bloco_menu(), texto, count=1)
    return limpar_widgets_legados(texto)


def gerar_home(origem: Path) -> str:
    texto = origem.read_text(encoding='utf-8')
    # 1) o menu e estatico: nada de o skinshortcuts regerar por cima
    texto = re.sub(r'\n[ \t]*<onload>[^<]*script\.skinshortcuts[^<]*</onload>', '', texto)
    texto = texto.replace(
        '\t<!-- Build Menu -->',
        '\t<!-- Build Menu (menu estatico SMARTEDTV: nao regerar) -->', 1)
    # 2) garante o layout Bingie ativo mesmo em perfil novo
    if 'Skin.SetString(HomeLayout,bingie)' not in texto:
        texto = texto.replace(
            '\t<onload>Skin.SetBool(tmdbhelper.directcallauto)</onload>',
            '\t<onload>Skin.SetBool(tmdbhelper.directcallauto)</onload>\n'
            '\t<onload condition="String.IsEmpty(Skin.String(HomeLayout))">'
            'Skin.SetString(HomeLayout,bingie)</onload>', 1)
    return texto


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    skin, destino = Path(sys.argv[1]), Path(sys.argv[2])
    includes = skin / 'xml' / 'script-skinshortcuts-includes.xml'
    home = skin / 'xml' / 'Home.xml'
    if not includes.is_file() or not home.is_file():
        raise SystemExit('skin Bingie invalida: %s' % skin)
    (destino / 'xml').mkdir(parents=True, exist_ok=True)
    (destino / 'xml' / 'script-skinshortcuts-includes.xml').write_text(
        gerar_includes(includes), encoding='utf-8')
    (destino / 'xml' / 'Home.xml').write_text(gerar_home(home), encoding='utf-8')
    print('overlay gerado em %s (%d entradas no menu superior)' % (destino, len(MENU)))


if __name__ == '__main__':
    main()
