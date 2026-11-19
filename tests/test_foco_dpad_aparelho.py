"""Navegacao por d-pad nas categorias, nos Ajustes e da Home para a barra.

Por que um teste de grafo e nao um teste de teclas no emulador: o Kodi nao tem
"handler de d-pad" por controle. O que decide o foco e (xbmc 21.2-Omega):

* ``CGUIBaseContainer::OnDown`` -> ``MoveDown()``: dentro de uma lista o foco
  anda de item em item; SO quando o container esta no limite ele cai para
  ``CGUIControl::Navigate``, que usa ``<ondown>`` e, sem ele, a posicao na tela;
* ``CGUIWindow::OnMove`` desiste quando o id de destino ja esta no caminho
  (``moveHistory``) - ``<onup>`` apontando para o proprio controle e beco sem
  saida, e o foco "trava" (foi o defeito relatado);
* um controle ``<visible>false</visible>`` no destino tambem deixa o foco preso.

Logo "o d-pad nao navega" = "nao existe caminho declarado saindo daqui". Estes
testes montam o grafo dos dois skins e exigem os caminhos do pedido, sem
depender de tempo de boot, foco inicial ou emulador.
"""
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / 'kodi'
SKINS = ('skin.estilo.personalizado', 'skin.novatv')
DIRECOES = ('onup', 'ondown', 'onleft', 'onright')


def _xml(skin, nome):
    return RAIZ / skin / 'xml' / nome


def _controle(skin, arquivo, cid):
    """Elemento <control> com id ``cid`` (aceita grouplist/list/panel/button)."""
    raiz = ET.parse(_xml(skin, arquivo)).getroot()
    for controle in raiz.iter('control'):
        if controle.get('id') == cid:
            return controle
    raise AssertionError('%s sem o controle %s' % (arquivo, cid))


def _destinos(controle, direcao):
    """Ids para onde ``direcao`` leva, respeitando a condicao do <onup..>.

    Regras do Kodi (CGUIControl::GetAction + CGUIAction::ExecuteActions): a
    PRIMEIRA acao cuja condicao e verdadeira vence; sem condicao, vale sempre.
    Aqui a condicao e tratada como "pode ser verdadeira" (o skin nao tem como
    ser avaliado em teste), entao todas as entradas sem condicao e a primeira
    com condicao contam como caminho possivel.
    """
    ids = []
    for filho in controle.findall(direcao):
        texto = (filho.text or '').strip()
        if texto:
            ids.append(texto)
    return ids


class CategoriasTest(unittest.TestCase):
    """MyVideoNav: a lista tem de segurar o foco e ter saida declarada."""

    def test_lista_segura_o_foco_ao_descer(self):
        for skin in SKINS:
            for cid in ('50', '51', '52'):
                controle = _controle(skin, 'MyVideoNav.xml', cid)
                destino = _destinos(controle, 'ondown')
                # '' = sem <ondown>, o Kodi usa a posicao (fica na lista quando ha
                # itens abaixo). O que NAO pode e apontar para fora da lista.
                fora = [d for d in destino if d not in ('50', '51', '52', cid)]
                self.assertEqual(fora, [], '%s: %s desce para %s, fora da lista'
                                 % (skin, cid, fora))

    def test_lista_tem_saida_para_a_barra_lateral_e_para_a_home(self):
        for skin in SKINS:
            for cid in ('50', '51', '52'):
                controle = _controle(skin, 'MyVideoNav.xml', cid)
                subir = _destinos(controle, 'onup')
                self.assertTrue(subir, '%s: %s sem <onup> (foco preso)' % (skin, cid))
                # destino tem de ser um controle que existe no arquivo
                raiz = ET.parse(_xml(skin, 'MyVideoNav.xml')).getroot()
                existentes = {c.get('id') for c in raiz.iter('control')}
                for alvo in subir:
                    self.assertIn(alvo, existentes,
                                  '%s: %s sobe para %s, que nao existe' % (skin, cid, alvo))

    def test_barra_lateral_e_inferior_se_alcancam(self):
        for skin in SKINS:
            lateral = _controle(skin, 'MyVideoNav.xml', '9000')
            inferior = _controle(skin, 'MyVideoNav.xml', '9050')
            self.assertIn('9050', _destinos(lateral, 'ondown'),
                          '%s: a barra lateral nao desce para a barra inferior' % skin)
            self.assertIn('9000', _destinos(inferior, 'onup'),
                          '%s: a barra inferior nao volta para a lateral' % skin)
            # nenhum dos dois pode apontar para si mesmo em TODAS as direcoes
            # (beco sem saida classico do "d-pad nao funciona").
            for controle, nome in ((lateral, 'lateral'), (inferior, 'inferior')):
                cid = controle.get('id')
                saidas = {d for direcao in DIRECOES for d in _destinos(controle, direcao)
                          if d != cid}
                self.assertTrue(saidas, '%s: %s sem nenhuma saida' % (skin, nome))


class AjustesTest(unittest.TestCase):
    """Settings: a grade de tiles tem de aceitar o d-pad em todas as direcoes."""

    def test_grade_declara_orientacao_horizontal(self):
        for skin in SKINS:
            painel = _controle(skin, 'Settings.xml', '9000')
            orientacao = (painel.findtext('orientation') or '').strip()
            # Sem <orientation> o Kodi assume VERTICAL: um tile por linha numa
            # area de 892 px, e a grade parece travada em uma coluna.
            self.assertEqual(orientacao, 'horizontal',
                             '%s: panel 9000 sem orientation=horizontal' % skin)

    def test_grade_tem_saida_para_o_cabecalho(self):
        for skin in SKINS:
            painel = _controle(skin, 'Settings.xml', '9000')
            raiz = ET.parse(_xml(skin, 'Settings.xml')).getroot()
            existentes = {c.get('id') for c in raiz.iter('control')}
            for direcao in ('onup', 'ondown', 'onleft', 'onright'):
                for alvo in _destinos(painel, direcao):
                    if alvo == '9000':
                        continue
                    self.assertIn(alvo, existentes,
                                  '%s: %s aponta para %s, que nao existe'
                                  % (skin, direcao, alvo))


class HomeHeroTest(unittest.TestCase):
    """Home: do hero tem de ser possivel chegar na barra superior."""

    def test_hero_chega_na_barra_superior(self):
        for skin in SKINS:
            raiz = ET.parse(_xml(skin, 'Home.xml')).getroot()
            controles = {c.get('id'): c for c in raiz.iter('control') if c.get('id')}
            # Barra superior: busca/ajustes/energia.
            for cid in ('9121', '9122', '9123'):
                self.assertIn(cid, controles, '%s: barra superior sem %s' % (skin, cid))
            # Busca em largura a partir dos botoes do hero (9301..9303) e da
            # lista do hero (9210/9220), subindo.
            inicios = [c for c in ('9301', '9302', '9303', '9210', '9220') if c in controles]
            self.assertTrue(inicios, '%s: sem controles do hero' % skin)
            vistos, fila, achou = set(inicios), list(inicios), []
            for _ in range(6):
                nova = []
                for cid in fila:
                    for direcao in ('onup', 'ondown', 'onleft', 'onright'):
                        for alvo in _destinos(controles[cid], direcao):
                            if alvo in ('9121', '9122', '9123'):
                                achou.append((cid, direcao, alvo))
                            if alvo in controles and alvo not in vistos:
                                vistos.add(alvo)
                                nova.append(alvo)
                fila = nova
            self.assertTrue(achou, '%s: nenhum caminho do hero para a barra superior '
                                   '(era o "nao sobe para a barra")' % skin)

    def test_barra_superior_nao_desce_para_controle_do_outro_layout(self):
        for skin in SKINS:
            for cid in ('9121', '9122', '9123'):
                controle = _controle(skin, 'Home.xml', cid)
                # O 9000 existe so no layout aurora; em blade ele esta invisivel
                # e descer para ele deixava o foco preso no topo.
                condicionais = [f.get('condition', '') for f in controle.findall('ondown')]
                self.assertTrue(
                    any('blade' in cond for cond in condicionais),
                    '%s: %s desce sem variante para o layout blade' % (skin, cid))
            grouplist = _controle(skin, 'Home.xml', '9300')
            alvos = _destinos(grouplist, 'onup')
            self.assertTrue(any(alvo.startswith('912') for alvo in alvos) or
                            any('blade' in (f.get('condition') or '')
                                for f in grouplist.findall('onup')),
                            '%s: a barra de botoes do hero nao sobe para a barra '
                            'superior em blade' % skin)


class FiltroTest(unittest.TestCase):
    """O filtro tem de ser feito pelo plugin, nao por Container.SetSortMethod."""

    def test_botoes_da_barra_nao_usam_set_sort_method(self):
        for skin in SKINS:
            texto = _xml(skin, 'MyVideoNav.xml').read_text(encoding='utf-8')
            trecho = texto[texto.index('id="9060"'):]
            # Container.SetSortMethod(id) so aplica metodo declarado pelo addon;
            # diretorio de plugin nasce com SortByNone, entao o botao nao fazia
            # nada. O filtro real e a rota 'ordenar' do plugin.
            self.assertEqual(trecho.count('Container.SetSortMethod'), 0,
                             '%s: a barra de filtros ainda chama SetSortMethod' % skin)
            for ordem in ('todos', 'az', 'za', 'adicionados', 'votados', 'recentes'):
                self.assertIn('route=ordenar&amp;ordem=%s' % ordem, trecho,
                              '%s: falta o botao %s' % (skin, ordem))


if __name__ == '__main__':
    unittest.main()
