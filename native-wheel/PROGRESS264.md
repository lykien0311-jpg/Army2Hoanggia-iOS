# Build264: equipment summary follows server character balance

37546.jpg shows HP51679 in the equipment summary while37547.jpg shows
maxHP168048 in battle. The user identifies battle as correct. Do not change
combat actors, HP packets, damage, turns, inventory use or accepted controls.

The supplied working JAR's BalanceClient494 receives command-110, marker
1379154228, ten character rules (enabled/base[5]/points[5]/attackGainPercent).
Its equipment calculator invokes apply after aggregating normal and costume
flat/percent equipment bonuses. The native IPA has neither this receiver nor
the configured formula and ends after the old hardcoded calculation.

Receive that typed configuration through the existing Notes dispatch. Keep
native equipment/costume aggregation and apply rules at its six calculator
epilogues to the five displayed totals only. Cache rules per variant and
connection. Disabled/missing configuration retains the old summary; malformed
packets cannot partially replace valid rules. Stream positions stay untouched.
The shared summary callback has its own claimed native cache slot44.

Host tests cover1000 stat calculations against the unmodified JAR running in
the JVM, plus462 malformed/truncated frames. The independent class identities
and protocol are recorded in stats-protocol-reference.json. The screenshot
does not expose its exact allocation/gear/configuration inputs; neither its
HP nor a fixed multiplier is embedded in the product. Device-library/native
integration and final IPA verification will be recorded after Apple CI.

Apple run41451158470 passed for sourced7b2af540c8a649b07e0d48749fa82bd3d59f2a2
(merge3a19f13177d07579c9dcf04507ea1c2c4ef53af1). Artifact13144233699 matches
bed30b62fc928c5bf575a9a1aac230cd66557ed2b0d5006740fb8f8e1b534f34.
The actual Apple library and installed native/controller calculators pass186
configuration/calculation calls across6variants with gear, costume and
characters0/4/9, dynamic replacement, malformed updates, disabled rules and
reconnections. All five totals match; combat/input bytes and saved registers
remain unchanged. Camera shared-cache546, blindness96, airship turns90,
UFO encounters60/long waits12 and native ABI134 cases also pass.

The IPA changes only main, device library and Info.plist;522 other archive
entries are unchanged. Native restoration round trip is verified. Accepted
auto, movement, airship and blindness C sources are unchanged. The same IPA
identity is now version15. validation264.json records hashes and limitations.
No physical iPhone or actual account validation is claimed.
