# -*- coding: utf-8 -*-
"""Home Aurora: o foco tem de subir das fileiras ate a barra superior.

Regressao que voltou: o commit d91326f trocou, nas fileiras 9201/9203, a regra
de subida por tres <onup> sobrepostos - 9300, 9201 e 9203. No Kodi 21
``CGUIControlFactory::GetActions`` acumula os <onup> e ``CGUIAction::GetNavigation``
devolve a PRIMEIRA acao sem condicao cuja condicao passa. Com os tres sem
condicao, o primeiro (9300) vence; mas quando o hero esta invisivel (setting
pb_hide_hero) o salto nao acontece e o foco fica preso na fileira. O mesmo
padrao em 9201 apontando para 9201 criava o auto-salto que o Kodi recusa em
``CGUIWindow::OnMove`` (moveHistory).

A regra que funcionava (873542f) e a que estes testes travam: subir sai SEMPRE
para um controle que existe no layout ativo, e cada direcao tem UMA acao
incondicional (as condicionais vem antes, para o caso da blade).
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKINS = ('skin.novatv', 'skin.estilo.personalizado')
# Controles que existem no layout Aurora (o da TV/projetor), pela visibilidade
# dos grupos do proprio XML.
AURORA = ('9000', '9121', '9122', '9123', '9201', '9203', '9300', '9301',
          '9302', '9303')


def _home(skin):
    return ET.parse(ROOT / 'kodi' / skin / 'xml' / 'Home.xml').getroot()


def _ctrl(raiz, ident):
    achado = raiz.find(".//control[@id='%s']" % ident)
    if achado is None:
        raise AssertionError('controle %s ausente' % ident)
    return achado


def _alvos(ctrl, tag):
    return [(f.text or '').strip() for f in ctrl.findall(tag)]


def _sem_condicao(ctrl, tag):
    return [(f.text or '').strip() for f in ctrl.findall(tag)
            if not (f.get('condition') or '').strip()]


class AuroraDpadTest(unittest.TestCase):
    def test_cada_direcao_tem_um_alvo_incondicional_so(self):
        """Duas acoes incondicionais na mesma direcao = a segunda nunca roda
        (GetNavigation pega a primeira) e a intencao fica ambigua."""
        for skin in SKINS:
            raiz = _home(skin)
            for ctrl in raiz.iter('control'):
                if not ctrl.get('id'):
                    continue
                for tag in ('onup', 'ondown', 'onleft', 'onright'):
                    sem = _sem_condicao(ctrl, tag)
                    self.assertLessEqual(
                        len(sem), 1,
                        '%s: controle %s tem %d <%s> sem condicao: %s'
                        % (skin, ctrl.get('id'), len(sem), tag, sem))

    def test_fileiras_sobem_para_controles_do_layout_ativo(self):
        for skin in SKINS:
            raiz = _home(skin)
            for ident in ('9201', '9203'):
                subidas = _alvos(_ctrl(raiz, ident), 'onup')
                self.assertTrue(subidas, '%s: %s sem onup' % (skin, ident))
                for alvo in subidas:
                    self.assertIn(alvo, AURORA,
                                  '%s: %s sobe para %s, que nao existe na '
                                  'Aurora (foco preso)' % (skin, ident, alvo))

    def test_fileira_nao_sobe_para_si_mesma(self):
        for skin in SKINS:
            raiz = _home(skin)
            for ident in ('9201', '9203'):
                self.assertNotIn(ident, _alvos(_ctrl(raiz, ident), 'onup'),
                                 '%s: %s sobe para si mesma' % (skin, ident))

    def test_hero_sobe_para_a_barra_superior_inclusive_na_aurora(self):
        for skin in SKINS:
            raiz = _home(skin)
            subidas = _alvos(_ctrl(raiz, '9300'), 'onup')
            self.assertIn('9000', subidas,
                          '%s: hero nao chega na barra superior 9000' % skin)
            incondicionais = _sem_condicao(_ctrl(raiz, '9300'), 'onup')
            self.assertEqual(incondicionais, ['9000'],
                             '%s: a subida do hero tem de valer em todo layout'
                             % skin)

    def test_barra_superior_desce_para_o_hero_em_cada_layout(self):
        for skin in SKINS:
            raiz = _home(skin)
            for ident in ('9121', '9122', '9123'):
                self.assertIn('9000', _alvos(_ctrl(raiz, ident), 'ondown'),
                              '%s: %s nao desce para as categorias' % (skin, ident))

    def test_categorias_descem_para_o_hero_nos_dois_layouts(self):
        for skin in SKINS:
            raiz = _home(skin)
            descidas = _alvos(_ctrl(raiz, '9000'), 'ondown')
            self.assertIn('9300', descidas, '%s: 9000 nao desce (Aurora)' % skin)
            self.assertIn('9320', descidas, '%s: 9000 nao desce (blade)' % skin)

    def test_categorias_existem_na_aurora_e_na_blade(self):
        """9000 e o nivel mais alto da Home; se so existir na Aurora, o foco
        nao tem para onde subir na blade."""
        for skin in SKINS:
            visivel = (_ctrl(_home(skin), '9000').findtext('visible') or '')
            self.assertNotIn('!Skin.String(home_layout,blade)', visivel,
                             '%s: as categorias nao aparecem na blade' % skin)

    def test_hierarquia_completa_do_ultimo_item_ate_o_topo(self):
        """O caminho que o usuario faz: ultima fileira -> hero -> barra."""
        for skin in SKINS:
            raiz = _home(skin)
            series = _ctrl(raiz, '9203')
            self.assertIn('9201', _alvos(series, 'onup'))
            self.assertIn('9300', _alvos(series, 'onup'))
            self.assertIn('9000', _alvos(series, 'ondown'))
            self.assertIn('9000', _alvos(_ctrl(raiz, '9300'), 'onup'))
            self.assertIn('9121', _alvos(_ctrl(raiz, '9000'), 'onup'))

    def test_navegacao_volta_ao_hero_depois_de_recarregar(self):
        """Fila de conteudo vazia nao pode quebrar a subida: ha sempre um
        fallback incondicional para 9000."""
        for skin in SKINS:
            for ident in ('9201', '9203'):
                self.assertEqual(_sem_condicao(_home(skin) and _ctrl(_home(skin), ident), 'onup'),
                                 ['9000'],
                                 '%s: %s sem fallback incondicional para 9000'
                                 % (skin, ident))


if __name__ == '__main__':
    unittest.main()
