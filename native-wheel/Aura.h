#pragma once
#include <stdint.h>

int AGAuraKnown(int variant);
int AGAuraReceive(void *env,void *message,int variant);
void AGAuraTick(void *env,int variant,uintptr_t connection);
int AGAuraHello(void *env,int variant,uintptr_t connection);
int AGAuraRank(int variant,uintptr_t connection,uint32_t id,unsigned hero);
int AGAuraPaintCode(int variant,uint32_t id,unsigned hero,int inScene);
int AGAuraPaintFrame(void);
int AGAuraSpritePaint(void *env,void *graphics,int x,int y,int tier,int level,int layer,int frame);
