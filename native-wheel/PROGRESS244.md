> Superseded by build 245. The owner reported all three repairs still failed on their device. In particular, the build-244 live-coordinate and int16-angle assumptions below were wrong; see PROGRESS245.md and the native-walking regression test.

# iOS 2.4.1 build 244

Three requested repairs are included:

- Room sprites are selected at the actual native sprite draw call. Rooms 8/9 use UFO (16), Super Boss room 16 uses Trex (15), and linked rooms use their current map's boss. The previous twelve patches were attached to player-slot X-coordinate calculations; those instructions are restored.
- The native base-screen small command row is suppressed only while the wheel overlay is visible. Its large UIKit commands remain, and GameCanvas continues to draw/handle the native keypad.
- UFO firing validates the live coordinates at 0x80/0x84. The old 0x114/0x118 fields are the separate shot-origin snapshot. Before invoking the original firing method, the bridge snapshots the live origin and writes the native short angle without overwriting its neighbouring field.

The old library reproduces the missing-shot regression when spawn/shot-origin and live coordinates differ. The first repaired candidate exposed a second regression: its native command 22 still contained the old origin. Both regressions are covered by the shipped tests.

Apple build: Actions run 41170599642, branch commit 4071fc510742d0a089a6a185df67da7f85620674, PR merge 35df6a9509a4e02b8665ccad067cd12756dfe8e0. The library was built with Xcode 16.4; strict Apple codesign and re-sign checks passed. Exact hashes and preservation results are in validation-ui244.json.

Passed offline checks: 480 actual room-sprite calls, 18 footer entry cases, 156 UFO turn/ticket cases, 12 complete Apple-bridge -> original player -> original Service command-22 packet cases, 624 grid input/layout cases, and 444 Notes bridge assertions. The packet tests run the actual native firing and packet-building methods and mock Java/OS primitives and final transport. Existing login, settings, menu and manual-captcha checks were retained.

Compared with build 243, only the main executable, AGWheel.dylib and Info.plist change; all 522 other IPA entries are byte-identical. The login marker remains 2.4.1-HG78-IPA. The user must re-sign the IPA using their installation certificate. No physical iPhone or live VPS test has been performed.

The guarded packager accepts untouched delivered builds 243 and 244 in addition to its prior baselines. Re-signed main binaries are deliberately rejected. Java-generated captcha answers are offline test fixtures and are never embedded in the IPA.
