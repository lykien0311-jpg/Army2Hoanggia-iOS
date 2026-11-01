# Build251: UFO and player turns are serialized

35373.mp4 reports Build250 still enters UFO without automatic shots and shows
local aim while the UFO's attack is active. The reference is32828(1).mp4.

The original native getters/turn method prove that arena globals266 is the
local player's index, whereas player-array globalsd0 is the current actor.
The old adapter named them in reverse. Identical local/current fixture indices
failed to detect this. In particular, an aim arriving while actor8 was current
was dropped even though it belonged to local player2.

Hook the exact command24 call to the original native changeTurn method in all
six variants. Defer that native HUD/input/ownership handoff until the preceding
projectile, flash and living actor movement/flight actually finish. Run the
original native method, with its coordinate sync, pose reset and camera/HUD
updates, then admit auto for that applied turn. A returned original method is
not sufficient: it can postpone its work while the native status/chat string
is nonempty. Verify the resulting current actor and retry the pending handoff.

Keep authoritative server trajectories and ordered POW26/item100 before shot22.
Do not accept a player ticket as completion of a UFO animation. Remove the
five-second timeout which previously let the dispatcher advance despite an
unfinished effect. Only completion or leaving the arena releases that wait.
UFO gravity and unrelated item flags still do not count as flight/movement.

The regression executes the original ARM64 turn changer, flight-completion
method, projectile finalizer and local gravity update. Scene/string literals,
terrain/math, HUD/camera, JVM and transport remain controlled boundaries.
The supplied250 library reproduces early native ownership during the UFO's
active flight/projectile. A first251 candidate passes the encounter sequence;
a postponed native status-string handoff adds a separate regression.

Final Apple provenance and package checks are recorded in validation251.json.
No physical iPhone or production VPS execution is claimed by these fixtures.

The complete command24 tail is part of the deferred handoff. The original
handler otherwise resets the projectile/HUD counter after changeTurn returns,
which can still alter the preceding UFO effect even when ownership was queued.
The installed hook now returns through the original dispatcher epilogue for a
deferred turn. Its original changeTurn and the exact counter/input-reset tail
run together on the game update after effects complete. Non-UFO and missing-
module fallback paths retain the original native call and tail.

The final encounter driver executes the original command24 frame, message
reader, busy reset, handoff call site and tail. Only command selection (already
known from the test packet) bypasses the unrelated switch branches. It checks
that counter/input state stays unchanged during the UFO's active attack and
resets only when the original native player turn is applied.
