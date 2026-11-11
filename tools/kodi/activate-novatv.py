#!/usr/bin/env python3
"""Torna a skin Nova TV a skin efetivamente carregada no APK.

Dois mecanismos independentes, ambos verificados antes de escrever:

1. Skin padrão do motor (assets/system/settings/settings.xml):
   `lookandfeel.skin` é o default compilado do Kodi. Instalações sem
   preferência salva passam a abrir na Nova TV.
2. Perfil semeado (assets/smarted/profile/...): instalações novas recebem o
   perfil com `skin.estilo.personalizado` ativo, inclusive nos backups do wizard
   (`My_Builds/*.zip`), que o plugin.program.openwizard pode restaurar.
   O `ProfileSeed.setDefaultSkin()` do dex troca apenas a linha
   `<setting id="lookandfeel.skin" default="true">skin.estuary</setting>`;
   se a linha não estiver nesse formato exato ele lança exceção e o
   bootstrap falha, impedindo o app de abrir. Por isso a troca é feita aqui,
   na origem, e o formato original é preservado.

O perfil existente do usuário não é tocado: `ProfileDirectorySeed.install`
retorna imediatamente quando `$HOME/.kodi` já existe.

Uso:
    python3 tools/kodi/activate-novatv.py DECODED_DIR
    python3 tools/kodi/activate-novatv.py --apk ENTRADA.apk SAIDA.apk
"""
import argparse
import io
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

SKIN_ID = 'skin.estilo.personalizado'
SKIN_DEFAULT = re.compile(br'<default>skin\.[a-z0-9_.]+</default>')
PROFILE_SKIN = re.compile(
    br'<setting id="lookandfeel\.skin"[^>]*>skin\.estuary</setting>')


def activate_settings(path: Path) -> bool:
    """Garante skin.estilo.personalizado como default em assets/system/settings/settings.xml.

    O APK de producao ja vem com skin.estilo.personalizado aqui; a funcao valida e corrige
    apenas se o default estiver apontando para outra skin.
    """
    data = path.read_bytes()
    matches = SKIN_DEFAULT.findall(data)
    if len(matches) != 1:
        raise SystemExit(f'{path}: esperava um unico <default>skin.*</default>')
    if matches[0] == b'<default>skin.estilo.personalizado</default>':
        return False
    updated = data.replace(matches[0], b'<default>skin.estilo.personalizado</default>')
    ET.fromstring(updated)
    if updated.count(b'<default>skin.estilo.personalizado</default>') != 1:
        raise SystemExit(f'{path}: substituicao nao aplicada')
    path.write_bytes(updated)
    return True


def activate_guisettings(data: bytes) -> tuple[bytes, bool]:
    """Ajusta guisettings.xml do perfil; idempotente."""
    matches = PROFILE_SKIN.findall(data)
    if len(matches) > 1:
        raise SystemExit('guisettings: mais de uma linha lookandfeel.skin')
    if len(matches) == 1:
        updated = PROFILE_SKIN.sub(
            b'<setting id="lookandfeel.skin" default="true">skin.estilo.personalizado</setting>', data, count=1)
        if b'skin.estuary' in updated:
            raise SystemExit('guisettings: skin.estuary remanescente')
        return updated, True
    if b'id="lookandfeel.skin"' in data and b'skin.estilo.personalizado' in data:
        return data, False
    raise SystemExit('guisettings: linha lookandfeel.skin ausente ou inesperada')


def rewrite_zip(path: Path, transform) -> bool:
    """Reescreve um ZIP preservando ordem/compressao; transform(name, bytes)->bytes|None."""
    with zipfile.ZipFile(path) as src:
        entries = [(item, src.read(item.filename)) for item in src.infolist()]
    changed = False
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as dst:
        for item, data in entries:
            new = transform(item.filename, data)
            if new is not None and new != data:
                changed = True
            dst.writestr(item, data if new is None else new)
    if changed:
        path.write_bytes(buffer.getvalue())
    return changed


def activate_profile(profile: Path) -> list[str]:
    """Ativa a skin nos arquivos do perfil e nos backups do wizard."""
    actions = []
    root = profile
    if not root.is_dir():
        raise SystemExit(f'perfil ausente: {root}')

    gui = root / 'userdata/guisettings.xml'
    if gui.is_file():
        updated, changed = activate_guisettings(gui.read_bytes())
        if changed:
            gui.write_bytes(updated)
            actions.append('userdata/guisettings.xml')

    candidates = sorted((root / 'My_Builds').glob('*.zip'))
    for extra in (root / 'SaveData.zip',):
        if extra.is_file():
            candidates.append(extra)
    for backup in candidates:
        def transform(name, data, _b=backup):
            if not name.endswith('guisettings.xml'):
                return None
            updated, _ = activate_guisettings(data)
            return updated

        try:
            if rewrite_zip(backup, transform):
                actions.append(str(backup.relative_to(root)))
        except SystemExit as exc:
            # Backups sem a linha-alvo nao afetam a skin ativa; registrar e seguir.
            print(f'  aviso: {backup.relative_to(root)}: {exc}', file=sys.stderr)
    return actions


def build_apk(source: Path, target: Path) -> None:
    from pyaxmlparser import APK

    if not APK(str(source)).package == 'org.xbmc.kodi':
        raise SystemExit('APK inesperado: pacote diferente de org.xbmc.kodi')
    with zipfile.ZipFile(source) as src:
        names = {i.filename for i in src.infolist()}
        if 'assets/system/settings/settings.xml' not in names:
            raise SystemExit('settings.xml ausente no APK')
    raise SystemExit('modo --apk indisponivel: use o pipeline de diretorio decodificado')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='diretorio decodificado (com assets/ e lib/)')
    parser.add_argument('--check', action='store_true', help='somente validar o estado atual')
    args = parser.parse_args()
    root = args.root
    settings = root / 'assets/system/settings/settings.xml'
    profile = root / 'assets/smarted/profile'
    if not settings.is_file():
        raise SystemExit(f'settings.xml ausente: {settings}')

    data = settings.read_bytes()
    already = b'<default>skin.estilo.personalizado</default>' in data
    if args.check:
        print(f'settings.xml: skin padrao = {"skin.estilo.personalizado" if already else "skin.estuary"}')
        gui = profile / 'userdata/guisettings.xml'
        if gui.is_file():
            active = b'skin.estilo.personalizado' in gui.read_bytes()
            print(f'perfil guisettings: {"skin.estilo.personalizado" if active else "skin.estuary"}')
        return
    if already:
        print('settings.xml ja aponta para skin.estilo.personalizado')
    else:
        activate_settings(settings)
        print('settings.xml: skin padrao alterada para skin.estilo.personalizado')

    for action in activate_profile(profile):
        print(f'perfil atualizado: {action}')

    # Verificacao final: nada deve apontar para a skin antiga.
    leftovers = []
    if b'skin.estuary' in settings.read_bytes():
        leftovers.append('settings.xml')
    gui = profile / 'userdata/guisettings.xml'
    if gui.is_file() and b'skin.estuary' in gui.read_bytes():
        leftovers.append('guisettings.xml')
    if leftovers:
        raise SystemExit('skin.estuary remanescente: ' + ', '.join(leftovers))
    print('OK: Nova TV e a skin padrao e a skin do perfil semeado')


if __name__ == '__main__':
    main()
