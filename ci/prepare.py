#!/usr/bin/env python3
"""Reconstruct the approved project, with integrity checks before building."""
import argparse
import hashlib
import io
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / 'project-src'
ARCHIVE_SHA256 = '51459cd72ca79dbdfd8ccb77745fd7bf47d3f6766f2f6af54b847aa351a0e9d6'
FONT_SHA256 = 'f45b6b4a68b6bf3d792fcbb6d7de24dc701a0f89c5900a21ef3aaece993b839a'
FONT_URL = 'https://raw.githubusercontent.com/ccbkv/J2MEEmulator-iOS/8afc8d808ca22160139333d1d58138c7dca91169/J2MEEmulator/Resources/sound_fonts/gs_instruments.sf2'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--with-font', action='store_true')
    args = parser.parse_args()
    parts = sorted((ROOT / 'payload').glob('source.zip.part*'))
    if [p.name for p in parts] != [f'source.zip.part{i:03}' for i in range(26)]:
        raise SystemExit('Missing or unexpected archive parts')
    data = b''.join(p.read_bytes() for p in parts)
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise SystemExit('Source archive SHA256 mismatch')
    PROJECT.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if not (PROJECT / name).resolve().is_relative_to(PROJECT.resolve()):
                raise SystemExit('Unsafe archive path')
        z.extractall(PROJECT)
    overrides = ROOT / 'overrides'
    if overrides.exists():
        shutil.copytree(overrides, PROJECT, dirs_exist_ok=True)
    if args.with_font:
        target = PROJECT / 'J2MEEmulator/Resources/sound_fonts/gs_instruments.sf2'
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(FONT_URL, timeout=120) as response:
            font = response.read()
        if hashlib.sha256(font).hexdigest() != FONT_SHA256:
            raise SystemExit('Upstream soundfont SHA256 mismatch')
        target.write_bytes(font)
    print('Project reconstructed; SHA256 verified.')

if __name__ == '__main__':
    main()
