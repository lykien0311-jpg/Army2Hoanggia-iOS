# Army2 Hoàng Gia — iOS 2.4.1, Notes78 and APK-style wheel

This revision applies the user's video 28835 wheel layout to the supplied native IPA, in both the lobby and V9. The panel uses the original bitmap fonts, a screen-relative scale, a yellow probability bar, previous winner details and the matching inline amount-entry controls. Compact screens scroll the panel while the controls remain visible. Keyboard layout is checked in portrait and landscape.

The Notes77 client bridge supports the supplied -122/-123 protocols, manual captcha controls, the invitation-blocking configuration row and the full inbox reader. Configuration OK queues the setting save and unconditionally executes the original native return-to-lobby callback, including when a server acknowledgement is still pending. The bridge does not wait for an acknowledgement before leaving settings.

## Apple build

Run `bash native-wheel/build.sh` on macOS with Xcode. The `native-wheel.yml` GitHub Actions workflow uses the existing macos-15 runner. It builds the iPhone arm64/iOS 12 dylib using Apple clang/ld, signs and verifies it with Apple codesign, then signs it a second time for verification. No Linux-built iOS dylib is used.

A separate iOS Simulator app loads a separately signed embedded dylib compiled from the same sources. It verifies six screen layouts, amount-entry/cancel and keyboard geometry, and exports screenshots. Fixture functions are excluded from the device dylib. These checks do not establish that the final re-signed IPA launches on a physical iPhone.

## Packaging

Use the untouched attached baseline IPA (SHA256 `b5fd4e77c62bb6751f53142711588ba0646dfe73e519bf2d504d4f9010ecc7cd`) and the exact `AGWheel.dylib` downloaded from the successful GitHub run. `package_from_baseline.py` recovers the prior native patch inputs with checksum guards, installs the updated static hooks and copies the dylib without modifying its Apple signature. Info.plist advances from 2.4.0/build241 to 2.4.1/build242. All other archive entries are preserved byte for byte. The delivered unsigned IPA is also a supported recovery input; a re-signed IPA is not. The user must re-sign the main app and its nested libraries with their installation certificate.

Original room/clan/DataFix repairs, V9 placement, Quay số/Xem giờ, and independent walking remain in the native patch. Source checks and reports describe offline checks explicitly; no live server, real wager or physical-device launch is performed by this build.

## Local native checks

The main executable is recovered from the guarded user-supplied IPA; it is not compiled from another game project. Tests execute the installed ARM64 callbacks and confirm that OK actually changes `GameCanvas.cScreen` to the lobby on all six variants. Compiled-dylib checks must run on the newly downloaded Apple build, not an earlier dylib. Server-generated Notes77 raster fixtures are local test data and are never embedded in the app.

## Notes78 version admission

The native login service in each of six variants sends `2.4.1-HG78-IPA` in the third UTF field of command1. User/password, the `z1` platform tail and registration remain unchanged. The shared native version label is 2.4.1. Only the supplied Notes78 server's `ClientBuild78.class` changes to admit this exact IPA marker in addition to the existing JAR/APK markers; old/plain-number markers still receive the existing Vietnamese update notice before account access. Installing the IPA alone cannot activate this gate on an older server. Install the companion server.jar to admit this IPA on Notes78.

`test_login78.py` executes the original and patched ARM64 login methods with mocked JVM string/transport primitives. It exports twelve packet fixtures. `update_server78.py` compiles the minimal server change and executes the shipped ClientEntry against those fixtures and old/new markers. Loopback checks reach the original validation/loading responses; they do not authenticate a real VPS account. Version markers identify releases and are not cryptographic anti-tamper protection.

Rebuild after downloading the Apple artifact into native-wheel/build:

```sh
python3 native-wheel/package_from_baseline.py --ipa /path/to/original.ipa --output Army2Hoanggia-2.4.1-Notes78-GitHub.ipa
python3 native-wheel/test_login78.py
python3 native-wheel/update_server78.py --notes78-zip /path/to/Army2-QuanTri-Game-Notes78.zip --native-packets native-wheel/build/login78-packets --output Army2-QuanTri-Game-Notes78-IPA241.zip
python3 native-wheel/generate_notes_fixtures.py --notes77-zip /path/to/Army2-QuanTri-Game-Notes78.zip
cc -shared -fPIC -O1 native-wheel/NotesProtocol.c -lm -o native-wheel/build/libnotesprotocol.so
python3 native-wheel/test_notes_protocol.py
```

Native tests require Python3, lief, keystone-engine and unicorn. Fixture/server compilation requires JDK17; the generator also accepts the checksum-guarded Notes77 input. Server-generated captcha fixtures stay offline and are not embedded in the IPA. Source and packaging scripts remain on the existing GitHub branch; the original app binary must be supplied by the owner.
