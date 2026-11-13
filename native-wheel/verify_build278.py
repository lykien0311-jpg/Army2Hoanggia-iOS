"""Audit the delivered IPA against its unchanged baseline and Apple build."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import plistlib
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import lief

from package_269 import BASE_SHA
from package_277 import APP, EMBEDDED_FW, INFO, NATIVE
from package_278 import FW

ROOT = Path(__file__).parent
NATIVE_SHA = 'bd3e51cfd4742046f868f712653f25ed29f62481c1f313be9c5f4eb4c504c1bf'


def verify(ipa, baseline):
    if sha256(baseline.read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError('Unexpected baseline IPA')
    framework = json.loads((ROOT / 'framework-278-sha256.json').read_text())
    art = json.loads((ROOT / 'boss-art-278.json').read_text())['bossEntries']
    with ZipFile(ipa) as current, ZipFile(baseline) as old:
        assert current.testzip() is None
        expected = {n for n in old.namelist() if not n.startswith(EMBEDDED_FW)}
        expected.update(APP + 'Frameworks/' + n for n in framework)
        expected.update(APP + 'BossMaps/' + n for n in art)
        assert set(current.namelist()) == expected and len(current.namelist()) == len(expected)
        before, info = plistlib.loads(old.read(INFO)), plistlib.loads(current.read(INFO))
        before['CFBundleVersion'] = '278'
        assert info == before
        assert info['CFBundleIdentifier'] == 'vn.army2hoanggia.game'
        native = current.read(NATIVE)
        assert sha256(native).hexdigest() == NATIVE_SHA
        preserved = 0
        for name in old.namelist():
            if name in (INFO, NATIVE) or name.startswith(EMBEDDED_FW):
                continue
            assert current.read(name) == old.read(name), name
            preserved += 1
        for name, expected_hash in framework.items():
            assert sha256(current.read(APP + 'Frameworks/' + name)).hexdigest() == expected_hash, name
        for name, expected_hash in art.items():
            assert sha256(current.read(APP + 'BossMaps/' + name)).hexdigest() == expected_hash, name
        signature = plistlib.loads(current.read(EMBEDDED_FW + '_CodeSignature/CodeResources'))
        for name in framework:
            if name.startswith(FW + 'viewer/'):
                relative = name.removeprefix(FW)
                assert sha256(current.read(APP + 'Frameworks/' + name)).digest() == signature['files2'][relative]['hash2']
        with TemporaryDirectory() as temp:
            paths = [Path(temp) / n for n in ('current', 'baseline')]
            paths[0].write_bytes(native)
            paths[1].write_bytes(old.read(NATIVE))
            owners = [lief.MachO.parse(str(p)) for p in paths]
            final, original = (o.at(0) for o in owners)
            assert [(s.name, s.value) for s in final.symbols] == [(s.name, s.value) for s in original.symbols]
            assert list(final.function_starts.functions) == list(original.function_starts.functions)
            def bindings(binary):
                return [(b.address, b.symbol.name if b.has_symbol else None, b.library_ordinal, b.addend)
                        for b in binary.dyld_info.bindings]
            assert bindings(final) == bindings(original)
            assert [(r.address, r.size, int(r.type)) for r in final.relocations] == [(r.address, r.size, int(r.type)) for r in original.relocations]
            assert [x.name for x in final.libraries] == [x.name for x in original.libraries]
            assert [(s.name, s.virtual_address, s.offset) for s in final.sections if s.segment_name in ('__TEXT', '__DATA')] == [
                (s.name, s.virtual_address, s.offset) for s in original.sections if s.segment_name in ('__TEXT', '__DATA')]
            segments = [s for s in final.segments if s.name != '__PAGEZERO']
            assert '__AGSCENE' in [s.name for s in segments]
            for first, second in zip(segments, segments[1:]):
                assert first.virtual_address + first.virtual_size <= second.virtual_address
                assert first.file_offset + first.file_size <= second.file_offset
            assert all(not (int(s.init_protection) & 2 and int(s.init_protection) & 4) for s in segments)
    result = dict(passed=True, file=ipa.name, sha256=sha256(ipa.read_bytes()).hexdigest(),
                  sizeBytes=ipa.stat().st_size, bundleIdentifier=info['CFBundleIdentifier'],
                  version=info['CFBundleShortVersionString'], build=info['CFBundleVersion'],
                  unchangedBaselineEntries=preserved, verifiedAppleFrameworkFiles=len(framework),
                  verifiedAPKResourceFiles=len(art), machoMetadataPreserved=True,
                  appleFrameworkBytesPreserved=True, mainAppRequiresResigning=True,
                  physicalDeviceTested=False, liveServerTested=False)
    print('PASS', json.dumps(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = verify(args.ipa, args.baseline)
    if args.report: args.report.write_text(json.dumps(report, indent=2))
