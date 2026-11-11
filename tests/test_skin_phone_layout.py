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
                     'Configura\u00e7\u00f5es Avan\u00e7adas', 'Diagn\u00f3stico Brazuca Play',
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

    def test_botoes_abrem_as_rotas_do_addon(self):
        esperado = (('9010', 21, '#menu_canais', 'TV ao vivo'),
                    ('9011', 27, '#filmes_menu', 'Filmes'),
                    ('9012', 27, '#series_menu', 'S\u00e9ries'))
        for botao, modo, marcador, rotulo in esperado:
            bloco = re.search(r'id="%s">.*?</control>' % botao, self.home, re.S)
            self.assertIsNotNone(bloco, botao)
            texto = bloco.group(0)
            self.assertIn('<label>%s</label>' % rotulo, texto)
            self.assertIn('plugin://plugin.video.BrazucaPlay.Matrix/', texto, botao)
            self.assertIn('mode=%d&amp;url=%%23%s' % (modo, marcador.lstrip('#')), texto, botao)
            self.assertIn('ActivateWindow(Videos, "plugin://plugin.video.BrazucaPlay.Matrix/', texto)
            self.assertIn(', return)', texto, botao)
            # a Home nao pode voltar para as rotas mortas da 1.0.32
            self.assertNotIn('mode=15', texto, botao)
            self.assertNotIn('plugin.video.smarted/?route=', texto, botao)

    def test_toda_url_do_addon_leva_icone_para_nao_estourar_o_menu(self):
        """Brazuca 2.1.4 faz quote_plus(iconimage); sem o parametro o menu cai.

        A URL precisa sair completa, como nos botoes do topo, senao o addon
        levanta "quote_from_bytes() expected bytes" e a tela fica vazia.
        """
        urls = re.findall(r'plugin://plugin\.video\.BrazucaPlay\.Matrix/\?[^"<]*', self.home)
        self.assertTrue(urls, 'Home sem chamadas ao Brazuca Play')
        for url in urls:
            self.assertIn('iconimage=', url, url)
            self.assertIn('fanart=', url, url)
            icone = re.search(r'iconimage=([^&]*)', url).group(1)
            self.assertNotEqual(icone, '', url)

    def test_linhas_da_home_usam_o_carrossel_de_conteudo(self):
        esperado = {'9200': 'canais', '9201': 'filmes', '9202': 'series'}
        for lista, alvo in esperado.items():
            bloco = re.search(r'<control type="list" id="%s">.*?</control>\n' % lista, self.home, re.S)
            self.assertIsNotNone(bloco, lista)
            texto = bloco.group(0)
            # a linha nao aponta mais para a pasta de menu do addon
            self.assertIn('plugin://plugin.video.smarted/?route=carrossel&amp;alvo=%s' % alvo, texto, lista)
            self.assertNotIn('url=%23filmes_menu', texto, lista)
            self.assertNotIn('url=%23series_menu', texto, lista)
            self.assertIn('<content target="videos">', texto, lista)
            # cards com poster, como a grade do addon
            self.assertIn('$VAR[ItemArt]', texto)
            self.assertIn('<aspectratio>keep</aspectratio>', texto)

    def test_home_nao_tem_bloco_de_favoritos(self):
        # v1.0.35: a Home mostra so carrosseis de midia; favoritos ficam no menu
        self.assertNotIn('favourites://', self.home, 'a Home nao deve listar favoritos')
        self.assertIsNone(re.search(r'<control type="list" id="9206">', self.home),
                          'a linha 9206 de favoritos deveria ter saido')
        # a aba Favoritos continua no menu (9019); o que sai e o bloco de cards
        self.assertIn('<label>Favoritos</label>', self.home)

    def test_primeiras_linhas_cabem_na_tela(self):
        # as duas primeiras linhas aparecem sem rolar; as demais ficam abaixo
        for lista, teto in (('9200', 1080), ('9201', 1080)):
            bloco = re.search(r'<control type="list" id="%s"><left>\d+</left><top>(\d+)</top>'
                              r'<right>\d+</right><height>(\d+)</height>' % lista, self.home)
            self.assertIsNotNone(bloco, lista)
            top, altura = int(bloco.group(1)), int(bloco.group(2))
            self.assertLessEqual(top + altura, teto, '%s passa da tela' % lista)

    def test_home_rola_na_vertical(self):
        self.assertIn('id="9400"', self.home, 'falta o grupo rolavel da Home')
        animacoes = re.findall(r'<animation[^>]*end="0,(-\d+)"[^>]*condition="Control\.HasFocus\((\d+)\)"',
                               self.home)
        self.assertGreaterEqual(len(animacoes), 3, 'rolagem vertical precisa animar as linhas de baixo')
        alvos = {cid for _, cid in animacoes}
        self.assertTrue({'9202', '9203', '9204', '9205'} <= alvos, alvos)
        # o grupo abrange o hero (9300) e as linhas ate 9205
        self.assertLess(self.home.index('id="9400"'), self.home.index('id="9300"'))
        self.assertLess(self.home.index('id="9300"'), self.home.index('id="9205"'))
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
        for lista in ('9200', '9201', '9202', '9203'):
            padrao = (r'<control type="label"><left>60</left><top>(\d+)</top>.*?</control>')
            achado = None
            for m in re.finditer(padrao, self.home, re.S):
                if 'Container(%s)' % lista in m.group(0):
                    achado = m.group(0)
            self.assertIsNotNone(achado, lista)
            self.assertIn('!String.IsEmpty(Container(%s).ListItem.Label)' % lista, achado, lista)

    def test_navegacao_real_dentro_do_addon(self):
        # o menu completo do addon (pastas, subpastas, canais, filmes, series) continua acessivel
        self.assertTrue('id="9022"' in self.home, 'falta o botao do menu completo do addon')
        self.assertTrue('plugin://plugin.video.BrazucaPlay.Matrix/?mode=0' in self.home,
                        'o botao Brazuca Play deve abrir o menu raiz do addon')
        atalhos = (BOOTSTRAP / 'favourites.py').read_text(encoding='utf-8')
        for url in ('#menu_canais', '#filmes_menu', '#series_menu'):
            self.assertTrue(url in atalhos, 'atalho %s ausente' % url)

    def test_variaveis_de_arte_existem(self):
        variables = (XML / 'Variables.xml').read_text(encoding='utf-8')
        self.assertIn('<variable name="ItemArt">', variables)
        self.assertIn('<variable name="ItemLand">', variables)


class NavegacaoCompletaTest(unittest.TestCase):
    """A arvore original do Brazuca Play continua acessivel a partir da skin.

    Home tem atalhos (favoritos), mas o menu raiz do addon e todas as suas
    pastas precisam estar a um clique: nada de lista estatica no lugar do addon.
    """

    def setUp(self):
        self.home = (XML / 'Home.xml').read_text(encoding='utf-8')

    def test_botao_abre_o_menu_raiz_do_addon(self):
        bloco = re.search(r'id="9022">.*?</control>', self.home, re.S)
        self.assertIsNotNone(bloco, 'falta o botao do addon')
        texto = bloco.group(0)
        self.assertIn('<label>Brazuca Play</label>', texto)
        self.assertIn('ActivateWindow(Videos, "plugin://plugin.video.BrazucaPlay.Matrix/', texto)
        self.assertIn('plugin://plugin.video.BrazucaPlay.Matrix/?mode=0', texto)

    def test_todo_atalho_executa_o_addon_e_nao_uma_lista_da_skin(self):
        esperado = {
            '9013': 'mode=25&amp;url=%23novelas_menu',
            '9014': 'mode=22&amp;url=%23animes_menu',
            '9015': 'mode=31&amp;url=%23doramas_menu',
            '9016': 'mode=28&amp;url=%23desenhos_menu',
        }
        for botao, rota in esperado.items():
            bloco = re.search(r'id="%s">.*?</control>' % botao, self.home, re.S)
            self.assertIsNotNone(bloco, botao)
            texto = bloco.group(0)
            self.assertIn('ActivateWindow(Videos, "plugin://plugin.video.BrazucaPlay.Matrix/', texto, botao)
            self.assertIn(rota, texto, botao)
            self.assertIn('iconimage=', texto, botao)
            self.assertIn('fanart=', texto, botao)

    def test_atalhos_de_categoria_abrem_a_janela_do_addon(self):
        for botao, modo in (('9010', 21), ('9011', 27), ('9012', 27)):
            bloco = re.search(r'id="%s">.*?</control>' % botao, self.home, re.S)
            texto = bloco.group(0)
            self.assertIn('plugin://plugin.video.BrazucaPlay.Matrix/', texto, botao)
            self.assertIn('mode=%d&amp;url=' % modo, texto, botao)
            self.assertIn('ActivateWindow(Videos, "plugin://plugin.video.BrazucaPlay.Matrix/', texto, botao)

    def test_addons_continuam_alcancaveis_pela_barra_superior(self):
        bloco = re.search(r'id="9124">.*?</control>', self.home, re.S)
        self.assertIn('ActivateWindow(10040)', bloco.group(0))

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

        Regressão de 2026-11-11: o botão Add-ons (9124) ficou com o ícone
        deslocado 16 px para a direita, aparecendo "de um lado e o ícone do
        outro". Como tudo é ancorado em <right>, o centro é
        right + width/2 — não depende da largura da tela.
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
                    '9121', '9122', '9123', '9124'):
                buttons.append((control.get('id'), right + width / 2.0))
            if (control.get('type') == 'image'
                    and (control.findtext('texture') or '').startswith('icons/')
                    and width == 28):
                icons.append(right + width / 2.0)
        self.assertEqual(len(buttons), 4)
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
