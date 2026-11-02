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
