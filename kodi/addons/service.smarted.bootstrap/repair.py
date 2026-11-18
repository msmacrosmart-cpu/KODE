# -*- coding: utf-8 -*-
"""Reparo do perfil Kodi usado pelo SMARTED-TV.

Objetivo: garantir que, no primeiro boot, o plugin.video.BrazucaPlay.Matrix e
todas as dependências obrigatórias estejam instalados (pasta addons do perfil),
com dados de addon criados e o bootstrap próprio do plugin (cloudrequest) já
descompactado — evitando que a interface abra vazia porque o addon "não pôde
ser carregado".

Regras:
  * nada é inventado — o reparo só usa os .zip oficiais que já vêm no perfil
    (``addons/packages/``) ou o payload embutido neste addon;
  * nada é apagado do usuário — só criamos o que falta;
  * qualquer falha é reportada, nunca silenciada.

O módulo não importa ``xbmc*``: recebe caminhos por parâmetro, para poder ser
testado fora do Kodi.
"""
from __future__ import absolute_import, unicode_literals

import os
import shutil
import zipfile
from xml.etree import ElementTree

# Addon que o app precisa carregar e, portanto, o alvo principal do reparo.
BRAZUCA_ID = 'plugin.video.BrazucaPlay.Matrix'

# Dependências usadas pelo menu principal do Brazuca Play. As duas últimas são
# opcionais no addon.xml, mas o app inteiro depende delas quando presentes.
BASE_ADDONS = [
    'script.module.six',
    'script.module.kodi-six',
    'script.module.requests',
    'script.module.simplejson',
    'script.module.certifi',
    'script.module.chardet',
    'script.module.idna',
    'script.module.urllib3',
]

# Payload embutido: o plugin baixa esse pacote em ``<addon>/cloudrequest`` na
# primeira execução. Sem rede (ou com o servidor fora) o import falha e o menu
# abre vazio; por isso já entregamos o pacote pronto.
CLOUDREQUEST_MEMBER = 'cloudrequest/requests_toolbelt/__init__.py'
CLOUDREQUEST_VERSION = '1.0.0'


def _log(entries, message):
    entries.append(message)


def parse_addon_xml(path):
    """Lê um addon.xml e devolve {id, version, requires, libraries} ou None."""
    try:
        root = ElementTree.parse(path).getroot()
    except Exception:
        return None
    if root.tag != 'addon' or not root.get('id'):
        return None
    requires = []
    for imp in root.findall('./requires/import'):
        addon_id = imp.get('addon')
        if not addon_id:
            continue
        requires.append({
            'id': addon_id,
            'version': imp.get('version') or '',
            'optional': (imp.get('optional') or '').lower() == 'true',
        })
    libraries = []
    for ext in root.findall('./extension'):
        point = ext.get('point') or ''
        library = ext.get('library')
        if library and point in (
            'xbmc.python.pluginsource',
            'xbmc.python.script',
            'xbmc.python.module',
            'xbmc.service',
        ):
            libraries.append(library)
    return {
        'id': root.get('id'),
        'version': root.get('version') or '',
        'requires': requires,
        'libraries': libraries,
    }


def addon_status(addons_dir, addon_id):
    """Devolve (ok, motivo) para o addon instalado em ``addons_dir``."""
    path = os.path.join(addons_dir, addon_id)
    if not os.path.isdir(path):
        return False, 'ausente'
    info = parse_addon_xml(os.path.join(path, 'addon.xml'))
    if info is None:
        return False, 'addon.xml invalido'
    if info['id'] != addon_id:
        return False, 'addon.xml de outro addon (%s)' % info['id']
    for library in info['libraries']:
        lib_path = os.path.join(path, library)
        if not os.path.exists(lib_path):
            # bibliotecas podem ser pastas de pacote python
            if not os.path.isdir(lib_path):
                return False, 'arquivo %s ausente' % library
    return True, 'ok'


def find_package(packages_dir, addon_id):
    """Localiza ``<id>-<versao>.zip`` na pasta de pacotes (maior versão)."""
    if not os.path.isdir(packages_dir):
        return None
    candidates = []
    for name in os.listdir(packages_dir):
        if not name.lower().endswith('.zip'):
            continue
        stem = name[:-4]
        if not stem.startswith(addon_id + '-'):
            continue
        rest = stem[len(addon_id) + 1:]
        if not rest or rest[0].isdigit():
            candidates.append(os.path.join(packages_dir, name))
    if not candidates:
        return None
    return sorted(candidates, key=os.path.basename)[-1]


def _safe_members(archive, addon_id, strip_root=True):
    """Valida os membros antes de extrair (sem path traversal/symlink).

    ``strip_root`` remove a pasta de topo quando ela é o próprio id do addon
    (pacotes de repositório) ou mantém o caminho completo (payload embutido).
    """
    root = ''
    names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
    if not names:
        raise ValueError('pacote vazio')
    if strip_root and addon_id and all('/' in name for name in names):
        first = names[0].split('/', 1)[0]
        if first == addon_id and all(name.split('/', 1)[0] == addon_id for name in names):
            root = first + '/'
    members = []
    for entry in archive.infolist():
        name = entry.filename
        if entry.is_dir():
            continue
        if name.startswith('/') or '\\' in name or '..' in name.split('/'):
            raise ValueError('caminho inseguro em %s' % name)
        if root and not name.startswith(root):
            raise ValueError('membro fora do addon: %s' % name)
        members.append((entry, name[len(root):]))
    return members


def _checar_espaco(pacote, destino, log, folga=8 * 1024 * 1024):
    """Avisa (sem abortar) quando o disco do perfil nao comporta a extracao.

    Addon grande extraido em projetor com pouca memoria interna e a causa mais
    comum de "erro nos addons" e de Home vazia. O aviso vai para o log do
    bootstrap, e a extracao segue (o sistema ainda pode ter espaco depois).
    """
    try:
        tamanho = os.path.getsize(pacote)
        livre = shutil.disk_usage(destino).free
    except Exception:
        return None
    if livre < tamanho + folga:
        _log(log, 'ESPACO BAIXO em %s: %d MB livres, pacote de %d MB'
             % (destino, livre // (1024 * 1024), tamanho // (1024 * 1024)))
        return False
    return True


def install_package(packages_dir, addons_dir, addon_id, log):
    """Extrai o pacote oficial do addon para ``addons_dir``. Devolve bool."""
    package = find_package(packages_dir, addon_id)
    if not package:
        _log(log, 'SEM PACOTE para %s em %s' % (addon_id, packages_dir))
        return False
    target = os.path.join(addons_dir, addon_id)
    temporario = target + '.novo'
    try:
        with zipfile.ZipFile(package) as archive:
            members = _safe_members(archive, addon_id)
            # Extrai para uma pasta temporaria e so entao troca: se o disco
            # encher no meio (comum em projetor/box com 8 GB), a pasta antiga
            # continua inteira em vez de virar um addon pela metade - era isso
            # que deixava "erro nos addons" no projetor.
            if os.path.isdir(temporario):
                shutil.rmtree(temporario)
            os.makedirs(temporario)
            _checar_espaco(package, addons_dir, log)
            for entry, relative in members:
                destination = os.path.join(temporario, *relative.split('/'))
                parent = os.path.dirname(destination)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent)
                with archive.open(entry) as source, open(destination, 'wb') as out:
                    shutil.copyfileobj(source, out, 256 * 1024)
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.move(temporario, target)
        ok, reason = addon_status(addons_dir, addon_id)
        _log(log, '%s %s a partir de %s (%s)' % (
            'RESTAURADO' if ok else 'FALHOU', addon_id, os.path.basename(package), reason))
        return ok
    except Exception as error:  # pacote corrompido, permissão, disco cheio...
        _log(log, 'ERRO ao extrair %s: %s' % (addon_id, error))
        shutil.rmtree(temporario, ignore_errors=True)
        # NAO apagar a versao que ja esta no perfil: um addon antigo que
        # carrega e melhor do que nenhum addon (tela preta nos addons).
        return False


def _ensure_addon(addon_id, addons_dir, packages_dir, log, seen, repaired):
    """Garante um addon e, recursivamente, suas dependências obrigatórias.

    Devolve a lista de problemas encontrados (vazia quando tudo está ok).
    """
    if addon_id in seen:
        return []
    seen.add(addon_id)
    problems = []
    ok, reason = addon_status(addons_dir, addon_id)
    if not ok:
        if reason != 'ausente':
            _log(log, 'PROBLEMA %s: %s' % (addon_id, reason))
        ok = install_package(packages_dir, addons_dir, addon_id, log)
        if ok:
            repaired.append(addon_id)
    if not ok:
        problems.append(addon_id)
        return problems
    info = parse_addon_xml(os.path.join(addons_dir, addon_id, 'addon.xml'))
    if not info:
        problems.append(addon_id)
        return problems
    for require in info['requires']:
        if require['optional']:
            continue
        if require['id'].startswith(('xbmc.', 'kodi.binary')):
            continue
        problems.extend(_ensure_addon(require['id'], addons_dir, packages_dir,
                                      log, seen, repaired))
    return problems


def ensure_addon_data(home, addon_id, addons_dir, log):
    """Cria ``userdata/addon_data/<id>`` quando o perfil não trouxe a pasta."""
    data_dir = os.path.join(home, 'userdata', 'addon_data', addon_id)
    if os.path.isdir(data_dir):
        return True
    try:
        os.makedirs(data_dir)
        _log(log, 'CRIADO dados de addon %s' % data_dir)
        return True
    except Exception as error:
        _log(log, 'ERRO ao criar dados de %s: %s' % (addon_id, error))
        return False


def cloudrequest_ready(addon_path):
    """True quando o pacote cloudrequest já está descompactado e na versão certa."""
    init_file = os.path.join(addon_path, *CLOUDREQUEST_MEMBER.split('/'))
    if not os.path.isfile(init_file):
        return False
    try:
        with open(init_file, 'r') as handle:
            content = handle.read()
    except Exception:
        return False
    marker = "__version__ = '%s'" % CLOUDREQUEST_VERSION
    return marker in content


def install_cloudrequest(addon_path, payload_zip, log):
    """Descompacta o cloudrequest embutido dentro do addon do Brazuca Play."""
    if cloudrequest_ready(addon_path):
        return True
    if not os.path.isfile(payload_zip):
        _log(log, 'SEM PAYLOAD cloudrequest (%s)' % payload_zip)
        return False
    try:
        with zipfile.ZipFile(payload_zip) as archive:
            members = _safe_members(archive, 'cloudrequest', strip_root=False)
            for entry, relative in members:
                if not relative:
                    continue
                destination = os.path.join(addon_path, *relative.split('/'))
                parent = os.path.dirname(destination)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent)
                with archive.open(entry) as source, open(destination, 'wb') as out:
                    shutil.copyfileobj(source, out, 256 * 1024)
        _log(log, 'INSTALADO cloudrequest em %s' % addon_path)
        return True
    except Exception as error:
        _log(log, 'ERRO ao instalar cloudrequest: %s' % error)
        return False


def repair_profile(home, payload_dir, log=None):
    """Executa o reparo completo. Devolve um relatório dict.

    ``home`` é a pasta ``.kodi`` do perfil; ``payload_dir`` aponta para a pasta
    ``payload`` deste addon (contém cloudrequest-py3.zip).
    """
    log = [] if log is None else log
    addons_dir = os.path.join(home, 'addons')
    packages_dir = os.path.join(addons_dir, 'packages')
    report = {
        'ok': False,
        'addons_dir': addons_dir,
        'installed': [],
        'repaired': [],
        'missing': [],
        'required': [],
        'log': log,
    }

    if not os.path.isdir(addons_dir):
        try:
            os.makedirs(addons_dir)
            _log(log, 'CRIADO %s' % addons_dir)
        except Exception as error:
            _log(log, 'ERRO ao criar %s: %s' % (addons_dir, error))
            return report

    seen = set()
    repaired = []
    problems = _ensure_addon(BRAZUCA_ID, addons_dir, packages_dir, log, seen, repaired)
    if BRAZUCA_ID in problems:
        # addon ausente e sem pacote: ainda tentamos as dependências conhecidas
        for addon_id in BASE_ADDONS:
            if addon_id in seen:
                continue
            problems.extend(_ensure_addon(addon_id, addons_dir, packages_dir,
                                          log, seen, repaired))
    report['required'] = sorted(seen)
    report['missing'] = problems
    report['repaired'] = repaired

    brazuca_path = os.path.join(addons_dir, BRAZUCA_ID)
    if os.path.isdir(brazuca_path):
        install_cloudrequest(brazuca_path, os.path.join(payload_dir, 'cloudrequest-py3.zip'), log)
        ensure_addon_data(home, BRAZUCA_ID, addons_dir, log)

    report['ok'] = not report['missing'] and addon_status(addons_dir, BRAZUCA_ID)[0]
    _log(log, 'RESULTADO: %s (restaurados=%d, faltando=%d)' % (
        'ok' if report['ok'] else 'incompleto',
        len(report['repaired']),
        len(report['missing']),
    ))
    return report
