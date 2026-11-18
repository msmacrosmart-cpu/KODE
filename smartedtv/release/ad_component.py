"""Declara UMA activity privada nova no AndroidManifest.xml, sem mexer na base.

A ``smartedtv.full.AdBreak`` é a ponte de ciclo de vida do anúncio. Ela entra
como elemento novo dentro de ``<application>`` e a string do nome é anexada ao
pool: os índices antigos (inclusive o resource map) ficam iguais e nenhum
atributo de activity existente é alterado.
"""
import struct

NOME = 'smartedtv.full.AdBreak'
PREROLL = 'smartedtv.full.PreRollActivity'


def _atributos(b, editor, pool, pos):
    """{nome: (namespace, nome, tipo, offset do valor)} da tag aberta em ``pos``."""
    passo = editor._u16(b, pos + 26)
    base = pos + 16 + editor._u16(b, pos + 24)
    saida = {}
    for i in range(editor._u16(b, pos + 28)):
        p = base + i * passo
        saida[pool[editor._u32(b, p + 4)]] = (editor._u32(b, p), editor._u32(b, p + 4),
                                              b[p + 15], p)
    return saida


def _tags(b, editor, pool):
    """Lista (pos, tipo, nome, profundidade) na ordem do arquivo."""
    profundidade, saida = 0, []
    for pos, tipo, _, _tamanho in editor._chunks_axml(b):
        if tipo == 0x102:
            profundidade += 1
            saida.append((pos, tipo, pool[editor._u32(b, pos + 20)], profundidade))
        elif tipo == 0x103:
            saida.append((pos, tipo, None, profundidade))
            profundidade -= 1
    return saida


def _elemento_atividade(ns_android, indice_tag, nome_attr, indice_nome, indice_exported):
    atributos = [(ns_android, nome_attr, 0x03, indice_nome),
                 (ns_android, indice_exported, 0x12, 0)]
    corpo = b''.join(struct.pack('<III', ns, nome, 0xffffffff) +
                     struct.pack('<HBBI', 8, 0, tipo, valor)
                     for ns, nome, tipo, valor in atributos)
    total = 36 + 20 * len(atributos)
    return (struct.pack('<HHIII', 0x102, 16, total, 1, 0xffffffff) +
            struct.pack('<II', 0xffffffff, indice_tag) +
            struct.pack('<HHHHHH', 20, 20, len(atributos), 0, 0, 0) + corpo +
            struct.pack('<HHIIIII', 0x103, 16, 24, 0, 0xffffffff, 0xffffffff, 0xffffffff))


def register(xml, editor):
    b = bytearray(xml)
    h, _, header, size = next(c for c in editor._chunks_axml(b) if c[1] == 1)
    if header != 28 or editor._u32(b, h + 12) or editor._u32(b, h + 24):
        raise ValueError('pool AXML com estilos: nao suportado')
    pool = editor._strings_do_pool(b, h)
    if NOME in pool:
        raise ValueError('ponte do anuncio ja registrada')

    tags = _tags(b, editor, pool)
    inicio_app = next((p for p, _, n, _ in tags if n == 'application'), None)
    if inicio_app is None:
        raise ValueError('<application> ausente')
    profundidade_app = next(prof for p, _, n, prof in tags if n == 'application')
    fim_app = next(p for p, tipo, _, prof in tags
                   if tipo == 0x103 and prof == profundidade_app)
    exemplo = None
    for pos, tipo, nome, prof in tags:
        if tipo != 0x102 or nome != 'activity' or prof != profundidade_app + 1:
            continue
        attrs = _atributos(b, editor, pool, pos)
        indice = editor._u32(b, attrs['name'][3] + 16)
        if indice < len(pool) and pool[indice] == PREROLL:
            exemplo = attrs
            break
    if exemplo is None:
        raise ValueError('PreRollActivity ausente da base')
    ns_android, nome_attr, _, _ = exemplo['name']
    if ns_android == 0xffffffff or pool[ns_android] != editor.ANDROID:
        raise ValueError('namespace android inesperado na activity de pre-roll')
    if 'exported' not in exemplo or exemplo['exported'][2] != 0x12:
        raise ValueError('android:exported booleano ausente na base')

    # 1. string do nome anexada ao pool (índices antigos não se movem)
    utf8 = bool(editor._u32(b, h + 16) & 0x100)
    texto = (bytes([len(NOME)] * 2) + NOME.encode() + b'\0' if utf8
             else struct.pack('<H', len(NOME)) + NOME.encode('utf-16-le') + b'\0\0')
    texto += bytes(-len(texto) % 4)
    strings_start = editor._u32(b, h + 20)
    b[h + size:h + size] = texto
    at = h + header + len(pool) * 4
    b[at:at] = struct.pack('<I', size - strings_start)
    struct.pack_into('<I', b, h + 4, size + 4 + len(texto))
    struct.pack_into('<I', b, h + 8, len(pool) + 1)
    struct.pack_into('<I', b, h + 16, editor._u32(b, h + 16) & ~1)
    struct.pack_into('<I', b, h + 20, strings_start + 4)

    # 2. insere a activity nova no fim do <application> (posições deslocadas)
    fim_app += 4 + len(texto)
    b[fim_app:fim_app] = _elemento_atividade(
        ns_android, pool.index('activity'), nome_attr, len(pool), exemplo['exported'][1])
    struct.pack_into('<I', b, 4, len(b))
    return bytes(b)
