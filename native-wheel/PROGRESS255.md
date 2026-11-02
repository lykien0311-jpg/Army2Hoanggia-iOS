# Build255: home return, manual camera pacing, maximum speed

The home-menu wheel action inherited the native pending-navigation flag at
instance offset 0x9f. The original painter draws the background but suppresses
the menu while that flag is set. Clear it only for the added wheel row, then
execute the existing home cleanup and layout. The other native rows retain
their original dispatch and state transitions.

Manual camera panning now uses separate 50 ms clocks for each axis and each
variant, independent of walking. Only the native directional delta setters in
manual mode 0 use those clocks. The native camera update, automatic following,
clamping, and all other modes remain unchanged. There is no sleep or queued
pan. The first step and direction changes are immediate.

At game speed 10 the native loop still called Thread.sleep(0). Bypass that
remaining scheduler yield at exactly level 10; preserve the original native
delay calculation at levels 1 through 9. Gameplay updates are not duplicated,
and the tick bridge still runs once per loop. The device determines the final
processing/render rate; physical-device performance has not been measured.

This change starts from the accepted Build254 branch. Turn33.c/.h and
UfoAuto.c/.h remain byte-identical to accepted Build253; the production B253
diagnostic overlay remains excluded. Auto uses normal shots and eligible POW,
without inventory items.

Validation executes all six native variants: the home selection prologue,
original layout/cleanup and painter gate; manual pan setters with the real C
clock; and all ten native speed levels with an absent/present tick bridge.
The old Build254 home painter gate is replayed first to reproduce the blank
home before checking the fix. Apple device-library signing and simulator UI
checks run in the existing native-wheel workflow. Release hashes and workflow
provenance are recorded separately after packaging.
