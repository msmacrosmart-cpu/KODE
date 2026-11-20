# -*- coding: utf-8 -*-
"""Perfil embarcado: sem YouTube/OpenWizard e com o pin que o dex do bootstrap le.

Medido no emulador de projetor:
  * o Kodi inicia os addons de servico de TUDO que esta instalado antes de
    qualquer Python do app, e o log de todo boot mostrava
        [COLOR limegreen][B]Open[/B][/COLOR]Wizard: [First Run] Skipping Save Data
        [plugin.video.youtube] ModuleNotFoundError: youtube_plugin.kodion.exceptions
  * limpar o perfil no aparelho nao resolve (o erro sai antes da limpeza);
  * trocar o pin por edicao de bytes no classes4.dex mata o app:
        A (perfil limpo + pin no classes4) -> NoClassDefFoundError: smartedtv/full/XBMCJsonRPC
        D (perfil limpo + classes4 intacto) -> app vivo
        C (tudo intacto)                    -> app vivo

Por isso o pin muda no Java do bootstrap e no dex recompilado (classes3.dex), e o
script falha se o pin do dex nao bater com o manifesto.
"""
import hashlib
import importlib.util
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FERRAMENTA = RAIZ / 'tools' / 'kodi' / 'sanear-perfil-embarcado.py'
PIN_ANTIGO = '1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede'


def _ferramenta():
    spec = importlib.util.spec_from_file_location('sanear_perfil', FERRAMENTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _dex_com_pin(pin):
    """Dex minimo (magic + cabecalho + pin ASCII), como o classes3.dex real."""
    corpo = b'\x00' * 104 + pin.encode('ascii') + b'\x00fim'
    dados = b'dex\n035\x00' + b'\x00' * 4 + corpo
    corpo = dados[32:]
    dados = dados[:12] + hashlib.sha1(corpo).digest() + dados[32:]
    return dados[:8] + b'\x00\x00\x00\x00' + dados[12:]


class PerfilEmbarcadoTest(unittest.TestCase):
    def setUp(self):
        self.modulo = _ferramenta()
        self.pasta = tempfile.mkdtemp()
        self.apk = os.path.join(self.pasta, 'base.apk')
        self.saida = os.path.join(self.pasta, 'saneado.apk')
        self.java = os.path.join(self.pasta, 'ProfileDirectoryBootstrap.java')
        with open(self.java, 'w', encoding='utf-8') as arquivo:
            arquivo.write('install(profile, manifest, home, privateDir,\n'
                          '    "%s");\n' % PIN_ANTIGO)
        self.perfil = {
            'userdata/guisettings.xml': b'<settings version="2"/>',
            'addons/plugin.video.BrazucaPlay.Matrix/addon.xml': b'<addon id="b"/>',
            'addons/plugin.video.BrazucaPlay.Matrix/default.py': b'# b\n',
            'addons/skin.novatv/addon.xml': b'<addon id="s"/>',
            'addons/audioencoder.kodi.builtin.aac/addon.xml': b'<addon id="a"/>',
            # os de terceiros que fazem o erro aparecer no projetor
            'addons/plugin.video.youtube/addon.xml': b'<addon id="y"/>',
            'addons/plugin.video.youtube/resources/lib/service.py': b'# y\n',
            'addons/plugin.program.openwizard/addon.xml': b'<addon id="o"/>',
            'addons/plugin.program.openwizard/service.py': b'# o\n',
            'addons/repository.redwizard/addon.xml': b'<addon id="r"/>',
        }
        manifesto = self.modulo.manifesto_de(self.perfil)
        with zipfile.ZipFile(self.apk, 'w') as z:
            z.writestr('AndroidManifest.xml', b'x')
            z.writestr('lib/arm64-v8a/libkodi.so', b'\x7fELF')
            for caminho, dados in self.perfil.items():
                z.writestr('assets/smarted/profile/' + caminho, dados)
            z.writestr(self.modulo.MANIFESTO, manifesto)
            z.writestr('classes3.dex', _dex_com_pin(PIN_ANTIGO))
            z.writestr('classes4.dex', _dex_com_pin('a' * 64))

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def executar(self):
        return self.modulo.executar(self.apk, self.saida, origem=self.java)

    def test_planeja_remover_so_os_de_terceiros(self):
        arquivos, removidos, mantidos = self.modulo.planejar(self.apk)
        self.assertIn('plugin.video.youtube', removidos)
        self.assertIn('plugin.program.openwizard', removidos)
        self.assertIn('repository.redwizard', removidos)
        self.assertIn('plugin.video.BrazucaPlay.Matrix', mantidos)
        self.assertIn('skin.novatv', mantidos)
        self.assertIn('audioencoder.kodi.builtin.aac', mantidos)
        self.assertEqual(len(arquivos), 5)

    def test_terceiros_saem_do_perfil_e_o_app_fica(self):
        self.executar()
        with zipfile.ZipFile(self.saida) as z:
            nomes = z.namelist()
            for addon in ('plugin.video.youtube', 'plugin.program.openwizard',
                          'repository.redwizard'):
                restante = [n for n in nomes
                            if n.startswith('assets/smarted/profile/addons/%s/' % addon)]
                self.assertEqual(restante, [], addon)
            for caminho, dados in self.perfil.items():
                if any(t in caminho for t in ('youtube', 'openwizard', 'redwizard')):
                    continue
                self.assertEqual(z.read('assets/smarted/profile/' + caminho), dados)

    def test_manifesto_novo_nao_cita_terceiro(self):
        resultado = self.executar()
        with zipfile.ZipFile(self.saida) as z:
            manifesto = z.read(self.modulo.MANIFESTO)
        self.assertEqual(hashlib.sha256(manifesto).hexdigest(), resultado['pin'])
        texto = manifesto.decode('utf-8')
        self.assertNotIn('youtube', texto)
        self.assertNotIn('openwizard', texto)
        self.assertIn('plugin.video.BrazucaPlay.Matrix/addon.xml', texto)

    def test_pin_do_bootstrap_java_acompanha_o_manifesto(self):
        resultado = self.executar()
        self.assertTrue(resultado['pin_atualizado_na_origem'])
        texto = open(self.java, encoding='utf-8').read()
        self.assertIn(resultado['pin'], texto)
        self.assertNotIn(PIN_ANTIGO, texto)

    def test_classes4_dex_do_app_nao_e_tocado(self):
        """Editar byte no classes4 fez o app morrer (NoClassDefFoundError)."""
        antes = zipfile.ZipFile(self.apk).read('classes4.dex')
        self.executar()
        self.assertEqual(zipfile.ZipFile(self.saida).read('classes4.dex'), antes)

    def test_falha_alto_se_o_dex_do_bootstrap_nao_tiver_o_pin_novo(self):
        """Sem recompilar o bootstrap o aparelho recusaria o proprio perfil."""
        self.executar()
        problemas = []
        try:
            self.modulo.conferir(self.saida, origem=self.java)
        except SystemExit as erro:
            problemas.append(str(erro))
        self.assertEqual(len(problemas), 1)
        self.assertIn('pin do dex', problemas[0])

    def test_conferencia_passa_depois_de_recompilar_o_bootstrap(self):
        resultado = self.executar()
        recompilado = os.path.join(self.pasta, 'recompilado.apk')
        with zipfile.ZipFile(self.saida) as entrada, \
                zipfile.ZipFile(recompilado, 'w') as saida:
            for item in entrada.infolist():
                dados = entrada.read(item)
                if item.filename == 'classes3.dex':
                    dados = _dex_com_pin(resultado['pin'])
                saida.writestr(item, dados)
        self.assertTrue(self.modulo.conferir(recompilado, origem=self.java))

    def test_conferencia_reprova_perfil_com_terceiro(self):
        with self.assertRaises(SystemExit):
            self.modulo.conferir(self.apk, origem=self.java)

    def test_rodar_duas_vezes_nao_muda_nada(self):
        self.executar()
        outra = os.path.join(self.pasta, 'outra.apk')
        self.modulo.executar(self.saida, outra, origem=self.java)
        with zipfile.ZipFile(self.saida) as a, zipfile.ZipFile(outra) as b:
            self.assertEqual(a.read(self.modulo.MANIFESTO), b.read(self.modulo.MANIFESTO))


if __name__ == '__main__':
    unittest.main()


class DexRecompiladoTest(unittest.TestCase):
    """`verify.py`: so o bootstrap (classes3.dex) pode diferir da base."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'verify_release', RAIZ / 'smartedtv' / 'release' / 'verify.py')
        cls.modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.modulo)

    def test_classes3_recompilado_e_permitido(self):
        self.assertEqual(self.modulo.DEX_RECOMPILAVEL, 'classes3.dex')

    def test_classes4_nunca_pode_diferir(self):
        """Patchear o classes4 matou o app no emulador."""
        self.assertNotEqual(self.modulo.DEX_RECOMPILAVEL, 'classes4.dex')
