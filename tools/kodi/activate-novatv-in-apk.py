#!/usr/bin/env python3
"""Ativa a Nova TV em um APK unsigned, sem tocar no dex/lib.

Aplica no nivel ZIP:
1. assets/smarted/profile/userdata/guisettings.xml -> skin.estilo.personalizado
2. os backups do wizard em assets/smarted/profile/My_Builds/*.zip e
   assets/smarted/profile/SaveData.zip -> guisettings internos com skin.estilo.personalizado

Reaproveita activate_guisettings() e rewrite_zip() do activate-novatv.py.
Os zips internos sao reescritos em memoria (BytesIO); o APK final preserva
ordem e compressao dos demais entries.

Uso:
    python3 tools/kodi/activate-novatv-in-apk.py ENTRADA.apk SAIDA.apk
"""
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'activate_novatv', ROOT / 'tools/kodi/activate-novatv.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

activate_guisettings = MOD.activate_guisettings

# Entradas do APK que sao zips internos e precisam de reescreva.
BACKUP_NAMES = (
    'assets/smarted/profile/My_Builds/BACKUP%2BSMARTED_guisettings.zip',
    'assets/smarted/profile/My_Builds/BACKUP+SMARTED.zip',
    'assets/smarted/profile/SaveData.zip',
)


def rewrite_zip_bytes(data: bytes, transform) -> tuple[bytes, bool]:
    """Reescreve um ZIP em memoria; transform(name, bytes)->bytes|None."""
    with zipfile.ZipFile(io.BytesIO(data)) as src:
        entries = [(item, src.read(item.filename)) for item in src.infolist()]
    changed = False
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as dst:
        for item, inner in entries:
            new = transform(item.filename, inner)
            if new is not None and new != inner:
                changed = True
            dst.writestr(item, inner if new is None else new)
    return buffer.getvalue(), changed


def backup_transform(name: str, data: bytes) -> bytes | None:
    """Transform aplicado aos zips internos dos backups."""
    if not name.endswith('guisettings.xml'):
        return None
    updated, _ = activate_guisettings(data)
    return updated


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('Usage: activate-novatv-in-apk.py ENTRADA.apk SAIDA.apk')
    inp, out = Path(sys.argv[1]), Path(sys.argv[2])
    if inp.resolve() == out.resolve():
        raise SystemExit('Input and output must differ')
    if out.exists():
        raise SystemExit('Output already exists')

    with zipfile.ZipFile(inp) as src:
        infos = src.infolist()
        names = [i.filename for i in infos if not i.is_dir()]
        if len(names) != len(set(names)):
            raise SystemExit('Duplicate ZIP members')

        # Le tudo em memoria (base ~238 MB; este host tem memoria suficiente).
        contents = {item.filename: src.read(item.filename) for item in infos}

    # --- Ativacao ---
    actions = []

    # 1. Perfil guisettings.xml
    gui = 'assets/smarted/profile/userdata/guisettings.xml'
    if gui not in contents:
        raise SystemExit(f'Perfil guisettings ausente: {gui}')
    data, changed = activate_guisettings(contents[gui])
    if changed:
        contents[gui] = data
        actions.append(gui)
    else:
        print(f'  {gui}: ja skin.estilo.personalizado (sem alteracao)')

    # 2. Backups do wizard (zips internos)
    for name in BACKUP_NAMES:
        if name not in contents:
            print(f'  {name}: ausente (ignorado)', file=sys.stderr)
            continue
        try:
            new_data, changed = rewrite_zip_bytes(contents[name], backup_transform)
        except SystemExit as exc:
            print(f'  {name}: {exc}', file=sys.stderr)
            continue
        if changed:
            contents[name] = new_data
            actions.append(name)
        else:
            print(f'  {name}: ja skin.estilo.personalizado (sem alteracao)')

    # Verificacao final: nenhum guisettings.xml com skin.estuary.
    # (O backup tambem contem skin.py/skin.pyc do wizard com a string
    # 'skin.estuary' no CODICE; isso nao afeta a skin ativa, apenas
    # os guisettings.xml restaurados, e por isso a checagem e restrita.)
    def iter_guisettings(data: bytes, prefix: str = ''):
        with zipfile.ZipFile(io.BytesIO(data)) as zi:
            for n in zi.namelist():
                if n.endswith('guisettings.xml'):
                    yield prefix + n, zi.read(n)

    for name in [gui]:
        if b'skin.estuary' in contents[name]:
            raise SystemExit(f'skin.estuary remanescente: {name}')
    for bname in BACKUP_NAMES:
        if bname not in contents:
            continue
        for gname, gdata in iter_guisettings(contents[bname], prefix=bname + ':'):
            if b'skin.estuary' in gdata:
                raise SystemExit(f'skin.estuary remanescente: {gname}')

    # --- Reescreve o APK preservando ordem e compressao ---
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', allowZip64=True) as dst:
        for item in infos:
            if item.is_dir():
                continue
            data = contents[item.filename]
            dst.writestr(item, data)

    print('Ações:')
    for a in actions:
        print(f'  - {a}')
    if not actions:
        print('  (nenhuma alteracao necessária)')
    print(f'Saída: {out} ({out.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
