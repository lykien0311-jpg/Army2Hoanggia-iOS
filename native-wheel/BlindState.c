#include "BlindState.h"
void AGBlindReset(AGBlindState *s){if(s)*s=(AGBlindState){0};}
int AGBlindContext(AGBlindState *s,uintptr_t arena,int local){
    if(!s)return 0;
    if(!arena||local<0||local>=8){AGBlindReset(s);return 0;}
    if(!s->valid||s->arena!=arena||s->local!=local)
        *s=(AGBlindState){.arena=arena,.local=local,.valid=1};
    return 1;
}
// Command106 wire order is [state,target], unlike the Java helper's
// (target,state,local) arguments. State0 applies; state1 removes blindness.
int AGBlindPacket(AGBlindState *s,uintptr_t arena,int local,int state,int target){
    if(!AGBlindContext(s,arena,local)||target!=local||(state!=0&&state!=1))return 0;
    s->active=state==0;return 1;
}
