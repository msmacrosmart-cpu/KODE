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

# Fontes de conteudo reais do Brazuca Play 2.1.4 (lidas do codigo do addon,
# modo=1 => url = base16(base64(url)) na mesma ordem usada por addDir()).
GIST_SERIES = 'https://gist.githubusercontent.com/skyrisk/16070347f20c87c72540f9f805b57a66/raw/'
GIST_NOVELAS = 'https://gist.githubusercontent.com/skyrisk/07f1f4cd1b203cbf2efec959c4e8645a/raw/'
GIST_FILMES = 'https://gist.githubusercontent.com/skyrisk/5b87797329c7b46422565ffbaab3be7e/raw/'

FILMES = GIST_FILMES + 'lancamentos.xml'
SERIES = GIST_SERIES + 'SeriesBase'
DORAMAS = GIST_SERIES + 'DoramasBase'
ANIMES = GIST_SERIES + 'AnimesBase'
DESENHOS = GIST_SERIES + 'DesenhosBase'
NOVELAS = GIST_NOVELAS + 'novelas.xml'

# Favoritos continuam saindo das rotas do plugin.video.smarted
FAVORITOS = SMARTED % 'route=favoritos-%s'

# rotas legadas que geravam erro no log (addons desligados/playlists ausentes)
LEGADOS = re.compile(
    r'plugin://script\.skin\.helper\.widgets/[^<\s"\']*'
    r'|plugin://plugin\.video\.themoviedb\.helper[^<\s\']*'
    r'|special://skin/(?:playlists|extras/widgetplaylists)/[^<\s"\']*\.xsp')


def codificar(url):
    """Mesma codificacao do addon: base16(base64(url)) e depois quote_plus."""
    import base64
    from urllib.parse import quote_plus
    return quote_plus(base64.b16encode(base64.b64encode(url.encode('utf-8'))).decode('ascii'))


def destino(mode, url, nome):
    """URL de plugin que cai direto na listagem final do Brazuca Play."""
    from urllib.parse import quote_plus
    url = codificar(url) if mode == 1 else quote_plus(url)
    return (BRAZUCA % 'url=%s&mode=%d&name=%s&iconimage=DefaultFolder.png'
            '&fanart=DefaultFolder.png&description=Menu'
            % (url, mode, quote_plus(nome)))


def acao(mode, url, nome):
    """Acao no padrao nativo da Bingie (sem aspas) abrindo a listagem final."""
    return 'ActivateWindow(Videos,%s,return)' % destino(mode, url, nome)


# (rotulo, acao, widget principal, tipo de widget, widgets extras)
# Oito botoes na ordem nativa da Bingie, cada um indo direto para a listagem
# final do Brazuca Play (sem menu intermediario de listas):
#   TV        -> mode=21 url=#todoscanais  (lista de canais; #menu_canais e menu)
#   Filmes    -> mode=1  lancamentos.xml
#   Series    -> mode=1  SeriesBase
#   Doramas   -> mode=1  DoramasBase
#   Novelas   -> mode=1  novelas.xml
#   Animes    -> mode=1  AnimesBase
#   Desenhos  -> mode=1  DesenhosBase
MENU = [
    ('Home', 'ActivateWindow(home,return)', '', 'video', []),
    ('TV', acao(21, '#todoscanais', 'TV'), '', 'video', []),
    ('Filmes', acao(1, FILMES, 'Filmes'),
     destino(1, FILMES, 'Filmes'), 'movies', [FAVORITOS % 'filmes']),
    ('Séries', acao(1, SERIES, 'Séries'),
     destino(1, SERIES, 'Séries'), 'tvshows', [FAVORITOS % 'series']),
    ('Doramas', acao(1, DORAMAS, 'Doramas'),
     destino(1, DORAMAS, 'Doramas'), 'tvshows', [FAVORITOS % 'doramas']),
    ('Novelas', acao(1, NOVELAS, 'Novelas'),
     destino(1, NOVELAS, 'Novelas'), 'tvshows', [FAVORITOS % 'novelas']),
    ('Animes', acao(1, ANIMES, 'Animes'),
     destino(1, ANIMES, 'Animes'), 'tvshows', [FAVORITOS % 'animes']),
    ('Desenhos', acao(1, DESENHOS, 'Desenhos'),
     destino(1, DESENHOS, 'Desenhos'), 'tvshows', [FAVORITOS % 'desenhos']),
    ('Busca', acao(20, '#pesquisar_filmes', 'Busca'), '', 'video', []),
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
