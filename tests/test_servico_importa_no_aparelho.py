# -*- coding: utf-8 -*-
"""O servico do addon tem de IMPORTAR no aparelho, nao so existir no zip.

O defeito que deixou o projetor sem nenhum trabalho do servico (log real de
2026-11-19) foi este, exatamente:

    File ".../smart_ads.py", line 66, in <module>  import ads_regra
    FileNotFoundError: .../service.smarted.bootstrap/ads_regra.py

``ads_regra.py`` nao estava dentro do APK. O ``import`` no topo do
``smart_ads.py`` abortava o ``service.py`` inteiro: nada de reparo, favoritos,
skin, menu ou anuncio, e uma notificacao de erro na tela da TV.

Aqui a prova e mais forte que "o nome esta na lista": o ``service.py`` e
importado DE VERDADE, na ordem do Kodi, com xbmc/xbmcgui falsos, em duas
situacoes - a pasta completa do repositorio (tem de passar) e uma copia SEM
``ads_regra.py`` (tem de falhar). Se alguem tirar um modulo da lista do
injetor, o primeiro teste continua passando (a pasta tem o arquivo), mas o
teste do APK gerado (``test_addon_completo_no_apk``) e a auditoria do CI
pegam. Juntos, os dois fecham o caminho que deixou a TV sem servico.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, 'kodi', 'addons', 'service.smarted.bootstrap')
FERRAMENTA = os.path.join(RAIZ, 'tools', 'kodi', 'simular-servico.py')


def _carregar_ferramenta():
    spec = importlib.util.spec_from_file_location('simular_servico', FERRAMENTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


MODULOS_DO_ADDON = ('service', 'repair', 'favourites', 'performance',
                    'menu_smarted', 'skin_setup', 'smart_ads', 'ads_regra',
                    'ads_vast', 'variante', 'vip', 'ad_return', 'ao_vivo',
                    'smarted_release', 'check')


def _limpar_modulos(pasta):
    """Tira do sys.modules os modulos do addon (import entre testes).

    Precisa ser pelo NOME tambem, nao so por ``__file__``: outra suite ja
    pode ter importado ``ads_regra`` da pasta real, e o cache do import faria
    o teste do APK incompleto passar (falso negativo - o pior tipo aqui).
    """
    for nome in MODULOS_DO_ADDON:
        sys.modules.pop(nome, None)
    for nome, modulo in list(sys.modules.items()):
        caminho = getattr(modulo, '__file__', '') or ''
        if caminho.startswith(pasta):
            sys.modules.pop(nome, None)


class ServicoImportaTest(unittest.TestCase):
    def setUp(self):
        self.ferramenta = _carregar_ferramenta()
        self.guardados = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcgui',
                                                           'xbmcaddon', 'xbmcvfs')}
        self.caminho = sys.path[:]
        # A pasta do addon NAO pode ficar no sys.path: um `import ads_regra`
        # acharia o arquivo do repositorio e o teste do APK incompleto passaria
        # por engano (foi o que aconteceu na suite completa).
        sys.path[:] = [p for p in sys.path if os.path.abspath(p) != ADDON]
        _limpar_modulos(ADDON)

    def tearDown(self):
        _limpar_modulos(ADDON)
        sys.path[:] = self.caminho
        for nome, antigo in self.guardados.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def test_service_importa_com_todos_os_modulos(self):
        ok, dados = self.ferramenta.simular(ADDON)
        self.assertTrue(ok, dados.get('traceback'))
        self.assertEqual(dados['faltando'], [])
        for exigido in ('repair', 'favourites', 'performance', 'menu_smarted',
                        'skin_setup', 'smart_ads'):
            self.assertIn(exigido, dados['modulos'])
        self.assertTrue(dados['tem_main'])

    def test_service_sem_ads_regra_falha_no_import(self):
        """Reproduz o erro do log do projetor (modulo ausente no APK)."""
        temporaria = tempfile.mkdtemp()
        try:
            for nome in os.listdir(ADDON):
                if nome.endswith(('.py', '.xml')):
                    shutil.copy(os.path.join(ADDON, nome),
                                os.path.join(temporaria, nome))
            os.remove(os.path.join(temporaria, 'ads_regra.py'))
            self.guardados.update({n: sys.modules.get(n)
                                   for n in ('xbmc', 'xbmcgui', 'xbmcaddon',
                                             'xbmcvfs')})
            ok, dados = self.ferramenta.simular(temporaria)
            self.assertFalse(ok, 'servico sem ads_regra nao pode importar')
            self.assertIn('ads_regra', dados['erro'])
            self.assertIn('FileNotFoundError', dados['erro'])
        finally:
            shutil.rmtree(temporaria, ignore_errors=True)

    def test_anuncio_que_falha_nao_derruba_o_boot(self):
        """Todo uso de ``smart_ads`` dentro de ``main()`` esta em try/except.

        E o que impede um erro de anuncio (tag, rede, SDK) de derrubar o
        servico inteiro: o boot vira uma linha WARNING no log, o resto do
        preparo continua e o conteudo abre.
        """
        import ast
        with open(os.path.join(ADDON, 'service.py'), encoding='utf-8') as handle:
            arvore = ast.parse(handle.read())
        principal = [n for n in arvore.body
                     if isinstance(n, ast.FunctionDef) and n.name == 'main']
        self.assertEqual(len(principal), 1)
        funcao = principal[0]

        def _protegidos(no, dentro_de_try):
            """Devolve (chamadas a smart_ads, chamadas fora de try)."""
            total, desprotegidas = [], []
            pilha = [(filho, dentro_de_try) for filho in ast.iter_child_nodes(no)]
            while pilha:
                atual, protegido = pilha.pop()
                agora = protegido or isinstance(atual, ast.Try)
                if isinstance(atual, ast.Call):
                    alvo = atual.func
                    if isinstance(alvo, ast.Attribute) and \
                            isinstance(alvo.value, ast.Name) and \
                            alvo.value.id == 'smart_ads':
                        total.append(alvo.attr)
                        if not agora:
                            desprotegidas.append(alvo.attr)
                pilha.extend((filho, agora)
                             for filho in ast.iter_child_nodes(atual))
            return total, desprotegidas

        total, desprotegidas = _protegidos(funcao, False)
        self.assertTrue(total, 'main() deveria usar smart_ads (anuncios no boot)')
        self.assertEqual(desprotegidas, [],
                         'chamadas de anuncio fora de try/except: %s'
                         % desprotegidas)


if __name__ == '__main__':
    unittest.main()
