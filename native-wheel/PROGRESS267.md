# Build267 — restore tier-11 gem percentage lookup by inventory identity

The user confirms 21 equipped attack gems, requiring +42% final attack. Their
Build266 equipment display shows 3,663; JAR/APK show 4,585 and combat is correct.

Root cause: the native collector incorrectly treated the long template ID at
item +0x80 as the encoded inventory handle. The actual handle is the int field
at +0xb0. All six RoboVM `j5_` descriptors and the original native equipment
selection code confirm these distinct fields. Therefore GEM1's per-inventory
gem lookup returned zero, and GEM2's selected-handle match also failed.

The one-line runtime correction reads +0xb0 as int32_t. Costume selection still
uses +0x80, exactly like the original calculator. All stat formulas, native
hooks, server, JAR/APK and combat remain unchanged. Previous emulation fixtures
incorrectly stored inventory handles in the template field; they now model
both fields independently, including multiple items sharing one template.

An independent server/Sua12-JAR fixture with 21 attack gems (+42%) returns
4,585. Build266's actual Apple ARM64 library returns 3,663 from the same packet
data and correct native layout, reproducing the exact reported pair without
injecting a desired snapshot result. The fixture uses synthetic base/points
and socket distribution; the user's complete account data was not supplied.

The expanded suite covers 0/1/3/15/21 gems, five gem families, all ten characters
and modern/legacy modes using real server config, inventory and snapshot bytes.
Final Apple build and ARM64 verification results follow in validation267.json.
No physical iPhone or live production account testing is claimed.
