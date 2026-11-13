"""Download the private retained Apple build using the owner's gh connection."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess


def restore(output):
    if output.exists():
        raise ValueError('Choose a new framework archive path')
    record = json.loads(Path(__file__).with_name('apple-build278-input.json').read_text())
    def chunk(key):
        value = json.loads(subprocess.check_output(['gh', 'api', f"repos/{record['repository']}/git/blobs/{key}"]))
        if value['sha'] != key or value['encoding'] != 'base64':
            raise ValueError('Unexpected retained blob')
        stored = base64.b64decode(value['content'])
        if sha1(b'blob ' + str(len(stored)).encode() + b'\0' + stored).hexdigest() != key:
            raise ValueError('Retained blob checksum differs')
        return base64.b64decode(stored, validate=True)
    # A tracked artifact keeps the checkpoint reachable if unreferenced Git
    # blobs are collected. Fall back to the original retained build.
    endpoint = f"repos/{record['repository']}/contents/{record['artifactPath']}?ref={record['artifactRef']}"
    attempt = subprocess.run(['gh', 'api', endpoint], capture_output=True)
    if attempt.returncode == 0:
        value = json.loads(attempt.stdout)
        if value['encoding'] != 'base64':
            raise ValueError('Unexpected tracked artifact encoding')
        data = base64.b64decode(value['content'])
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            data = b''.join(pool.map(chunk, record['chunks']))
    if sha256(data).hexdigest() != record['sha256']:
        raise ValueError('Retained Apple build checksum differs')
    with output.open('xb') as target:
        target.write(data)
    print('PASS retained Apple build', record['sha256'], output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    restore(parser.parse_args().output)
