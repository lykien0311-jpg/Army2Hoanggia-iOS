# Build259: keep fallen airship parts dead through projectile impacts

37527.mp4 shows a fallen airship gun on the ground while the turn clock and
camera remain stuck. Build258 consumed the marked corpse93 packet, but its
tests started every corpse in death state5 and stopped the following command24
at the original controller entry. They did not execute the native endShoot gate.

The native hurt method598af8 writes hurt8 without checking HP. After a fatal HP
update, a projectile impact can therefore replace death5 with hurt8. Build258's
corpse hook skips Player.update, including its delayed hurt-to-death transition.
The native arena update546620 counts gravity166 && state16f!=5 as moving and
withholds Service.endShoot23. Replaying that native gate with Build258 confirms
that dead parts in state0/8 block command23, whereas state5 permits it.

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
