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

Apple build41439894541 passed for source4ac9f7e2ba9c43dbd5857ea93a1d69d608750804
(mergeb763a8977249cc0787c423ef91fed347a01b225e). The artifact ZIP matches
0aa148991ad54311dbd0160733be253a0fa52b763d158e11f6a2a7cb042378bf.
The new regression fails on Build262 after ordinary controller/HUD warmup and
passes546 shared-cache cases across6variants and3warmup orders after the fix.
All four directions,30ms gating, auto-camera bypass and typed dispatch remain
correct.120 native pan/ABI cases,48 Apple timing cases,96 blindness cases,
corrected corpse routing/falls/turns,60 UFO encounters and native hooks pass.

Only24 bytes in the injected native code differ from Build262; gameplay C
sources and the complete Apple device library are byte-identical. The IPA
changes its native executable and Info.plist;523 other entries are unchanged.
No diagnostic UI or logging is re-enabled. The supported native recovery entry
was added and its round trip verified. validation263.json records provenance
and controlled-runtime limits.
