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


# (rotulo, acao, widgets) — cada widget e (nome da fileira, tipo, caminho).
#
# UM widget por botao. Antes cada categoria tinha dois (a lista do Brazuca e a
# rota de favoritos): a Home empilhava as duas fileiras no mesmo grouplist
# (itemgap 2), o que aparecia como "lancamentos" duplicados/sobrepostos e
# cortava a segunda fileira no rodape.
#
# A Home fica com as duas fileiras pedidas: Lancamentos/Filmes em cima e
# Series embaixo (o botao Home e o que recebe o foco ao abrir o app).
#
#   TV        -> mode=21 url=#todoscanais  (lista de canais; #menu_canais e menu)
#   Filmes    -> mode=1  lancamentos.xml
#   Series    -> mode=1  SeriesBase
#   Doramas   -> mode=1  DoramasBase
#   Novelas   -> mode=1  novelas.xml
#   Animes    -> mode=1  AnimesBase
#   Desenhos  -> mode=1  DesenhosBase
FILEIRA_FILMES = ('Lan\u00e7amentos', 'movies', destino(1, FILMES, 'Filmes'))
FILEIRA_SERIES = ('S\u00e9ries', 'tvshows', destino(1, SERIES, 'S\u00e9ries'))


def fileira(nome, tipo, mode, url):
    return (nome, tipo, destino(mode, url, nome))


MENU = [
    ('Home', 'ActivateWindow(home,return)', [FILEIRA_FILMES, FILEIRA_SERIES]),
    ('TV', acao(21, '#todoscanais', 'TV'), []),
    ('Filmes', acao(1, FILMES, 'Filmes'), [FILEIRA_FILMES]),
    ('S\u00e9ries', acao(1, SERIES, 'S\u00e9ries'), [FILEIRA_SERIES]),
    ('Doramas', acao(1, DORAMAS, 'Doramas'), [fileira('Doramas', 'tvshows', 1, DORAMAS)]),
    ('Novelas', acao(1, NOVELAS, 'Novelas'), [fileira('Novelas', 'tvshows', 1, NOVELAS)]),
    ('Animes', acao(1, ANIMES, 'Animes'), [fileira('Animes', 'tvshows', 1, ANIMES)]),
    ('Desenhos', acao(1, DESENHOS, 'Desenhos'), [fileira('Desenhos', 'tvshows', 1, DESENHOS)]),
    ('Busca', acao(20, '#pesquisar_filmes', 'Busca'), []),
    ('Ajustes', 'ActivateWindow(Settings)', []),
    ('Sair', 'ActivateWindow(ShutdownMenu)', []),
]


def esc(valor):
    return (valor.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def item(indice, rotulo, acao_, widgets):
    linhas = ['\t\t<item id="%d">' % indice,
              '\t\t\t<property name="id">%d</property>' % indice,
              '\t\t\t<label>%s</label>' % esc(rotulo),
              '\t\t\t<label2>%s</label2>' % esc(rotulo),
              '\t\t\t<icon></icon>',
              '\t\t\t<thumb />',
              '\t\t\t<property name="labelID">%d</property>' % indice,
              '\t\t\t<property name="defaultID">%d</property>' % indice]
    for pos, (nome, tipo, caminho) in enumerate(widgets):
        sufixo = '' if pos == 0 else '.%d' % pos
        linhas += ['\t\t\t<property name="widget%s">%s</property>' % (sufixo, esc(nome)),
                   '\t\t\t<property name="widgetTarget%s">videos</property>' % sufixo,
                   '\t\t\t<property name="widgetType%s">%s</property>' % (sufixo, tipo),
                   '\t\t\t<property name="widgetPath%s">%s</property>' % (sufixo, esc(caminho)),
                   '\t\t\t<property name="widgetName%s">%s</property>' % (sufixo, esc(nome))]
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
    # qualquer widget legado que tenha sobrado cai na lista real de filmes do
    # Brazuca Play (nunca em rota generica nem em playlist ausente)
    return LEGADOS.sub(destino(1, FILMES, 'Filmes').replace('&', '&amp;'), texto)


def gerar_includes(origem: Path) -> str:
    texto = origem.read_text(encoding='utf-8')
    padrao = re.compile(r'\t<include name="skinshortcuts-mainmenu">.*?\n\t</include>', re.S)
    if not padrao.search(texto):
        raise SystemExit('menu superior do skinshortcuts nao encontrado em %s' % origem)
    texto = padrao.sub(lambda _: bloco_menu(), texto, count=1)
    return limpar_widgets_legados(texto)


# Cinza-escuro oficial dos paineis (pedido do usuario): nada de branco na UI.
COR_PAINEL = 'cc121212'
# Respiro entre as duas fileiras de carrossel da Home (px).
ESPACO_FILEIRAS = 36

# A Bingie pinta os paineis com Skin.String(...) usado direto em colordiffuse:
# quando o valor nao e um ARGB valido (o padrao de fabrica e "None") o Kodi cai
# no branco. Era essa a origem do painel branco nas listas de pastas.
# Aqui os valores sao fixados no boot (sem reescrever quando ja estao certos).
TEMA_ESCURO = (
    '\t<!-- Tema escuro SMARTEDTV: paineis sempre em cinza-escuro, nunca branco -->\n'
    '\t<onload condition="!String.IsEqual(Skin.String(GeneralPanelsColor),' + COR_PAINEL + ')">'
    'Skin.SetString(GeneralPanelsColor,' + COR_PAINEL + ')</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(GeneralPanelsColor.name),Black)">'
    'Skin.SetString(GeneralPanelsColor.name,Black)</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(ViewDetailsPanelColor),' + COR_PAINEL + ')">'
    'Skin.SetString(ViewDetailsPanelColor,' + COR_PAINEL + ')</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(ViewDetailsPanelColor.name),Black)">'
    'Skin.SetString(ViewDetailsPanelColor.name,Black)</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(HomeWidgetsBorderColor),' + COR_PAINEL + ')">'
    'Skin.SetString(HomeWidgetsBorderColor,' + COR_PAINEL + ')</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(HomeWidgetsBorderColor.name),Black)">'
    'Skin.SetString(HomeWidgetsBorderColor.name,Black)</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(SideBladePanelColor),' + COR_PAINEL + ')">'
    'Skin.SetString(SideBladePanelColor,' + COR_PAINEL + ')</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(FooterPanelColor),00FFFFFF)">'
    'Skin.SetString(FooterPanelColor,00FFFFFF)</onload>\n'
    '\t<onload condition="!String.IsEqual(Skin.String(HeaderPanelColor),00FFFFFF)">'
    'Skin.SetString(HeaderPanelColor,00FFFFFF)</onload>\n'
    '\t<!-- Fileiras landscape (212 px): duas cabem com respiro na area dos carrosseis -->\n'
    '\t<onload condition="!String.IsEqual(Skin.String(widgetstyle),landscape)">'
    'Skin.SetString(widgetstyle,landscape)</onload>\n'
    '\t<onload condition="!String.IsEqual(Window(Home).Property(widgetstyle),landscape)">'
    'SetProperty(widgetstyle,landscape,Home)</onload>\n'
)

def gerar_home(origem: Path) -> str:
    texto = origem.read_text(encoding='utf-8')
    # 1) o menu e estatico: nada de o skinshortcuts regerar por cima
    texto = re.sub(r'\n[ \t]*<onload>[^<]*script\.skinshortcuts[^<]*</onload>', '', texto)
    texto = texto.replace(
        '\t<!-- Build Menu -->',
        '\t<!-- Build Menu (menu estatico SMARTEDTV: nao regerar) -->', 1)
    # 2) tema escuro fixo (paineis cinza-escuro) + estilo das fileiras
    if 'Skin.SetString(GeneralPanelsColor' not in texto:
        texto = texto.replace('\t<!-- Build Menu', TEMA_ESCURO + '\n\t<!-- Build Menu', 1)
    # 3) garante o layout Bingie ativo mesmo em perfil novo
    if 'Skin.SetString(HomeLayout,bingie)' not in texto:
        texto = texto.replace(
            '\t<onload>Skin.SetBool(tmdbhelper.directcallauto)</onload>',
            '\t<onload>Skin.SetBool(tmdbhelper.directcallauto)</onload>\n'
            '\t<onload condition="String.IsEmpty(Skin.String(HomeLayout))">'
            'Skin.SetString(HomeLayout,bingie)</onload>', 1)
    return texto


def gerar_widgets_home(origem: Path) -> str:
    """Abre espaco vertical entre as fileiras de carrossel da Home.

    O grouplist dos widgets (id 77777) vem com ``<itemgap>2</itemgap>``: as duas
    fileiras ficam coladas e a de baixo e cortada pelo rodape do player.
    """
    texto = origem.read_text(encoding='utf-8')
    texto, trocas = re.subn(r'<itemgap>2</itemgap>',
                            '<itemgap>%d</itemgap>' % ESPACO_FILEIRAS, texto, count=1)
    if trocas != 1:
        raise SystemExit('itemgap do grouplist de widgets nao encontrado em %s' % origem)
    return texto


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    skin, destino = Path(sys.argv[1]), Path(sys.argv[2])
    includes = skin / 'xml' / 'script-skinshortcuts-includes.xml'
    home = skin / 'xml' / 'Home.xml'
    widgets = skin / 'xml' / 'IncludesHomeBingie.xml'
    if not includes.is_file() or not home.is_file() or not widgets.is_file():
        raise SystemExit('skin Bingie invalida: %s' % skin)
    (destino / 'xml').mkdir(parents=True, exist_ok=True)
    (destino / 'xml' / 'script-skinshortcuts-includes.xml').write_text(
        gerar_includes(includes), encoding='utf-8')
    (destino / 'xml' / 'Home.xml').write_text(gerar_home(home), encoding='utf-8')
    (destino / 'xml' / 'IncludesHomeBingie.xml').write_text(
        gerar_widgets_home(widgets), encoding='utf-8')
    print('overlay gerado em %s (%d entradas no menu superior)' % (destino, len(MENU)))


if __name__ == '__main__':
    main()
