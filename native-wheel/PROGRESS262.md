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
