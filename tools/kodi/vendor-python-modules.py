#!/usr/bin/env python3
"""Empacota modulos Python de terceiros como addons `script.module.*`.

A skin Bingie (e os scripts que ela usa) nao traz as bibliotecas que importa:
`script.skinshortcuts` precisa de `unidecode` e `simpleeval`, os scripts
`script.skin.helper.*` precisam de `arrow`, `script.bingie.helper` precisa de
`simplejson`, e o `plugin.video.themoviedb.helper` precisa de `requests`. Sem
esses modulos os servicos morrem no boot (ModuleNotFoundError) e o menu da skin
nao e gerado.

Este script baixa as wheels do PyPI (aarch64/cp311, que e o Python do Kodi 21 no
Android) e monta addons no formato do Kodi:

    script.module.<nome>/
        addon.xml   -> extension point xbmc.python.module, library="lib"
        lib/        -> pacotes prontos para o sys.path do Kodi

Uso:
    python3 tools/kodi/vendor-python-modules.py <destino>
    python3 tools/kodi/vendor-python-modules.py --check <pasta-de-addons>
"""
import ast
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# (id do addon no Kodi, pacote no PyPI)
MODULOS = [
    ('script.module.arrow', 'arrow'),
    ('script.module.dateutil', 'python-dateutil'),
    ('script.module.unidecode', 'unidecode'),
    ('script.module.simpleeval', 'simpleeval'),
    ('script.module.requests', 'requests'),
    ('script.module.urllib3', 'urllib3'),
    ('script.module.idna', 'idna'),
    ('script.module.certifi', 'certifi'),
    ('script.module.charset_normalizer', 'charset-normalizer'),
    ('script.module.beautifulsoup4', 'beautifulsoup4'),
    ('script.module.soupsieve', 'soupsieve'),
    ('script.module.musicbrainzngs', 'musicbrainzngs'),
    ('script.module.simplejson', 'simplejson'),
]

# modulos que o Kodi ja entrega (nao precisam de addon)
NATIVOS = {'xbmc', 'xbmcgui', 'xbmcplugin', 'xbmcaddon', 'xbmcvfs', 'xbmcdrm', 'xbmcwsgi'}

# imports opcionais que nunca sao obrigatorios (py2 antigo, extras de terceiros)
OPCIONAIS = {
    'httplib', 'urllib2', 'urlparse', 'StringIO', 'cStringIO', 'UserDict',
    '_typeshed', '_interpreters', 'pyodide', 'js', 'brotli', 'brotlicffi',
    'socks', 'h2', 'cchardet', 'html5lib', 'lxml', 'numpy', 'olefile',
    'defusedxml', 'cryptography', 'tzdata', 'typing_extensions', 'OpenSSL',
    'PyQt6', 'PySide6', 'IPython', 'backports', 'compression', 'chardet',
}

# ids empacotados por este script: nao entram na verificacao (as proprias
# bibliotecas trazem imports opcionais que nao fazem parte da skin)
EMPACOTADOS = {addon_id for addon_id, _ in MODULOS}

ADDON_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<addon id="{addon_id}" name="{addon_id}" version="{versao}" provider-name="SMARTED-TV">
  <requires>
    <import addon="xbmc.python" version="3.0.0"/>
  </requires>
  <extension point="xbmc.python.module" library="lib"/>
  <extension point="xbmc.addon.metadata">
    <summary lang="pt_BR">{pacote} empacotado para o SMARTED-TV</summary>
    <description lang="pt_BR">Modulo Python {pacote} ({versao}) empacotado como addon para que a skin e os scripts do SMARTED-TV funcionem sem depender de repositorio externo.</description>
    <platform>all</platform>
    <license>GPL-2.0-or-later</license>
  </extension>
</addon>
'''


def baixar(pacote: str, pasta: Path) -> Path:
    """Baixa a wheel compativel com o Python 3.11 do Kodi (aarch64)."""
    comando = [sys.executable, '-m', 'pip', 'download', pacote, '--no-deps',
               '--only-binary=:all:', '--platform', 'manylinux2014_aarch64',
               '--python-version', '3.11', '--implementation', 'cp', '--abi', 'cp311',
               '-d', str(pasta)]
    subprocess.run(comando, check=True, capture_output=True)
    wheels = sorted(pasta.glob('*.whl')) or sorted(pasta.glob('*.zip'))
    if not wheels:
        raise SystemExit('sem wheel para %s' % pacote)
    return wheels[0]


def montar(addon_id: str, pacote: str, destino: Path, temporaria: Path) -> dict:
    pasta_pacote = temporaria / pacote
    pasta_pacote.mkdir(parents=True, exist_ok=True)
    wheel = baixar(pacote, pasta_pacote)
    versao = wheel.name.split('-')[1]
    alvo = destino / addon_id
    if alvo.exists():
        shutil.rmtree(alvo)
    (alvo / 'lib').mkdir(parents=True)
    with zipfile.ZipFile(wheel) as z:
        for nome in z.namelist():
            if nome.endswith('/') or '.dist-info/' in nome or nome.startswith('bin/'):
                continue
            z.extract(nome, alvo / 'lib')
    (alvo / 'addon.xml').write_text(
        ADDON_XML.format(addon_id=addon_id, pacote=pacote, versao=versao), encoding='utf-8')
    return {'addon': addon_id, 'pacote': pacote, 'versao': versao,
            'arquivos': sum(1 for p in alvo.rglob('*') if p.is_file())}


def _imports_do_arquivo(arvore):
    """Devolve os imports que nao estao protegidos por try/except ImportError."""
    protegidos = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Try):
            continue
        tipos = []
        for tratador in no.handlers:
            tipo = tratador.type
            if isinstance(tipo, ast.Name):
                tipos.append(tipo.id)
            elif isinstance(tipo, ast.Tuple):
                tipos.extend(e.id for e in tipo.elts if isinstance(e, ast.Name))
        if not ({'ImportError', 'ModuleNotFoundError', 'Exception'} & set(tipos)):
            continue
        for filho in no.body:
            for interno in ast.walk(filho):
                protegidos.add(id(interno))
    for no in ast.walk(arvore):
        if id(no) in protegidos:
            continue
        if isinstance(no, ast.Import):
            nomes = [a.name.split('.')[0] for a in no.names]
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes = [no.module.split('.')[0]]
        else:
            continue
        for nome in nomes:
            yield nome


def imports_de(addons: Path) -> dict:
    """Mapeia modulo de terceiro -> addons que o importam de verdade."""
    locais = {p.name for p in addons.iterdir() if p.is_dir()}
    usados = {}
    for addon in sorted(addons.iterdir()):
        if not addon.is_dir() or addon.name in EMPACOTADOS:
            continue
        for py in addon.rglob('*.py'):
            try:
                arvore = ast.parse(py.read_text(encoding='utf-8', errors='ignore'))
            except SyntaxError:
                continue
            for nome in _imports_do_arquivo(arvore):
                if (nome in NATIVOS or nome in locais or nome in OPCIONAIS
                        or nome in sys.stdlib_module_names):
                    continue
                usados.setdefault(nome, set()).add(addon.name)
    return usados


def modulos_empacotados(addons: Path) -> set:
    nomes = set()
    for addon in sorted(addons.iterdir()):
        lib = addon / 'lib'
        if not addon.is_dir() or not lib.is_dir():
            continue
        for item in lib.iterdir():
            if item.is_dir():
                nomes.add(item.name)
            elif item.suffix in ('.py', '.so'):
                nomes.add(item.stem.split('.')[0])
    return nomes


def verificar(addons: Path) -> int:
    """Confere que todo import de terceiro tem um addon embarcado."""
    disponiveis = modulos_empacotados(addons)
    faltando = {}
    for modulo, donos in imports_de(addons).items():
        if modulo in disponiveis:
            continue
        faltando[modulo] = sorted(donos)
    if not faltando:
        print('Dependencias Python conferidas: todos os imports de terceiro estao embarcados '
              '(%d modulos).' % len(disponiveis))
        return 0
    for modulo, donos in sorted(faltando.items()):
        print('::error::modulo Python ausente: %s (importado por %s)'
              % (modulo, ', '.join(donos)))
    print('Faltando: %s' % ', '.join(sorted(faltando)))
    return 1


def main(argv):
    if len(argv) == 1:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    if argv[1] == '--check':
        if len(argv) != 3:
            raise SystemExit('Uso: vendor-python-modules.py --check <pasta-de-addons>')
        return verificar(Path(argv[2]))
    if len(argv) != 2:
        raise SystemExit('Uso: vendor-python-modules.py <destino>')
    destino = Path(argv[1])
    destino.mkdir(parents=True, exist_ok=True)
    temporaria = Path(tempfile.mkdtemp(prefix='modulos-pypi-'))
    for addon_id, pacote in MODULOS:
        try:
            info = montar(addon_id, pacote, destino, temporaria)
        except subprocess.CalledProcessError as erro:
            detalhe = erro.stderr.decode('utf-8', 'ignore').strip().splitlines()[-3:]
            print('::warning::%s (%s) nao empacotado: %s'
                  % (addon_id, pacote, ' | '.join(detalhe)))
            continue
        print('%-34s %-18s %-10s %3d arquivos' % (
            info['addon'], info['pacote'], info['versao'], info['arquivos']))
    shutil.rmtree(temporaria, ignore_errors=True)
    return verificar(destino)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
