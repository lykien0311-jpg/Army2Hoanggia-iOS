# Rebuild requested 30/10/2026

The user identified the initial video-28835 wheel update as the restart point, supplied Army2Hoanggia(2).ipa, and explicitly requested the previous GitHub build process. The user then supplied Army2-QuanTri-Game-Notes77(2).zip and requested that configuration OK save and return to the lobby. The supplied ZIP matches the prior Notes77 package byte for byte.

The wheel UI and Notes77 client bridge are staged for an Apple Xcode/macOS build. Configuration OK's native wrapper always invokes the original exit callback; the save request is queued separately. This revision uses the original user IPA as the recovery and resource baseline.

State: source prepared; GitHub build and Simulator results must be verified before delivery. No new IPA has yet been validated or tested on a physical iPhone. Older Linux/Zig deliverables do not establish success for this revision. Do not label this revision as a verified physical-device launch fix.

Repository: lykien0311-jpg/Army2Hoanggia-iOS
Branch: codex/army-ios-build
Workflow: .github/workflows/native-wheel.yml
