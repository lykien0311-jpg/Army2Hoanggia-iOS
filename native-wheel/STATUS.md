# IPA 2.4.1 / Notes78 — 30/10/2026

Built from the user-supplied original IPA, retaining the video-28835 responsive wheel in lobby/V9 and all Notes77 functionality. Configuration OK saves and returns through the original lobby callback without waiting for a server acknowledgement.

The native version and Info.plist now read 2.4.1 (build242). All six native login services send 2.4.1-HG78-IPA. Companion Notes78 server admits that exact marker alongside JAR/APK2.4.1 and rejects old versions before account access. Only one runtime server class changes; APK/JAR/web/lib/rollback are unchanged.

GitHub Apple build: SUCCESS, run41003030845, headac99b72ec367a553b754b6a1503bd23157be4291. The artifact records the PR merge build commit94bc66cbff2ac58e8caaa39ecdeba6896882748a. Xcode16.4, Apple clang17, device SDK18.5/iOS12 minimum. Apple codesign strict verification and re-sign verification passed. Simulator loaded a signed embedded dylib compiled from the same sources and passed six viewport/input checks.

Offline checks passed: 25 actual native login/version cases; 100 shipped server login assertions with loopback notice framing; 12 actual native settings→lobby screen transitions; 444 compiled Apple Notes bridge assertions; 48 compiled wheel +36 room +36 movement checks; 1507 Notes protocol assertions using30 fresh Notes78 server fixtures. Full hook/menu/room regressions passed. Packaging reproduces the final unsigned IPA byte for byte. See validation.json for hashes and limits.

IPA SHA256: fc465ce2855da8d4430acaaf6fccdd67b9b4491058bfd196d5928c361a3492ba
Companion Notes78 ZIP SHA256: 40440fbcc30fe1032474b8cc7227e3066ffd0fe63d669f7eed603f54a72bc200
Apple dylib SHA256: b34bc3d5851fc84782f04f3de1d6b820b2063f6d0ae33eafb0cb34f2f5f01d9c

Not tested on a physical iPhone or production VPS account. The owner must re-sign the IPA app and nested libraries and install the companion server.jar. This is not a verified claim that every prior launch crash is fixed. No VPS deployment or account login was performed.

Repository: lykien0311-jpg/Army2Hoanggia-iOS
Branch: codex/army-ios-build
Workflow: .github/workflows/native-wheel.yml
