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
and unsaved selection changes. The new native regression passes 54 checks
across six variants, including late GEM1-only configuration and costume mode.
The preceding 3,000 server-fixture checks, 24 six-slot/costume checks, 186 native
summary checks and 2,000 independent JAR-oracle arithmetic cases also pass.

Apple Actions run `41549580456` succeeded with Xcode 16.4 / SDK 18.5. The device
library passed codesign strict verification and an independent re-sign check;
SHA256 `dbf32beef9ac9944ae01f569d57c2cc36fdf456eac2799b11e6b0d477478a0f4`.
Source commit: `8fb58ed1e706d1c83d58e5fc0448ecd33501eab6` (Apple merge
`e9268caa1f3ff20af07940e769c3ac3d727af1d7`). Build266 keeps the 2.4.1 login
marker, IPs, game assets and previous gameplay repairs. The native patch fits
inside the existing reserved RX/RW segments; new code size is 30,352 bytes.

The screenshot output values are tested as a server-snapshot output fixture.
The exact production account's points/gear and timing were not supplied, so
physical iPhone validation of the reported case remains pending. The IPA must
be re-signed by the user before installation. See validation266.json.
