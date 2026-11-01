# IPA 2.4.1 build248 — auto only

Build247 still auto-starts without firing in `32854.mp4`. Physical acceptance
has not passed. Preserve all UI, boss-room, unsigned-area and login repairs.
Keep the status ABI silent: do not reintroduce an AutoUFO window or message.

## Verified mismatch with working JAR

The native actor flags were not equivalent to those used by JAR Turn33:

| Reference field | Native proof | Offset |
|---|---|---|
| Turn33 CP157 / Player CP410, local falling | constructor stores1 at593ab8 |166|
| Turn33 CP163 / Player CP334, awaitMove | constructor initializes0 at5937bc |167|
| Turn33 CP160 / Player CP342, awaitFlight | constructor5937e4 and g(II)59a2f4 |14e|
| Player CP338, separate item animation | constructor5937d0 and setter599aac |16a|

Reference pulse checks166 only on the local actor, then14e/167 on every
living actor. Old iOS checked166/16a on every actor and checked16a on the
local actor too. Predicate waits also used166/16a instead of167/14e.
Correct both firing and wait predicates; retain the actual current-turn,
ticket, HP, state, position, projectile, flash, modal and connection guards.

The new regression executes original player/UFO constructors (Nv16) and the
original item/flight setters, then passes through the compiled bridge and
original Service.shoot packet writer. Constructor-created boss166 and native
item16a are not manually cleared. Old247 emits no packet on the first such
ticket; the new library must emit command22 exactly once on repeated turns.
Actual14e flight must still defer until completed. Java/graphics/allocation
and final transport are controlled boundaries. This is not a recording of
real iPhone state and must not be described as physical acceptance.

Correction to an earlier source comment: d0_.n compares Y with map height+200,
not time+200ms. Its flag reset must not be described as a200ms animation timer.

## Build and verification

- Native-constructor/item/flight regression: old247 fails with no shot on the
  first ticket; new248 passes48 cases across rooms8/9, six variants and three
  successive turns per room. The local actor settles through original n();
  only its Java/terrain boundaries are mocked. Boss166 and item16a stay set.
-174 protocol/turn/HP/origin/manual/modal guards;150 native predicate waits;
  36 installed-update-to-wire and18 original-walk-to-wire cases pass.
-134 native hook/exception and86 ABI/fallback checks pass. The existing32
  keypad projection,624 grid/pointer and444 notes/captcha checks also pass.
- Apple run41198183405, job124528499437, artifact13041521742. Source branch
  commit21417183cdda50a04be4c2efe6193888487bed65, tested PR merge
  56c85d4cc328a28c8dcb20920d49ef4bc4e8535e. Xcode16.4, iOS SDK18.5,
  minimum iOS12; strict signature/re-sign and six UIKit viewport checks pass.
- Device dylib SHA2569d0da73301f9f72cdd4773af976105555f370d775461711d1a4cec79577e6f44.
- IPA Army2Hoanggia-2.4.1-Build248-GitHub.ipa:16,562,591 bytes;
  SHA25620a400629803ed2e8ac6faa0070c2b830915ed5f71d79e5fa1abb57d960b9803.
- Only the dylib and Info.plist change from247. Native executable SHA256
  3fda3b084de5b4119c5ea60ec1a6998b4fb7af46ea0de73a4bcc7e0546abd08b
  is identical;523 other entries are unchanged. No AutoUFO status string or
  window; retained status callback is a single RET. Login marker stays
  2.4.1-HG78-IPA. Server/JAR/APK are not changed by this repair.

Physical iPhone / production VPS acceptance remains unverified. The above
fixtures prove the field/predicate defect and original command22 emission,
not that32854's undisplayed live bits had exactly the same values. The user
still needs actual automatic shots, damage and continued turns like the JAR
reference. Re-sign the IPA with the owner's installation certificate.
