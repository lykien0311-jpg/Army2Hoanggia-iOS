# Pending update: classic wheel UI, in-battle V9 entry, independent walking

User said "Ok chỉnh đi" after noting the three changes. Source and native hooks are prepared; NO new IPA was built or delivered for this update yet. Existing Library v4 IPA still has the earlier circle UI, outside-lobby menu only, and original walking speed.

Prepared files: AGWheel.m + ClassicWheelUI.inc + PixelFonts.h replace the circular UIKit interface with the supplied JAR's light-blue/gold information panel, original bitmap fonts, timer, proportional bar, balance/tax/pool/participation and previous winner/prize/stake. Three bottom controls are Tham gia/Cập nhật/Trở ra. PNG font data is embedded in the header; no separate asset copy is needed by build or packaging. Original game fonts were decoded from the supplied JAR and their metrics recovered by emulating the original native font initializer. Alert entry/confirmation and protocol/nonce logic remain intact.

map_native.py/patch_ipa.py now prepend V9's first item by extending the original Vector constructor call. A distinct instance of the original clock callback class identifies the wheel command; the original clock command still executes its untouched body. Key states clear before opening the wheel. __AGDATA is 216 bytes: six identity slots start160; AGMoveAllow pointer cache208. Both home-menu and V9 entries open the same overlay.

Movement.c gates ONLY the two local left/right walk calls per variant, not the original walk body, server animation calls or game speed loop. One original walk step per50ms (normal20Hz), immediate direction/player change, no sleep or catch-up queue. New dylib MUST include exported AGMoveAllow; patcher refuses old dylib. build.sh includes Movement.c and test_movement.py. Tests passed:122 original hooks,54 home menu,900 width cases,612 room display,324 native font calls,48 new battle hooks, C pacing across20–1000 input ticks/sec. New UIKit source has NOT been compiled/rendered on Xcode yet.

Authorization received 27/10/2026: user replied "Cho phép" to the explicit request to upload these changes to private lykien0311-jpg/Army2Hoanggia-iOS and run GitHub Actions. Proceed with source upload and build. Last branch head21c27baab06ec342ba17cd048bcab0c666b6fb4f, tree c263a38c510b570839ad8e1d47144548468cc924; branch codex/army-ios-build, draft PR1. Include prior unpushed room/menu changes too. Required upload source: AGWheel.m, ClassicWheelUI.inc, PixelFonts.h, Movement.c/.h, build.sh, map_native.py, native-map.json, patch_ipa.py, test_hooks.py, test_menu_room_display.py, test_battle_hooks.py, test_movement.py, test_device_bridge.py, README/STATUS. A normal commit without skip-ci triggers native-wheel.yml. Verify new actual UIKit screenshots, execute test_device_bridge.py on NEW compiled dylib, package and validate new IPA, then replace Library identity libfile_f56e81dfc4608191bc5868cfbac72082 with expected_current_version4 and apply metadata. Do not label the old dylib or v4 IPA as the new update.

Previous delivery details:

# Army2Hoanggia — current checkpoint, 27/10/2026 (Asia/Saigon)

User authorized the three pending changes below. Previous GitHub create_tree was rejected by automatic approval review: upload of native source to the identified repository was not considered explicitly authorized. User subsequently explicitly approved this exact destination and Actions build with "Cho phép". This previous block is resolved.

Current deliverable: deliverables/Army2Hoanggia-Phong-Video2-Wheel.ipa, 16,520,722 bytes, SHA256 0c0c1b4dd957e599dd246f7a8c6172348540c86dd49f298c3514681b8b455fc4. Latest request moves the wheel below Quay số and requires room labels to match video 2 exactly.

Verified dylib: native-wheel/build/verified-ci/AGWheel.dylib, SHA256 9fac50bbc4da985c12b572d20bf8e2012e401a20cfc152aedadd0046bf621658. Built from 3de2ccf7707e5cf2959e821df80769bd010d02d9, successful Actions run 40419576327 / artifact 12696207572. Earlier first-ci dylib has the pre-fix empty-string room-label bug; do not use it.

The native home category-0 menu has a seventh row, VÒNG XOAY MAY MẮN, immediately below Quay số across all six variants. Xem giờ and its label are restored exactly. Menu width adjusts only for this submenu. Pattern-based discovery accounts for variant-specific function placement; long conditional transfers use a local condition plus an unconditional branch. -101 receive interception, polls and confirmed bet submissions use the existing game connection on the proper game thread. UIKit stays on the main thread. Old Quay số remains.

The paint hook now chooses the exact video-2 title using the actual room ID (0–17), independent of absent/late/shifted server titles. IDs 0/1/2/17 use the native default, 3–16 use the reference boss names; unknown IDs retain server names. It does not change room objects or routing. Literal caches are stable RW slots registered by RoboVM; text remains RX. Room cache -19 receives actual unsigned ID / MUTF name / marker -1. Names persist before screen construction and replay after the native list builder. Default labels use NULL, not an allocated empty String (native renderer uses reference equality). Header IDs 255 are untouched. Actual native sorting yields video groups 0 / 1 / 2 / 3–16 / 17. All old DataFix/room/clan instruction changes and resources remain except the explicitly reported new hooks. Speed remains capped at10 (already0ms sleep).

New tests: 54 native menu/selection, 900 width/register preservation, 612 room-display cases and 324 full native label-to-font-draw paths across six variants, using independently transcribed video-2 labels and faulty video-1 fixtures. All passed.

Tests: 16 wheel packets +24524 malformed/fuzz cases; 122 hook/guard cases; 18 actual room build/sort runs +24 native paint dispatch cases; C parser 5 valid /319 malformed plus60 reordered/rebuilt layouts; actual compiled dylib48 wheel +36 room/JNI cases, including same-nonce retry, stale ack, connection change, real native Java exception recovery. Simulator screenshots show the wheel and entry dialog. ZIP consistency, library version compatibility and LIEF Mach-O layout checks passed.

Main executable load dependency version is 0.0.0 to match clang's default dylib current version; requiring1.0.0 would cause dyld rejection. Separate RX/RW injected segments keep LINKEDIT last and retain all old bindings/rebases/VM addresses.

NOT performed: physical-device install, live login/server interaction, real bet. Final IPA needs main and nested dylib re-signing. Do not claim the room fix or wheel is confirmed on the user's iPhone until they test.

Repository: private lykien0311-jpg/Army2Hoanggia-iOS, branch codex/army-ios-build, draft PR1. Native source and build workflow are uploaded. Separate legacy miniJVM workflow artifacts are a different app and must not be substituted.
