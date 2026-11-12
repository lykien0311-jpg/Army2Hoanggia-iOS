#import <Foundation/Foundation.h>
#include <mach-o/dyld.h>
#include <stdatomic.h>
#include <stdint.h>
#include "BossNativeMap.h"

extern int AGBossNativeHook(void *, uintptr_t, uintptr_t, uintptr_t, int, int);
extern int AGWheelGuard(void *, int (*)(void *, void *), void *, void *);
static const uintptr_t tileVector[6] = {0x4f6b4c,0x5e5544,0x6ca208,0x7aeecc,0x893b90,0x978854};
static const uintptr_t collide[6] = {0x4f72a8,0x5e5ca0,0x6ca964,0x7af628,0x8942ec,0x978fb0};
static const uintptr_t loadSite[6] = {0x51a07c,0x607ac4,0x6ec788,0x7d144c,0x8b6110,0x99add4};
static atomic_flag started = ATOMIC_FLAG_INIT;

static void loadViaBridge(void *env, uint64_t *owner, int map, int v, uintptr_t b) {
    uintptr_t site = b + loadSite[v];
    uint32_t word = *(uint32_t *)site;
    int32_t delta = (int32_t)((word & 0x03ffffffU) << 6) >> 4;
    ((void (*)(void *, void *, int))(site + delta))(env, owner, map);
}

typedef struct { int variant, stage, dragonCount, mimicCount, dragonPixels, mimicPixels, restored; } Result;

static int test(void *env, void *context) {
    Result *r = context;
    int v = r->variant;
    uintptr_t b = (uintptr_t)_dyld_get_image_header(0);
    void *(*vector)(void *) = (void *)(b + tileVector[v]);
    int (*count)(void *, void *) = (void *)(b + 0x1dfce8);
    int (*pixel)(void *, int, int) = (void *)(b + collide[v]);
    NSLog(@"AGMAP enter variant=%d main=%d", v, NSThread.isMainThread);
    void *original = vector(env);
    NSLog(@"AGMAP original vector initialized");
    uint64_t dummy[4] = {0};
    r->stage = 1;
    loadViaBridge(env, dummy, 41, v, b);
    if (((int *)dummy)[4] != 41) return 0;
    NSLog(@"AGMAP map 41 loaded");
    r->stage = 2;
    r->dragonCount = count(env, vector(env));
    r->dragonPixels = pixel(env, 143, 303) && !pixel(env, 138, 301);
    r->stage = 3;
    if (r->dragonCount != 20 || !r->dragonPixels) return 0;
    uint8_t *(*at)(void *, void *, int) = (void *)(b + 0x1dfcb8);
    uint8_t *tile = at(env, vector(env), 0);
    uint8_t *pixels = *(uint8_t **)(tile + 0x10);
    *(uint32_t *)(pixels + 0x14 + 27 * 4) = 0;
    tile[0x39] = 1;
    ((void (*)(void *, void *))(b + AGBossNativeMaps[v].tileRefresh))(env, tile);
    r->dragonPixels = r->dragonPixels && !tile[0x39] && !pixel(env, 143, 303);
    loadViaBridge(env, dummy, 42, v, b);
    if (((int *)dummy)[4] != 42) return 0;
    r->stage = 4;
    r->mimicCount = count(env, vector(env));
    r->mimicPixels = pixel(env, 57, 165) && !pixel(env, 52, 163);
    AGBossNativeHook(env, (uintptr_t)dummy, 0, 0, v, 0);
    r->restored = vector(env) == original;
    r->stage = 5;
    return r->dragonCount == 20 && r->mimicCount == 10 && r->dragonPixels && r->mimicPixels && r->restored;
}

void AGBossNativeProbe(void *env, int v) {
    if (!env || v < 0 || v >= 6 || atomic_flag_test_and_set(&started)) return;
    @autoreleasepool {
        uintptr_t b = (uintptr_t)_dyld_get_image_header(0);
        Result r = {.variant = v};
        NSURL *file = [[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory
              inDomains:NSUserDomainMask].firstObject URLByAppendingPathComponent:@"map-native-probe.txt"];
        [@"START\n" writeToURL:file atomically:YES encoding:NSUTF8StringEncoding error:NULL];
        int ok = AGWheelGuard(env, test, &r, (void *)(b + 0x1300d54));
        NSString *report = [NSString stringWithFormat:@"%@ variant=%d stage=%d dragon=%d/%d mimic=%d/%d restored=%d\n",
            ok == 1 ? @"PASS" : @"FAIL", v, r.stage, r.dragonCount, r.dragonPixels,
            r.mimicCount, r.mimicPixels, r.restored];
        [report writeToURL:file atomically:YES encoding:NSUTF8StringEncoding error:NULL];
    }
}
