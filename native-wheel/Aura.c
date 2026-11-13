#include "Aura.h"
#include "BossNative.h"
#include "AuraState.h"
#include "Spectator.h"
#include <mach-o/dyld.h>
#include <math.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static AGAuraState states[6];
static double nextHello[6];
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;

static uintptr_t base(void) { return (uintptr_t)_dyld_get_image_header(0); }
static double now(void) {
    struct timespec value;
    clock_gettime(CLOCK_MONOTONIC,&value);
    return value.tv_sec+value.tv_nsec/1e9;
}

int AGAuraKnown(int v) {
    pthread_mutex_lock(&lock);
    int known=states[v].connection!=0;
    pthread_mutex_unlock(&lock);
    return known;
}

int AGAuraReceive(void *env,void *message,int v) {
    if(*(int8_t *)((uint8_t *)message+0x30)!=-114)return 0;
    const uint8_t *in=*(uint8_t **)((uint8_t *)message+0x20);
    const uint8_t *array=in?*(uint8_t **)(in+0x10):NULL;
    if(!array)return 0;
    const int pos=*(int *)(in+0x20), end=*(int *)(in+0x18);
    if(pos<0||end<pos||end>*(int *)(array+0x10)||end-pos<20||end-pos>65535)return 0;
    const uintptr_t connection=AGViewerConnection(env,v);
    if(!connection)return 0;
    pthread_mutex_lock(&lock);
    AGAuraState *state=&states[v];
    uintptr_t old=state->connection;
    uint32_t peer=state->serverConnection;
    uint64_t epoch=state->epoch;
    int accepted=AGAuraApply(state,connection,array+0x14+pos,(size_t)(end-pos));
    if(old!=state->connection||peer!=state->serverConnection||epoch!=state->epoch)nextHello[v]=0;
    pthread_mutex_unlock(&lock);
    return accepted;
}

void AGAuraTick(void *env,int v,uintptr_t connection) {
    double time=now();
    pthread_mutex_lock(&lock);
    AGAuraState *state=&states[v];
    if(state->connection && state->connection!=connection){
        memset(state,0,sizeof *state);
        nextHello[v]=0;
    }
    int hello=state->serverConnection&&!state->sceneSerial&&time>=nextHello[v];
    if(hello)nextHello[v]=time+1.5;
    pthread_mutex_unlock(&lock);
    if(hello)AGAuraHello(env,v,connection);
}

int AGAuraRank(int v,uintptr_t connection,uint32_t id,unsigned hero) {
    pthread_mutex_lock(&lock);
    const AGAuraState *state=&states[v];
    int aura=state->connection==connection?AGAuraLookup(state,id,hero,0):0;
    pthread_mutex_unlock(&lock);
    return aura;
}

int AGAuraPaintCode(int v,uint32_t id,unsigned hero,int inScene) {
    if(v<0||v>=6||!id||id>INT32_MAX||hero>=10)return 0;
    pthread_mutex_lock(&lock);
    int aura=AGAuraLookup(&states[v],id,hero,inScene);
    pthread_mutex_unlock(&lock);
    return aura;
}

int AGAuraPaintFrame(void) {
    return (int)((uint64_t)(now()/0.042)&63);
}

typedef void (*Painter)(void *,void *,void *);
__attribute__((visibility("default"))) void AGAuraPaintActor(void *env,uint8_t *actor,uint8_t *graphics,int v,Painter nativePaint) {
    if(AGBossPaintActor(env,actor,graphics,v))return;
    const uint32_t id=*(uint32_t *)(actor+0x7c);
    const unsigned hero=actor[0x16c];
    int aura=0;
    if(actor[0x159] && *(int64_t *)(actor+0x68)>0)
        aura=AGAuraPaintCode(v,id,hero,1);
    if(!aura){nativePaint(env,actor,graphics);return;}
    const int x=*(int *)(actor+0x114),y=*(int *)(actor+0x118);
    const int frame=AGAuraPaintFrame();
    AGAuraSpritePaint(env,graphics,x,y,aura>>5,aura&31,0,frame);
    nativePaint(env,actor,graphics);
    AGAuraSpritePaint(env,graphics,x,y,aura>>5,aura&31,1,frame);
}
