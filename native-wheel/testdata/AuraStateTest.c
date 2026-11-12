#include "../AuraState.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    static AGAuraState state;
    uint8_t global[]={ 'A','U','R','A',1,0,0,0,0,0,0,0,9,0,0,0,15,1,0,1,
                       0,0,0,7,6,7,16,0,0,0,0,0,0,0,11 };
    uint8_t scene[]={ 'A','U','R','A',2,0,0,0,0,0,0,0,9,0,0,0,15,
                      0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,30,0,1,0,0,0,7,6,5,12 };
    assert(AGAuraApply(&state,44,global,sizeof global));
    assert(AGAuraLookup(&state,7,6,0)==240);
    assert(!AGAuraLookup(&state,7,5,0));
    assert(!AGAuraApply(&state,44,global,sizeof global-1));
    assert(AGAuraLookup(&state,7,6,0)==240);
    assert(AGAuraApply(&state,44,scene,sizeof scene));
    assert(AGAuraLookup(&state,7,6,1)==172);
    assert(AGAuraLookup(&state,7,6,0)==240);
    scene[40]=0;scene[41]=0;
    assert(AGAuraApply(&state,44,scene,sizeof scene));
    assert(AGAuraLookup(&state,7,6,1)==172);
    scene[24]=20;
    assert(AGAuraApply(&state,44,scene,sizeof scene));
    assert(!AGAuraLookup(&state,7,6,1));
    assert(AGAuraLookup(&state,7,6,0)==240);
    global[17]=2;global[34]=12;
    assert(AGAuraApply(&state,44,global,sizeof global));
    assert(!AGAuraLookup(&state,7,6,0));
    global[17]=0;global[34]=11;
    assert(AGAuraApply(&state,44,global,sizeof global));
    assert(!AGAuraLookup(&state,7,6,0));
    global[16]=16;
    assert(AGAuraApply(&state,55,global,sizeof global));
    assert(AGAuraLookup(&state,7,6,1)==240);
    assert(!state.sceneSerial && !state.sceneCount);
    puts("PASS aura global, hero identity, scene precedence, stale frames, removal, reconnect, truncated frame");
    return 0;
}
