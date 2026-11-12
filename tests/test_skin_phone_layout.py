"""Contratos da skin para celular/HD: addons, Ajustes e tela cheia.

Três defeitos relatados em 2026-11-11 (log do Kodi + screenshot do aparelho):

1. ``plugin.video.BrazucaPlay.Matrix`` quebrava com
   ``TypeError: quote_from_bytes() expected bytes`` ao abrir Filmes/Séries. A
   causa não é o addon: a skin abria o plugin só com ``mode``/``url``/``name``,
   então ``iconimage``/``fanart`` chegavam ``None`` e o ``addDir`` do plugin
   chamava ``quote_plus(None)``. Toda URL da skin precisa levar os dois.
2. Ajustes tinha ``Skin.SetSetting`` (builtin inexistente no Kodi 21) e uma
   grade de 4 colunas que estourava a borda inferior.
3. A tela não preenchia a largura (faixa vazia à direita): vários controles com
   ``<width>1920</width>`` fixo num canvas que, no aparelho, é a resolução real
   do display (2400x1080).
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import unquote_plus
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SKIN = ROOT / 'kodi/skin.estilo.personalizado'
XML = SKIN / 'xml'
BOOTSTRAP = ROOT / 'kodi/addons/service.smarted.bootstrap'
RUNNER = ROOT / 'tests/kodi_plugin_stubs/run_plugin.py'
PROFILE = os.environ.get('SMARTED_PROFILE', '')

PLUGIN_PREFIX = 'plugin://plugin.video.BrazucaPlay.Matrix/'
FULL_BLEED = re.compile(r'<left>0</left><top>0</top><width>1920</width><height>1080</height>')


def skin_xml_files():
    return sorted(XML.glob('*.xml'))


class PluginCallTest(unittest.TestCase):
    def test_toda_chamada_do_plugin_leva_iconimage_e_fanart(self):
        found = 0
        for path in skin_xml_files():
            text = path.read_text(encoding='utf-8')
            for url in re.findall(re.escape(PLUGIN_PREFIX) + r'\?[^"\'()\s]*', text):
                found += 1
                self.assertIn('iconimage=', url, '%s: %s' % (path.name, url))
                self.assertIn('fanart=', url, '%s: %s' % (path.name, url))
        self.assertGreaterEqual(found, 20, 'esperava as chamadas do plugin na skin')

    def test_plugin_nao_quebra_sem_dados_opcionais(self):
        """Documenta o bug: sem iconimage/fanart o addon estoura TypeError."""
        if not (PROFILE and Path(PROFILE).is_dir()):
            self.skipTest('defina SMARTED_PROFILE com um perfil .kodi semeado')
        result = subprocess.run(
            [sys.executable, str(RUNNER), PROFILE, 'mode=27&url=%23filmes_menu&name=Filmes'],
            capture_output=True, text=True, timeout=600)
        self.assertIn('quote_from_bytes', result.stdout)

    def test_url_da_skin_abre_o_menu_de_filmes(self):
        if not (PROFILE and Path(PROFILE).is_dir()):
            self.skipTest('defina SMARTED_PROFILE com um perfil .kodi semeado')
        home = (XML / 'Home.xml').read_text(encoding='utf-8')
        url = re.search(re.escape(PLUGIN_PREFIX) + r'\?mode=27&amp;url=%23filmes_menu[^"]*', home)
        self.assertIsNotNone(url, 'botão Filmes ausente do Home')
        query = url.group(0).split('?', 1)[1].replace('&amp;', '&')
        self.assertIn('iconimage=', query)
        result = subprocess.run(
            [sys.executable, str(RUNNER), PROFILE, query],
            capture_output=True, text=True, timeout=600)
        self.assertIn('RUN OK', result.stdout, result.stdout[-1500:])
        self.assertIn('PESQUISE POR FILMES', result.stdout)


class SecretUnlockTest(unittest.TestCase):
    """Modo avançado = 5 entradas consecutivas em Ajustes (v1.0.32)."""

    def test_sem_builtin_inexistente_na_skin(self):
        for path in skin_xml_files():
            text = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'), flags=re.S)
            self.assertNotIn('Skin.SetSetting', text, path.name)
            self.assertNotIn('Skin.GetSetting', text, path.name)

    def test_cinco_entradas_em_ajustes_liberam_o_modo_avancado(self):
        source = (BOOTSTRAP / 'check.py').read_text(encoding='utf-8')
        self.assertIn('SETTINGS_VISITS_TO_UNLOCK = 5', source)
        self.assertIn("Skin.SetBool(secret_unlocked)", source)
        self.assertIn('Notification(SMARTEDTV, Modo avancado liberado', source)
        self.assertIn('def bump_settings_visits', source)

    def test_ajustes_conta_uma_visita_por_abertura(self):
        settings = (XML / 'Settings.xml').read_text(encoding='utf-8')
        self.assertIn('<onload>RunScript(service.smarted.bootstrap,secret-cycle)</onload>', settings)

    def test_nao_existe_mais_clique_na_logo(self):
        home = (XML / 'Home.xml').read_text(encoding='utf-8')
        self.assertNotIn('secret-click', home)
        includes = (XML / 'Includes_SecretUnlock.xml').read_text(encoding='utf-8')
        self.assertNotIn('secret-click', includes)
        self.assertNotIn('secret_click_count', includes)
        for path in skin_xml_files():
            self.assertNotIn('secret_click_count', path.read_text(encoding='utf-8'), path.name)

    def test_modo_basico_esconde_opcoes_administrativas(self):
        settings = (XML / 'Settings.xml').read_text(encoding='utf-8')
        avancados = ('File Manager', 'Informa\u00e7\u00f5es do Sistema', 'Event Log', 'Perfis',
                     'Configura\u00e7\u00f5es Avan\u00e7adas', 'Diagn\u00f3stico SMARTED',
                     'Restaurar atalhos', 'LibreELEC')
        for rotulo in avancados:
            bloco = re.search(r'<item>\s*<label>%s</label>.*?</item>' % re.escape(rotulo), settings, re.S)
            self.assertIsNotNone(bloco, rotulo)
            self.assertIn('Skin.HasSetting(secret_unlocked)', bloco.group(0), rotulo)
        # as opcoes do dia a dia continuam sempre visiveis
        for rotulo in ('Add-ons', 'Apar\u00eancia', 'Interface', 'Reprodutor', 'M\u00eddia',
                       'TV ao vivo', 'Servi\u00e7os', 'Favoritos', 'Add-ons de v\u00eddeo', 'Energia'):
            bloco = re.search(r'<item>\s*<label>%s</label>.*?</item>' % re.escape(rotulo), settings, re.S)
            self.assertIsNotNone(bloco, rotulo)
            self.assertNotIn('secret_unlocked', bloco.group(0), rotulo)

    def test_confirmacao_discreta_e_persistente(self):
        settings = (XML / 'Settings.xml').read_text(encoding='utf-8')
        self.assertIn('Modo avan\u00e7ado ativo', settings)
        self.assertIn('<visible>Skin.HasSetting(secret_unlocked)</visible>', settings)
        # Skin.SetBool grava em addon_data/skin.novatv/settings.xml -> sobrevive ao restart
        variables = (XML / 'Variables.xml').read_text(encoding='utf-8')
        self.assertNotIn('secret_click_count', variables)
        self.assertIn('Skin.HasSetting(secret_unlocked)', variables)


class HomeBrazucaFavoritosTest(unittest.TestCase):
    """As linhas/botoes da Home vivem do conteudo real do Brazuca Play.

    v1.0.33 passou a Home para as rotas do addon (antes era mode=15/ponte).
    v1.0.34 vai alem: as tres linhas deixam de listar PASTAS de menu e usam o
    carrossel da ponte, que desce a arvore do addon ate midia (canais e filmes
    reproduzem) ou ate as capas das series. A navegacao interna abre a janela
    Videos com `return`, para o Back continuar nativo.
    """

    def setUp(self):
        self.home = (XML / 'Home.xml').read_text(encoding='utf-8')

    def test_barra_superior_usa_as_pastas_reais_do_addon(self):
        """Cada botao abre a pasta real descoberta no menu do addon.

        O rotulo e a URL chegam por Skin.String (rota sync-nav, que le o menu
        raiz do Brazuca por Files.GetDirectory); o clique e o mesmo builtin
        nativo que o Kodi usa para abrir um diretorio de plugin.
        """
        for slot in range(1, 9):
            bloco = re.search(r'id="%d">.*?</control>' % (9029 + slot), self.home, re.S)
            self.assertIsNotNone(bloco, 'slot %d ausente' % slot)
            texto = bloco.group(0)
            self.assertIn('$INFO[Skin.String(smarted_nav_%d)]' % slot, texto)
            self.assertIn('!String.IsEmpty(Skin.String(smarted_nav_%d))' % slot, texto)
            self.assertIn('RunPlugin(plugin://plugin.video.smarted/?route=abrir-nav&#38;indice=%d)'
                          % (slot - 1), texto)
            self.assertNotIn('mode=21', texto)
            self.assertNotIn('mode=27', texto)

    def test_espacamento_das_opcoes_abaixo_do_hero(self):
        """As opcoes do meio da tela (abaixo do HERO) ficaram mais espacadas."""
        opcoes = re.search(r'<control type="grouplist" id="9300">.*?(?=<control type="button")',
                           self.home, re.S).group(0)
        self.assertIn('<itemgap>38</itemgap>', opcoes)
        self.assertIn('<top>460</top>', opcoes)

    def test_espacamento_da_barra_superior(self):
        """A barra de pastas tambem ganhou mais distancia entre os nomes."""
        barra = re.search(r'<control type="grouplist" id="9000">.*?(?=<control type="group">)',
                          self.home, re.S).group(0)
        self.assertIn('<itemgap>26</itemgap>', barra)
        # mesmo visual: tipografia, cores e textura
        self.assertIn('<font>font12</font>', barra)
        self.assertIn('<textcolor>pb_muted</textcolor>', barra)
        self.assertIn('pb_rounded.png', barra)

    def test_fileiras_com_espaco_vertical_e_sem_sobreposicao(self):
        # rodada 17: Home com apenas Filmes e Series abaixo do HERO
        alturas = {'9202': 200, '9203': 200}
        tops = {}
        for cid in alturas:
            m = re.search(r'<control type="list" id="%s"><left>60</left><top>(\d+)</top>' % cid,
                          self.home)
            tops[cid] = int(m.group(1))
        titulos = {top - 52: top for top in tops.values()}
        ordenadas = sorted(tops.items(), key=lambda par: par[1])
        for (cid, top), (proximo, top_seguinte) in zip(ordenadas, ordenadas[1:]):
            fim = top + alturas[cid]
            self.assertGreaterEqual(top_seguinte, fim + 26,
                                    'fileira %s encosta na seguinte' % cid)
        # a primeira fileira comeca depois dos botoes do HERO (460 + 60)
        primeira = min(tops.values())
        self.assertGreaterEqual(primeira, 600)
        # posters com respiro horizontal
        self.assertIn('<itemgap>28</itemgap>', self.home)
        # nada de Canais nem das linhas da biblioteca do Kodi
        for fora in ('9200', '9204', '9205'):
            self.assertNotIn('<control type="list" id="%s">' % fora, self.home, fora)
        # HERO alterna sozinho de verdade (rolagem nativa, sem roubar foco)
        hero = re.search(r'<control type="list" id="9201">.*?</control>', self.home, re.S).group(0)
        self.assertIn('<autoscroll>8000</autoscroll>', hero)

    def test_barra_superior_nao_tem_mais_categorias_fixas(self):
        for antigo in ('9010', '9011', '9012', '9013', '9014', '9015', '9016'):
            # o id 9010 continua existindo como grouplist do layout top10; o que
            # nao existe mais e o botao de categoria fixa dentro da barra 9000
            self.assertNotIn('<control type="button" id="%s">' % antigo, self.home, antigo)
        barra = re.search(r'<control type="grouplist" id="9000">.*?(?=<control type="group">)',
                          self.home, re.S).group(0)
        # nenhuma categoria fixa dentro da barra: o destino de cada botao e um
        # favorito do addon, resolvido em tempo de execucao
        for fixa in ('mode=21', 'mode=27', 'mode=25', 'mode=31', 'mode=22', 'mode=28',
                     'BrazucaPlay.Matrix'):
            self.assertNotIn(fixa, barra, fixa)
        # a janela de Favoritos do Kodi continua na barra
        self.assertIn('<label>Favoritos</label>', barra)

    def test_home_sincroniza_a_barra_ao_abrir(self):
        # toda abertura da Home relê os favoritos do addon (sem configurar nada)
        self.assertIn('<onload>RunPlugin(plugin://plugin.video.smarted/?route=sync-nav)</onload>',
                      self.home)

    def test_linhas_da_home_usam_o_carrossel_de_conteudo(self):
        esperado = {'9202': 'filmes', '9203': 'recent-series'}
        for lista, alvo in esperado.items():
            bloco = re.search(r'<control type="list" id="%s">.{0,9000}?</content>' % lista, self.home, re.S)
            self.assertIsNotNone(bloco, lista)
            texto = bloco.group(0)
            # a linha nao aponta mais para a pasta de menu do addon
            if alvo == 'recent-series':
                self.assertIn('route=recent-series', texto, lista)
            else:
                self.assertIn('plugin://plugin.video.smarted/?route=carrossel&amp;alvo=%s' % alvo, texto, lista)
            self.assertNotIn('url=%23filmes_menu', texto, lista)
            self.assertNotIn('url=%23series_menu', texto, lista)
            self.assertIn('<content target="videos">', texto, lista)
            # cards com arte real do addon (poster no carrossel, paisagem na linha de series)
            self.assertTrue('$VAR[ItemArt]' in texto or '$VAR[ItemLand]' in texto, lista)
            self.assertIn('<aspectratio', texto, lista)

    def test_hero_e_alimentado_pela_pasta_lancamentos(self):
        bloco = re.search(r'<control type="list" id="9201">.*?<content[^>]*>[^<]*</content>',
                          self.home, re.S)
        self.assertIsNotNone(bloco)
        self.assertIn('route=recent-movies', bloco.group(0))
        self.assertIn('limit="8"', bloco.group(0))
        # o fundo do HERO acompanha o filme em destaque (linha 9201)
        self.assertIn('$INFO[Container(9201).ListItem.Art(fanart)]', self.home)
        self.assertNotIn('$INFO[Container(9200).ListItem.Art(fanart)]', self.home)
        # titulo da linha coerente com a fonte
        self.assertIn('Filmes', self.home)

    def test_hero_mostra_ano_genero_nota_e_data(self):
        variables = (XML / 'Variables.xml').read_text(encoding='utf-8')
        bloco = re.search(r'<variable name="SmartedHeroMeta">(.*?)</variable>', variables, re.S)
        self.assertIsNotNone(bloco, 'falta a variavel de metadados do HERO')
        texto = bloco.group(1)
        self.assertIn('Container(9201).ListItem.Year', texto)
        self.assertIn('Container(9201).ListItem.Genre', texto)
        self.assertIn('Container(9201).ListItem.Rating', texto)
        self.assertIn('Container(9201).ListItem.Premiered', texto)
        self.assertIn('$VAR[SmartedHeroMeta]', self.home)

    def test_home_nao_tem_bloco_de_favoritos(self):
        # v1.0.35: a Home mostra so carrosseis de midia; favoritos ficam no menu
        self.assertNotIn('favourites://', self.home, 'a Home nao deve listar favoritos')
        self.assertIsNone(re.search(r'<control type="list" id="9206">', self.home),
                          'a linha 9206 de favoritos deveria ter saido')
        # a aba Favoritos continua no menu (9019); o que sai e o bloco de cards
        self.assertIn('<label>Favoritos</label>', self.home)

    def test_primeiras_linhas_cabem_na_tela(self):
        # as duas primeiras linhas aparecem sem rolar; as demais ficam abaixo
        for lista, teto in (('9201', 1080), ('9202', 1080)):
            bloco = re.search(r'<control type="list" id="%s"><left>\d+</left><top>(\d+)</top>'
                              r'<right>\d+</right><height>(\d+)</height>' % lista, self.home)
            self.assertIsNotNone(bloco, lista)
            top, altura = int(bloco.group(1)), int(bloco.group(2))
            self.assertLessEqual(top + altura, teto, '%s passa da tela' % lista)

    def test_home_rola_na_vertical(self):
        self.assertIn('id="9400"', self.home, 'falta o grupo rolavel da Home')
        animacoes = re.findall(r'<animation[^>]*end="0,(-\d+)"[^>]*condition="Control\.HasFocus\((\d+)\)"',
                               self.home)
        self.assertGreaterEqual(len(animacoes), 2, 'rolagem vertical precisa animar as linhas de baixo')
        alvos = {cid for _, cid in animacoes}
        self.assertTrue({'9202', '9203'} <= alvos, alvos)
        # o grupo abrange o hero (9300) e as duas fileiras
        self.assertLess(self.home.index('id="9400"'), self.home.index('id="9300"'))
        self.assertLess(self.home.index('id="9300"'), self.home.index('id="9203"'))
        # as animacoes vem antes do conteudo que rolam
        self.assertLess(self.home.index('<animation effect="slide"'), self.home.index('id="9300"'))

    def test_hero_expandido_mostra_lancamentos(self):
        hero = re.search(r'<control type="textbox">(.*?)</control>', self.home, re.S).group(1)
        self.assertIn('Container(9201).ListItem.Plot', hero)
        altura = int(re.search(r'<height>(\d+)</height>', hero).group(1))
        self.assertGreaterEqual(altura, 100, 'sinopse do hero precisa de mais linhas')
        # nada de "LANÇAMENTO" fixo antes de o destaque carregar
        self.assertIn('!String.IsEmpty(Container(9201).ListItem.Label)', hero)

    def test_titulos_so_aparecem_com_conteudo(self):
        for lista in ('9201', '9202', '9203'):
            padrao = (r'<control type="label"><left>60</left><top>(\d+)</top>.*?</control>')
            achado = None
            for m in re.finditer(padrao, self.home, re.S):
                if 'Container(%s)' % lista in m.group(0):
                    achado = m.group(0)
            self.assertIsNotNone(achado, lista)
            self.assertIn('!String.IsEmpty(Container(%s).ListItem.Label)' % lista, achado, lista)

    def test_navegacao_real_dentro_do_addon(self):
        # a barra aponta para o plugin, que abre as pastas reais do addon
        navegacao = (ROOT / 'kodi/addons/plugin.video.smarted/navigation.py').read_text(encoding='utf-8')
        self.assertIn("('TV ao vivo', 21, '#menu_canais')", navegacao)
        self.assertIn("brazuca(0, '')", navegacao)  # menu raiz do addon
        self.assertIn('ActivateWindow(Videos', navegacao)  # abre a pasta no Kodi
        atalhos = (BOOTSTRAP / 'favourites.py').read_text(encoding='utf-8')
        for url in ('#menu_canais', '#filmes_menu', '#series_menu'):
            self.assertTrue(url in atalhos, 'atalho %s ausente' % url)

    def test_variaveis_de_arte_existem(self):
        variables = (XML / 'Variables.xml').read_text(encoding='utf-8')
        self.assertIn('<variable name="ItemArt">', variables)
        self.assertIn('<variable name="ItemLand">', variables)


class NavegacaoCompletaTest(unittest.TestCase):
    """A arvore do Brazuca Play continua acessivel a partir da Home.

    A barra agora e dinamica (favoritos), mas todo destino dela e uma rota real
    do addon: nenhuma lista estatica no lugar do catalogo.
    """

    def setUp(self):
        self.home = (XML / 'Home.xml').read_text(encoding='utf-8')
        self.navegacao = (ROOT / 'kodi/addons/plugin.video.smarted/navigation.py').read_text(
            encoding='utf-8')

    def test_barra_abre_os_destinos_pelo_plugin(self):
        # o botao abre o diretorio do addon como o proprio Kodi faria
        botao = re.search(r'id="9030">.*?</control>', self.home, re.S).group(0)
        self.assertIn('RunPlugin(plugin://plugin.video.smarted/?route=abrir-nav&#38;indice=0)', botao)
        # o plugin abre com ActivateWindow sem ",return" (nunca reusa o diretorio anterior)
        navegacao = (ROOT / 'kodi/addons/plugin.video.smarted/navigation.py').read_text(encoding='utf-8')
        self.assertNotIn("ActivateWindow(Videos,%s,return)", navegacao)

    def test_sem_favoritos_a_barra_usa_o_menu_do_addon(self):
        # ordem: favoritos -> menu raiz do addon -> pastas reais (nunca vazio)
        self.assertIn('def root_entries(rpc):', self.navegacao)
        self.assertIn("brazuca(0, '')", self.navegacao)
        self.assertIn('def folder_entries():', self.navegacao)
        self.assertLess(self.navegacao.index('def favorites_entries'),
                        self.navegacao.index('def folder_entries'))

    def test_atalhos_de_categoria_continuam_abrindo_janela_do_addon(self):
        # o fallback usa as mesmas pastas reais que os botoes antigos abriam
        for rota in ("21, '#menu_canais')", "27, '#filmes_menu')", "27, '#series_menu')",
                     "25, '#novelas_menu')", "22, '#animes_menu')", "31, '#doramas_menu')",
                     "28, '#desenhos_menu')"):
            self.assertIn(rota, self.navegacao)

    def test_barra_superior_tem_so_busca_ajustes_e_sair(self):
        # botao de addons removido a pedido (rodada 15)
        self.assertIsNone(re.search(r'id="9124">', self.home))
        self.assertNotIn('ActivateWindow(10040)', self.home)

    def test_skin_nao_embute_catalogo(self):
        # nada de canais/filmes ficticios na skin: o conteudo vem do addon
        proibido = re.search(r'(Globo|SBT|Netflix|Canais\s*<|Movie\s*<)', self.home)
        self.assertIsNone(proibido, 'a skin nao deve listar canais/filmes fixos')

    def test_ponte_cobre_as_categorias_da_home(self):
        bridge = (BOOTSTRAP.parents[0] / 'plugin.video.smarted' / 'favorites.py').read_text(encoding='utf-8')
        for categoria in ('canais', 'filmes', 'series'):
            self.assertIn("'%s'" % categoria, bridge)


class SettingsScreenTest(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(XML / 'Settings.xml').getroot()

    def test_grade_ancorada_nas_quatro_bordas(self):
        panel = self.root.find(".//control[@id='9000']")
        self.assertIsNotNone(panel)
        self.assertIsNotNone(panel.find('right'), 'painel precisa de <right> para esticar')
        self.assertIsNotNone(panel.find('bottom'), 'painel precisa de <bottom> para não cortar')
        self.assertIsNone(panel.find('height'), 'altura fixa corta a última linha')

    def test_todo_item_tem_icone(self):
        items = self.root.findall(".//control[@id='9000']/content/item")
        self.assertGreaterEqual(len(items), 12)
        for item in items:
            label = item.findtext('label')
            icon = item.findtext('icon')
            self.assertTrue(icon, 'item sem ícone: %s' % label)
            self.assertTrue((SKIN / 'media' / icon).is_file(), icon)

    def test_tiles_cabem_na_tela(self):
        includes = ET.parse(XML / 'Includes.xml').getroot()
        tile = includes.find(".//include[@name='SettingsTile']")
        self.assertIsNotNone(tile, 'include SettingsTile ausente')
        for name in ('itemlayout', 'focusedlayout'):
            layout = tile.find(name)
            self.assertIsNotNone(layout, name)
            self.assertEqual(layout.get('width'), '320')
            self.assertEqual(layout.get('height'), '180')

    def test_cabecalho_nao_sobrepoe(self):
        ids = {c.get('id'): c for c in self.root.iter('control') if c.get('id')}
        voltar = ids['9050']
        self.assertEqual(voltar.findtext('top'), '40')
        self.assertEqual(voltar.findtext('left'), '60')
        titulo = [c for c in self.root.iter('control')
                  if c.get('type') == 'label' and (c.findtext('label') or '') == 'AJUSTES']
        self.assertTrue(titulo)
        self.assertEqual(titulo[0].findtext('left'), '240')


class FullScreenTest(unittest.TestCase):
    def test_resolucao_unica_1080p(self):
        addon = ET.parse(SKIN / 'addon.xml').getroot()
        resolutions = list(addon.iter('res'))
        self.assertEqual(len(resolutions), 1, 'mais de um <res> desalinha o canvas')
        self.assertEqual(resolutions[0].get('width'), '1920')
        self.assertEqual(resolutions[0].get('height'), '1080')
        self.assertEqual(resolutions[0].get('default'), 'true')

    def test_sem_fundo_fixo_de_1920(self):
        for path in skin_xml_files():
            text = path.read_text(encoding='utf-8')
            self.assertIsNone(FULL_BLEED.search(text), path.name)

    def test_fundos_usam_porcentagem(self):
        home = (XML / 'Home.xml').read_text(encoding='utf-8')
        self.assertIn('<width>100%</width><height>100%</height>', home)

    def test_barra_superior_ancorada_a_direita(self):
        root = ET.parse(XML / 'Home.xml').getroot()
        for control_id in ('9121', '9122', '9123'):
            node = root.find(".//control[@id='%s']" % control_id)
            self.assertIsNotNone(node, control_id)
            self.assertIsNotNone(node.find('right'), '%s precisa de <right>' % control_id)

    def test_icones_da_barra_superior_centrados_no_botao(self):
        """Botão e ícone redondos precisam compartilhar o mesmo centro.

        Tudo é ancorado em <right>, então o centro é right + width/2 e não
        depende da largura da tela.
        """
        root = ET.parse(XML / 'Home.xml').getroot()
        buttons = []
        icons = []
        for control in root.iter('control'):
            if control.find('right') is None:
                continue
            right = int(control.findtext('right'))
            width = int(control.findtext('width') or 0)
            if control.get('type') == 'button' and control.get('id') in (
                    '9121', '9122', '9123'):
                buttons.append((control.get('id'), right + width / 2.0))
            if (control.get('type') == 'image'
                    and (control.findtext('texture') or '').startswith('icons/')
                    and width == 28):
                icons.append(right + width / 2.0)
        self.assertEqual(len(buttons), 3)
        for control_id, center in buttons:
            self.assertIn(center, icons, 'ícone não centrado no botão %s' % control_id)

    def test_listas_do_home_esticam_ate_a_borda(self):
        root = ET.parse(XML / 'Home.xml').getroot()
        for control_id in ('9200', '9210', '9220'):
            node = root.find(".//control[@id='%s']" % control_id)
            if node is None:
                continue
            self.assertIsNotNone(node.find('right'), '%s precisa de <right>' % control_id)


if __name__ == '__main__':
    unittest.main()
