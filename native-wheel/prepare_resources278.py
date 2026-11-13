"""Extract the exact 278 boss art from the owner's checksum-guarded APK.

The host C helper only decodes the existing resource bundle. It is never
embedded in the IPA. No image is redrawn or resized.
"""
import argparse
import ctypes
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def prepare(apk, server, output):
    root = Path(__file__).parent
    manifest = json.loads((root / 'boss-art-278.json').read_text())
    if output.exists():
        raise ValueError('Choose a new resource directory')
    for path, expected in [(apk, manifest['apkSha256']), (server, manifest['serverSha256'])]:
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Unexpected reference input: {path.name}')
    with ZipFile(apk) as archive:
        bundle = archive.read('assets/res/hoanggia/b95f21.dat')
    if sha256(bundle).hexdigest() != manifest['bundleSha256']:
        raise ValueError('Unexpected APK resource bundle')
    magic, count = struct.unpack_from('>IH', bundle)
    if magic != 1830074818 or count != manifest['entryCount']:
        raise ValueError('Unexpected resource index')
    records = {}
    for i in range(count):
        key, offset, length, nonce, checksum = struct.unpack_from('>QIIQI', bundle, 6 + i * 28)
        if key in records or offset < 6 + 28 * count or offset + length > len(bundle):
            raise ValueError('Invalid resource entry')
        records[key] = offset, length, nonce, checksum
    resources = {}
    with TemporaryDirectory() as temp, ZipFile(server) as reference:
        library = Path(temp) / 'resource-unpack.so'
        subprocess.run(['cc', '-shared', '-fPIC', '-O2', str(root / 'resource-unpack.c'), '-o', str(library)], check=True)
        decoder = ctypes.CDLL(str(library)).decode
        decoder.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint64]
        decoder.restype = None
        for name, expected in manifest['bossEntries'].items():
            key = (-6699764405322699424) & 0xffffffffffffffff
            for c in '/' + name:
                key = ((key ^ ord(c)) * 1099511628211) & 0xffffffffffffffff
            offset, length, nonce, checksum = records[key]
            data = ctypes.create_string_buffer(bundle[offset:offset + length], length)
            decoder(data, length, nonce)
            decoded = data.raw
            actual = 2166136261
            for b in decoded:
                actual = ((actual ^ b) * 16777619) & 0xffffffff
            if actual != checksum or sha256(decoded).hexdigest() != expected:
                raise ValueError(f'Invalid decoded APK resource: {name}')
            if (name.endswith('.map') or '/tile-' in name) and decoded != reference.read(name):
                raise ValueError(f'APK and server terrain differ: {name}')
            resources[name] = decoded
    for name, data in resources.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f'PASS {len(resources)} original APK boss resources; checksums and server terrain match')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('server', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(args.apk, args.server, args.output)
