#ifndef AG_MOVEMENT_H
#define AG_MOVEMENT_H
#include <stdint.h>
#include <stddef.h>
typedef struct { uintptr_t player; uint64_t step; int direction, initialized; } AGMoveClock;
int AGMoveAllowAt(AGMoveClock *,uintptr_t,int,uint64_t);
int AGCameraAllowAt(AGMoveClock [2],uintptr_t,int,int,uint64_t);
#endif
