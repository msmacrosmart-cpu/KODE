#!/usr/bin/env python3
"""Restore all unchanged classes*.dex after apktool rebuild, or fail closed.

Run before alignment/signing. The trusted reference must be the precise APK
whose code the rebuild is supposed to preserve; never use this for new code.
"""
import argparse
import re
import zipfile
from pathlib import Path

DEX = re.compile(r'^classes(?:([2-9]|[1-9][0-9]+))?\.dex$')


def dexes(archive):
    result = {}
    for info in archive.infolist():
        match = DEX.fullmatch(info.filename)
        if not match:
            continue
        number = int(match.group(1) or '1')
        if number in result:
            raise ValueError('Duplicate DEX entry')
        result[number] = info
    if not result or sorted(result) != list(range(1, max(result) + 1)):
        raise ValueError('DEX entries are missing or non-contiguous')
    return result


def restore(reference, rebuilt):
    if Path(reference).resolve() == Path(rebuilt).resolve():
        raise ValueError('Reference and rebuilt APK must differ')
    with zipfile.ZipFile(reference) as src, zipfile.ZipFile(rebuilt, 'a') as dst:
        expected, present = dexes(src), dexes(dst)
        if not set(present).issubset(expected):
            raise ValueError('Unexpected DEX in rebuilt APK')
        for number, info in present.items():
            if src.read(expected[number]) != dst.read(info):
                raise ValueError('Rebuilt DEX differs from reference')
        for number in sorted(set(expected) - set(present)):
            info = expected[number]
            dst.writestr(info.filename, src.read(info), compress_type=info.compress_type)
        assert sorted(dexes(dst)) == sorted(expected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('rebuilt', type=Path)
    args = parser.parse_args()
    restore(args.reference, args.rebuilt)
    print('All reference DEX files are present and identical; align and sign next.')
