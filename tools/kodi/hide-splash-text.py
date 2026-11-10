#!/usr/bin/env python3
"""Hide Kodi's status TextView without removing the control Kodi writes to."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

ANDROID = '{http://schemas.android.com/apk/res/android}'


def hide(layout):
    text = layout.read_text(encoding='utf-8')
    root = ET.fromstring(text)
    views = [v for v in root.iter('TextView') if v.get(ANDROID + 'id') == '@id/textView1']
    if len(views) != 1 or views[0].get(ANDROID + 'visibility') not in (None, 'gone'):
        raise ValueError('Unexpected splash status TextView')
    old = 'android:id="@id/textView1"'
    if text.count(old) != 1:
        raise ValueError('Unexpected splash layout')
    if views[0].get(ANDROID + 'visibility') is None:
        text = text.replace(old, old + ' android:visibility="gone"', 1)
        ET.fromstring(text)
        layout.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path)
    args = parser.parse_args()
    hide(args.decoded / 'res/layout/activity_splash.xml')
