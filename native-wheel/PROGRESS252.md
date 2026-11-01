# Build252: capture the real iPhone UFO stall

35375.mp4 still shows no auto shot with Build251. The turn dial stays26 and a
UFO beam persists while a local aim line is visible. Video does not expose
packet receipt, native owner, animation flags, pending handoff, or a queued
shot. This build is diagnostic; no physical-device fix is claimed.

Prior ARM64 encounter fixtures executed native completion methods with
controlled terrain/JVM results. They prove ordering under those boundaries,
not the video's internal state. Do not interpret their passes as iPhone
acceptance. Do not change a wait or clear an animation flag speculatively.

Capture scalar snapshots on the network/game threads: mode/turn/aim receipt
and lengths, parsed ticket/owner/origin, current/local actor, completion
predicates, modal/captcha guards, pending/applied native turn, send success,
manual cancellation and active native wait. UIKit polls the copied scalars
without calling Java, writing packets or reading Java objects.

A temporary passive label identifies Build252 and its current blocking
condition; compact values make a short video sufficient to inspect it. A
bounded1MiB JSON-lines log is also written to Documents/AutoUFO-Build252.txt.
No passwords, chat contents, account names or socket payloads are logged.
The overlay never becomes key and passes all touches through.

The auto, native handoff and native waits retain Build251 behavior. Diagnostic
state does not grant a turn, complete an effect, or issue a shot. Actual device
observations are required before choosing the next gameplay change.
