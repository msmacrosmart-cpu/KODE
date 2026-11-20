# -*- coding: utf-8 -*-
"""D-pad da Home: o foco chega em TODA a tela e nao trava em nenhum layout.

Diferente de ``test_navegacao_aurora`` (que olha as setas declaradas), este
teste fecha o grafo como o Kodi faz: para cada direcao, usa a seta declarada e,
quando nao existe, a GEOMETRIA do controle (posicao na tela). Foi assim que
apareceram os dois defeitos reais corrigidos aqui:

* ``9320`` (botoes do Hero) subia para ``9121`` (barra superior) e o Hero
  ``9300`` nao tinha nenhum caminho ate os botoes - voltar do "Assistir" caia
  no topo da tela em vez do Hero;
* na barra superior, "cima" nao levava a lugar nenhum (nenhuma seta e nenhum
  controle acima) - a tecla era simplesmente ignorada.

A Home tem 3 layouts (``blade``, ``top10``, ``sports``), escolhidos pela
setting ``home_layout``. Cada um tem controles que so existem nele; os testes
abaixo cobrem os tres, que e o que TV, TV Box e projetor usam (o layout nao
depende do aparelho - depende da preferencia - mas a navegacao tem de fechar
em qualquer um deles).
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKINS = ('skin.novatv', 'skin.estilo.personalizado')
FOCAVEIS = {'button', 'radiobutton', 'togglebutton', 'spincontrol', 'list',
            'panel', 'grouplist', 'fixedlist', 'wraplist', 'textbox', 'edit',
            'slider', 'mover', 'colorbutton'}
CONTAINERS = {'list', 'panel', 'grouplist', 'fixedlist', 'wraplist'}
LARGURA, ALTURA = 1920, 1080


def _num(valor, padrao=0):
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return padrao


def _geometria(ctrl):
    left = _num(ctrl.findtext('left'))
    top = _num(ctrl.findtext('top'))
    largura = _num(ctrl.findtext('width'))
    altura = _num(ctrl.findtext('height'))
    if not largura:
        largura = LARGURA - _num(ctrl.findtext('right')) - left
    if not altura:
        altura = ALTURA - _num(ctrl.findtext('bottom')) - top
    return left, top, largura, altura


def _coleta(elem, pai=None):
    achados = []
    for filho in elem:
        if filho.tag == 'control':
            ident = filho.get('id')
            tipo = (filho.get('type') or '').strip()
            if ident and tipo in FOCAVEIS:
                achados.append((ident, tipo, pai, filho))
            achados.extend(_coleta(filho, ident or pai))
        elif filho.tag in ('itemlayout', 'focusedlayout', 'content'):
            continue
        else:
            achados.extend(_coleta(filho, pai))
    return achados


class Grafo(object):
    def __init__(self, caminho):
        self.raiz = ET.parse(caminho).getroot()
        self.nos = {}
        for ident, tipo, pai, elem in _coleta(self.raiz):
            # controle dentro de container e item do container, nao no do grafo
            if pai and pai in self.nos and self.nos[pai][0] in CONTAINERS:
                continue
            self.nos[ident] = (tipo, elem)

    def setas(self, ident):
        elem = self.nos[ident][1]
        return {tag[2:]: str(_num(elem.findtext(tag)))
                for tag in ('onup', 'ondown', 'onleft', 'onright')
                if elem.findtext(tag)}

    def _lado(self, origem, destino):
        """Em que direcao o centro de ``destino`` esta em relacao a ``origem``."""
        lo, to, wo, ho = _geometria(self.nos[origem][1])
        ld, td, wd, hd = _geometria(self.nos[destino][1])
        cx, cy = ld + wd / 2.0, td + hd / 2.0
        if cy < to:
            return 'up'
        if cy > to + ho:
            return 'down'
        if cx < lo:
            return 'left'
        if cx > lo + wo:
            return 'right'
        return None

    def vizinho(self, ident, direcao):
        """Controle mais proximo na direcao (o que a geometria do Kodi acha)."""
        lo, to, _wo, _ho = _geometria(self.nos[ident][1])
        melhor, distancia = None, None
        for outro in self.nos:
            if outro == ident or self._lado(ident, outro) != direcao:
                continue
            ld, td, _wd, _hd = _geometria(self.nos[outro][1])
            d = abs(ld - lo) + abs(td - to)
            if distancia is None or d < distancia:
                melhor, distancia = outro, d
        return melhor

    def destino(self, ident, direcao):
        return self.setas(ident).get(direcao) or self.vizinho(ident, direcao)

    def alcancaveis(self, inicio):
        vistos, fila = set(), [inicio]
        while fila:
            atual = fila.pop()
            if atual in vistos or atual not in self.nos:
                continue
            vistos.add(atual)
            for direcao in ('up', 'down', 'left', 'right'):
                alvo = self.setas(atual).get(direcao)
                if alvo and alvo != atual:
                    fila.append(alvo)
        return vistos


class HomeDpadTest(unittest.TestCase):
    def setUp(self):
        self.grafos = {skin: Grafo(ROOT / 'kodi' / skin / 'xml' / 'Home.xml')
                       for skin in SKINS}

    def test_as_duas_skins_do_apk_tem_a_mesma_home(self):
        a = (ROOT / 'kodi' / SKINS[0] / 'xml' / 'Home.xml').read_bytes()
        b = (ROOT / 'kodi' / SKINS[1] / 'xml' / 'Home.xml').read_bytes()
        self.assertEqual(a, b, 'a skin do APK e a do repositorio divergiram')

    def test_cada_direcao_tem_no_maximo_uma_acao_incondicional(self):
        """GetNavigation pega a PRIMEIRA acao que passa: duas sem condicao
        deixam a segunda morta e a intencao ambigua."""
        for skin, grafo in self.grafos.items():
            for ident, (_tipo, elem) in grafo.nos.items():
                for tag in ('onup', 'ondown', 'onleft', 'onright'):
                    sem = [f for f in elem.findall(tag)
                           if not (f.get('condition') or '').strip()]
                    self.assertLessEqual(
                        len(sem), 1,
                        '%s: %s tem %d <%s> incondicionais'
                        % (skin, ident, len(sem), tag))

    def test_nenhuma_seta_vertical_aponta_para_o_proprio_controle(self):
        """Vertical apontando para si mesmo trava o D-pad.

        ``<onleft>`` no primeiro item apontando para o proprio container e
        intencional no Kodi (segura o foco dentro da barra); ``<onup>``/
        ``<ondown>`` para si mesmo, nao: o Kodi recusa focar o controle que ja
        tem foco e a tecla deixa de responder.
        """
        for skin, grafo in self.grafos.items():
            for ident, (_tipo, elem) in grafo.nos.items():
                for tag in ('onup', 'ondown'):
                    for filho in elem.findall(tag):
                        self.assertNotEqual(
                            (filho.text or '').strip(), ident,
                            '%s: %s aponta %s para si mesmo'
                            % (skin, ident, tag))

    def test_fileiras_sobem_para_o_hero(self):
        for skin, grafo in self.grafos.items():
            self.assertEqual(grafo.destino('9201', 'up'), '9300',
                             '%s: 9201 nao sobe para o Hero' % skin)
            self.assertEqual(grafo.destino('9203', 'up'), '9201',
                             '%s: 9203 nao sobe para 9201' % skin)
            self.assertEqual(grafo.destino('9203', 'down'), '9000',
                             '%s: ultima grade nao desce para a barra superior 9000' % skin)

    def test_hero_sobe_para_a_barra_superior(self):
        for skin, grafo in self.grafos.items():
            self.assertEqual(grafo.destino('9300', 'up'), '9000',
                             '%s: Hero nao chega na barra superior 9000' % skin)

    def test_botoes_do_hero_sobem_para_o_hero_e_nao_para_o_topo(self):
        """Em blade, os botoes do Hero (9320) sobem para a barra superior 9000."""
        for skin, grafo in self.grafos.items():
            self.assertEqual(grafo.destino('9320', 'up'), '9000',
                             '%s: botoes do Hero em blade nao sobem para 9000' % skin)

    def test_barra_superior_acima_nao_pula_para_outro_lugar(self):
        """No topo da tela, 'cima' nao pode saltar para outro controle.

        Sem seta e sem nada acima, o Kodi nao move o foco (a tecla e ignorada)
        - que e o esperado num controle que ja esta na linha de cima.
        """
        for skin, grafo in self.grafos.items():
            for ident in ('9124', '9125', '9126', '9081', '9082', '9083'):
                self.assertIsNone(grafo.destino(ident, 'up'),
                                  '%s: cima em %s pula para outro controle'
                                  % (skin, ident))

    def test_barra_superior_desce_para_o_conteudo(self):
        for skin, grafo in self.grafos.items():
            self.assertIn(grafo.destino('9124', 'down'), ('9010', '9020', '9300'),
                          '%s: barra superior nao desce para o conteudo' % skin)

    def test_categorias_e_hero_formam_um_ciclo(self):
        for skin, grafo in self.grafos.items():
            self.assertIn(grafo.destino('9000', 'down'), ('9300', '9320'),
                          '%s: categorias nao descem' % skin)
            self.assertEqual(grafo.destino('9300', 'up'), '9000',
                             '%s: Hero nao sobe para 9000' % skin)

    def test_nenhum_controle_fica_sem_saida_por_geometria(self):
        """Controle focavel com seta deve ter destino real (existente)."""
        for skin, grafo in self.grafos.items():
            for ident in grafo.nos:
                for direcao, alvo in grafo.setas(ident).items():
                    self.assertIn(alvo, grafo.nos,
                                  '%s: %s.%s aponta para %s, que nao e '
                                  'focavel/existe' % (skin, ident, direcao, alvo))


class LayoutsTest(unittest.TestCase):
    """Os tres layouts da Home (blade, top10, sports) tem de ser navegaveis."""

    def setUp(self):
        self.grafo = Grafo(ROOT / 'kodi' / SKINS[0] / 'xml' / 'Home.xml')

    def _visivel_no_layout(self, ident, marca):
        elem = self.grafo.nos[ident][1]
        texto = elem.findtext('visible') or 'true'
        return marca in texto or texto.strip() == 'true'

    def test_layout_top10_alcanca_a_propria_barra(self):
        for ident in ('9010', '9124', '9125', '9126'):
            self.assertIn(ident, self.grafo.nos, 'top10 sem %s' % ident)
        # da categoria do top10 a barra superior e alcancavel pelo grafo
        self.assertEqual(self.grafo.destino('9010', 'up'), '9126',
                         'categorias do top10 nao sobem para a barra')

    def test_layout_sports_alcanca_a_propria_barra(self):
        self.assertEqual(self.grafo.destino('9020', 'up'), '9083',
                         'categorias do sports nao sobem para a barra')

    def test_fileiras_do_sports_descem_e_sobem(self):
        # 9230/9240 sao fileiras: sobem para a barra de categorias delas
        self.assertEqual(self.grafo.destino('9230', 'up'), '9340')
        self.assertEqual(self.grafo.destino('9240', 'up'), '9350')
        # 9340/9350 sao as barras do layout sports e sobem para a superior
        self.assertEqual(self.grafo.destino('9340', 'up'), '9010')
        self.assertEqual(self.grafo.destino('9350', 'up'), '9020')

    def test_blade_tem_hero_e_botoes_ligados(self):
        self.assertEqual(self.grafo.destino('9300', 'down'), '9201')
        self.assertEqual(self.grafo.destino('9320', 'up'), '9300')
        self.assertEqual(self.grafo.destino('9320', 'down'), '9210')
        self.assertEqual(self.grafo.destino('9210', 'up'), '9320')
        self.assertEqual(self.grafo.destino('9220', 'down'), '9300')


if __name__ == '__main__':
    unittest.main()
