# Build259: keep fallen airship parts dead through projectile impacts

37527.mp4 shows a fallen airship gun on the ground while the turn clock and
camera remain stuck. Build258 consumed the marked corpse93 packet, but its
tests started every corpse in death state5 and stopped the following command24
at the original controller entry. They did not execute the native endShoot gate.

The native turn changer512b44 resets its selected actor to idle0 unless that
actor is in hurt8; it does not check HP or preserve death5. A handoff targeting
a part whose death arrived earlier therefore replaces death5 with idle0.
Build258's corpse hook skips Player.update and preserves that stale live state.
The native arena update546620 counts gravity166 && state16f!=5 as moving and
withholds Service.endShoot23. Replaying that native gate with Build258 confirms
that dead parts in state0/8 block command23, whereas state5 permits it. The new
regression reproduces the state5-to0 edge through the real native command24
and turn changer, and fails on Build258 at the first corpse update. The native
hurt method598af8 actually preserves state5; it is not the source of that reset.

For confirmed dead airship actors17..21 in rooms10/14/15, restore death5 and
native death-frame/status cleanup before animating each update. Clear obsolete
live-flight/walking flags and leave gravity set only while the marked server
destination is still being approached. A corpse with no matching motion is
settled. Do not infer a turn, send a synthetic turn, or use an elapsed timeout.
The native arena sends its normal completion packet and the server selects the
next actor; the unchanged native turn changer then selects that actor's camera.

Keep all accepted UFO/POW code and 30ms movement/manual camera unchanged.
Validation and Apple build provenance will be appended after compilation.
No physical iPhone or live game-server acceptance is available here.

Apple build41406604542 passed for source5af6fd25f786a1e1a743e2846b51ab7f52248fda
(Apple merge77e2bc97af7b421ad5a29fdef1197429a400ffec). The downloaded ZIP
matched digest7d620ae9687457e087bd0c1d1b771cdd9ef5721eb9b7c7c4599e97060e38aee5.
The compiled iPhone library passes90 full native completion/next-turn/camera
sequences across all six variants, rooms10/14/15 and characters17..21. The
regression fails on Build258 after a real native command24 resets death5 to0.
A living moving actor still prevents completion; a landed corpse cannot re-arm
gravity, pin live flight/walking, duplicate ACK23 or steal the next camera.

Previous corpse routing/fall/reset, airship and UFO waits, native UFO encounters,
bomb blindness,30ms camera/walking, speed10, wheel return and hook ABI/preservation
checks also pass on the final Apple library. See validation259.json for counts,
hashes, archive preservation and controlled-boundary limits. The packaged IPA
changes only the verified library and Info.plist relative to Build258;523 other
archive entries, including the main executable, are byte-identical.
