# Build263: isolate camera/HUD/corpse native function caches

37539.mp4 shows manual camera arrows responding without moving the viewport.
The patched camera and corpse receiver both cached their dlsym result in slot40.
The blindness painter and corpse updater also shared slot41. Normal startup
could therefore cache AGCorpseReceive as the camera callback, whose mismatched
arguments returned0 and suppressed every pan. HUD painting could likewise
make a corpse call the blindness function. Isolated previous tests substituted
or initialized only one callback and did not cover the shared data page.

Keep the camera and painter in their existing slots40/41. Move corpse receive
and update to dedicated42/43. The patch generator now claims every function,
Java literal and native callback slot and rejects collisions before assembly.
The report includes the complete slot registry for inspection.

Add an ARM64 regression with controller-first, camera-first and corpse-first
warmups, native pan setters, actual Apple camera/corpse functions and the native
HUD hook in one shared data page. Check all four directions at30ms, automatic
camera bypass and that controller/HUD/corpse dispatch still use their own ABI.
The release library remains free of diagnostic windows, sampling and logs.
Gameplay C sources, the airship protocol fix and accepted auto remain unchanged.

Record the old collisions/failure and the final package/provenance after testing.
