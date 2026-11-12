#include "AuraState.h"
#include <string.h>

static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0]<<24 | (uint32_t)p[1]<<16 | (uint32_t)p[2]<<8 | p[3];
}
static uint64_t u64(const uint8_t *p) { return (uint64_t)u32(p)<<32 | u32(p+4); }
static size_t u16(const uint8_t *p) { return ((size_t)p[0]<<8) | p[1]; }

static size_t slot(const AGAuraState *state, uint32_t id) {
    const size_t capacity = sizeof state->global / sizeof *state->global;
    size_t at = (id * UINT32_C(2654435761)) & (capacity - 1);
    for(size_t i=0;i<capacity;i++) {
        if(!state->global[at].id || state->global[at].id==id)return at;
        at=(at+1)&(capacity-1);
    }
    return capacity;
}

int AGAuraApply(AGAuraState *state, uintptr_t connection, const uint8_t *wire, size_t size) {
    if(!connection || size<20 || memcmp(wire,"AURA",4))return 0;
    const unsigned kind=wire[4];
    const uint64_t epoch=u64(wire+5);
    const uint32_t peer=u32(wire+13);
    size_t header, stride, count;
    uint64_t sequence=0, scene=0;
    unsigned mode=0;
    if(!peer || peer>INT32_MAX)return 0;
    if(kind==1){
        header=20;stride=15;mode=wire[17];count=u16(wire+18);
        if(mode>2 || count>4096)return 0;
    }else if(kind==2 && size>=35){
        header=35;stride=7;sequence=u64(wire+17);scene=u64(wire+25);count=u16(wire+33);
        if(!sequence || sequence>INT64_MAX || scene>INT64_MAX || count>128)return 0;
    }else return 0;
    if(size!=header+count*stride)return 0;
    for(size_t i=0;i<count;i++){
        const uint8_t *row=wire+header+i*stride;
        const uint32_t id=u32(row);
        if(!id || id>INT32_MAX || row[4]>9 || row[5]>7 || row[6]>16)return 0;
        if(kind==1 && (!u64(row+7)||u64(row+7)>INT64_MAX))return 0;
    }
    const int same=connection==state->connection && epoch==state->epoch;
    if(same && peer<state->serverConnection)return 1;
    if(!same || peer!=state->serverConnection){
        if(kind==2)return 1;
        memset(state,0,sizeof *state);
        state->connection=connection;state->epoch=epoch;state->serverConnection=peer;
    }
    if(kind==2){
        if(sequence<=state->sceneSerial)return 1;
        state->sceneSerial=sequence;state->scene=scene;state->sceneCount=scene?count:0;
    }
    for(size_t i=0;i<count;i++){
        const uint8_t *row=wire+header+i*stride;
        AGAuraRow value={.id=u32(row),.hero=row[4],.tier=row[5],.level=row[6]};
        if(kind==2){state->roster[i]=value;continue;}
        value.serial=u64(row+7);
        if(mode==2){value.tier=0;value.level=0;}
        size_t at=slot(state,value.id);
        if(at<sizeof state->global / sizeof *state->global && value.serial>state->global[at].serial)
            state->global[at]=value;
    }
    return 1;
}

int AGAuraLookup(const AGAuraState *state, uint32_t id, unsigned hero, int inScene) {
    if(!id || hero>9)return 0;
    if(inScene){
        for(size_t i=0;i<state->sceneCount;i++){
            const AGAuraRow *row=&state->roster[i];
            if(row->id==id)return row->hero==hero && row->tier ? row->tier<<5 | row->level : 0;
        }
    }
    size_t at=slot(state,id);
    if(at>=sizeof state->global / sizeof *state->global)return 0;
    const AGAuraRow *row=&state->global[at];
    return row->id==id && row->hero==hero && row->tier ? row->tier<<5 | row->level : 0;
}
