# Build250: rebuilt UFO auto controller

The user reports that the supplied Build248 enters a UFO battle without firing
and requests a new UFO auto implementation, with automatic POW, following
32828.mp4. The new controller replaces the previous Turn33 state and dispatch;
no server, JAR, APK, login, room or user-interface change is part of this work.

UfoAuto.c owns connection, turn, queued aim, dispatch claim and completion.
It consumes the same server-generated trajectories used by the reference JAR,
so aiming retains the server's target and projectile simulation. It accepts
the first turn before the native battle screen activates, tolerates repeated
turn/aim messages and gives each turn at most one completed shot. A stable
60ms native origin check replaces dependence on unrelated animation flags.
HP, current/local owner, origin, scene, captcha, dialog and wheel guards remain.
Failed Java allocation/writes release the claim for a paced retry.

The dispatcher builds command22 through the original native Message constructor,
byte writer and connected session. It preserves the native bullet mapper and
the optional release byte for bullets17/19. This replaces the old player-fire
entry and its rendering/notification dependencies. It updates the original
native firing fields after successful queueing without changing coordinates.

When native rage172 is100, queue command26/item100 before command22 and apply
the exact native POW callback fields. The verified native callback is5d9470,
the rage setter is59c14c, and Service.useItem26 is50335c in variant0. Other
variants share the layout. Inventory items are never selected. The controller
remembers a successfully queued POW if the following shot write fails.

UFO animation monitors still wait for their predicates, with a five-second
upper bound so an orphaned flag cannot permanently stop the packet dispatcher.
The normal waits on other maps remain unchanged. Diagnostics/status overlays
are absent.

Offline verification and Apple build provenance are recorded with the final
package. These checks do not establish physical-iPhone or live-VPS acceptance.
The resulting IPA requires signing with the owner's installation certificate.

## Completed verification

-125 C controller scenarios;234 Apple-compiled ARM64 packet and installed-update
cases;120 wait cases, including five-second orphaned flags without clearing
native animation state; native bullet mapping executes for all ten characters
and all six variants.
- POW26/item100 is queued before shot22 only at full rage. A shot-write exception
after POW does not repeat the successful skill request on retry. Both dispatch
entry points and repeated server messages leave each completed turn consumed.
- The identical initial animation fixture produces no shot with the supplied
248 library and the expected shot with250. This is an offline regression;
the video's actual internal bits remain unobserved.
-134 static hook/exception cases,86 update/wait/keypad ABI cases and48 V9/input
cases pass. Apple signing/re-signing, six UIKit viewports and six captcha modes
also pass. No physical-device or production-server test was performed.

Apple run41274098171 / artifact13070214264; source6256c4110e7e27a0267e9e7e304fbacba340809b;
tested merge40c6035974af0c987b25677f9aa1aea593bf5a85. Device library SHA256
2e8c7259c93067f1df74ae40d0aaac7b66deea7082cbc0a6fb0abc0251743a28.

Final IPA Army2Hoanggia-2.4.1-Build250-AutoUFO.ipa:16,563,592 bytes;
SHA256b93d85219aa402c6108bfa7ce4a24467799bf04c0e56e18088cc24071f5253fd.
Only AGWheel.dylib and Info.plist differ from the supplied248;523 entries,
including the original native executable and game resources, are unchanged.
