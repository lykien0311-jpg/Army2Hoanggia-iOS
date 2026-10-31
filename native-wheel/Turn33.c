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
extern void AGTurnStatusUpdate(int,int);
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
typedef struct {int v;uintptr_t connection;uint8_t *arena,*canvas,*globals,*players,*playerGlobals,*projectiles;int local,ufo;} Context;
static int context(void *env,void *opaque){
    Context *c=opaque;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    uint8_t *room=*(uint8_t **)(base+AGNotesMaps[c->v].room_class);
    c->ufo=room&&room[0x131]==5&&(room[0x130]==8||room[0x130]==9);
    void *(*get)(void *)=(void *)(base+AGMaps[c->v].service);uint8_t *volatile service=get(env);
    if(!service)return 0;c->connection=*(uintptr_t *)(service+0x10);if(!c->connection)return 0;
    c->globals=*(uint8_t **)(base+AGTurnMaps[c->v].arena_class);
    c->canvas=*(uint8_t **)(base+AGNotesMaps[c->v].canvas);
    c->playerGlobals=*(uint8_t **)(base+AGTurnMaps[c->v].player_class);
    c->projectiles=*(uint8_t **)(base+AGTurnMaps[c->v].projectile_class);
    uint8_t *g=*(uint8_t **)(base+AGTurnMaps[c->v].array_class);
    c->players=g?*(uint8_t **)(g+0xa0):NULL;c->local=g?(int8_t)g[0xd0]:-1;
    c->arena=c->globals?*(uint8_t **)(c->globals+0xe8):NULL;
    return 1;
}
static int getContext(void *env,Context *c){return AGWheelGuard(env,context,c,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));}
static int active(const Context *c){return c->arena&&c->canvas&&*(void **)(c->canvas+0xb8)==c->arena;}
// Match the actual fields referenced by Turn33 in the working JAR. Native
// d0_.<init> and g(II) prove these mappings; they are different animations.
// 166 is gravity/falling, 167 is server-directed movement, 14e is flight.
// 16a belongs to the separate item animation started by d0_.f(B).
enum { PLAYER_FALLING=0x166, PLAYER_MOVING=0x167, PLAYER_FLIGHT=0x14e };
// Working Turn33 uses predicate waits: an animation may finish before the
// network thread enters its monitor, so an unconditional wait loses notify.
// Keep the native monitor enter/exit and Java exception propagation intact.
// kind: 0 projectile, 1 flash, 2 walk, 3 flight.
__attribute__((visibility("default"))) void AGTurnAwait(void *env,void *lock,int v,int kind,int actor){
    if(!env||!lock||v<0||v>=6)return;
    uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    Context c={.v=v};int ok=getContext(env,&c);
    if(!c.ufo){
        void (*wait)(void *,void *)=(void *)(base+0xaaa6e8);wait(env,lock);return;
    }
    if(ok<=0||!active(&c))return;
    uint8_t *volatile arena=c.arena;
    for(;;){
        int busy=0;
        if(kind==0)busy=c.projectiles&&((volatile uint8_t *)c.projectiles)[0x118];
        else if(kind==1)busy=((volatile uint8_t *)c.canvas)[0x13c];
        else if((kind==2||kind==3)&&c.players){
            int count=*(int *)(c.players+0x10);
            if(actor>=0&&actor<count&&count<=64){
                uint8_t *p=*(uint8_t **)(c.players+0x18+actor*8);
                busy=p&&((volatile uint8_t *)p)[kind==2?PLAYER_MOVING:PLAYER_FLIGHT];
            }
        }
        if(!busy)return;
        void (*wait)(void *,void *,int64_t)=(void *)(base+0xaaa730);
        wait(env,lock,16);
        c=(Context){.v=v};
        if(getContext(env,&c)<=0||!active(&c)||c.arena!=arena||!c.ufo)return;
    }
}
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
        // The observer runs before the original dispatcher. The first turn
        // can arrive while that dispatcher is still activating the arena.
        // Cache the ticket now; screen/owner checks belong to the game tick.
        if(n==17&&be32(b+1)==1429485652U&&b[0]<8){
            t->valid=1;t->owner=b[0];t->turn=(int32_t)be32(b+5);t->ticket=be64(b+9);t->arena=active(&c)?(uintptr_t)c.arena:0;
        }
    }else if(n==4){
        uint32_t mode=be32(b);if((mode&~1U)==0x55464f00U){t->enabled=mode&1U;if(!t->enabled)t->pending=0;}
    }else if(n==21&&t->enabled&&t->valid&&!t->used){
        unsigned angle=(b[13]<<8)|b[14];
        if((int32_t)be32(b)==t->turn&&b[4]==t->owner&&be64(b+5)==t->ticket&&b[4]==c.local&&angle<360&&b[15]>=1&&b[15]<=30&&b[16]<=30){
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
    // The original movement routine updates the int32 position at 114/118.
    // Do not rewrite it. The angle at a4 is also one int32, not two shorts.
    *(int32_t *)(p+0xa4)=s->angle;p[0x16d]=(uint8_t)s->force;p[0x16e]=(uint8_t)s->release;*(int *)(p+0x134)=0;
    void (*fire)(void *,void *)=(void *)((uintptr_t)_dyld_get_image_header(0)+AGTurnMaps[s->v].fire);
    fire(env,p);return 1;
}
void AGTurnTick(void *env,int v){
    if(!env||v<0||v>=6)return;
    pthread_mutex_lock(&turnMutex);Turn copy=turns[v];pthread_mutex_unlock(&turnMutex);
    Context c={.v=v};int ok=getContext(env,&c);
    if(!active(&c)||!c.ufo){AGTurnStatusUpdate(v,0);return;}
    if(!copy.enabled){AGTurnStatusUpdate(v,10);return;}
    if(!copy.valid){AGTurnStatusUpdate(v,1);return;}
    if(copy.used){AGTurnStatusUpdate(v,8);return;}
    if(!copy.pending){AGTurnStatusUpdate(v,2);return;}
    if(ok<=0||c.connection!=copy.connection||(copy.arena&&c.arena&&(uintptr_t)c.arena!=copy.arena)){
        pthread_mutex_lock(&turnMutex);if(turns[v].generation==copy.generation){invalidate(&turns[v]);if(c.connection!=copy.connection)turns[v].enabled=0;}pthread_mutex_unlock(&turnMutex);AGTurnStatusUpdate(v,9);return;
    }
    if(!c.globals||!c.playerGlobals||!c.players){AGTurnStatusUpdate(v,9);return;}
    if(AGNotesBlocksAuto(v)||*(void **)(c.canvas+0x108)){AGTurnStatusUpdate(v,7);return;}
    if(c.globals[0x266]!=copy.owner||c.local!=copy.owner){AGTurnStatusUpdate(v,6);return;}
    // JAR Turn33 checks the primary shot-busy flag reset for the new turn.
    // 1a8 is a separate deferred-shot notification consumed by V.s(); it
    // survives owner changes and must not veto the next ticketed auto shot.
    if(c.playerGlobals[0x1a7]||(c.projectiles&&c.projectiles[0x118])||c.canvas[0x13c]){AGTurnStatusUpdate(v,4);return;}
    int count=*(int *)(c.players+0x10);if(count<1||count>64||copy.owner<0||copy.owner>=8||copy.owner>=count)return;
    // Confirmed against d0_.l(Z): native walking and terrain settling write
    // full int32 values at 114/118. C0/D0 at 80/84 are unrelated fields.
    uint8_t *p=*(uint8_t **)(c.players+0x18+copy.owner*8);
    if(!p||*(int64_t *)(p+0x68)<=0||p[0x16f]!=0||p[PLAYER_FALLING]){AGTurnStatusUpdate(v,3);return;}
    if(*(int32_t *)(p+0x114)!=copy.x||*(int32_t *)(p+0x118)!=copy.y){AGTurnStatusUpdate(v,5);return;}
    for(int i=0;i<count;i++){uint8_t *other=*(uint8_t **)(c.players+0x18+i*8);if(other&&*(int64_t *)(other+0x68)>0&&(other[PLAYER_MOVING]||other[PLAYER_FLIGHT])){AGTurnStatusUpdate(v,3);return;}}
    Shot shot={v,p,copy.angle,copy.force,copy.release};int ready=0;
    pthread_mutex_lock(&turnMutex);Turn *t=&turns[v];
    if(t->generation==copy.generation&&t->enabled&&t->pending&&!t->used&&t->ticket==copy.ticket){t->used=1;t->pending=0;ready=1;}
    pthread_mutex_unlock(&turnMutex);
    if(ready){int sent=AGWheelGuard(env,shoot,&shot,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));AGTurnStatusUpdate(v,sent>0?8:11);}
}

