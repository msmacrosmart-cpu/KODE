# -*- coding: utf-8 -*-
"""Todo modulo que o servico importa tem de entrar no APK.

Bug real (log do projetor, 2026-11-19):

    Error Type: <class 'FileNotFoundError'>
    Error Contents: ... No such file or directory:
    '/data/user/0/smartedtv.full/cache/apk/assets/addons/
     service.smarted.bootstrap/ads_regra.py'
    File ".../smart_ads.py", line 66, in <module> import ads_regra
    File ".../service.py", line 21, in <module> import smart_ads

``ads_regra.py`` existia no repositorio e era importado no TOPO de
``smart_ads.py``, mas nao estava na lista MODULOS do injetor. No APK o arquivo
nao existia, o import estourava e o ``service.py`` inteiro abortava: nenhum
trabalho do servico (reparo, favoritos, skin, anuncio) rodava e o Kodi mostrava
a notificacao de erro Python no boot. ``ads_vast.py`` dependia da mesma sorte -
ele era injetado por outro script (injetar-tela-entrada.py), que o pipeline
atual nao usa.

Estes testes comparam a PASTA do addon com a lista do injetor, para que um
modulo novo que esqueca de entrar no APK falhe aqui, e nao no aparelho.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
INJETOR = ROOT / 'tools' / 'kodi' / 'atualizar-apk-v17.py'


def _modulos_do_injetor():
    arvore = ast.parse(INJETOR.read_text(encoding='utf-8'))
    for no in arvore.body:
        if isinstance(no, ast.Assign) and any(
                getattr(alvo, 'id', None) == 'MODULOS' for alvo in no.targets):
            return list(ast.literal_eval(no.value))
    raise AssertionError('MODULOS nao encontrado em %s' % INJETOR)


def _imports_do_addon():
    """{(arquivo que importa, modulo importado)} de todo import interno."""
    nome = {}
    for caminho in ADDON.glob('*.py'):
        nome[caminho.stem] = caminho
    achados = set()
    for caminho in ADDON.glob('*.py'):
        arvore = ast.parse(caminho.read_text(encoding='utf-8'))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for alias in no.names:
                    if alias.name in nome:
                        achados.add((caminho.name, alias.name))
            elif isinstance(no, ast.ImportFrom) and no.module in nome:
                achados.add((caminho.name, no.module))
    return achados


class ModulosNoApkTest(unittest.TestCase):
    def test_ads_regra_entra_no_apk(self):
        self.assertIn('ads_regra.py', _modulos_do_injetor(),
                      'sem ads_regra.py o service.py aborta no boot (bug do '
                      'projetor)')

    def test_ads_vast_entra_no_apk(self):
        self.assertIn('ads_vast.py', _modulos_do_injetor(),
                      'sem ads_vast.py a TV fica sem o anuncio de video')

    def test_todo_modulo_importado_esta_na_lista(self):
        lista = set(_modulos_do_injetor())
        faltando = sorted({mod for _, mod in _imports_do_addon()
                           if mod + '.py' not in lista})
        self.assertEqual(faltando, [],
                         'modulos importados que nao entram no APK: %s'
                         % faltando)

    def test_os_modulos_da_lista_existem_no_repositorio(self):
        for nome in _modulos_do_injetor():
            self.assertTrue((ADDON / nome).is_file(),
                            'lista do injetor cita %s, que nao existe' % nome)

    def test_service_py_nao_importa_nada_opcional_no_topo(self):
        """O import que derruba o servico e o do TOPO do arquivo. Os opcionais
        tem de ser importados dentro da funcao, com try/except."""
        fonte = (ADDON / 'service.py').read_text(encoding='utf-8')
        topo = []
        for linha in fonte.splitlines():
            if linha.startswith(('def ', 'class ', 'if __name__')):
                break
            if linha.startswith(('import ', 'from ')):
                topo.append(linha.split()[1].split('.')[0])
        proibidos = {'ads_regra', 'ads_vast', 'ao_vivo', 'ad_return'}
        self.assertEqual(sorted(proibidos & set(topo)), [],
                         'service.py importa modulo opcional no topo: %s'
                         % sorted(proibidos & set(topo)))


class FalhaNaoDerrubaOTest(unittest.TestCase):
    """Um addon com problema nao pode impedir o resto do boot."""

    def test_smart_ads_tolera_ads_vast_ausente(self):
        fonte = (ADDON / 'smart_ads.py').read_text(encoding='utf-8')
        # _ads_vast() devolve None quando o modulo nao esta la, e quem chama
        # tem de tratar None (anuncio inexistente) sem levantar.
        self.assertIn('def _ads_vast()', fonte)
        self.assertIn('return None', fonte)

    def test_servico_envolve_o_anuncio_em_try(self):
        fonte = (ADDON / 'service.py').read_text(encoding='utf-8')
        trecho = fonte[fonte.index('explicar_anuncio_tv'):]
        antes = fonte[:fonte.index('explicar_anuncio_tv')]
        self.assertIn('try:', antes[-400:])
        self.assertTrue(trecho)

    def test_ads_regra_importado_com_tratamento(self):
        fonte = (ADDON / 'smart_ads.py').read_text(encoding='utf-8')
        self.assertIn('except ImportError', fonte)


if __name__ == '__main__':
    unittest.main()
