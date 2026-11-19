# -*- coding: utf-8 -*-
"""Addon com erro na tela (YouTube, OpenWizard...) nao pode quebrar a Home.

O que o dono do app viu no projetor: no boot o Kodi abre a tela de varios
addons dizendo "Add-on com erro" e, com isso, a Home nao carrega o conteudo.

Causa: o Kodi conhece os addons que estao no APK (``addon.xml``) e os que
sobraram no perfil do usuario; quando o codigo do addon nao existe (pasta sem
arquivo, ``library`` apontando para um arquivo ausente, zip de repositorio
removido), ele monta a tela de erro. O SMARTEDTV nunca entregou YouTube nem
OpenWizard - eles vem de repositorio de terceiros e do perfil antigo.

Estes testes usam o injetor REAL (``tools/kodi/atualizar-apk-v17.py``) sobre
um APK sintetico montado aqui, com um addon sadio, um anunciado sem codigo e
uma pasta vazia.
"""
import importlib.util
import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
INJETOR = RAIZ / 'tools' / 'kodi' / 'atualizar-apk-v17.py'

ADDON_XML = """<?xml version="1.0" encoding="UTF-8"?>
<addon id="%s" name="%s" version="1.0.0" provider-name="teste">
  <requires><import addon="xbmc.python" version="3.0.0"/></requires>
  <extension point="xbmc.python.pluginsource" library="%s">
    <provides>video</provides>
  </extension>
</addon>
"""


def _carregar_injetor():
    spec = importlib.util.spec_from_file_location('injetor_v17', INJETOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class ApkSintetico(object):
    """Zip no formato do APK: assets/addons, addon-manifest e um .so por ABI."""

    def __init__(self):
        self.pasta = tempfile.mkdtemp()
        self.caminho = os.path.join(self.pasta, 'base.apk')
        with zipfile.ZipFile(self.caminho, 'w') as z:
            z.writestr('AndroidManifest.xml', b'manifest')
            z.writestr('classes.dex', b'dex')
            z.writestr('lib/arm64-v8a/libkodi.so', b'\x7fELF' + b'\0' * 60)
            z.writestr('lib/armeabi-v7a/libkodi.so', b'\x7fELF' + b'\0' * 60)
            # addon sadio: addon.xml + default.py
            z.writestr('assets/addons/plugin.video.bom/addon.xml',
                       ADDON_XML % ('plugin.video.bom', 'Bom', 'default.py'))
            z.writestr('assets/addons/plugin.video.bom/default.py', '# ok\n')
            # o servico do app (o injetor exige service.py)
            z.writestr('assets/addons/service.smarted.bootstrap/addon.xml',
                       ADDON_XML % ('service.smarted.bootstrap', 'B', 'service.py'))
            z.writestr('assets/addons/service.smarted.bootstrap/service.py', '# ok\n')
            # addon ANUNCIADO e sem codigo: addon.xml aponta default.py ausente
            z.writestr('assets/addons/plugin.video.openwizard/addon.xml',
                       ADDON_XML % ('plugin.video.openwizard', 'W', 'default.py'))
            # addon de terceiro que a entrega nao inclui (skin cita o YouTube)
            z.writestr('assets/addons/plugin.video.youtube/addon.xml',
                       ADDON_XML % ('plugin.video.youtube', 'Y', 'default.py'))
            z.writestr('assets/addons/plugin.video.youtube/default.py', '# y\n')
            # pasta sem addon.xml (resto de instalacao)
            z.writestr('assets/addons/plugin.program.resto/lixo.txt', 'x')
            z.writestr('assets/system/addon-manifest.xml',
                       '<addon-manifest><addon id="plugin.video.bom"/>'
                       '<addon id="plugin.video.openwizard"/></addon-manifest>')
            z.writestr('assets/addon-manifest.xml',
                       '<addon-manifest><addon id="plugin.video.bom"/>'
                       '<addon id="plugin.video.openwizard"/></addon-manifest>')
            for skin in ('skin.novatv', 'skin.smartedtv.classic'):
                z.writestr('assets/addons/%s/addon.xml' % skin,
                           ADDON_XML % (skin, skin, 'Home.xml'))
                z.writestr('assets/addons/%s/xml/Home.xml' % skin, '<window/>')
            z.writestr('assets/addons/script.smartedtv.welcome/addon.xml',
                       ADDON_XML % ('script.smartedtv.welcome', 'w', 'default.py'))
            z.writestr('assets/addons/script.smartedtv.welcome/default.py', '# ok\n')

    def limpar(self):
        import shutil
        shutil.rmtree(self.pasta, ignore_errors=True)


class AddonsComErroTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.injetor = _carregar_injetor()
        cls.apk = ApkSintetico()

    @classmethod
    def tearDownClass(cls):
        cls.apk.limpar()

    def _analisar(self):
        with zipfile.ZipFile(self.apk.caminho) as z:
            nomes = set(z.namelist())
            return self.injetor.addons_sem_entrega(nomes, z)

    def test_remove_addon_anunciado_sem_o_codigo(self):
        removidos, motivos = self._analisar()
        self.assertIn('plugin.video.openwizard', removidos)
        self.assertIn('sem o codigo', motivos['plugin.video.openwizard'])

    def test_remove_addon_de_terceiro_que_a_entrega_nao_inclui(self):
        removidos, _motivos = self._analisar()
        self.assertIn('plugin.video.youtube', removidos)
        self.assertIn('plugin.program.openwizard', self.injetor.ADDONS_QUE_NAO_VEM)

    def test_remove_pasta_sem_addon_xml(self):
        removidos, motivos = self._analisar()
        self.assertIn('plugin.program.resto', removidos)
        self.assertIn('addon.xml', motivos['plugin.program.resto'])

    def test_nao_toca_no_addon_completo(self):
        removidos, _motivos = self._analisar()
        self.assertNotIn('plugin.video.bom', removidos)
        self.assertNotIn('service.smarted.bootstrap', removidos)

    def test_monta_o_apk_sem_os_addons_com_erro(self):
        saida = os.path.join(self.apk.pasta, 'saida.apk')
        with open(os.devnull, 'w') as vazio:
            antigo, sys.stdout = sys.stdout, vazio
            try:
                self.injetor.main(['--apk', self.apk.caminho, '--saida', saida])
            finally:
                sys.stdout = antigo
        with zipfile.ZipFile(saida) as z:
            nomes = set(z.namelist())
        for addon in ('plugin.video.openwizard', 'plugin.video.youtube',
                      'plugin.program.resto'):
            self.assertFalse([n for n in nomes
                              if n.startswith('assets/addons/%s/' % addon)],
                             '%s continuou no APK' % addon)
        self.assertIn('assets/addons/plugin.video.bom/default.py', nomes,
                      'o injetor apagou um addon sadio')


class PerfilDoAparelhoTest(unittest.TestCase):
    """O mesmo defeito no perfil do usuario (fora do APK)."""

    def _servico(self):
        spec = importlib.util.spec_from_file_location(
            'simular_servico_addons',
            RAIZ / 'tools' / 'kodi' / 'simular-servico.py')
        ferramenta = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ferramenta)
        ok, dados = ferramenta.simular(str(RAIZ / 'kodi' / 'addons' /
                                           'service.smarted.bootstrap'))
        self.assertTrue(ok, dados.get('traceback'))
        return sys.modules['service']

    def test_o_servico_limpa_pasta_de_addon_sem_addon_xml(self):
        servico = self._servico()
        self.assertTrue(callable(getattr(servico, 'limpar_addons_quebrados',
                                         None)),
                        'o servico precisa limpar addon sem addon.xml')


if __name__ == '__main__':
    unittest.main()
