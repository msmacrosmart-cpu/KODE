#!/usr/bin/env python3
"""Troca um texto dentro do ``resources.arsc`` sem recompilar o APK.

Um APK traz ``resources.arsc`` com um *string pool* global no comeco do
arquivo. O nome exibido do aplicativo (``android:label="@string/app_name"``) e
uma dessas strings. Para trocar o texto nao basta substituir bytes: o pool
guarda o tamanho de cada string e os deslocamentos sao relativos, entao trocar
"SMARTED-TV" por "SMARTEDTV" muda o arquivo de tamanho.

O que este modulo faz:

1. le o cabecalho do ``resources.arsc`` e o *string pool* global;
2. decodifica todas as strings (UTF-8 ou UTF-16, os dois formatos do AAPT2);
3. troca **exatamente** as ocorrencias do texto pedido;
4. remonta o pool com os mesmos flags, estilos e ordem (os indices usados
   pelas entradas de recurso continuam valendo);
5. atualiza o tamanho do chunk do pool e do cabecalho da tabela.

Se o texto pedido nao existir, ou se o pool tiver qualquer coisa fora do
formato esperado, o modulo levanta ``ERRO`` e o build para — nunca publica um
APK com a tabela de recursos inconsistente.

Uso:
    python3 tools/kodi/patch-resources-label.py ENTRADA.apk SAIDA.apk SMARTED-TV SMARTEDTV
    python3 tools/kodi/patch-resources-label.py --listar ENTRADA.apk
"""
from __future__ import annotations

import struct
import sys
import zipfile
from pathlib import Path

FORMATO = '<HHI'          # type, headerSize, size
RES_STRING_POOL = 0x0001
RES_TABLE = 0x0002
FLAG_SORTED = 0x00000001
FLAG_UTF8 = 0x00000100


class ERRO(SystemExit):
    """Erro de formato: aborta o build com mensagem legivel."""


def _alinhar4(valor: int) -> int:
    return (valor + 3) & ~3


class Pool:
    """String pool de um ``resources.arsc`` (somente leitura + remontagem)."""

    def __init__(self, dados: bytes, inicio: int):
        self.dados = dados
        self.inicio = inicio
        tipo, header_size, tamanho = struct.unpack_from(FORMATO, dados, inicio)
        if tipo != RES_STRING_POOL:
            raise ERRO('resources.arsc: o primeiro chunk nao e um string pool '
                       '(tipo 0x%04X em 0x%X)' % (tipo, inicio))
        if header_size < 28:
            raise ERRO('string pool: headerSize inesperado (%d)' % header_size)
        (self.string_count, self.style_count, self.flags,
         self.strings_start, self.styles_start) = struct.unpack_from('<IIIII', dados, inicio + 8)
        self.header_size = header_size
        self.tamanho = tamanho
        self.fim = inicio + tamanho
        if self.fim > len(dados):
            raise ERRO('string pool passa do fim do arquivo')
        offsets_de = inicio + header_size
        self.string_offsets = list(struct.unpack_from('<%dI' % self.string_count, dados, offsets_de))
        self.style_offsets = list(struct.unpack_from('<%dI' % self.style_count,
                                                     dados, offsets_de + 4 * self.string_count))
        self.strings = [self._ler_string(offset) for offset in self.string_offsets]
        self.estilos = b''
        if self.style_count and self.styles_start:
            self.estilos = dados[inicio + self.styles_start:self.fim]

    @property
    def utf8(self) -> bool:
        return bool(self.flags & FLAG_UTF8)

    def _ler_string(self, offset: int) -> str:
        pos = self.inicio + self.strings_start + offset
        if self.utf8:
            # tamanho em caracteres e em bytes, cada um em 1 ou 2 bytes
            n_chars, pos = _ler_len_utf8(self.dados, pos)
            n_bytes, pos = _ler_len_utf8(self.dados, pos)
            bruto = self.dados[pos:pos + n_bytes]
            return bruto.decode('utf-8', 'surrogatepass')
        n_chars, pos = _ler_len_utf16(self.dados, pos)
        bruto = self.dados[pos:pos + n_chars * 2]
        return bruto.decode('utf-16-le', 'surrogatepass')

    def montar(self, novas: list[str]) -> bytes:
        if len(novas) != self.string_count:
            raise ERRO('quantidade de strings mudou (%d -> %d)' % (self.string_count, len(novas)))
        dados = bytearray()
        offsets = []
        for texto in novas:
            offsets.append(len(dados))
            if self.utf8:
                bruto = texto.encode('utf-8', 'surrogatepass')
                dados += _escrever_len_utf8(len(texto))
                dados += _escrever_len_utf8(len(bruto))
                dados += bruto + b'\x00'
            else:
                bruto = texto.encode('utf-16-le', 'surrogatepass')
                dados += _escrever_len_utf16(len(bruto) // 2)
                dados += bruto + b'\x00\x00'
            while len(dados) % 4:
                dados += b'\x00'
        # os estilos comecam alinhados e depois da area de strings
        estilos = bytearray(self.estilos)
        while estilos and len(estilos) % 4:
            estilos += b'\x00'
        strings_start = self.header_size + 4 * (self.string_count + self.style_count)
        styles_start = strings_start + len(dados) if estilos else 0
        tamanho = _alinhar4(strings_start + len(dados) + len(estilos))
        # A flag SORTED descreve a ordem lexicografica: trocar um texto pode
        # quebra-la, entao ela e removida (o Kodi/Android nao depende dela).
        flags = self.flags & ~FLAG_SORTED
        cabecalho = struct.pack('<HHIIIIII', RES_STRING_POOL, self.header_size, tamanho,
                                self.string_count, self.style_count, flags,
                                strings_start, styles_start)
        corpo = bytearray(cabecalho)
        corpo += struct.pack('<%dI' % len(offsets), *offsets)
        if self.style_count:
            corpo += struct.pack('<%dI' % self.style_count, *self.style_offsets)
        corpo += dados
        corpo += estilos
        while len(corpo) < tamanho:
            corpo += b'\x00'
        return bytes(corpo)


def _ler_len_utf8(dados: bytes, pos: int) -> tuple[int, int]:
    primeiro = dados[pos]
    if primeiro & 0x80:
        return ((primeiro & 0x7F) << 8) | dados[pos + 1], pos + 2
    return primeiro, pos + 1


def _escrever_len_utf8(valor: int) -> bytes:
    if valor > 0x7F:
        return bytes([0x80 | (valor >> 8), valor & 0xFF])
    return bytes([valor])


def _ler_len_utf16(dados: bytes, pos: int) -> tuple[int, int]:
    (primeiro,) = struct.unpack_from('<H', dados, pos)
    if primeiro & 0x8000:
        (segundo,) = struct.unpack_from('<H', dados, pos + 2)
        return ((primeiro & 0x7FFF) << 16) | segundo, pos + 4
    return primeiro, pos + 2


def _escrever_len_utf16(valor: int) -> bytes:
    if valor > 0x7FFF:
        return struct.pack('<HH', 0x8000 | (valor >> 16), valor & 0xFFFF)
    return struct.pack('<H', valor)


def principal(dados: bytes, antigo: str, novo: str,
              tolerante: bool = False) -> tuple[bytes, int]:
    """Devolve (arsc novo, quantidade de ocorrencias trocadas).

    Com ``tolerante=True``, um APK que ja tem o nome novo (rebuild em cima de
    uma release nossa) passa sem erro: devolve os bytes originais e 0 trocas.
    """
    if len(dados) < 12:
        raise ERRO('resources.arsc curto demais (%d bytes)' % len(dados))
    tipo, header_size, tamanho = struct.unpack_from(FORMATO, dados, 0)
    if tipo != RES_TABLE:
        raise ERRO('resources.arsc: tipo 0x%04X (esperado 0x%04X)' % (tipo, RES_TABLE))
    if header_size < 12:
        raise ERRO('resources.arsc: headerSize inesperado (%d)' % header_size)
    if tamanho > len(dados):
        raise ERRO('resources.arsc: size %d maior que o arquivo (%d)' % (tamanho, len(dados)))

    pool = Pool(dados, header_size)
    trocas = 0
    novas = []
    for texto in pool.strings:
        if texto == antigo:
            novas.append(novo)
            trocas += 1
        else:
            novas.append(texto)
    if not trocas:
        # build em cima de um APK que JA foi renomeado (1.0.58 em diante): nada
        # a trocar, e isso nao e erro — devolve o arquivo como veio.
        if tolerante and novo in pool.strings:
            return dados, 0
        raise ERRO('texto %r nao existe no pool (nada foi alterado)' % antigo)

    corpo_novo = pool.montar(novas)
    resto = dados[pool.fim:tamanho]
    novo_total = header_size + len(corpo_novo) + len(resto)
    cabecalho = struct.pack('<HHI', tipo, header_size, novo_total) + dados[8:header_size]
    resultado = bytearray(cabecalho)
    resultado += corpo_novo
    resultado += resto
    # confere o resultado com o mesmo leitor antes de devolver
    conferencia = Pool(bytes(resultado), header_size)
    if conferencia.strings != novas:
        raise ERRO('remontagem inconsistente do string pool')
    return bytes(resultado), trocas


def listar(dados: bytes) -> list[str]:
    _, header_size, _ = struct.unpack_from(FORMATO, dados, 0)
    return Pool(dados, header_size).strings


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == '--listar':
        with zipfile.ZipFile(argv[1]) as z:
            for i, texto in enumerate(listar(z.read('resources.arsc'))):
                if texto.strip():
                    print('%4d  %s' % (i, texto))
        return 0
    if len(argv) != 4:
        print(__doc__)
        return 2
    entrada, saida, antigo, novo = argv
    if antigo == novo:
        raise ERRO('texto de origem e destino iguais')
    with zipfile.ZipFile(entrada) as z:
        if 'resources.arsc' not in z.namelist():
            raise ERRO('APK sem resources.arsc')
        dados = z.read('resources.arsc')
        info = z.getinfo('resources.arsc')
        conteudo, trocas = principal(dados, antigo, novo)
        with zipfile.ZipFile(saida, 'w', allowZip64=True) as dst:
            for item in z.infolist():
                if item.filename == 'resources.arsc':
                    dst.writestr(info, conteudo)
                elif item.is_dir():
                    continue
                else:
                    with z.open(item) as fonte, dst.open(item, 'w') as alvo:
                        alvo.write(fonte.read())
    print('%s: %d ocorrencia(s) de %r trocadas por %r'
          % (saida, trocas, antigo, novo))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
