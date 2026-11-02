# Build262: remove airship diagnostic panel and logging

The user requests removal of the diagnostic display from the accepted IPA.
Exclude AirshipDiagnostics.m and ShipTrace.c from the iPhone device target.
Keep the diagnostic ABI as no-op functions, with no native snapshots, timer,
window, file queue or log writes. The diagnostic implementation remains only
in the separate development Simulator target and is never packaged in the IPA.

Keep Corpse.c, BattleWait.c, AGWheel.m, accepted UFO/POW sources and Movement.c
byte-identical to Build261. The corrected43503439 corpse marker, roster-pointer
lookup,30ms controls and every other accepted gameplay change remain included.
The main executable's installed hook ABI and all native patches stay unchanged.

Apple device build checks must reject airship/UFO diagnostic window classes,
on-screen build prefixes, log filenames and the airship log-queue label.
Run the corrected corpse/turn and accepted gameplay regressions on the final
device library. Packaging, hashes and provenance will be recorded after build.

Apple build41435278986 passed for source6540d9023c248404e3f994e1a6bfeb973167ac3d
(mergeb8951756daa866a5e4a623a79073bcd2f7264fdd). The downloaded artifact ZIP
matches0b8e72682588330dfc87d34063f73ba32cd0904f2db170ee64c82caaebc6ca2a.
The packaged device library contains no diagnostic window class, B260/B261
label, diagnostic log filename/queue or snapshot storage. All8 recorded
gameplay source hashes and the installed native executable match Build261.

Corrected corpse routing/falls/reset cases, native turn/camera continuation,
UFO encounters,30ms controls, wheel return and native hook ABI checks pass on
the final library. Only the verified library and Info.plist differ from the
prior IPA;523 archive entries remain byte-identical. validation262.json records
full provenance and the controlled-runtime limits.
