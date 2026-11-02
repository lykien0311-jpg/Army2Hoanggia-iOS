# Build257: shot and falling-part completion waits in airship battles

In 36819.mp4 the native menus remain responsive after the airship/B52 action,
while battle progress stalls. The controller's original shot tail fires the
actor, acquires its monitor, then calls Object.wait without rechecking whether
the projectile manager already completed and notified. Build256's predicate
wait protects UFO rooms only; airship battles still take the indefinite wait.
The user also reported a normal shot stalling when one airship part falls.
The native part-death body submits four particle effects and sets canvas13c;
its frame counter clears13c after20 updates. Its controller waits have the
same missed-completion window, so this change covers those waits as well.

Route the existing animation-wait hooks through AGBattleAwait. In room10,
and rooms14/15 when their NPC roster contains native balloon character17,
check the original completion flag before waiting and after timed wakeups.
Return only after completion or leaving/changing the arena/connection.
No elapsed-time threshold clears effects, skips projectile work, or forces
the next player turn. Other rooms retain the accepted AGTurnAwait behavior.

The accepted UFO/POW sources are unchanged. Room/area routing, projectile
damage and flight bodies are unchanged. Build256 blindness, wheel return,
camera pacing and speed10 remain included. Device acceptance is not claimed.

Validation: the Apple ARM64 library and installed native waits pass390 cases
across all six variants, standalone room10 and linked rooms14/15, with roster
capacities9,100,127. In18 projectile and18 part-effect replays, original
native completion runs before the controller wait: the previous bridge still
calls indefinite Object.wait, and the installed bridge returns immediately.
The part replay executes its original four particle submissions and20-frame
completion counter. Busy flags survive79 spurious wakes, while leaving the
arena or changing connection releases the wait without clearing any flag.
UFO native encounters, blindness/HUD, wheel return and camera/speed regression
checks pass. These are controlled ARM64 replays, not live server or iPhone
acceptance, and do not establish the device stack state in the supplied video.
