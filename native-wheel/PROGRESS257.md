# Build257: B52 completion wait in airship battles

In 36819.mp4 the native menus remain responsive after the airship/B52 action,
while battle progress stalls. The controller's original shot tail fires the
actor, acquires its monitor, then calls Object.wait without rechecking whether
the projectile manager already completed and notified. Build256's predicate
wait protects UFO rooms only; airship battles still take the indefinite wait.

Route the existing animation-wait hooks through AGBattleAwait. In room10,
and rooms14/15 when their NPC roster contains native balloon character17,
check the original completion flag before waiting and after timed wakeups.
Return only after completion or leaving/changing the arena/connection.
No elapsed-time threshold clears effects, skips projectile work, or forces
the next player turn. Other rooms retain the accepted AGTurnAwait behavior.

The accepted UFO/POW sources are unchanged. Room/area routing, projectile
damage and flight bodies are unchanged. Build256 blindness, wheel return,
camera pacing and speed10 remain included. Device acceptance is not claimed.
