#pragma once
#include <stdint.h>

int AGAuraKnown(int variant);
int AGAuraReceive(void *env,void *message,int variant);
void AGAuraTick(void *env,int variant,uintptr_t connection);
int AGAuraHello(void *env,int variant,uintptr_t connection);
int AGAuraRank(int variant,uintptr_t connection,uint32_t id,unsigned hero);
