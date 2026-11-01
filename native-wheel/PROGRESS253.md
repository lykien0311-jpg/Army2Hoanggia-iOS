# Build253: accept the real100-slot native UFO roster

35378.mp4 and35379.mp4 show Build252 receiving valid mode, turn and21-byte
aim packets, with zero shots and a pending handoff; local coordinates stay
0,0 while server aim origins are293,294 or378,336.

The native client allocates the Player[] roster from its server capacity,
not the number of occupied slots. ServerManager.maxElementFight defaults
to100; the capacity is serialized as a positive Java byte. The adapter's
count>64 guard rejects that valid100-slot array in effects, dispatch, pulse
and animation waits. Pulse exits before reading the local coordinates.
This also strands queued ownership and can skip high-capacity flight waits.

The regression now runs the original native server-capacity setter/getter,
Player[] allocator wrapper and array setter. Only the final JVM allocation
primitive is controlled. With the shipped252 library and a100-slot roster,
it reproduces count100, enabled1, hasPlan1, nativePending1, applied0, x0,y0,
blocked0 and shots0. The former ten-slot fixtures masked this guard error.

Support positive-byte capacities through127 throughout the adapter. Null
slots remain null and are skipped. Slots/local owners remain bounds checked.
Apply an idle incoming turn on the original dispatcher thread before its
following flight/shot packet, as the original native path does. Busy handoffs
still wait for completion and retain their complete deferred tail. Preserve
an in-progress native-change permit when a later turn notification arrives.

User scope: normal weapon shots and automatic POW only at full rage100. The
auto packet writer permits command22, or command26 with the native POW token
100 only. It never chooses an inventory item. Verify all ten characters, all
six variants, rage0/99/100 and no repeated skill/shot.

Retain the passive status label for verification, identify it asB253 and
show roster capacity and pulse count. No physical-device acceptance is
claimed until the user has tested this exact IPA.
