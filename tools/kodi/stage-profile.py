#!/usr/bin/env python3
"""Stage the verified SMARTEDTV backup in a new private directory.

This is an offline preparation tool, NOT an in-app restore. Never run it against
an active Kodi profile. No existing directory is merged or overwritten.
"""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from zipfile import ZipFile

EXPECTED_SHA256 = 'e38ee0e23356948a008a895fbefd8b659f62504b72d50712ac91c7305a774cde'
MAX_BYTES = 256 * 1024 * 1024
MAX_FILES = 10000


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            sha.update(block)
    return sha.hexdigest()


def validate(archive):
    """Validate every member before any destination data is written."""
    entries = archive.infolist()
    if len(entries) > MAX_FILES or sum(e.file_size for e in entries) > MAX_BYTES:
        raise ValueError('Backup exceeds size limits')
    names = set()
    files = set()
    directories = set()
    for e in entries:
        name = e.filename
        path = PurePosixPath(name)
        if (not name or '\\' in name or '\x00' in name or path.is_absolute()
                or any(part in ('.', '..') for part in name.split('/'))
                or stat.S_ISLNK(e.external_attr >> 16)):
            raise ValueError('Unsafe archive path')
        # The root directory itself is the only permitted shorter path.
        if path.parts[:2] != ('files', '.kodi') and name != 'files/':
            raise ValueError('Unexpected archive path')
        if len(path.parts) <= 2 and not e.is_dir():
            raise ValueError('Expected a directory at the archive root')
        if name in names:
            raise ValueError('Duplicate archive entry')
        names.add(name)
        key = str(path).casefold()
        if e.is_dir():
            if key in files:
                raise ValueError('File/directory conflict')
            directories.add(key)
        else:
            if key in files or key in directories:
                raise ValueError('File/directory conflict')
            files.add(key)
    for name in files:
        for ancestor in PurePosixPath(name).parents:
            if str(ancestor) in files:
                raise ValueError('File used as a directory')
    return entries


def stage(backup, destination, expected_sha=EXPECTED_SHA256):
    backup, destination = Path(backup), Path(destination)
    if digest(backup) != expected_sha:
        raise ValueError('Backup SHA-256 does not match')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination already exists; refusing to overwrite')
    parent = destination.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError('Destination parent is not a directory')
    # Private temporary directory, on the same filesystem as the destination.
    temp = Path(tempfile.mkdtemp(prefix='.smarted-stage-', dir=parent))
    try:
        with ZipFile(backup) as archive:
            entries = validate(archive)
            for entry in entries:
                rel = PurePosixPath(entry.filename).parts[2:]
                if not rel:
                    continue
                target = temp.joinpath(*rel)
                if entry.is_dir():
                    target.mkdir(mode=0o700, parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    with archive.open(entry) as src, target.open('xb') as dst:
                        os.chmod(target, 0o600)
                        shutil.copyfileobj(src, dst, 1024 * 1024)
        # mkdir is atomic and refuses an existing destination, including symlinks.
        # Transfer only into the newly created, private directory.
        destination.mkdir(mode=0o700)
        try:
            for child in temp.iterdir():
                child.rename(destination / child.name)
        except BaseException:
            shutil.rmtree(destination)
            raise
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup', type=Path)
    parser.add_argument('destination', type=Path, help='new private directory (must not exist)')
    args = parser.parse_args()
    stage(args.backup, args.destination)
    print('Backup verificado e preparado em diretório privado. Nenhum perfil ativo foi alterado.')


if __name__ == '__main__':
    main()
