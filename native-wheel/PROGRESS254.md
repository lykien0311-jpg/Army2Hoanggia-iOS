# Build254: rebuilt shot session with the verified native roster fix

User requests replacing auto UFO: chat auto enables server-driven start/restart, each authoritative human turn fires once, no inventory items, POW at full rage, all ten characters and both force values for Apache/Chicky.

Replace UfoAuto.c shot-session implementation, retain its exported ABI and the corrected253 native bridge. The100-slot roster defect and synchronous initial NPC handoff discovered in253 must not regress. Keep native effect completion and owner checks; do not force a turn on elapsed time. The earlier proposal to remove the native handoff bridge was abandoned before publication after the253 native capacity evidence became available.

Remove production diagnostic window and logging timer. Existing wheel/room/area repairs remain. Use server Auto31/Aim31 trajectories, including separate release force for bullets17/19. Aim31 simulates actual projectiles; Chicky gives its highest score to primary plus egg damage but can fall back to a single hit when no double hit is found. Do not claim every shot hits both: no live collision evidence is available and impossible trajectories exist.

Normal shots22 and POW26/token100 are the only auto combat messages. Server already owns chat auto and restart; no server update is shipped. Existing server trajectories are used unchanged. Offline packet tests are not physical-iPhone or live-VPS acceptance.
