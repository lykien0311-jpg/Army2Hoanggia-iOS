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

Apple build41410437040 passed for source99575994c61bff2a8f916e849dbdb982db4fe48f
(mergef3d79f22425ecb82cabddfb7d36f218460275085). The artifact ZIP matches
6403aa2ef322ae71f004306eecfbd316c5b6eb50f3436b8fe7af769062056aeb.
UIKit preview passes320/390/844 layouts, touch passthrough and an actual local
log write; the screenshot was visually inspected.48 Apple ARM64 observer
cases expose differing server/native/camera owners and roster/native indices
without mutating battle or reader bytes or sending any packet.

All accepted corpse/turn/UFO/wait/controls/blindness/speed/wheel and native ABI
regressions pass on the final compiled library. Packaging changes only the
Apple-built library and Info.plist versus Build259;523 other entries and the
main executable are byte-identical. validation260.json records full provenance.
This diagnostic evidence does not establish physical resolution of37529.mp4.
