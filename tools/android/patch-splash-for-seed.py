#!/usr/bin/env python3
"""Patch an apktool-decoded Splash for an isolated bootstrap experiment.

This is not a release builder. The caller must compile/add the bootstrap DEX
and synthetic backup separately and sign only with a throwaway emulator key.
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path)
    args = parser.parse_args()
    splash = args.decoded / 'smali/org/xbmc/kodi/Splash.smali'
    source = splash.read_text(encoding='utf-8')
    old = '.method protected startXBMC()V\n'
    if source.count(old) != 1 or 'startXBMCOriginal' in source:
        raise SystemExit('Unexpected Splash layout; refusing to patch')
    replacement = '''.method protected startXBMC()V
    .locals 0
    invoke-static {p0}, Lorg/smartedtv/bootstrap/ProfileBootstrap;->start(Landroid/app/Activity;)V
    return-void
.end method

.method protected startXBMCOriginal()V
'''
    splash.write_text(source.replace(old, replacement, 1), encoding='utf-8')


if __name__ == '__main__':
    main()
