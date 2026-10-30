// Port of the server's Turn33 protocol to the six guarded RoboVM variants.
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <pthread.h>
#include <mach-o/dyld.h>
#include "Turn33.h"
#include "TurnMap.h"
#include "NativeMap.h"
#include "NotesMap.h"
extern int AGNotesBlocksAuto(int);
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {
    uintptr_t connection,arena;
    uint64_t ticket,generation;
    int enabled,used,pending,valid,turn,owner,angle,force,release,x,y;
} Turn;
static Turn turns[6];
static pthread_mutex_t turnMutex=PTHREAD_MUTEX_INITIALIZER;
static uint32_t be32(const uint8_t *b){return (uint32_t)b[0]<<24|(uint32_t)b[1]<<16|(uint32_t)b[2]<<8|b[3];}
static uint64_t be64(const uint8_t *b){return (uint64_t)be32(b)<<32|be32(b+4);}
static int short16(const uint8_t *b){return (int16_t)((b[0]<<8)|b[1]);}
static void invalidate(Turn *t){t->valid=t->pending=t->used=0;t->arena=t->ticket=0;t->owner=-1;t->generation++;}
typedef struct {int v;uintptr_t connection;uint8_t *arena,*canvas,*globals,*players,*playerGlobals;int local;} Context;
static int context(void *env,void *opaque){
    Context *c=opaque;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    void *(*get)(void *)=(void *)(base+AGMaps[c->v].service);uint8_t *volatile service=get(env);
    if(!service)return 0;c->connection=*(uintptr_t *)(service+0x10);if(!c->connection)return 0;
    c->globals=*(uint8_t **)(base+AGTurnMaps[c->v].arena_class);
    c->canvas=*(uint8_t **)(base+AGNotesMaps[c->v].canvas);
    c->playerGlobals=*(uint8_t **)(base+AGTurnMaps[c->v].player_class);
    uint8_t *g=*(uint8_t **)(base+AGTurnMaps[c->v].array_class);
    c->players=g?*(uint8_t **)(g+0xa0):NULL;c->local=g?(int8_t)g[0xd0]:-1;
    c->arena=c->globals?*(uint8_t **)(c->globals+0xe8):NULL;
    return 1;
}
static int getContext(void *env,Context *c){return AGWheelGuard(env,context,c,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));}
static int active(const Context *c){return c->arena&&c->canvas&&*(void **)(c->canvas+0xb8)==c->arena;}
__attribute__((visibility("default"))) void AGTurnReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return;
    int cmd=*(int8_t *)((uint8_t *)message+0x30);
    if(cmd!=-115&&cmd!=24&&cmd!=20)return;
    uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);if(!input)return;
    uint8_t *a=*(uint8_t **)(input+0x10);if(!a)return;
    int capacity=*(int *)(a+0x10),count=*(int *)(input+0x18),pos=*(int *)(input+0x20);
    if(capacity<0||count<0||count>capacity||pos<0||pos>count)return;
    const uint8_t *b=a+0x14+pos;size_t n=(size_t)(count-pos);
    Context c={.v=v};int ok=getContext(env,&c);
    pthread_mutex_lock(&turnMutex);Turn *t=&turns[v];
    if(ok<=0||!c.connection||t->connection!=c.connection){memset(t,0,sizeof *t);t->connection=ok>0?c.connection:0;invalidate(t);}
    if(ok<=0){pthread_mutex_unlock(&turnMutex);return;}
    if(cmd==20){invalidate(t);}
    else if(cmd==24){
        invalidate(t);
        // This trailer is emitted only for UFO by Auto31.announce. Never infer
        // map identity from a display title or accept an unticketed turn.
        if(n==17&&be32(b+1)==1429485652U&&b[0]<8&&active(&c)){
            t->valid=1;t->owner=b[0];t->turn=(int32_t)be32(b+5);t->ticket=be64(b+9);t->arena=(uintptr_t)c.arena;
        }
    }else if(n==4){
        uint32_t mode=be32(b);if((mode&~1U)==0x55464f00U){t->enabled=mode&1U;if(!t->enabled)t->pending=0;}
    }else if(n==21&&t->enabled&&t->valid&&!t->used&&active(&c)&&t->arena==(uintptr_t)c.arena&&c.globals){
        unsigned angle=(b[13]<<8)|b[14];
        if((int32_t)be32(b)==t->turn&&b[4]==t->owner&&be64(b+5)==t->ticket&&b[4]==c.globals[0x266]&&b[4]==c.local&&angle<360&&b[15]>=1&&b[15]<=30&&b[16]<=30){
            t->angle=angle;t->force=b[15];t->release=b[16];t->x=short16(b+17);t->y=short16(b+19);t->pending=1;
        }
    }
    pthread_mutex_unlock(&turnMutex);
}
__attribute__((visibility("default"))) void AGTurnManual(int v){
    if(v<0||v>=6)return;pthread_mutex_lock(&turnMutex);turns[v].used=1;turns[v].pending=0;pthread_mutex_unlock(&turnMutex);
}
typedef struct {int v;uint8_t *player;int angle,force,release;} Shot;
static int shoot(void *env,void *opaque){
    Shot *s=opaque;uint8_t *volatile p=s->player;
    *(int *)(p+0xa4)=s->angle;p[0x16d]=(uint8_t)s->force;p[0x16e]=(uint8_t)s->release;*(int *)(p+0x134)=0;
    void (*fire)(void *,void *)=(void *)((uintptr_t)_dyld_get_image_header(0)+AGTurnMaps[s->v].fire);
    fire(env,p);return 1;
}
void AGTurnTick(void *env,int v){
    if(!env||v<0||v>=6)return;
    pthread_mutex_lock(&turnMutex);Turn copy=turns[v];pthread_mutex_unlock(&turnMutex);
    if(!copy.enabled||!copy.pending||!copy.valid||copy.used)return;
    Context c={.v=v};int ok=getContext(env,&c);
    if(ok<=0||c.connection!=copy.connection||!active(&c)||(uintptr_t)c.arena!=copy.arena){
        pthread_mutex_lock(&turnMutex);if(turns[v].generation==copy.generation){invalidate(&turns[v]);if(c.connection!=copy.connection)turns[v].enabled=0;}pthread_mutex_unlock(&turnMutex);return;
    }
    if(!c.globals||!c.playerGlobals||!c.players||AGNotesBlocksAuto(v)||*(void **)(c.canvas+0x108)||c.globals[0x266]!=copy.owner||c.local!=copy.owner||c.playerGlobals[0x1a7]||c.playerGlobals[0x1a8])return;
    int count=*(int *)(c.players+0x10);if(count<1||count>64||copy.owner<0||copy.owner>=8||copy.owner>=count)return;
    uint8_t *p=*(uint8_t **)(c.players+0x18+copy.owner*8);if(!p||p[0x16f]!=0||p[0x166]||p[0x16a]||*(int *)(p+0x114)!=copy.x||*(int *)(p+0x118)!=copy.y)return;
    for(int i=0;i<count;i++){uint8_t *other=*(uint8_t **)(c.players+0x18+i*8);if(other&&(other[0x166]||other[0x16a]))return;}
    Shot shot={v,p,copy.angle,copy.force,copy.release};int ready=0;
    pthread_mutex_lock(&turnMutex);Turn *t=&turns[v];
    if(t->generation==copy.generation&&t->enabled&&t->pending&&!t->used&&t->ticket==copy.ticket){t->used=1;t->pending=0;ready=1;}
    pthread_mutex_unlock(&turnMutex);
    if(ready)AGWheelGuard(env,shoot,&shot,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));
}
