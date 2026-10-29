# Army2 Hoàng Gia — APK-style wheel and Notes77 configuration

This revision applies the user's video 28835 wheel layout to the supplied native IPA, in both the lobby and V9. The panel uses the original bitmap fonts, a screen-relative scale, a yellow probability bar, previous winner details and the matching inline amount-entry controls. Compact screens scroll the panel while the controls remain visible. Keyboard layout is checked in portrait and landscape.

The Notes77 client bridge supports the supplied -122/-123 protocols, manual captcha controls, the invitation-blocking configuration row and the full inbox reader. Configuration OK queues the setting save and unconditionally executes the original native return-to-lobby callback, including when a server acknowledgement is still pending. The bridge does not wait for an acknowledgement before leaving settings.

## Apple build

Run `bash native-wheel/build.sh` on macOS with Xcode. The `native-wheel.yml` GitHub Actions workflow uses the existing macos-15 runner. It builds the iPhone arm64/iOS 12 dylib using Apple clang/ld, signs and verifies it with Apple codesign, then signs it a second time for verification. No Linux-built iOS dylib is used.

A separate iOS Simulator app loads a separately signed embedded dylib compiled from the same sources. It verifies six screen layouts, amount-entry/cancel and keyboard geometry, and exports screenshots. Fixture functions are excluded from the device dylib. These checks do not establish that the final re-signed IPA launches on a physical iPhone.

## Packaging

Use the untouched attached baseline IPA (SHA256 `b5fd4e77c62bb6751f53142711588ba0646dfe73e519bf2d504d4f9010ecc7cd`) and the exact `AGWheel.dylib` downloaded from the successful GitHub run. `package_from_baseline.py` recovers the prior native patch inputs with checksum guards, installs the updated static hooks and copies the dylib without modifying its Apple signature. All other archive entries are preserved byte for byte. The user must re-sign the main app and its nested libraries with their installation certificate.

Original room/clan/DataFix repairs, V9 placement, Quay số/Xem giờ, and independent walking remain in the native patch. Source checks and reports describe offline checks explicitly; no live server, real wager or physical-device launch is performed by this build.

## Local native checks

The main executable is recovered from the guarded user-supplied IPA; it is not compiled from another game project. Tests execute the installed ARM64 callbacks and confirm that OK actually changes `GameCanvas.cScreen` to the lobby on all six variants. Compiled-dylib checks must run on the newly downloaded Apple build, not an earlier dylib. Server-generated Notes77 raster fixtures are local test data and are never embedded in the app.
