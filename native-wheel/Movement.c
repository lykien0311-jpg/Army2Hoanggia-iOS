#include "Movement.h"
#include <time.h>
// Local input only. No sleeping, deferred movement, or catch-up burst.
// Native walk steps retain their original collision/stamina/network handling.
int AGMoveAllowAt(AGMoveClock *c,uintptr_t player,int direction,uint64_t now){
    if(!c||!player)return 0;
    direction=!!direction;
    if(!c->initialized||c->player!=player||c->direction!=direction||now<c->step){
        *c=(AGMoveClock){player,now,direction,1};return 1;
    }
    uint64_t elapsed=now-c->step;
    if(elapsed<50000000)return 0;
    // Retain sub-frame time so 60/120/144 Hz do not become a slower walk.
    // Discard a long pause instead of replaying missed movement steps.
    c->step=elapsed>=100000000?now:c->step+50000000;return 1;
}
__attribute__((visibility("default"))) int AGMoveAllow(int variant,void *player,int direction){
    static AGMoveClock clocks[6];
    if(variant<0||variant>=6)return 0;
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return AGMoveAllowAt(&clocks[variant],(uintptr_t)player,direction,(uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec);
}
