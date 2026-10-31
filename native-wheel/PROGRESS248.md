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

Apple build, final tests and package hashes will be recorded after completion.
