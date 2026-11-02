#ifndef AG_BLIND_STATE_H
#define AG_BLIND_STATE_H
#include <stdint.h>
typedef struct {uintptr_t arena;int local,valid,active;} AGBlindState;
void AGBlindReset(AGBlindState *);
int AGBlindContext(AGBlindState *,uintptr_t,int);
int AGBlindPacket(AGBlindState *,uintptr_t,int,int,int);
#endif
