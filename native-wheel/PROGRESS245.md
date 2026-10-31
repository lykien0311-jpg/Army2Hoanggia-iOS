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

Native client ghost preview sprites use 23/24; server actor IDs 25/26 are not
preview IDs. Rooms 8/9 use UFO16, room16 Superboss uses Trex15, and other boss
rooms retain their own types. R5.w0 at 0x132 is the area ID, not the map ID;
linked rooms retain their native current stage instead of looking up an area
number in a map table.

GameCanvas draws default small commands after the screen painter. In addition
to the prior base-screen guard, both GameCanvas fallback text calls are now
guarded while the wheel is visible. The native keypad/input path is preserved.

Area list labels, formatted area titles and waiting-room area indices now read
the unsigned byte. IDs 128/129 display as 128/129. Raw bytes, join requests,
fees, player counts and custom area names keep their original paths.

Validation and Apple artifact identity are recorded after the final build.
No physical iPhone/live VPS test is available in this environment. Offline
results must not be described as a completed on-device verification.
