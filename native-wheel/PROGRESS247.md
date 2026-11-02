# IPA 2.4.1 build 247

Build 246 still auto-starts UFO without firing in `32850.mp4`. Its status row
shows the animation guard, meaning valid mode/turn/aim reached the bridge.
The reference is `32828(1).mp4`. `32852.jpg` also shows strips exposed above
and below the wheel command row. The user requires no diagnostic status row.

## Fixes

The JAR pulse checks the primary busy flag mapped to native player globals
`1a7`. The old bridge additionally vetoed firing on `1a8`, a deferred-shot
notification consumed/reset in native `V.s()`. The original native primary-busy
reset leaves that notification intact. With this state, 246 emits no command22;
247 emits the original shot packet on successive valid turns. Remove only the
extra veto; keep projectile/flash, owner, ticket, position, actor and modal guards.
The device video did not expose the individual bits, so do not claim that its
exact live bit value was directly observed.

The old keypad fixture stopped before N/h's final coordinate translation at
`1fd9b4..1fd9dc`. It therefore validated pre-translation bounds. Read the final
native button rectangles using the original List/Iterator calls and project all
corners through the batch's combined matrix. Capture on the game tick as well as
the paint path; the tick can run while the batch is outside drawing state.
An opaque footer view fills from the panel edge through the relocated controls
to the keypad touch boundary, covering both reported strips.

Remove the diagnostic window, label and timer. The retained status ABI is a
single RET; the device library contains neither `Auto UFO:` nor its window class.

## Validation

- Old246 stale-notification fixture fails with no shot; the identical native
  reset and aim fixture passes 12 shot-wire cases with247 across six variants.
- 168 turn guards, 36 update-to-wire, 18 native-walk-to-shot, 150 predicate waits.
- 32 final native key translation/projection cases, including game-tick capture,
  skew and non-drawing batches; UIKit footer/input checks on six sizes.
- 624 grid/pointer and 444 notes/captcha model checks also pass.

Apple run `41195206993`, artifact `13040885862`, source branch commit
`06451efe91b031df319aac098bc8c88afa556853`, tested merge
`59412d29426ca4b5e47917f5a6416d672bb0e7db`; Xcode16.4 / SDK18.5.
Signature and re-sign checks pass. A simulator-only subpixel coverage assertion
was adjusted to a .01 point tolerance; failures now report their reason.

Device library SHA256:
`b0ff27bc8b41973fb62df6896ca62f11f36ba80953e9c5f2b1dbc6c57d6e68f5`.
IPA SHA256: `efa2cfaf794e9456383a54e0f421fb4dc85aa6decce184c5e8717fbda581f4a9`.
IPA size: 16,562,609 bytes. Executable byte-identical to246; only the library and
Info.plist change, with523 archive entries retained, including previous boss
mapping, unsigned zone labels and login marker repairs.

No physical iPhone or live VPS test. JVM/OS, list/iterator and final transport
boundaries are mocked, as is the arena update body in the update-to-wire test.
Physical acceptance still requires automatic start, actual shots, boss HP loss
and continued turns like the reference. Installation requires user signing.
