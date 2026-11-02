# Build260: requested on-device airship diagnostics

37529.mp4 and the user's follow-up disprove physical acceptance of Build259.
The expected order is a living airship part, then a player; after a kill the
next surviving part takes the following boss turn. Do not invent that order in
the IPA or infer it from a corpse landing: capture the actual server turns.

At the user's request, add an airship-only touch-through diagnostic panel that
remains visible when native state stops advancing. Display server command24
owner versus native owner and camera actor/mode; projectile118, completion115,
canvas13c, player pending/notification flags; active wait kind/actor; update,
receive and wait ages; per-part roster/native indices, character, HP, state and
gravity/flight/walking flags; marked corpse93 destination and corpse-hook
accept/reject observations; and the recent command/first-byte sequence.

Native callbacks copy numeric snapshots on their own Env under the existing
RoboVM exception guard. UIKit and the file queue access copied scalars only.
Sample native state at most5Hz and append a bounded local KhiCau-B260.txt log
at most1Hz. The panel never becomes key, accepts no touches and is armed in
standalone room10 or an active airship stage in linked rooms14/15. Room10
also shows A0/E when battle recognition fails, so that failure is recordable.
The file is in the app's Documents folder,
already exposed through iOS Files by the accepted package settings.

This is a diagnostic build for the user to sign and record. It adds no packet
send, synthetic turn or timeout and makes no new claim that the underlying
battle stall has been solved. Keep Build259's combat behavior and all accepted
UFO/POW, no-inventory-auto,30ms controls, wheel, speed and blindness behavior.

Apple compilation, on-screen layout and ARM64 read-only-observer validation
will be recorded after the build.
