#import <Foundation/Foundation.h>
#include <mach-o/dyld.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "BossMaps.h"
#include "BossNative.h"
#include "BossNativeMap.h"
#include "NotesMap.h"
#include "TurnMap.h"
#include "Aura.h"
#include "StatsNativeMap.h"

extern int AGWheelGuard(void *, int (*)(void *, void *), void *, void *);

enum { Background, FireLarge, FireSmall, IceLarge, IceSmall, Egg, CrackedEgg, ArtCount };
enum { LoadMap, DestroyTerrain, PaintBackground, PaintEffects, MimicProjectile };

typedef struct {
    int map;
    uint8_t *arena;
    void *vanillaTiles;
    unsigned terrainVersion;
    uint8_t *tiles[20];
    AGBossMap spec;
    AGBossState fight;
} NativeFight;

typedef struct {
    int map, variant;
    void *art[ArtCount], *oldArt[ArtCount];
    void *vector;
    uint8_t *tiles[20];
    AGBossMap spec;
    const uint8_t *tileBytes[20], *artBytes[ArtCount];
    int tileLength[20], artLength[ArtCount];
} Load;

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static NativeFight fights[6];
static void *art[2][ArtCount];

static uintptr_t base(void) { return (uintptr_t)_dyld_get_image_header(0); }
static uint64_t now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000 + (uint64_t)t.tv_nsec / 1000000;
}
static int guarded(void *env, int (*fn)(void *, void *), void *job) {
    return AGWheelGuard(env, fn, job, (void *)(base() + 0x1300d54));
}
static uint8_t *globals(uintptr_t offset) { return *(uint8_t **)(base() + offset); }
static uint8_t *arena(int v) {
    uint8_t *g = globals(AGTurnMaps[v].arena_class);
    uint8_t *canvas = globals(AGNotesMaps[v].canvas);
    uint8_t *screen = g ? *(uint8_t **)(g + 0xe8) : NULL;
    return screen && canvas && *(void **)(canvas + 0xb8) == screen ? screen : NULL;
}
static uint8_t *roster(int v) {
    uint8_t *g = globals(AGTurnMaps[v].array_class);
    return g ? *(uint8_t **)(g + 0xa0) : NULL;
}
static int rosterSize(uint8_t *roster) {
    int count = roster ? *(int *)(roster + 0x10) : 0;
    return count >= AGHumanSlots && count <= 127 ? count : 0;
}
static uint8_t *actor(uint8_t *roster, int slot) { return *(uint8_t **)(roster + 0x18 + slot * 8); }
static int roomMap(int v) {
    uint8_t *room = globals(AGNotesMaps[v].room_class);
    if (!room || room[0x131] != 5) return 0;
    if (room[0x130] == 18) return AGDragonMap;
    if (room[0x130] == 19) return AGMimicMap;
    return 0;
}

static void *pin(void *env, void *object) {
    return ((void *(*)(void *, void *))(*(void ***)env)[21])(env, object);
}
static void unpin(void *env, void *object) {
    if (object) ((void (*)(void *, void *))(*(void ***)env)[22])(env, object);
}
static void *image(void *env, const uint8_t *bytes, int length) {
    void **jni = *(void ***)env;
    void *volatile array = ((void *(*)(void *, int))jni[176])(env, length);
    if (!array) return NULL;
    ((void (*)(void *, void *, int, int, const uint8_t *))jni[208])(env, array, 0, length, bytes);
    /* Image.f([BII), with the normal GDX render-thread handoff. */
    void *result = ((void *(*)(void *, void *, int, int))(base() + 0xc46e04))(env, array, 0, length);
    ((void (*)(void *, void *))jni[23])(env, array);
    return result;
}
__attribute__((noinline,optnone)) static int buildMap(void *env, void *context) {
    Load *j = context;
    uintptr_t b = base();
    const AGBossNativeMap *native = &AGBossNativeMaps[j->variant];
    void *volatile vector = ((void *(*)(void *))(b + 0xbe3f1c))(env);
    ((void (*)(void *, void *))(b + 0xbe6b7c))(env, vector);
    j->vector = pin(env, vector);
    if (!j->vector) return 0;
    for (int i = 0; i < j->spec.count; ++i) {
        const AGBossTile *spec = &j->spec.tiles[i];
        void *volatile picture = image(env, j->tileBytes[i], j->tileLength[i]);
        if (!picture) return 0;
        int width = ((int (*)(void *, void *))(b + 0x1c61b0))(env, picture);
        int height = ((int (*)(void *, void *))(b + 0x1c61a0))(env, picture);
        if (width < 1 || height < 1 || width > 2048 || height > 2048) return 0;
        uint8_t *volatile tile = ((uint8_t *(*)(void *))(b + native->tileNew))(env);
        ((void (*)(void *, void *, int64_t, int, int, void *, int))(b + native->tileInit))
            (env, tile, spec->id, spec->x, spec->y, NULL, 1);
        uint8_t *volatile pixels = ((uint8_t *(*)(void *, int))(b + 0x12e7d28))(env, width * height);
        ((void (*)(void *, void *, void *, int, int, int, int, int, int))(b + 0x1c61a4))
            (env, picture, pixels, 0, width, 0, 0, width, height);
        *(void **)(tile + 0x10) = pixels;
        *(void **)(tile + 0x18) = picture;
        *(int *)(tile + 0x28) = width;
        *(int *)(tile + 0x2c) = height;
        ((void (*)(void *, void *, void *))(b + 0x1dfcac))(env, vector, tile);
        j->tiles[i] = tile;
    }
    for (int i = 0; i < ArtCount; ++i) {
        if (!j->artLength[i]) continue;
        void *volatile picture = image(env, j->artBytes[i], j->artLength[i]);
        if (!picture || !(j->art[i] = pin(env, picture))) return 0;
    }
    return 1;
}
static NSData *asset(NSString *root, NSString *name) {
    NSString *path = [[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:root]
        stringByAppendingPathComponent:name];
    return [NSData dataWithContentsOfFile:path options:NSDataReadingMappedIfSafe error:NULL];
}
static int resetInput(void *env, void *opaque) {
    Load *j = opaque;
    ((void (*)(void *))(base() + AGBossNativeMaps[j->variant].resetInput))(env);
    return 1;
}
static int load(void *env, int v, uint8_t *owner, int map) {
    uint8_t *g = globals(AGBossNativeMaps[v].mapClass);
    if (!g || !owner) return 0;
    pthread_mutex_lock(&lock);
    NativeFight *f = &fights[v];
    if (map != AGDragonMap && map != AGMimicMap) {
        void *old = f->vanillaTiles;
        if (old) *(void **)(g + 0xb8) = old;
        memset(f, 0, sizeof *f);
        pthread_mutex_unlock(&lock);
        unpin(env, old);
        return 0;
    }
    Load j = { .map = map, .variant = v };
    memcpy(j.oldArt, art[map - AGDragonMap], sizeof j.oldArt);
    pthread_mutex_unlock(&lock);

    @autoreleasepool {
        NSString *root = map == AGDragonMap ? @"BossMaps/dragon105" : @"BossMaps/mimic111";
        NSData *definition = asset(root, [NSString stringWithFormat:@"%d.map", map]);
        if (!AGBossParseMap(map, definition.bytes, definition.length, &j.spec)) return 0;
        __attribute__((objc_precise_lifetime)) NSMutableArray<NSData *> *retained = [NSMutableArray array];
        for (int i = 0; i < j.spec.count; ++i) {
            NSData *png = asset(root, [NSString stringWithFormat:@"tile-%d.png", j.spec.tiles[i].id]);
            if (!png.length || png.length > 400000) return 0;
            [retained addObject:png];
            j.tileBytes[i] = png.bytes;
            j.tileLength[i] = (int)png.length;
        }
        NSArray<NSString *> *names = map == AGDragonMap ?
            @[@"background.png", @"fire-226.png", @"fire-100.png", @"ice-226.png",
              @"ice-100.png", @"egg-0.png", @"egg-1.png"] : @[@"background.png", @"boss.png"];
        for (NSUInteger i = 0; i < names.count; ++i) {
            if (j.oldArt[i]) continue;
            NSData *png = asset(root, names[i]);
            if (!png.length || png.length > 2000000) return 0;
            [retained addObject:png];
            j.artBytes[i] = png.bytes;
            j.artLength[i] = (int)png.length;
        }
        if (guarded(env, buildMap, &j) <= 0) {
            for (int i = 0; i < ArtCount; ++i) unpin(env, j.art[i]);
            unpin(env, j.vector);
            NSLog(@"Army2 map %d texture loading failed", map);
            return 0;
        }
    }
    pthread_mutex_lock(&lock);
    for (int i = 0; i < ArtCount; ++i) {
        if (art[map - AGDragonMap][i]) continue;
        art[map - AGDragonMap][i] = j.art[i];
        j.art[i] = NULL;
    }
    void *vanilla = f->vanillaTiles;
    pthread_mutex_unlock(&lock);
    if (!vanilla) vanilla = pin(env, *(void **)(g + 0xb8));
    if (!vanilla) {
        unpin(env, j.vector);
        for (int i = 0; i < ArtCount; ++i) unpin(env, j.art[i]);
        return 0;
    }

    pthread_mutex_lock(&lock);
    f->vanillaTiles = vanilla;
    f->map = map;
    f->arena = arena(v);
    f->spec = j.spec;
    f->terrainVersion++;
    memcpy(f->tiles, j.tiles, sizeof f->tiles);
    *(void **)(g + 0xb8) = j.vector;
    *(int *)(g + 0xd8) = j.spec.width;
    *(int *)(g + 0xdc) = j.spec.height;
    g[0xe0] = 0;
    *(int *)(owner + 0x10) = map;
    *(int *)(owner + 0x14) = 0;
    *(int *)(owner + 0x18) = 0;
    pthread_mutex_unlock(&lock);
    unpin(env, j.vector); // C5.d now owns the vector and its tiles.
    for (int i = 0; i < ArtCount; ++i) unpin(env, j.art[i]);
    guarded(env, resetInput, &j);
    return 1;
}

static int active(NativeFight *f, int v) {
    if (!f->map || f->map != roomMap(v)) return 0;
    uint8_t *current = arena(v);
    if (!current || (f->arena && f->arena != current)) return 0;
    f->arena = current;
    return f->map;
}
static void applyHole(NativeFight *f, const AGBossHole *hole) {
    for (int i = 0; i < f->spec.count; ++i) {
        uint8_t *tile = f->tiles[i];
        if (!tile) continue;
        uint8_t *pixels = *(uint8_t **)(tile + 0x10);
        int w = *(int *)(tile + 0x28), h = *(int *)(tile + 0x2c);
        if (!pixels || w <= 0 || h <= 0 || w > 2048 || h > 2048 || *(int *)(pixels + 0x10) != w * h)
            continue;
        if (AGBossModifyTile(hole, f->map, &f->spec.tiles[i], w, h, (uint32_t *)(pixels + 0x14))) {
            tile[0x39] = 1;
            f->terrainVersion++;
        }
    }
}
static void place(uint8_t *player, int x, int y) {
    *(int *)(player + 0x114) = x;
    *(int *)(player + 0x118) = y;
}
static void syncActors(NativeFight *f, int v, uint64_t time) {
    uint8_t *players = roster(v);
    int size = rosterSize(players);
    for (int i = AGHumanSlots; i < size && i < AGBossSlots; ++i) {
        const AGBossActor *a = &f->fight.actors[i];
        uint8_t *p = actor(players, i);
        if (!a->present || !p) continue;
        int x, y;
        AGBossPosition(a, time, &x, &y);
        place(p, x, y);
        *(int64_t *)(p + 0x68) = a->hp;
        *(int64_t *)(p + 0x70) = a->maxHP;
        p[0x166] = 0; // Boss movement is authored by the server.
        if (f->map == AGMimicMap && a->hp > 0 && p[0x16f] == 5) {
            p[0x16f] = 0;
            p[0x159] = 1;
        }
    }
}

int AGBossReceive(void *env, void *message, int v) {
    (void)env;
    const int command = *(int8_t *)((uint8_t *)message + 0x30);
    if (command == 20) {
        pthread_mutex_lock(&lock);
        memset(&fights[v].fight, 0, sizeof fights[v].fight);
        fights[v].arena = NULL;
        pthread_mutex_unlock(&lock);
        return 0;
    }
    int map = roomMap(v);
    if (!map || (command != AGDragonCommand && command != AGMimicCommand &&
        command != 89 && command != 93)) return 0;
    uint8_t *input = *(uint8_t **)((uint8_t *)message + 0x20);
    uint8_t *array = input ? *(uint8_t **)(input + 0x10) : NULL;
    if (!array) return 0;
    int end = *(int *)(input + 0x18), pos = *(int *)(input + 0x20);
    if (pos < 0 || end < pos || end > *(int *)(array + 0x10) || end - pos > 16405) return 0;
    uint8_t *data = array + 0x14 + pos;
    size_t length = (size_t)(end - pos);
    if (command == 89) {
        if (map == AGDragonMap) AGBossRosterAlias(data, length);
        return 0;
    }
    pthread_mutex_lock(&lock);
    NativeFight *f = &fights[v];
    if (command == 93 && length == 5 && active(f, v)) {
        int slot = data[0];
        uint8_t *players = roster(v);
        uint8_t *p = slot < rosterSize(players) ? actor(players, slot) : NULL;
        if (p && (slot < AGHumanSlots || (map == AGDragonMap && slot < AGBossSlots &&
            f->fight.actors[slot].present))) {
            place(p, (int16_t)(data[1] << 8 | data[2]), (int16_t)(data[3] << 8 | data[4]));
            p[0x166] = 0;
            pthread_mutex_unlock(&lock);
            return 1;
        }
    }
    if ((map == AGDragonMap && command == AGDragonCommand) ||
        (map == AGMimicMap && command == AGMimicCommand)) {
        AGBossHole hole;
        uint64_t time = now();
        AGBossUpdate update = AGBossRead(&f->fight, map, data, length, time, &hole);
        if (active(f, v)) {
            if (update == AGBossTerrain) applyHole(f, &hole);
            if (update == AGBossSnapshot) syncActors(f, v, time);
        }
        pthread_mutex_unlock(&lock);
        return 1;
    }
    pthread_mutex_unlock(&lock);
    return 0;
}

typedef struct {
    uintptr_t refresh;
    unsigned version;
    uint8_t *tiles[20];
} Refresh;
static int refreshTiles(void *env, void *opaque) {
    Refresh *j = opaque;
    void (*refresh)(void *, void *) = (void *)j->refresh;
    for (int i = 0; i < 20 && j->tiles[i]; ++i) refresh(env, j->tiles[i]);
    return 1;
}
void AGBossTick(void *env, int v) {
    if (!env || v < 0 || v >= 6 || !roomMap(v)) return;
    Refresh j = { .refresh = base() + AGBossNativeMaps[v].tileRefresh };
    int count = 0;
    pthread_mutex_lock(&lock);
    NativeFight *f = &fights[v];
    if (active(f, v)) {
        syncActors(f, v, now());
        j.version = f->terrainVersion;
        for (int i = 0; i < f->spec.count; ++i)
            if (f->tiles[i][0x39]) j.tiles[count++] = f->tiles[i];
    }
    pthread_mutex_unlock(&lock);
    if (!count) return;
    int drawn = guarded(env, refreshTiles, &j);
    pthread_mutex_lock(&lock);
    if (drawn <= 0 || j.version != f->terrainVersion)
        for (int i = 0; i < count; ++i)
            for (int k = 0; k < f->spec.count; ++k)
                if (j.tiles[i] == f->tiles[k]) f->tiles[k][0x39] = 1;
    pthread_mutex_unlock(&lock);
}

int AGBossBlind(int v) {
    if (v < 0 || v >= 6 || roomMap(v) != AGMimicMap) return 0;
    pthread_mutex_lock(&lock);
    NativeFight *f = &fights[v];
    int blind = 0;
    if (active(f, v) == AGMimicMap) {
        blind = now() < f->fight.blindUntil;
        for (int i = AGHumanSlots; !blind && i < AGBossSlots; ++i)
            blind = f->fight.actors[i].present && f->fight.actors[i].dark;
    }
    pthread_mutex_unlock(&lock);
    return blind;
}

typedef struct {
    uint8_t *g;
    uint8_t *mimicForm;
    void *art[ArtCount];
    int v, map;
    uint64_t time;
    AGBossActor actor;
    AGBossEffect fx;
    AGBossHuman humans[AGHumanSlots];
} Paint;

static void drawImage(void *env, Paint *p, void *image, int x, int y, int anchor) {
    if (image) ((void (*)(void *, void *, void *, int, int, int))(base() + 0x1c6144))
        (env, p->g, image, x, y, anchor);
}
static void region(void *env, Paint *p, void *image, int w, int h, int frame, int mirror, int x, int y) {
    if (image) ((void (*)(void *, void *, void *, int, int, int, int, int, int, int, int))
        (base() + 0x1c6150))(env, p->g, image, frame % 4 * w, frame / 4 * h, w, h,
                            mirror ? 2 : 0, x - w / 2, y - h, 0);
}
static void color(void *env, Paint *p, int rgb) {
    ((void (*)(void *, void *, int))(base() + 0x1c6194))(env, p->g, rgb);
}
static void fill(void *env, Paint *p, int x, int y, int w, int h) {
    ((void (*)(void *, void *, int, int, int, int))(base() + 0x1c6170))(env, p->g, x, y, w, h);
}
static void line(void *env, Paint *p, int x, int y, int x2, int y2) {
    ((void (*)(void *, void *, int, int, int, int))(base() + 0xc454e8))(env, p->g, x, y, x2, y2);
}
static void label(void *env, Paint *p, const char *text, int x, int y) {
    void **jni = *(void ***)env;
    uintptr_t b = base();
    const AGNotesNativeMap *map = &AGNotesMaps[p->v];
    void *volatile font = ((void *(*)(void *))(b + map->font_get))(env);
    void *volatile s = ((void *(*)(void *, const char *))jni[167])(env, text);
    if (s && font) ((void (*)(void *, void *, void *, void *, int, int, int))(b + map->font))
        (env, font, p->g, s, x, y, 2);
    if (s) ((void (*)(void *, void *))jni[23])(env, s);
}
static int renderActor(void *env, void *opaque) {
    Paint *p = opaque;
    AGBossActor *a = &p->actor;
    int x, y, barWidth = 40, top;
    AGBossPosition(a, p->time, &x, &y);
    if (p->map == AGDragonMap) {
        if (a->element == 0) {
            drawImage(env, p, p->art[a->pose == 4 || a->timer <= 2 ? CrackedEgg : Egg], x, y, 33);
            barWidth = 32;
            top = y - 52;
        } else {
            int w = a->small ? 100 : 226, h = a->small ? 93 : 210;
            int frame = (int)(p->time / 110 % 8);
            static const int poses[9] = {-1, 9, 10, -1, 12, -1, 9, 8, 9};
            if (poses[a->pose] >= 0) frame = poses[a->pose];
            if (a->pose == 3 && p->time / 110 % 2 == 0) frame = 11;
            int atlas = (a->element == 1 ? FireLarge : IceLarge) + a->small;
            region(env, p, p->art[atlas], w, h, frame, a->mirror, x, y);
            barWidth = a->small ? 38 : 48;
            top = y - h - 16;
        }
    } else {
        static const uintptr_t spriteDraw[6] =
            {0x5d9030, 0x6be08c, 0x7a2d50, 0x887a14, 0x96c6d8, 0xa5139c};
        void *sprite = p->mimicForm ? *(void **)(p->mimicForm + 0x48) : NULL;
        if (sprite) {
            ((void (*)(void *, void *, int, int, int, int, int, void *))(base() + spriteDraw[p->v]))
                (env, sprite, 0, x, y, *(int *)(p->mimicForm + 0xcc), 33, p->g);
        } else {
            drawImage(env, p, p->art[FireLarge], x, y, 33);
        }
        top = y - 46;
    }
    if (a->hp > 0) {
        color(env, p, 0x102020);
        fill(env, p, x - barWidth / 2 - 1, top - 1, barWidth + 2, 8);
        color(env, p, p->map == AGMimicMap ? 0xd95cec :
            (int64_t)a->hp * 3 <= a->maxHP ? 0xff0000 : 0x00ff00);
        fill(env, p, x - barWidth / 2, top, (int)((int64_t)barWidth * a->hp / a->maxHP), 6);
        char text[44];
        snprintf(text, sizeof text, "HP: %d/%d", a->hp, a->maxHP);
        label(env, p, text, x, top - 16);
    }
    if (a->damage > 0 && p->time - a->hitAt < 1300) {
        char text[24];
        snprintf(text, sizeof text, "-%d", a->damage);
        label(env, p, text, x, top - 27 - (int)((p->time - a->hitAt) / 50));
    }
    return 1;
}
int AGBossPaintActor(void *env, uint8_t *player, uint8_t *g, int v) {
    if (!roomMap(v)) return 0;
    Paint p = { .g = g, .v = v, .time = now() };
    pthread_mutex_lock(&lock);
    NativeFight *f = &fights[v];
    p.map = active(f, v);
    if (p.map) {
        uint8_t *players = roster(v);
        int size = rosterSize(players);
        for (int i = AGHumanSlots; i < size && i < AGBossSlots; ++i) {
            if (actor(players, i) != player) continue;
            p.actor = f->fight.actors[i];
            if (p.map == AGMimicMap && p.actor.present && p.actor.form >= 0)
                p.mimicForm = actor(players, p.actor.form);
            break;
        }
        memcpy(p.art, art[p.map - AGDragonMap], sizeof p.art);
    }
    pthread_mutex_unlock(&lock);
    if (!p.actor.present) return 0;
    if ((p.map == AGMimicMap && (p.actor.dark || !p.actor.hp)) ||
        (p.map == AGDragonMap && p.actor.pose == 5)) return 1;
    uint8_t colorState[16];
    memcpy(colorState, g + 0x28, sizeof colorState);
    int drawn = guarded(env, renderActor, &p) > 0;
    memcpy(g + 0x28, colorState, sizeof colorState);
    return drawn;
}

static int renderBackground(void *env, void *opaque) {
    Paint *p = opaque;
    int tx = p->g[0x50] ? *(int *)(p->g + 0x48) : 0;
    int ty = p->g[0x50] ? *(int *)(p->g + 0x4c) : 0;
    int clipX = *(int *)(p->g + 0x38) - tx, clipY = *(int *)(p->g + 0x3c) - ty;
    int width = *(int *)(p->g + 0x40), height = *(int *)(p->g + 0x44);
    if (width > 0 && height > 0) {
        color(env, p, p->map == AGDragonMap ? 0x26399b : 0x171123);
        fill(env, p, clipX, clipY, width, height);
    }
    drawImage(env, p, p->art[Background], 0, 0, 20);
    return 1;
}
static int renderEffects(void *env, void *opaque) {
    Paint *p = opaque;
    AGBossEffect *fx = &p->fx;
    if (fx->kind > 0 && fx->count >= 1 && p->time >= fx->time &&
        p->time - fx->time < (uint64_t)(p->map == AGDragonMap ? 1200 : fx->duration)) {
        int rgb = p->map == AGMimicMap ? 0xbf94ff : fx->kind >= 20 ? 0xc2faff : 0xffaa44;
        color(env, p, rgb);
        for (int i = 1; i < fx->count; ++i) {
            line(env, p, fx->x[i - 1], fx->y[i - 1], fx->x[i], fx->y[i]);
            fill(env, p, fx->x[i] - 2, fx->y[i] - 2, 5, 5);
        }
    }
    if (p->map == AGDragonMap) {
        for (int i = 0; i < AGHumanSlots; ++i) {
            AGBossHuman *person = &p->humans[i];
            if (!person->frozen && !person->burn) continue;
            int x = person->x, y = person->y - 24;
            color(env, p, person->frozen ? 0xc2faff : 0xffad49);
            line(env, p, x - 10, y + 14, x - 8, y - 8);
            line(env, p, x + 10, y + 14, x + 8, y - 8);
            label(env, p, person->frozen ? "Bang: -1 luot" : "Dot", x, y - 18);
        }
    }
    return 1;
}

__attribute__((visibility("default"))) int AGBossNativeHook(void *env, uintptr_t x1, uintptr_t x2,
    uintptr_t x3, int v, int operation) {
    (void)x3;
    if (!env || v < 0 || v >= 6) return 0;
    if (operation == LoadMap) return load(env, v, (uint8_t *)x1, (int)x2);
    if (!roomMap(v)) return 0;
    pthread_mutex_lock(&lock);
    NativeFight *f = &fights[v];
    int map = active(f, v);
    if (!map || operation == DestroyTerrain) {
        pthread_mutex_unlock(&lock);
        return map && operation == DestroyTerrain;
    }
    if (operation == MimicProjectile) {
        if (map == AGMimicMap && x1) {
            uint8_t *flight = (uint8_t *)x1;
            uint8_t *paths = *(uint8_t **)(flight + 0x10);
            int shooter = flight[0x60];
            if (paths && *(int *)(paths + 0x10) == 1 && shooter >= AGHumanSlots &&
                shooter < AGBossSlots && f->fight.actors[shooter].present) {
                // A copied multi-projectile weapon arrives as one server path.
                flight[0x5f] = 0;
            }
        }
        pthread_mutex_unlock(&lock);
        return 0;
    }
    Paint p = { .v = v, .map = map, .g = (uint8_t *)(operation == PaintEffects ? x2 : x1), .time = now() };
    memcpy(p.art, art[map - AGDragonMap], sizeof p.art);
    p.fx = f->fight.effect;
    memcpy(p.humans, f->fight.humans, sizeof p.humans);
    pthread_mutex_unlock(&lock);
    if (!p.g) return 0;
    uint8_t colors[16];
    memcpy(colors, p.g + 0x28, sizeof colors);
    guarded(env, operation == PaintEffects ? renderEffects : renderBackground, &p);
    memcpy(p.g + 0x28, colors, sizeof colors);
    return 0;
}

enum { WaitRoomAssets, WaitRoomBoss, LocalAura, RoomPlayerAura };
enum { Preview, Fire, Ice, WaitArtCount };

typedef struct {
    void *art[WaitArtCount];
    void *name;
    int width, height;
} WaitRoomArt;
typedef struct {
    WaitRoomArt *art;
    const uint8_t *png[WaitArtCount];
    int length[WaitArtCount];
    int map, width, height;
} WaitArtJob;

// Java draws the waiting room and its previews on the game render thread.
static WaitRoomArt waitRoomArt[3];

static int loadWaitArt(void *env, void *opaque) {
    WaitArtJob *job = opaque;
    WaitRoomArt result = { .width = job->width, .height = job->height };
    void **jni = *(void ***)env;
    const char *name = job->map == AGDragonMap ? "Thung Lũng Rồng" : "Đền Gương Vỡ";
    void *javaName = ((void *(*)(void *, const char *))jni[167])(env, name);
    result.name = javaName ? pin(env, javaName) : NULL;
    if (javaName) ((void (*)(void *, void *))jni[23])(env, javaName);
    for (int i = 0; i < WaitArtCount && result.name; ++i) {
        if (!job->length[i]) continue;
        void *picture = image(env, job->png[i], job->length[i]);
        if (!picture || !(result.art[i] = pin(env, picture))) break;
    }
    if (!result.name || !result.art[Preview] || !result.art[Fire] ||
        (job->map == AGDragonMap && !result.art[Ice])) {
        unpin(env, result.name);
        for (int i = 0; i < WaitArtCount; ++i) unpin(env, result.art[i]);
        return 0;
    }
    *job->art = result;
    return 1;
}

static WaitRoomArt *roomArt(void *env, int map, int width) {
    const BOOL dragon = map == AGDragonMap, large = dragon && width >= 350;
    WaitRoomArt *art = &waitRoomArt[dragon ? (large ? 1 : 0) : 2];
    if (art->name) return art;
    NSString *root = dragon ? @"BossMaps/dragon105" : @"BossMaps/mimic111";
    NSArray<NSString *> *names = dragon ?
        @[@"preview-map.png", large ? @"fire-160.png" : @"fire-100.png",
                              large ? @"ice-160.png" : @"ice-100.png"] :
        @[@"minimap.png", @"boss.png"];
    __attribute__((objc_precise_lifetime)) NSMutableArray<NSData *> *data = [NSMutableArray array];
    WaitArtJob job = { .map = map, .art = art, .width = large ? 160 : 100,
                      .height = large ? 149 : 93 };
    for (NSUInteger i = 0; i < names.count; ++i) {
        NSData *png = asset(root, names[i]);
        if (!png.length || png.length > 1024 * 1024) return NULL;
        [data addObject:png];
        job.png[i] = png.bytes;
        job.length[i] = (int)png.length;
    }
    return guarded(env, loadWaitArt, &job) > 0 ? art : NULL;
}

typedef struct {
    uint8_t *room;
    WaitRoomArt *art;
    uintptr_t namesGetter;
    int index;
} WaitPreview;

static int arrayCount(uint8_t *array) {
    return array ? *(int *)(array + 0x10) : 0;
}

static void **arrayItems(uint8_t *array) {
    return (void **)(array + 0x18);
}

static uint8_t *withPreviewEntry(void *env, uint8_t *old, void *entry, int index) {
    int count = arrayCount(old);
    if (count < 0 || count > 256) return NULL;
    if (count > index) {
        if (arrayItems(old)[index] != entry)
            ((void (*)(void *, void *, int, void *))(base() + 0x12e7f74))(env, old, index, entry);
        return old;
    }
    void **jni = *(void ***)env;
    void *example = entry;
    for (int i = 0; i < count; ++i) {
        if (arrayItems(old)[i]) { example = arrayItems(old)[i]; break; }
    }
    void *klass = ((void *(*)(void *, void *))jni[31])(env, example);
    if (!klass) return NULL;
    uint8_t *array = ((void *(*)(void *, int, void *, void *))jni[172])(env, 43, klass, NULL);
    ((void (*)(void *, void *))jni[23])(env, klass);
    if (!array) return NULL;
    if (count) memcpy(arrayItems(array), arrayItems(old), (size_t)count * sizeof(void *));
    arrayItems(array)[index] = entry;
    return array;
}

static int installWaitPreview(void *env, void *opaque) {
    WaitPreview *job = opaque;
    uint8_t **thumbs = (uint8_t **)(job->room + 0xb0);
    uint8_t *oldNames = ((void *(*)(void *))job->namesGetter)(env);
    uint8_t *names = withPreviewEntry(env, oldNames, job->art->name, job->index);
    if (!names) return 0;
    if (names != oldNames) {
        ((void (*)(void *, void *))(job->namesGetter + 0x3c))(env, names);
        ((void (*)(void *, void *))(*(void ***)env)[23])(env, names);
    }
    uint8_t *oldThumbs = *thumbs;
    uint8_t *updated = withPreviewEntry(env, oldThumbs, job->art->art[Preview], job->index);
    if (!updated) return 0;
    if (updated != oldThumbs) {
        *thumbs = updated;
        ((void (*)(void *, void *))(*(void ***)env)[23])(env, updated);
    }
    return 1;
}

typedef struct {
    Paint paint;
    WaitRoomArt *art;
    int x, y;
} WaitBoss;

static int drawWaitBoss(void *env, void *opaque) {
    WaitBoss *job = opaque;
    if (job->paint.map == AGMimicMap) {
        drawImage(env, &job->paint, job->art->art[Fire], job->x, job->y, 33);
    } else {
        const int width = job->art->width, height = job->art->height;
        const int frame = (int)(now() / 140 % 8), offset = width / 2 + 9;
        region(env, &job->paint, job->art->art[Fire], width, height, frame, 1, job->x - offset, job->y);
        region(env, &job->paint, job->art->art[Ice], width, height, frame, 0, job->x + offset, job->y);
    }
    return 1;
}

typedef void (*SpritePainter)(void *, void *, int, int, int, int, int, void *);
typedef struct { int variant; uint32_t id; } LocalAuraPlayer;

static int readLocalAuraPlayer(void *env, void *opaque) {
    LocalAuraPlayer *job = opaque;
    uint8_t *player = ((void *(*)(void *))(base() + AGStatsMaps[job->variant].player))(env);
    job->id = player ? *(uint32_t *)(player + 0xb8) : 0;
    return 1;
}

__attribute__((visibility("default"))) void AGSceneHook(void *env, void *graphics, int hero, int pose,
    int x, int y, int mode, void *costume, uintptr_t hook, uintptr_t original, uintptr_t data) {
    const int v = (int)(hook >> 4), operation = (int)(hook & 15);
    if (operation == WaitRoomAssets) {
        ((void (*)(void *, void *))original)(env, graphics);
        const int map = roomMap(v);
        if (!map || !graphics) return;
        int width = *(int *)((uint8_t *)graphics + 0x48);
        WaitRoomArt *art = roomArt(env, map, width);
        if (!art) return;
        WaitPreview job = { .room = globals(AGNotesMaps[v].room_class), .art = art,
                            .index = map == AGDragonMap ? 41 : 42, .namesGetter = data };
        guarded(env, installWaitPreview, &job);
        return;
    }
    SpritePainter paint = (SpritePainter)original;
    if (operation == WaitRoomBoss) {
        const int map = roomMap(v);
        if (map && graphics) {
            WaitRoomArt *art = roomArt(env, map, *(int *)((uint8_t *)graphics + 0x48));
            if (art) {
                WaitBoss job = { .paint = { .g = graphics, .map = map },
                                 .art = art, .x = x, .y = y };
                if (guarded(env, drawWaitBoss, &job) > 0) return;
            }
        }
        paint(env, graphics, hero, pose, x, y, mode, costume);
        return;
    }
    LocalAuraPlayer player = { .variant = v };
    if (operation == RoomPlayerAura) {
        if (data) player.id = *(uint32_t *)(data + 0xb8);
    } else if (AGAuraKnown(v)) {
        guarded(env, readLocalAuraPlayer, &player);
    }
    int aura = AGAuraPaintCode(v, player.id, (unsigned)hero, operation == RoomPlayerAura);
    if (!aura) {
        paint(env, graphics, hero, pose, x, y, mode, costume);
        return;
    }
    const int frame = AGAuraPaintFrame();
    AGAuraSpritePaint(env, graphics, x, y, aura >> 5, aura & 31, 0, frame);
    paint(env, graphics, hero, pose, x, y, mode, costume);
    AGAuraSpritePaint(env, graphics, x, y, aura >> 5, aura & 31, 1, frame);
}
