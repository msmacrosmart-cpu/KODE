# -*- coding: utf-8 -*-
"""O perfil embarcado precisa sair SEM os addons de terceiros, e o pin do dex
tem de continuar batendo.

Medido no emulador de projetor (APK 1.0.141): mesmo com a limpeza no aparelho
funcionando, o log continuava com

    [COLOR limegreen][B]Open[/B][/COLOR]Wizard: [First Run] Skipping Save Data
    [plugin.video.youtube] ModuleNotFoundError: youtube_plugin.kodion.exceptions

porque o Kodi inicia os addons de servico de TODOS os addons instalados antes de
qualquer Python do app. A correcao e tirar esses addons do perfil que o APK
instala. O `ProfileDirectorySeed` (dex) recusa o perfil se o sha256 do
profile-manifest.txt nao for o pin gravado nele - por isso o mesmo passo troca o
pin. Estes testes montam um APK sintetico com o pin real e provam os dois lados.
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


def _ferramenta():
    spec = importlib.util.spec_from_file_location('sanear_perfil', FERRAMENTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class SanearPerfilTest(unittest.TestCase):
    def setUp(self):
        self.modulo = _ferramenta()
        self.pasta = tempfile.mkdtemp()
        self.apk = os.path.join(self.pasta, 'base.apk')
        self.saida = os.path.join(self.pasta, 'saneado.apk')
        self.perfil = {
            'userdata/guisettings.xml': b'<settings version="2"/>',
            'addons/plugin.video.BrazucaPlay.Matrix/addon.xml': b'<addon id="b"/>',
            'addons/plugin.video.BrazucaPlay.Matrix/default.py': b'# b\n',
            'addons/skin.novatv/addon.xml': b'<addon id="s"/>',
            'addons/audioencoder.kodi.builtin.aac/addon.xml': b'<addon id="a"/>',
            # os de terceiros que causam o erro no projetor
            'addons/plugin.video.youtube/addon.xml': b'<addon id="y"/>',
            'addons/plugin.video.youtube/resources/lib/service.py': b'# y\n',
            'addons/plugin.program.openwizard/addon.xml': b'<addon id="o"/>',
            'addons/repository.redwizard/addon.xml': b'<addon id="r"/>',
        }
        manifesto = self._manifesto(self.perfil)
        with zipfile.ZipFile(self.apk, 'w') as z:
            z.writestr('AndroidManifest.xml', b'x')
            z.writestr('lib/arm64-v8a/libkodi.so', b'\x7fELF')
            for caminho, dados in self.perfil.items():
                z.writestr('assets/smarted/profile/' + caminho, dados)
            z.writestr(self.modulo.MANIFESTO, manifesto)
            # dex com o pin antigo (64 caracteres ASCII, como no APK real), com
            # cabecalho valido: o ART recusa dex com checksum/assinatura errados
            z.writestr('classes4.dex', self.modulo.consertar_cabecalho_do_dex(
                b'dex\n035\x00' + b'\x00' * 4 + b'\x00' * 104 +
                self.modulo.PIN_ANTIGO.encode('ascii') + b'\x00fim'))
            z.writestr('classes.dex', self.modulo.consertar_cabecalho_do_dex(
                b'dex\n035\x00' + b'\x00' * 4 + b'\x00' * 104 + b'\x00fim'))

    @staticmethod
    def _manifesto(perfil):
        linhas = []
        for caminho in sorted(perfil):
            dados = perfil[caminho]
            linhas.append('%s\t%d\t%s' % (hashlib.sha256(dados).hexdigest(),
                                          len(dados), caminho))
        return ('\n'.join(linhas) + '\n').encode('utf-8')

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_planeja_remover_so_os_de_terceiros(self):
        arquivos, removidos, mantidos = self.modulo.planejar(self.apk)
        self.assertIn('plugin.video.youtube', removidos)
        self.assertIn('plugin.program.openwizard', removidos)
        self.assertIn('repository.redwizard', removidos)
        self.assertIn('plugin.video.BrazucaPlay.Matrix', mantidos)
        self.assertIn('skin.novatv', mantidos)
        self.assertIn('audioencoder.kodi.builtin.aac', mantidos)
        self.assertTrue(any('youtube' in a for a in arquivos))

    def test_apk_saneado_nao_tem_addon_de_terceiro_no_perfil(self):
        resultado = self.modulo.executar(self.apk, self.saida, atualizar_origem=False)
        self.assertTrue(resultado['removidos'])
        with zipfile.ZipFile(self.saida) as z:
            nomes = z.namelist()
        for addon in ('plugin.video.youtube', 'plugin.program.openwizard',
                      'repository.redwizard'):
            self.assertFalse([n for n in nomes
                              if n.startswith('assets/smarted/profile/addons/%s/' % addon)],
                             '%s continuou no perfil embarcado' % addon)
        # o que o app usa continua
        self.assertIn('assets/smarted/profile/addons/plugin.video.BrazucaPlay.Matrix/addon.xml',
                      nomes)
        self.assertIn('assets/smarted/profile/addons/audioencoder.kodi.builtin.aac/addon.xml',
                      nomes)

    def test_manifesto_e_pin_do_dex_batem_no_apk_final(self):
        resultado = self.modulo.executar(self.apk, self.saida, atualizar_origem=False)
        with zipfile.ZipFile(self.saida) as z:
            manifesto = z.read(self.modulo.MANIFESTO)
            pin = hashlib.sha256(manifesto).hexdigest()
            self.assertEqual(pin, resultado['pin'])
            # o dex que o seed confere tem de carregar ESSE pin
            dex = z.read('classes4.dex')
            self.assertIn(pin.encode('ascii'), dex)
            self.assertNotIn(self.modulo.PIN_ANTIGO.encode('ascii'), dex)
            self.assertTrue(self.modulo.cabecalho_do_dex_confere(dex),
                            'cabecalho do dex invalido (checksum/assinatura)')

    def test_manifesto_corresponde_aos_arquivos_que_ficaram(self):
        self.modulo.executar(self.apk, self.saida, atualizar_origem=False)
        with zipfile.ZipFile(self.saida) as z:
            linhas = z.read(self.modulo.MANIFESTO).decode('utf-8').splitlines()
            for linha in linhas:
                sha, tamanho, caminho = linha.split('\t')
                dados = z.read('assets/smarted/profile/' + caminho)
                self.assertEqual(int(tamanho), len(dados), caminho)
                self.assertEqual(sha, hashlib.sha256(dados).hexdigest(), caminho)

    def test_cabecalho_do_dex_e_recalculado(self):
        """Sem isso o ART recusa o dex: NoClassDefFoundError no projetor."""
        corpo = b'\x00' * 104 + b'1' * 64
        dex = self.modulo.consertar_cabecalho_do_dex(b'dex\n035\x00' + b'\x00' * 4 + corpo)
        self.assertTrue(self.modulo.cabecalho_do_dex_confere(dex))
        novo, quantos = self.modulo.trocar_pin_no_dex(dex, '1' * 64, '2' * 64)
        self.assertEqual(quantos, 1)
        self.assertTrue(self.modulo.cabecalho_do_dex_confere(novo))
        self.assertIn(b'2' * 64, novo)

    def test_conferencia_acha_o_pin_dentro_do_dex(self):
        with zipfile.ZipFile(self.apk) as z:
            self.assertEqual(self.modulo.pin_do_dex(z), self.modulo.PIN_ANTIGO)

    def test_conferencia_do_apk_final_pega_perfil_sujo(self):
        """O build confere o APK assinado: perfil com terceiro nao passa."""
        with self.assertRaises(SystemExit):
            self.modulo.conferir(self.apk, pin_esperado=hashlib.sha256(
                zipfile.ZipFile(self.apk).read(self.modulo.MANIFESTO)).hexdigest())

    def test_conferencia_do_apk_saneado_passa(self):
        resultado = self.modulo.executar(self.apk, self.saida,
                                         atualizar_origem=False)
        self.assertTrue(self.modulo.conferir(self.saida,
                                             pin_esperado=resultado['pin']))

    def test_conferencia_pega_dex_com_cabecalho_quebrado(self):
        """APK 1.0.143: dex com pin trocado e cabecalho velho -> app caiu."""
        quebrado = os.path.join(self.pasta, 'quebrado.apk')
        resultado = self.modulo.executar(self.apk, self.saida,
                                         atualizar_origem=False)
        with zipfile.ZipFile(self.saida) as entrada, \
                zipfile.ZipFile(quebrado, 'w') as saida:
            for item in entrada.infolist():
                dados = entrada.read(item)
                if item.filename == 'classes4.dex':
                    dados = dados[:12] + b'\x00' * 20 + dados[32:]
                saida.writestr(item, dados)
        with self.assertRaises(SystemExit):
            self.modulo.conferir(quebrado, pin_esperado=resultado['pin'])

    def test_falha_alto_quando_o_pin_nao_esta_no_dex(self):
        """Sem o pin, o dex recusaria o perfil e a Home ficaria vazia."""
        apk_sem_pin = os.path.join(self.pasta, 'sem-pin.apk')
        with zipfile.ZipFile(self.apk) as entrada, \
                zipfile.ZipFile(apk_sem_pin, 'w') as saida:
            for item in entrada.infolist():
                dados = entrada.read(item)
                if item.filename.endswith('.dex'):
                    dados = b'dex sem o pin'
                saida.writestr(item, dados)
        with self.assertRaises(SystemExit):
            self.modulo.executar(apk_sem_pin, self.saida, atualizar_origem=False)


if __name__ == '__main__':
    unittest.main()


class DexSoComPinTrocadoTest(unittest.TestCase):
    """`verify.py` exige dex identico a base: abrir so para a troca do pin."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'verify_release', RAIZ / 'smartedtv' / 'release' / 'verify.py')
        cls.modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.modulo)

    # o pin vem depois do cabecalho (112 bytes no dex real)
    CABECALHO = b'dex\n035' + b'\x00' * 105   # pin comeca no byte 112 do dex

    def test_troca_do_pin_e_permitida(self):
        base = self.CABECALHO + b'a' * 64 + b'\x00' * 10
        novo = self.CABECALHO + b'b' * 64 + b'\x00' * 10
        self.assertTrue(self.modulo.so_mudou_o_pin(novo, base))

    def test_cabecalho_recalculado_tambem_e_aceito(self):
        base = self.CABECALHO + b'a' * 64 + b'\x00' * 10
        # so os bytes 8..32 (checksum + assinatura) alem do pin
        novo = (b'dex\n035\x00' + b'\xff' * 24 + b'\x00' * 80 +
                b'b' * 64 + b'\x00' * 10)
        self.assertTrue(self.modulo.so_mudou_o_pin(novo, base))
        # cabecalho E pin: vale; mas codigo fora disso continua barrado
        self.assertFalse(self.modulo.so_mudou_o_pin(novo + b'', base + b'\x00'))
        self.assertFalse(self.modulo.so_mudou_o_pin(
            novo[:-1] + b'\x01', base))

    def test_qualquer_outra_mudanca_no_dex_e_barrada(self):
        base = self.CABECALHO + b'a' * 64 + b'\x00' * 10
        self.assertFalse(self.modulo.so_mudou_o_pin(base.replace(b'dex', b'dey'), base))
        self.assertFalse(self.modulo.so_mudou_o_pin(base + b'\x00', base))
        self.assertFalse(self.modulo.so_mudou_o_pin(b'curto', base))
