# Build258: accept Corpse497 airship packets; movement/camera30ms

The new37525.mp4 report disproves Build257's lost-notify-only diagnosis.
The working JAR adds Client497.move to its command93 reader. It recognizes
the server's exact10-byte payload: actor u8, x/y signed i16, magic43505239,
then a remove boolean. The unchanged IPA reads the first5bytes as normal
flight, sets actor14e and waits. Its NPC update switch has no flight-ending
branch for detached airship characters18..21, so a predicate wait still never
finishes and incoming turn/leave messages stay queued behind it.

Add guarded AGCorpseReceive routing before the original controller. For the
airship rooms10/14/15 and characters17..21, consume only the exact marked
extension and ignore stale packets targeting live actors. Keep the original
reader and live5-byte flight path unchanged. Move dead parts on the native NPC
update with Client497's acceleration2/update, maximum24/update and exact
server destination; optionally hide when the server's remove flag requests it.
This animation never waits or gates the controller. Sidecar state is keyed by
variant, session, arena, roster index and actor pointer, and resets on match20
or actor revival. Other actors and stages retain their original update path.

Use30ms for both walking and manual camera, independent of game speed and
of one another. No forced turn timeout, repeated shot or inventory item is
introduced. The accepted UFO/POW source files remain byte-identical.

Validation must replay a real marked corpse packet through the installed
native controller, the original detached-part switch and patched NPC update,
then verify a subsequent controller command and untouched live-flight fallback.
Physical iPhone or live-server acceptance is not available in this environment.

Apple build41401825604 passed. Controlled ARM64 validation reproduces24 old
detached-part flight stalls across6variants: the original flight starter sets
14e, then the unchanged NPC type dispatch leaves it set through5updates for
characters18/19/20/21. The unrelated base Player.update boundary is mocked in
these dispatch replays. The installed controller and compiled replacement pass
90complete packet/fall sequences across rooms10/14/15, all characters17..21
and capacities9/100/127. Another90cases check live actors, plain/malformed
packets, other rooms, UFO fallback and state invalidation. A following command24
reaches the original controller while a corpse is still falling. No JVM wait
is called for a marked corpse packet. The original input reader is unchanged.

Regression checks also pass390prior airship wait cases,150installed UFO wait
cases,60native UFO encounters,12long UFO-effect/fallback cases,96blindness
cases,48Apple ARM64 timing cases at30ms,120speed cases and12wheel-return
transitions, plus the native hook ABI and archive-preservation checks.
