# IPA 2.4.1 build 245 — device-reported regressions

The owner reported that build 244 still showed Trex in UFO lobbies, auto started
matches without firing, and native small wheel commands leaked below UIKit.
The requested scope also includes unsigned area labels after 127, in every room.

The original native walking method d0_.l(Z), beginning at 0x59bde0 in variant 0,
writes full int32 live positions at 0x114/0x118. Build 244 instead compared its
aim to constructor copies at 0x80/0x84. It also treated the int32 angle at 0xa4
as a short. These assumptions in the old offline fixtures were wrong. The new
bridge validates actual positions without rewriting them, writes a full int32
angle, and invokes the original native fire/Service command-22 path.

The receive observer runs before the original dispatcher. It now caches a valid
ticket/aim while the first arena screen and owner are activating, and applies
screen, owner, movement, captcha, connection and duplicate checks on the game
tick. This follows the reference JAR's receive-then-pulse ordering.

The original native renderer explicitly draws ghost images for 25/26. The
reference JAR's Room32 returns 23/24, which fall through to the normal image
array in this IPA; those JAR numbers must not replace the native ghost cases.
Rooms 8/9 use UFO16, room16 Superboss uses Trex15, and other boss rooms retain
their own types. R5.w0 at 0x132 is the area ID, not the map ID;
linked rooms retain their native current stage instead of looking up an area
number in a map table.

GameCanvas draws default small commands after the screen painter. In addition
to the prior base-screen guard, both GameCanvas fallback text calls are now
guarded while the wheel is visible. The native keypad/input path is preserved.

Area list labels, formatted area titles and waiting-room area indices now read
the unsigned byte. IDs 128/129 display as 128/129. Raw bytes, join requests,
fees, player counts and custom area names keep their original paths.

Apple build: run 41176019802, artifact 13033790327, branch 324c1bd29e5e7d994b4a96570c54a1f0b76a4d94, tested merge 7f80315ace467ea502328b06260e1398b7648464. Strict Apple signature and re-sign checks passed.

The actual native walking method -> deferred ticket/aim -> original native player/Service command22 test passed 18 repeated-turn cases, in addition to 12 shot-wire and 162 guard cases. The previous compiled 244 bridge reproduces a missing shot with the same actual-coordinate fixture. Original sprite image selection passed 96 cases; both footer sources passed 54; unsigned area display passed 348. Grid, Notes and login checks remained green. Exact identities and test limits are in validation-ui245.json.

Only the main executable, Apple-built AGWheel.dylib and Info.plist differ from 244; all other 522 archive entries match. The guarded packager accepts the delivered 245 as a recovery input. The existing login marker is unchanged.

IPA SHA256: 745b50bce5433bb8ba350da6756afc5b95acce0a41c05c4a2269b2e81b3f1381.
No physical iPhone/live VPS test is available in this environment. Offline
results must not be described as a completed on-device verification.
