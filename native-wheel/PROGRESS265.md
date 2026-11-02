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

Apple build completed successfully: Actions run `41544345642`, artifact
`13188850376`, Xcode 16.4 / SDK 18.5. Codesign strict verification and a second
ad-hoc signing verification both passed. The compiled library SHA256 is
`d79780407415b66f5f124b65e9f10140130b46b4b03c4a9ccc129e257c8d6e6f`.

The actual Apple ARM64 library and original native equipment calculator pass
3,000 matching/preview checks from 400 actual Sua12 server fixtures across all
six variants, plus 24 checks covering six slots including the selected costume.
The existing 186 native stats integration checks pass, including connection
isolation, malformed updates, unchanged combat inputs, stack/register ABI and
stream positions. Static camera, turn, blind, footer, clan and login checks pass.

Output: `Army2Hoanggia-2.4.1-Build265-Sua12.ipa`, 16,573,432 bytes, SHA256
`df0262cae94806bb36f55fc35b395b0b346e9890edee63192fc93177d60e9932`.
Exactly the native main, AGWheel library and Info.plist changed; the other 522
entries match the user's IPA. Version remains 2.4.1; bundle build is 265.
The native main can be restored using the new baseline-recovery entry.
See validation265.json for source hashes and build provenance.

No physical iPhone or live account testing is claimed. The user must re-sign
the IPA with their own certificate. The APK still awaits the matching Sua08
private key; the duplicate Sua11 ZIP supplied alongside the IPA has no such key.
