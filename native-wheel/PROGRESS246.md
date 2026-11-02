# IPA 2.4.1 build 246 — UFO waits, arena pulse and wheel footer

Video `32843.mp4` confirms that build 245 still starts UFO auto without firing.
Its waiting-room UFO image is now correct. Image `32842.jpg` requests moving
the entire large wheel command row down over the exposed strip above the keypad.

## Resulting implementation

- Port the working JAR's predicate waits at five exact sites per variant:
  remote walk, flight, shot completion, lucky flash and arena flash. In UFO
  rooms the code waits in 16 ms intervals only while the relevant animation is
  active in the same arena. An already completed animation never enters the
  unconditional native wait. The native monitor and throwable path remain;
  other rooms retain the original wait calls.
- Pulse auto after both original arena update entries, on the original game
  thread and Env. Keep the existing canvas tick as well. Turn/ticket/used guards
  prevent duplicate shots when update paths overlap.
- Consume the private `-115` packet after its bridge handler, as the JAR does.
  Preserve a first-turn ticket received before the battle becomes active.
  Ignore stale motion flags on dead actors and check projectile/flash busy state.
- Call the original player fire method and original Service command 22 writer.
  Keep the live int32 position and angle fields repaired in build 245.
- Capture the actual N/d keypad SpriteBatch combined matrix. Project the native
  key geometry to the render surface and align the wheel backdrop, three-button
  row and touch boundary with that edge. Re-layout after projection arrives.
  Keep the existing suppression of both small-label painters.
- Show a noninteractive `Auto UFO: ...` status row during UFO battles. This
  distinguishes missing turn/aim data, animation, position, owner and dialog
  guards. `Đã gọi bắn` reports a call, not server-confirmed damage.

The new source repairs verified differences from the working JAR/APK. The exact
blocking state on the user's physical device was not logged by build 245; do not
state that offline fixtures alone prove the reported device problem is resolved.

## Validation and packaging

The Apple-built device library passed signing and re-signing verification with
Xcode 16.4 / iOS SDK 18.5. Run `41192348295`, artifact `13039725977`.
Source branch commit `19d6611d94243f3bbd0838f42156621164dc5a8c`; tested PR merge
commit `b6a83a99e3f0f75fc471a7ede1c1f4e49595a796`.

All 15 local check scripts passed against that device library and the packaged
native image. `validation-ui246.json` records counts and limitations, including:

- 150 predicate wait cases, replaying an old unconditional wait after completion;
- 36 installed update-hook → compiled pulse → original command 22 cases;
- 18 original-walking → repeated-shot cases and 174 turn/aim guard cases;
- 8 original keypad geometry/projection checks and UIKit footer/touch geometry
  on six sizes, including landscape;
- retained boss rendering, small-footer suppression, unsigned zone labels,
  grid/pointer input, captcha/settings hooks and login checks.

The original arena update body is controlled in the update-to-wire fixture;
Java/OS/graphics primitives and final transport are mocked. No live VPS or
physical iPhone test was performed.

Only the executable, `AGWheel.dylib` and Info.plist differ from the delivered 245
archive; 522 entries are byte-identical. Build 246 can be repackaged byte-for-byte
through the guarded baseline recovery. Keep the current server, JAR and APK
updates intact; this delivery replaces the IPA only.

IPA: `Army2Hoanggia-2.4.1-Build246-GitHub.ipa` — 16,563,458 bytes.
SHA256: `b98328de1a9a09bde0369bbdd4625a17fac0f033bc62a8a839946a0436b0e97c`.
Device library SHA256:
`1cd5d7496f05a282390bc6b69dd0f85e77c0656620ee60cbf172a61ffc5c2e5f`.
Requires the user's installation certificate for IPA signing.
