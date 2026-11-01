# Build256: bomb-blind white world layer

Reference: 35401.mp4 shows the IPA world remaining visible; 35400.mp4 shows
the APK hiding the world in white while retaining HUD, menus and keys.

The supplied reference client's Client46.blindPacket and arena painter use
command106's wire bytes [state,target]. State0 blinds the local player;
state1 clears it. Other players' status packets must not alter the local
mask. The native IPA painter lacks this added Client46 white-world branch.

Observe command106 without consuming or changing its reader position. The
original controller still handles both command106 and new-match command20.
Bind blindness to the current arena and local slot; clear on a new match,
leaving that arena, a changed local slot, or the server's clear packet.
There is no client timer or frame-count expiry.

At the native arena painter's guarded world boundary, a blinded player gets
an opaque RGBffffff rectangle over the logical game viewport. Continue at
the original HUD boundary, with the native tail's three shared constants
initialized. GameCanvas subsequently paints menus and the keypad normally.
Normal players follow the original world painter. Native Graphics color,
clip and translation layout is verified against the exact executable, and
the guarded draw restores state on Java exceptions.

Build255 camera/speed/wheel-return patches and accepted Build253 UFO/POW
sources are retained. The production diagnostic overlay remains excluded.
