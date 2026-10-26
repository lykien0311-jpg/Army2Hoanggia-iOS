# Army2Hoanggia — current checkpoint, 27/10/2026 (Asia/Saigon)

User explicitly authorized uploading code to the existing private GitHub repository and continuing native IPA repairs. No approval block remains.

Completed native wheel and room cache repair. Deliverable: deliverables/Army2Hoanggia-V9-Wheel-RoomFix.ipa, 16,519,153 bytes, SHA256 82802ce256e4a96daca59f4c4ffd784e33b28171af2a70a5f1fee5549c8df8c6.

Verified dylib: native-wheel/build/verified-ci/AGWheel.dylib, SHA256 9fac50bbc4da985c12b572d20bf8e2012e401a20cfc152aedadd0046bf621658. Built from 3de2ccf7707e5cf2959e821df80769bd010d02d9, successful Actions run 40419576327 / artifact 12696207572. Earlier first-ci dylib has the pre-fix empty-string room-label bug; do not use it.

Native V9 Xem giờ is replaced by Vòng xoay may mắn across all six variants. -101 receive interception, polls and confirmed bet submissions use the existing game connection on the proper game thread. UIKit stays on the main thread. Old Quay số remains.

Room cache -19 receives actual unsigned ID / MUTF name / marker -1. Names persist before screen construction and replay after the native list builder. Default labels use NULL, not an allocated empty String (native renderer uses reference equality). Header IDs 255 are untouched. Actual native sorting yields video groups 0 / 1 / 2 / 3–16 / 17. All old DataFix/room/clan instruction changes and resources remain except the explicitly reported new hooks. Speed remains capped at10 (already0ms sleep).

Tests: 16 wheel packets +24524 malformed/fuzz cases; 122 hook/guard cases; 18 actual room build/sort runs +24 native paint dispatch cases; C parser 5 valid /319 malformed plus60 reordered/rebuilt layouts; actual compiled dylib48 wheel +36 room/JNI cases, including same-nonce retry, stale ack, connection change, real native Java exception recovery. Simulator screenshots show the wheel and entry dialog. ZIP consistency, library version compatibility and LIEF Mach-O layout checks passed.

Main executable load dependency version is 0.0.0 to match clang's default dylib current version; requiring1.0.0 would cause dyld rejection. Separate RX/RW injected segments keep LINKEDIT last and retain all old bindings/rebases/VM addresses.

NOT performed: physical-device install, live login/server interaction, real bet. Final IPA needs main and nested dylib re-signing. Do not claim the room fix or wheel is confirmed on the user's iPhone until they test.

Repository: private lykien0311-jpg/Army2Hoanggia-iOS, branch codex/army-ios-build, draft PR1. Native source and build workflow are uploaded. Separate legacy miniJVM workflow artifacts are a different app and must not be substituted.
