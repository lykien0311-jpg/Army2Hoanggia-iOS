#!/usr/bin/env python3
"""Materialize pinned upstream sources, then apply the private Army overlay."""
from pathlib import Path
import hashlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'build/source'
UPSTREAM = 'https://github.com/ccbkv/J2MEEmulator-iOS.git'
REVISION = '8afc8d808ca22160139333d1d58138c7dca91169'
CLIENT_SHA256 = '8e31f6bc4a41fe0ded091cfbab28239ab91b5dd001a060dc83db4aacf429ca82'
if SOURCE.exists():
    raise SystemExit('build/source already exists; use a clean build directory.')
SOURCE.mkdir(parents=True)
subprocess.run(['git', 'init', '-q', str(SOURCE)], check=True)
subprocess.run(['git', '-C', str(SOURCE), 'fetch', '--depth', '1', UPSTREAM, REVISION], check=True)
subprocess.run(['git', '-C', str(SOURCE), 'checkout', '-q', '--detach', 'FETCH_HEAD'], check=True)
actual = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
assert actual == REVISION, actual
for file in sorted((ROOT / 'overlay').rglob('*')):
    if file.is_file():
        dest = SOURCE / file.relative_to(ROOT / 'overlay')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, dest)
client = SOURCE / 'J2MEEmulator/Resources/jars/army2hoanggia.jar'
assert hashlib.sha256(client.read_bytes()).hexdigest() == CLIENT_SHA256
print('Prepared:', SOURCE)
print('Verified upstream revision and unchanged Army client.')
