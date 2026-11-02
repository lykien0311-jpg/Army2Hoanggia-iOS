# Build266 — refresh the native equipment screen after server replies

The user reports Build265 displaying HP 51,679 and attack 3,337, while JAR/APK
correctly show 168,048 and 4,585. The remaining three displayed stats agree.
No JAR, APK, server or combat formula is changed in this revision.

An ARM64 regression demonstrates an uncovered lifecycle bug in Build265:
the server snapshot can be received after the summary array was calculated,
but the open screen keeps painting that old array. The prior tests always
received a packet before explicitly invoking calculate(), missing this order.
The new test fails on Build265's unchanged paint entry with the screenshot
output fixture still showing the old values. This does not claim to recreate
the user's unseen points, equipment data or precise network timing.

Build266 refreshes only the display array before the original native paint.
It obtains the current player, costume flag and costume handle through the
verified native getters, totals the current selected gear in C stack memory,
and applies the same GEM1 rules or a fully matching GEM2 snapshot. It neither
allocates Java arrays nor sends requests, and retains unsaved-preview guards.
Incoming Message constructors also observe stats extensions before controller
routing, so early login configuration is cached before the screen opens.
Original constructors, packet positions and painting continue unchanged.

Tests include the original native Message constructor and paint entry, with
both early packets and late replies, all six variants, register/stack guards,
and unsaved selection changes. Apple build and final device-emulation results
are recorded after verification. Physical iPhone validation remains pending.
