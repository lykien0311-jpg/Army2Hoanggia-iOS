#ifndef AG_BOSS_MAPS_H
#define AG_BOSS_MAPS_H

#include <stddef.h>
#include <stdint.h>

enum { AGDragonMap = 41, AGMimicMap = 42, AGBossSlots = 100, AGHumanSlots = 8 };
enum { AGDragonCommand = -113, AGMimicCommand = -112 };

typedef struct {
    int id, x, y;
} AGBossTile;

typedef struct {
    int width, height, count;
    AGBossTile tiles[20];
} AGBossMap;

typedef struct {
    int present, slot, element, small, main, pose, timer, mirror, duration;
    int dark, echo, form, hp, maxHP, x, y, fromX, fromY, damage;
    uint32_t sequence;
    uint64_t moveAt, poseAt, hitAt;
} AGBossActor;

typedef struct { int frozen, burn, x, y; } AGBossHuman;
typedef struct {
    int kind, duration, count, radius, x[32], y[32];
    uint64_t time;
} AGBossEffect;

typedef struct {
    uint64_t match, blindUntil;
    uint32_t sequence;
    int finished, focus;
    AGBossActor actors[AGBossSlots];
    AGBossHuman humans[AGHumanSlots];
    AGBossEffect effect;
} AGBossState;

typedef struct {
    int x, y, radius, width, height;
    const uint8_t *mask;
} AGBossHole;

typedef enum { AGBossInvalid, AGBossIgnored, AGBossSnapshot, AGBossTerrain } AGBossUpdate;

int AGBossParseMap(int map, const uint8_t *data, size_t length, AGBossMap *result);
AGBossUpdate AGBossRead(AGBossState *state, int map, const uint8_t *wire, size_t length,
                        uint64_t time, AGBossHole *hole);
void AGBossPosition(const AGBossActor *actor, uint64_t time, int *x, int *y);
int AGBossModifyTile(const AGBossHole *hole, int map, const AGBossTile *tile, int width,
                     int height, uint32_t *pixels);
int AGBossRosterAlias(uint8_t *wire, size_t length);

#endif
