#include "BossMaps.h"
#include <string.h>

static unsigned u16(const uint8_t *p) { return (unsigned)p[0] << 8 | p[1]; }
static int s16(const uint8_t *p) { return (int16_t)u16(p); }
static uint32_t u32(const uint8_t *p) { return (uint32_t)u16(p) << 16 | u16(p + 2); }
static uint64_t u64(const uint8_t *p) { return (uint64_t)u32(p) << 32 | u32(p + 4); }
static int min(int a, int b) { return a < b ? a : b; }
static int max(int a, int b) { return a > b ? a : b; }

int AGBossParseMap(int map, const uint8_t *data, size_t length, AGBossMap *result) {
    int dragon = map == AGDragonMap;
    int count = dragon ? 20 : 10;
    int width = dragon ? 1120 : 960;
    int height = dragon ? 840 : 560;
    if ((map != AGDragonMap && map != AGMimicMap) || !data || !result ||
        length != (size_t)(6 + count * 5 + 8 * 4) || data[4] != count ||
        u16(data) != (unsigned)width || u16(data + 2) != (unsigned)height ||
        data[5 + count * 5] != AGHumanSlots) return 0;
    AGBossMap spec = { .width = width, .height = height, .count = count };
    for (int i = 0; i < count; ++i) {
        const uint8_t *row = data + 5 + i * 5;
        int id = !dragon && i == 9 ? 102 : 90 + i;
        int x = s16(row + 1), y = s16(row + 3);
        if (row[0] != id || x < 0 || x >= width || y < 0 || y >= height) return 0;
        spec.tiles[i] = (AGBossTile){ id, x, y };
    }
    *result = spec;
    return 1;
}

void AGBossPosition(const AGBossActor *a, uint64_t time, int *x, int *y) {
    uint64_t elapsed = time >= a->moveAt ? time - a->moveAt : 0;
    if (a->duration <= 0 || elapsed >= (uint64_t)a->duration) {
        *x = a->x;
        *y = a->y;
        return;
    }
    *x = a->fromX + (a->x - a->fromX) * (int)elapsed / a->duration;
    *y = a->fromY + (a->y - a->fromY) * (int)elapsed / a->duration;
}

static AGBossUpdate dragon(AGBossState *state, uint64_t match, const uint8_t *p,
                           size_t n, uint64_t time) {
    if (n < 69) return AGBossInvalid;
    uint32_t sequence = u32(p);
    int finished = p[8], count = p[9];
    size_t end = 10 + (size_t)count * 24 + AGHumanSlots * 6;
    if (count > AGBossSlots - AGHumanSlots || (n != end + 11 && n != end + 12) ||
        !sequence || u32(p + 4) > INT32_MAX || finished > 1) return AGBossInvalid;
    if (match < state->match || (match == state->match &&
        (state->finished || sequence <= state->sequence))) return AGBossIgnored;

    AGBossState next = { .match = match, .sequence = sequence, .finished = finished, .focus = -1 };
    for (int i = 0; i < count; ++i) {
        const uint8_t *row = p + 10 + 24 * i;
        int slot = row[0];
        uint32_t hp = u32(row + 4), cap = u32(row + 8), timer = u32(row + 17);
        if (slot < AGHumanSlots || slot >= AGBossSlots || next.actors[slot].present ||
            row[1] > 2 || row[2] > 1 || row[3] > 1 || hp > cap || !cap || cap > INT32_MAX ||
            row[16] > 8 || timer > INT32_MAX || row[21] > 1 || u16(row + 22) > 1600)
            return AGBossInvalid;
        AGBossActor *a = &next.actors[slot];
        *a = (AGBossActor){ .present = 1, .slot = slot, .element = row[1], .small = row[2],
            .main = row[3], .hp = (int)hp, .maxHP = (int)cap, .x = s16(row + 12),
            .y = s16(row + 14), .pose = row[16], .timer = (int)timer, .mirror = row[21],
            .duration = (int)u16(row + 22), .poseAt = time, .moveAt = time };
        a->fromX = a->x;
        a->fromY = a->y;
        const AGBossActor *old = &state->actors[slot];
        if (match != state->match || !old->present || old->element != a->element) continue;
        if (old->pose == a->pose) a->poseAt = old->poseAt;
        a->hitAt = old->hitAt;
        a->damage = old->damage;
        if (old->hp > a->hp && old->maxHP == a->maxHP) {
            a->hitAt = time;
            a->damage = old->hp - a->hp;
        }
        if (a->x == old->x && a->y == old->y && a->duration) {
            a->fromX = old->fromX;
            a->fromY = old->fromY;
            a->duration = old->duration;
            a->moveAt = old->moveAt;
        } else {
            AGBossPosition(old, time, &a->fromX, &a->fromY);
        }
    }
    const uint8_t *humans = p + 10 + (size_t)count * 24;
    for (int i = 0; i < AGHumanSlots; ++i) {
        const uint8_t *row = humans + 6 * i;
        if (row[0] > 1 || row[1] > 3) return AGBossInvalid;
        next.humans[i] = (AGBossHuman){ row[0], row[1], s16(row + 2), s16(row + 4) };
    }
    const uint8_t *fx = p + end;
    int kind = (int8_t)fx[0], focus = n == end + 12 ? (int8_t)fx[11] : -1;
    if ((kind != -1 && (kind < 10 || kind > 23)) || u16(fx + 9) > 120 ||
        (focus != -1 && (focus < AGHumanSlots || focus >= AGBossSlots ||
        !next.actors[focus].present))) return AGBossInvalid;
    next.focus = focus;
    next.effect = (AGBossEffect){ .kind = kind, .count = 2, .radius = (int)u16(fx + 9),
        .x = {s16(fx + 1), s16(fx + 5)}, .y = {s16(fx + 3), s16(fx + 7)}, .time = time };
    AGBossEffect *previous = &state->effect;
    if (match == state->match && kind == previous->kind && next.effect.x[0] == previous->x[0] &&
        next.effect.x[1] == previous->x[1] && next.effect.y[0] == previous->y[0] &&
        next.effect.y[1] == previous->y[1]) next.effect.time = previous->time;
    if (finished) {
        memset(next.actors, 0, sizeof next.actors);
        memset(next.humans, 0, sizeof next.humans);
        next.effect.kind = -1;
        next.focus = -1;
    }
    *state = next;
    return AGBossSnapshot;
}

static AGBossUpdate mimic(AGBossState *state, uint64_t match, const uint8_t *p,
                          size_t n, uint64_t time) {
    if (n != 25) return AGBossInvalid;
    int slot = p[4], echo = p[5], form = (int8_t)p[6];
    uint32_t sequence = u32(p), hp = u32(p + 9), cap = u32(p + 13);
    if (!sequence || slot < AGHumanSlots || echo != slot + 1 || echo >= AGBossSlots ||
        form < -1 || form >= AGHumanSlots || p[7] > 1 || p[8] > 1 ||
        hp > cap || !cap || cap > INT32_MAX) return AGBossInvalid;
    if (match < state->match || (match == state->match &&
        (state->finished || sequence <= state->actors[slot].sequence))) return AGBossIgnored;
    if (match != state->match) *state = (AGBossState){ .match = match };
    AGBossActor *a = &state->actors[slot];
    if (p[7] && !a->dark) state->blindUntil = time + 1150;
    int damage = a->present && a->hp > (int)hp ? a->hp - (int)hp : 0;
    *a = (AGBossActor){ .present = 1, .slot = slot, .form = form, .dark = p[7],
        .hp = (int)hp, .maxHP = (int)cap, .x = s16(p + 17), .y = s16(p + 19),
        .sequence = sequence, .hitAt = time, .damage = damage };
    state->actors[echo] = (AGBossActor){ .present = 1, .slot = echo, .form = form,
        .dark = p[7], .echo = 1, .hp = p[8] ? (int)hp : 0, .maxHP = (int)cap,
        .x = s16(p + 21), .y = s16(p + 23), .sequence = sequence };
    return AGBossSnapshot;
}

AGBossUpdate AGBossRead(AGBossState *state, int map, const uint8_t *wire, size_t length,
                        uint64_t time, AGBossHole *hole) {
    int isDragon = map == AGDragonMap;
    if (!state || !wire || !hole || length < 13 || (!isDragon && map != AGMimicMap) ||
        u32(wire) != (isDragon ? 1146242894U : 1296649521U)) return AGBossInvalid;
    uint64_t match = u64(wire + 5);
    if (!match || match > INT64_MAX) return AGBossInvalid;
    const uint8_t *p = wire + 13;
    size_t n = length - 13;
    int mode = wire[4];
    if (mode == 1) return isDragon ? dragon(state, match, p, n, time) : mimic(state, match, p, n, time);
    if (state->match != match || state->finished) return AGBossIgnored;
    if (!isDragon && mode == 0 && n == 0) {
        *state = (AGBossState){ .match = match, .finished = 1, .focus = -1 };
        return AGBossSnapshot;
    }
    if (isDragon && mode == 2 && n == 6 && u16(p + 4) <= 120) {
        *hole = (AGBossHole){ .x = s16(p), .y = s16(p + 2), .radius = (int)u16(p + 4) };
        return AGBossTerrain;
    }
    if (mode == 3 && n >= 8) {
        unsigned width = u16(p + 4), height = u16(p + 6);
        if (!width || !height || width > 128 || height > 128 || n != 8 + width * height)
            return AGBossInvalid;
        for (size_t i = 8; i < n; ++i) if (p[i] > 2) return AGBossInvalid;
        *hole = (AGBossHole){ .x = s16(p), .y = s16(p + 2), .width = (int)width,
            .height = (int)height, .mask = p + 8 };
        return AGBossTerrain;
    }
    if (!isDragon && mode == 2 && n >= 4) {
        int kind = p[0], duration = (int)u16(p + 1), count = p[3];
        if (kind < 1 || kind > 5 || duration < 1 || duration > 1500 ||
            count < (kind == 5 ? 1 : 2) || count > 32 || n != (size_t)(4 + 4 * count))
            return AGBossInvalid;
        AGBossEffect effect = { .kind = kind, .duration = duration, .count = count,
            .time = kind == 5 && state->blindUntil > time ? state->blindUntil : time };
        for (int i = 0; i < count; ++i) {
            effect.x[i] = s16(p + 4 + i * 4);
            effect.y[i] = s16(p + 6 + i * 4);
        }
        state->effect = effect;
        return AGBossSnapshot;
    }
    return AGBossInvalid;
}

int AGBossModifyTile(const AGBossHole *h, int map, const AGBossTile *t, int width,
                     int height, uint32_t *pixels) {
    if (!h || !t || !pixels || width < 1 || height < 1 || width > 2048 || height > 2048 ||
        (map == AGMimicMap && t->id == 102)) return 0;
    int left = h->x - (h->mask ? h->width / 2 : h->radius);
    int top = h->y - (h->mask ? h->height / 2 : h->radius);
    int right = left + (h->mask ? h->width : 2 * h->radius + 1);
    int bottom = top + (h->mask ? h->height : 2 * h->radius + 1);
    int changed = 0;
    for (int y = max(top, t->y); y < min(bottom, t->y + height); ++y) {
        for (int x = max(left, t->x); x < min(right, t->x + width); ++x) {
            int dx = x - h->x, dy = y - h->y;
            unsigned mode = h->mask ? h->mask[(y - top) * h->width + x - left] :
                (dx * dx + dy * dy <= h->radius * h->radius);
            uint32_t *pixel = &pixels[(y - t->y) * width + x - t->x];
            uint32_t after = mode == 1 ? 0 : mode == 2 && (*pixel >> 24) ? 0xff000000U : *pixel;
            changed |= *pixel != after;
            *pixel = after;
        }
    }
    return changed;
}

int AGBossRosterAlias(uint8_t *wire, size_t length) {
    if (!wire || length < 20 || wire[0] != 1 || u32(wire + 1) != UINT32_MAX) return 0;
    size_t form = 15 + u16(wire + 5);
    if (length != form + 5 || wire[form] < 27 || wire[form] > 29) return 0;
    wire[form] = 25;
    return 1;
}
