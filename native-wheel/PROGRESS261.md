# Build261: correct actual Corpse497 marker and resolve NPCs by roster slot

37532.mp4 supplies decisive B260 device data. Around30s, server/native owner
are both0; camera is focused on10; incoming command93 has10bytes; the controller
is in wait kind3 for actor10. Actor10 is dead (HP0, state5), gravity0, flight1.
The marked-corpse observer still shows no recognized destination. Every NPC in
slots8..11 has actor field16b==0, rather than its roster slot.

Re-read both the working JAR and server constant pools, independently of the
patch implementation: Client497.move pool56 and Corpse497.sync pool134 both
contain decimal1129329721, hex43503439. The patch and its fixtures wrongly used
43505239. It therefore let the real marked packet enter the original live
flight starter and waited on flight14e forever. Previous synthetic tests copied
the wrong marker and manually set16b to the slot; those fixtures masked both
errors. Their prior pass counts did not establish real protocol compatibility.

Recognize only the real43503439 marker in the existing scoped corpse receiver
and diagnostic observer. Resolve a corpse's slot by scanning the active roster
for its pointer, not by actor16b. Clear revived sidecars by pointer too. Do not
modify actor16b or invent server turn order. Keep the existing death/settlement
and completion behavior, accepted UFO/POW code, no inventory auto-use,30ms
controls, speed, wheel and blindness behavior. Retain the diagnostic panel as
B261 for physical confirmation after signing.

The corrected protocol fixture records both independent class hashes and pool
indices. Native tests use that source-derived marker, NPC16b==0 and actual
native virtual dispatch/vtables where applicable, rather than routing directly
to a presumed NPC update. Build260 must fail the corrected packet regression.
Apple build and final validation details will be appended after compilation.

Apple build41426875965 passed for sourcecf61f2abb31524a38d3e82637485c305cd1ff38e
(merge02be66ca80b1df3d7e727cefc510ebe9489e8721). The downloaded ZIP matches
eeee3af894ce54fc96514f64014d836e8edab13d06747dffadf9297b679281ff.
Build260 independently fails the corrected marked-packet and zero-field actor
regressions. The final iPhone library passes90 real-marker fall sequences,96
fallback/reset cases,6 distinct-part/revival sequences sharing field16b==0, and
90 native completion/turn/camera sequences. Original virtual dispatch and NPC
vtables execute instead of redirecting straight to the presumed update entry.

Both independent JAR class constants were re-read and their hashes verified.
UFO, waits,30ms controls, blindness, speed, wheel, diagnostics and native ABI
regressions pass. The B261 panel/log remains enabled for physical confirmation.
The package changes only the verified library and Info.plist relative to
Build260;523 entries and the main executable remain byte-identical. Full test
evidence, provenance and limits are in validation261.json.
