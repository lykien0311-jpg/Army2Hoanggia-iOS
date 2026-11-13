#include "Blind.h"
#include "Spectator.h"
#include "BossNative.h"
#include "BlindState.h"
#include "NotesMap.h"
#include "TurnMap.h"
#include <mach-o/dyld.h>
#include <pthread.h>
#include <string.h>
static AGBlindState states[6];
static pthread_mutex_t blindLock=PTHREAD_MUTEX_INITIALIZER;
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
typedef struct {uintptr_t arena;int local,width,height;} BlindContext;
static BlindContext context(int v){
    BlindContext c={0};uintptr_t b=base();
    uint8_t *g=*(uint8_t **)(b+AGTurnMaps[v].arena_class);
    uint8_t *canvas=*(uint8_t **)(b+AGNotesMaps[v].canvas);
    if(!g||!canvas)return c;
    uint8_t *arena=*(uint8_t **)(g+0xe8);
    if(!arena||*(uint8_t **)(canvas+0xb8)!=arena)return c;
    c.arena=(uintptr_t)arena;c.local=(int8_t)g[0x266];
    c.width=*(int *)(canvas+0x130);c.height=*(int *)(canvas+0x128);
    return c;
}
void AGBlindTick(int v){
    if(v<0||v>=6||!AGBlindActive(v))return;BlindContext c=context(v);
    pthread_mutex_lock(&blindLock);AGBlindContext(&states[v],c.arena,c.local);pthread_mutex_unlock(&blindLock);
}
__attribute__((visibility("default"))) int AGBlindActive(int v){
    if(v<0||v>=6||AGViewerActive(v))return 0;pthread_mutex_lock(&blindLock);int active=states[v].active;pthread_mutex_unlock(&blindLock);return active;
}
__attribute__((visibility("default"))) void AGBlindReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return;
    int cmd=*(int8_t *)((uint8_t *)message+0x30);
    if(cmd==20){pthread_mutex_lock(&blindLock);AGBlindReset(&states[v]);pthread_mutex_unlock(&blindLock);return;}
    if(cmd!=106)return;
    const uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);if(!input)return;
    const uint8_t *array=*(uint8_t **)(input+0x10);if(!array)return;
    int capacity=*(int *)(array+0x10),length=*(int *)(input+0x18),pos=*(int *)(input+0x20);
    if(capacity<0||length<0||length>capacity||pos<0||pos>length||length-pos<2)return;
    const uint8_t *wire=array+0x14+pos;BlindContext c=context(v);
    pthread_mutex_lock(&blindLock);AGBlindPacket(&states[v],c.arena,c.local,wire[0],wire[1]);pthread_mutex_unlock(&blindLock);
    // Read-only observer: native dispatcher still consumes the original bytes.
}
typedef struct {uint8_t *graphics;int width,height;} BlindPaintJob;
static int drawWhite(void *env,void *opaque){
    BlindPaintJob *j=opaque;uintptr_t b=base();void *g=j->graphics;
    void (*translate)(void *,void *,int,int)=(void *)(b+0x1c619c);
    void (*clip)(void *,void *,int,int,int,int)=(void *)(b+0x1c6190);
    void (*color)(void *,void *,int)=(void *)(b+0x1c6194);
    void (*fill)(void *,void *,int,int,int,int)=(void *)(b+0x1c6170);
    int tx=*(int *)(j->graphics+0x48),ty=*(int *)(j->graphics+0x4c);
    translate(env,g,-tx,-ty);clip(env,g,0,0,j->width,j->height);
    color(env,g,0xffffff);fill(env,g,0,0,j->width,j->height);return 1;
}
__attribute__((visibility("default"))) int AGBlindPaint(void *env,void *graphics,int v){
    if(!env||!graphics||v<0||v>=6||AGViewerActive(v))return 0;
    int bossBlind=AGBossBlind(v);
    if(!bossBlind&&!AGBlindActive(v))return 0;
    BlindContext c=context(v);
    pthread_mutex_lock(&blindLock);int active=AGBlindContext(&states[v],c.arena,c.local)&&states[v].active;pthread_mutex_unlock(&blindLock);
    active|=bossBlind;
    if(!active||c.width<32||c.width>4096||c.height<32||c.height>4096)return 0;
    // Validated native Graphics primitive layout: RGBA at28, clip at38,
    // translation at48, flags at50. Preserve color and recover all fields on
    // Java exceptions; successful painting hands an unclipped screen to HUD.
    uint8_t saved[0x2c];uint8_t *g=graphics;memcpy(saved,g+0x28,sizeof saved);
    BlindPaintJob j={g,c.width,c.height};int ok=AGWheelGuard(env,drawWhite,&j,(void *)(base()+0x1300d54));
    memcpy(g+0x28,saved,sizeof saved);
    if(ok<=0)return 0;
    int viewport[6]={0,0,c.width,c.height,0,0};memcpy(g+0x38,viewport,sizeof viewport);
    g[0x50]=0;g[0x51]=1;return 1;
}

