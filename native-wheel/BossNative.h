#ifndef AG_BOSS_NATIVE_H
#define AG_BOSS_NATIVE_H

#include <stdint.h>

int AGBossReceive(void *env, void *message, int variant);
void AGBossTick(void *env, int variant);
int AGBossBlind(int variant);
int AGBossPaintActor(void *env, uint8_t *actor, uint8_t *graphics, int variant);

#endif
