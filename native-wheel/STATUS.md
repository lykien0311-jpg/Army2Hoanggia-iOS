# Current delivery — 27/10/2026, Asia/Saigon

Completed classic lucky wheel UI, first-row battle V9 entry, and independent local walking. User explicitly permitted upload to private lykien0311-jpg/Army2Hoanggia-iOS and GitHub Actions with "Cho phép". The earlier upload approval block is resolved.

IPA: deliverables/Army2Hoanggia-V9-Wheel-Speed.ipa
Size: 16521098 bytes
SHA256: 08357ec70cb6c04b7bfd2278d54f79c904aa01defb5cf415e4e7fc6e17a87aa4
Dylib: native-wheel/build/classic-ci/AGWheel.dylib
Dylib SHA256: 362a6ca1cee2e5112cf790b15ef0b88de549d16cc005e43f6ffcea2ac05c6d49
Source commit: 707866d166fd658da3f05129493bdd3423e9cc66
Build merge commit: a1bb398effcdf2bcb15ce8489a3c7e4b1776d9fa
Successful Actions run: 40531573505; artifact: 12746861405
Repository branch: codex/army-ios-build, draft PR1. Do not use the separate legacy miniJVM workflow's IPA.

ClassicWheelUI.inc + PixelFonts.h use the original JAR fonts and reference 27450.jpg. Actual Simulator screenshots in native-wheel/build/classic-ci/ were inspected: active round, waiting02:00/large balance and native amount input/keyboard. UI is compiled for iPhone arm64/iOS12; simulator fixtures are excluded from the device dylib.

V9 inserts a new first item above Tắt vẽ căn góc using a distinct clock callback instance. Actual Xem giờ still executes its original body; input keys clear before opening the overlay. The home entry below Quay số is retained. The new read/write data segment is216 bytes; callback identities start160, AGMoveAllow pointer208. No runtime code patching/JIT.

Movement.c gates only the two original local left/right calls per variant. Monotonic50ms pacing keeps20 original walk steps/second regardless of fast update rate; immediate direction changes; no sleeping or queued replay. Global game speed, other walk/animation call sites and the original walk body remain untouched. Exact subjective match to the user's16.8s video still needs iPhone testing.

Room labels retain exact video2 titles for0–17 at paint; unknown IDs keep server labels. All previous room/clan/DataFix instruction patches and 523 resource entries preserved. ZIP, dylib exports/loader versions, Mach-O layout, RX/RW separation and LINKEDIT-last checks passed.

Tests passed:122 original ARM64 hooks;54 home menu;900 width;612 room display;324 native title-to-font;48 battle/clock/movement hook cases;18 original room builds/sorts plus24 native room paint cases. Actual newly compiled dylib:48 wheel state/protocol,36 room/JNI,36 movement checks. CI C tests:16 protocol snapshots +24524 malformed/fuzz;5 room packets +319 malformed +60 list layouts;20–1000Hz movement pacing. No live server, login, physical-device install or actual bet performed. IPA needs main/nested-dylib re-signing.

