# iOS build 278 QA package

Completes the four requested menu, aura, market-chest and room-18/19 changes already committed in `44cd85deb66b48a16d85c430ae30523c7f16497e`.

The Apple framework job succeeded, but Actions artifact storage was full. Its signed delta was retained as private Git blobs. `restore_framework278.py` retrieves those exact bytes from the private `qa/ios-278-artifacts` branch, falling back to the original Git blobs with Git-ID checks, and verifies the archived SHA256. The packager verifies all 137 framework members against the Apple manifest. It preserves the device binary and its Apple-generated signature bytes. No Linux-built iOS library is used.

The finished IPA, framework checkpoint, checksums, notes and UI screenshots are retained on `qa/ios-278-artifacts`. This uses the same private repository audience. Release-asset upload returned HTTP 401 at `uploads.github.com`, so no release-upload link is claimed.

The original packager required an unpublished build-277 IPA. The new `--from-269` path uses the existing private `qa-input-269` release. It applies the guarded 275 and 277 native patches, verifies the resulting executable against the original 277 SHA256, then applies the existing 278 scene patch. The original 277 packaging path and its input checks remain available.

`prepare_resources278.py` extracts 46 original resources from the checksum-guarded user APK without redrawing/resizing them. The host C decoder never enters the IPA. Every decoded checksum and SHA256 is verified, and map/tile bytes are compared with the uploaded server JAR. The four waiting-room resources match the hashes already required by `package_278.py`.

## Reproduce

From this repository checkout, with `gh` authorized to the private repository and a host C compiler:

```sh
mkdir -p work278
gh release download qa-input-269 --repo lykien0311-jpg/Army2Hoanggia-iOS --pattern Army2HoangGiaTF.ipa --dir work278
python3 native-wheel/restore_framework278.py work278/framework-delta.zip
python3 native-wheel/prepare_resources278.py '/path/to/Army2HoangGia-2.4.2-QA2 (1).apk' /path/to/server-B275-BossNhanh-PvP05s.jar work278/boss-art
python3 native-wheel/package_278.py work278/Army2HoangGiaTF.ipa work278/framework-delta.zip work278/boss-art work278/Army2HoangGia-2.4.1-B278-QA.ipa --from-269
python3 -m venv work278/venv
work278/venv/bin/pip install -r native-wheel/requirements-qa278.txt
work278/venv/bin/python native-wheel/verify_build278.py work278/Army2HoangGia-2.4.1-B278-QA.ipa work278/Army2HoangGiaTF.ipa
work278/venv/bin/python native-wheel/test_build278_native.py work278/Army2HoangGia-2.4.1-B278-QA.ipa
```

The package SHA256 is `01d8669bcae44d2438963eb96f8bb792126786395dcbd18588328964a520bbc1` (27,465,109 bytes). The main executable is `bd3e51cfd4742046f868f712653f25ed29f62481c1f313be9c5f4eb4c504c1bf`. The bundle remains `vn.army2hoanggia.game`, version 2.4.1/build 278, retaining the existing server version marker. No server JAR is modified.

The browser check is `node native-wheel/test_lobby.js` with Playwright installed. Set `ARMY2_CHROMIUM` to an installed Chromium when necessary. If browser policy blocks file URLs, serve `native-wheel/viewer` over loopback HTTP and set `ARMY2_VIEWER_URL` to its `lobby.html` URL.

## Validation and limits

- Packaged ARM64 and compiled Apple scene logic: 318 native menu cases, 96 per-player aura cases, 24 preview/name-array updates, 24 boss draw cases. Missing scene-symbol fallback and native register/stack preservation are covered.
- Existing browser UI checks pass, including confirmation/cancel, post-match return, inventory sprites/+16 metadata, grid wrapping, quantities and compact layout.
- Existing C aura-state and boss-map tests pass.
- Packaging audits all 137 signed framework members, 46 APK resources and 522 preserved baseline archive entries; verifies unchanged Mach-O symbols, imports, rebases, function starts, original section mappings and non-overlapping segments without writable executable mappings.
- Independently re-extracted resources produce a second byte-identical IPA. Wrong native and retained-framework inputs are rejected.

The main app must be re-signed together with its nested code for installation. No physical iPhone launch, real account login, production VPS operation or live battle was performed. The ARM64 checks use controlled UIKit/JVM/OS/final-draw boundaries and cached image objects. They verify the packaged native paths but do not establish full device rendering or signing compatibility.
