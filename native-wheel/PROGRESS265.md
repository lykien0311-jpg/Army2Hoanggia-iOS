# Build265 — Sua12 equipment display

Input: the user's unchanged Build264 IPA, SHA256
`feb2fe694bd2240c4804bce46f443403693223fcade11e35c661aa6f3ad8f9cf`.

The native summary now accepts the GEM1 trailer after the existing 455-byte
Balance494 configuration, and the new GEM2 snapshot on command -124 from
Sua12's Display89. A snapshot applies only when character, assigned points,
raw flat and percentage totals, and the multiset of equipped inventory handles
match. Unsaved previews use the same two-stage gem arithmetic as Sua12's JAR.
Five regular equipment slots plus the original calculator's selected costume
contribute their GEM1 percentages. No combat data is written.

The existing summary hook passes its already-resolved costume pointer in x6.
The original aggregation, native method frames, stream positions, all existing
gameplay hooks, movement cadence, camera, IPs and login marker are preserved.
The cache stays isolated by native variant and connection; malformed packets
do not partially replace accepted state. A new valid -110 clears GEM2 state.

Host validation: 1,000 prefix-only cases and 1,000 GEM1 cases match the Sua12
JAR, including all ten characters, all five gem families, 0/1/3/15 gems, and
modern/legacy modes. 682 malformed packets are rejected atomically. The 134
existing static ARM64 hook/ABI checks pass against the rebuilt native main.

The installable library must come from the macOS/Xcode workflow and pass Apple
codesign verification. Device-emulation and packaging results are recorded
after that build. No physical iPhone or live account testing is claimed.
