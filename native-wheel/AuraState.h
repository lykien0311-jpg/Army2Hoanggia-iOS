#pragma once
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint64_t serial;
    uint32_t id;
    uint8_t hero, tier, level;
} AGAuraRow;

typedef struct {
    uintptr_t connection;
    uint64_t epoch, scene, sceneSerial;
    uint32_t serverConnection;
    size_t sceneCount;
    AGAuraRow global[8192];
    AGAuraRow roster[128];
} AGAuraState;

int AGAuraApply(AGAuraState *state, uintptr_t connection, const uint8_t *wire, size_t size);
int AGAuraLookup(const AGAuraState *state, uint32_t id, unsigned hero, int inScene);
