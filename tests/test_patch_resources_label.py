"""Testes do trocador de texto do resources.arsc.

O APK do Kodi guarda o nome exibido ("SMARTED-TV") no string pool global do
``resources.arsc``. Trocar o texto muda o tamanho do arquivo, entao o pool
inteiro e remontado: estes testes garantem que a remontagem devolve exatamente
as mesmas strings (menos a trocada) e que o arquivo continua legivel.
"""
import importlib.util
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'patch_resources', ROOT / 'tools' / 'kodi' / 'patch-resources-label.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

STRINGS = ['Kodi', 'SMARTED-TV', 'xbmc_version', '21.4-Omega', 'OK']


def montar_arsc(strings, utf8=True):
    """resources.arsc minimo: cabecalho da tabela + string pool global."""
    header_size = 28
    dados = bytearray()
    offsets = []
    for texto in strings:
        offsets.append(len(dados))
        if utf8:
            bruto = texto.encode('utf-8')
            dados += patch._escrever_len_utf8(len(texto))
            dados += patch._escrever_len_utf8(len(bruto)) + bruto + b'\x00'
        else:
            bruto = texto.encode('utf-16-le')
            dados += patch._escrever_len_utf16(len(bruto) // 2) + bruto + b'\x00\x00'
        while len(dados) % 4:
            dados += b'\x00'
    strings_start = header_size + 4 * len(strings)
    flags = patch.FLAG_UTF8 if utf8 else 0
    tamanho = strings_start + len(dados)
    pool = struct.pack('<HHIIIIII', patch.RES_STRING_POOL, header_size, tamanho,
                       len(strings), 0, flags, strings_start, 0)
    pool += struct.pack('<%dI' % len(offsets), *offsets) + dados
    tabela = struct.pack('<HHI', patch.RES_TABLE, 12, 12 + len(pool)) + struct.pack('<I', 0)
    return bytes(tabela) + bytes(pool)


class ResourcesLabelTest(unittest.TestCase):
    def test_le_as_strings_do_pool(self):
        for utf8 in (True, False):
            with self.subTest(utf8=utf8):
                self.assertEqual(patch.listar(montar_arsc(STRINGS, utf8)), STRINGS)

    def test_troca_o_texto_e_preserva_o_resto(self):
        for utf8 in (True, False):
            with self.subTest(utf8=utf8):
                novo, trocas = patch.principal(montar_arsc(STRINGS, utf8),
                                               'SMARTED-TV', 'SMARTEDTV')
                self.assertEqual(trocas, 1)
                esperado = [s if s != 'SMARTED-TV' else 'SMARTEDTV' for s in STRINGS]
                self.assertEqual(patch.listar(novo), esperado)

    def test_tamanho_do_pool_e_da_tabela_ficam_coerentes(self):
        novo, _ = patch.principal(montar_arsc(STRINGS), 'SMARTED-TV', 'SMARTEDTV')
        _, _, tamanho_tabela = struct.unpack_from(patch.FORMATO, novo, 0)
        self.assertEqual(tamanho_tabela, len(novo))
        _, _, tamanho_pool = struct.unpack_from(patch.FORMATO, novo, 12)
        self.assertEqual(tamanho_pool % 4, 0)
        self.assertLessEqual(12 + tamanho_pool, len(novo))

    def test_texto_inexistente_falha_sem_alterar(self):
        with self.assertRaises(patch.ERRO):
            patch.principal(montar_arsc(STRINGS), 'NAO-EXISTE', 'X')

    def test_arquivo_que_nao_e_arsc_falha(self):
        with self.assertRaises(patch.ERRO):
            patch.principal(b'\x00' * 64, 'SMARTED-TV', 'SMARTEDTV')

    def test_troca_todas_as_ocorrencias(self):
        strings = ['SMARTED-TV', 'SMARTED-TV']
        novo, trocas = patch.principal(montar_arsc(strings), 'SMARTED-TV', 'SMARTEDTV')
        self.assertEqual(trocas, 2)
        self.assertEqual(patch.listar(novo), ['SMARTEDTV', 'SMARTEDTV'])


class ApkZipTest(unittest.TestCase):
    def test_reescreve_so_o_arsc(self):
        with tempfile.TemporaryDirectory() as tmp:
            entrada = Path(tmp) / 'in.apk'
            saida = Path(tmp) / 'out.apk'
            with zipfile.ZipFile(entrada, 'w') as z:
                z.writestr('resources.arsc', montar_arsc(STRINGS))
                z.writestr('AndroidManifest.xml', b'<manifest/>')
                z.writestr('classes.dex', b'dex\n035\x00')
            self.assertEqual(patch.main([str(entrada), str(saida),
                                         'SMARTED-TV', 'SMARTEDTV']), 0)
            with zipfile.ZipFile(saida) as z:
                self.assertEqual(z.read('AndroidManifest.xml'), b'<manifest/>')
                self.assertEqual(z.read('classes.dex'), b'dex\n035\x00')
                self.assertIn('SMARTEDTV', patch.listar(z.read('resources.arsc')))


if __name__ == '__main__':
    unittest.main()
