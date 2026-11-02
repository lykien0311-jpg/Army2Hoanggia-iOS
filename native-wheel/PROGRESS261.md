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
