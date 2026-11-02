/* UFO auto: server turn, native handoff, completed effects, then one shot. */
#include <stdint.h>
#include <stddef.h>
#include <pthread.h>
#include <time.h>
#include <mach-o/dyld.h>
#include "Turn33.h"
#include "TurnMap.h"
#include "NativeMap.h"
#include "NotesMap.h"
#include "UfoAuto.h"
#include "UfoDiagnostics.h"
extern int AGNotesBlocksAuto(int);
extern int AGWheelSuppressFooter(int);
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static AGUfoAuto autos[6];
typedef struct {
    uintptr_t connection,arena;
    uint64_t sequence,applied;
    int owner,pending,applying;
} NativeTurn;
static NativeTurn nativeTurns[6];
static AGUfoDiagnostic diagnostics[6];
static pthread_mutex_t autoMutex=PTHREAD_MUTEX_INITIALIZER;
/* maxElementFight is sent as a positive Java byte. It is the roster's
 * capacity (100 by default), not its number of occupied/live slots. */
enum { AGUfoMaxActorSlots=127 };
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
__attribute__((visibility("default"))) int AGUfoDiagnosticsGet(int v,AGUfoDiagnostic *out){
    if(v<0||v>=6||!out)return 0;
    pthread_mutex_lock(&autoMutex);*out=diagnostics[v];
    const AGUfoAuto *a=&autos[v];const NativeTurn *n=&nativeTurns[v];
    out->variant=v;out->enabled=a->enabled;out->valid=a->valid;out->hasPlan=a->hasPlan;
    out->early=a->hasEarlyPlan;out->sent=a->sent;out->claimed=a->claimed;out->stable=a->stable;
    out->turn=a->turn;out->serverOwner=a->owner;out->ticket=a->ticket;
    out->planX=a->plan.x;out->planY=a->plan.y;out->angle=a->plan.angle;
    out->nativePending=n->pending;out->nativeApplying=n->applying;out->nativeOwner=n->owner;
    out->sequence=n->sequence;out->applied=n->applied;
    pthread_mutex_unlock(&autoMutex);return out->ticks||out->receives;
}
static uint32_t be32(const uint8_t *p){return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3];}
static uint64_t be64(const uint8_t *p){return (uint64_t)be32(p)<<32|be32(p+4);}
static int short16(const uint8_t *p){return (int16_t)((p[0]<<8)|p[1]);}
static void put16(uint8_t *p,int n){p[0]=(uint8_t)(n>>8);p[1]=(uint8_t)n;}
typedef struct {
    int v,local,owner,ufo;
    uintptr_t connection;
    uint8_t *arena,*canvas,*globals,*players,*playerGlobals,*projectiles;
} Context;
static int context(void *env,void *opaque){
    Context *c=opaque;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    void *(*get)(void *)=(void *)(base+AGMaps[c->v].service);
    uint8_t *volatile service=get(env);if(!service)return 0;
    c->connection=*(uintptr_t *)(service+0x10);if(!c->connection)return 0;
    uint8_t *room=*(uint8_t **)(base+AGNotesMaps[c->v].room_class);
    c->ufo=room&&room[0x131]==5&&(room[0x130]==8||room[0x130]==9);
    c->globals=*(uint8_t **)(base+AGTurnMaps[c->v].arena_class);
    c->canvas=*(uint8_t **)(base+AGNotesMaps[c->v].canvas);
    c->playerGlobals=*(uint8_t **)(base+AGTurnMaps[c->v].player_class);
    c->projectiles=*(uint8_t **)(base+AGTurnMaps[c->v].projectile_class);
    uint8_t *g=*(uint8_t **)(base+AGTurnMaps[c->v].array_class);
    c->players=g?*(uint8_t **)(g+0xa0):NULL;
    /* Original native getters prove266 is MY index and d0 is the CURRENT
     * turn. They differ during UFO turns; identical-slot fixtures hid this. */
    c->owner=g?(int8_t)g[0xd0]:-1;
    c->local=c->globals?(int8_t)c->globals[0x266]:-1;
    c->arena=c->globals?*(uint8_t **)(c->globals+0xe8):NULL;return 1;
}
static int getContext(void *env,Context *c){return AGWheelGuard(env,context,c,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));}
static int active(const Context *c){return c->arena&&c->canvas&&*(void **)(c->canvas+0xb8)==c->arena;}
static int effectsBusy(const Context *c){
    if(c->projectiles&&c->projectiles[0x118])return 1;
    if(c->canvas&&c->canvas[0x13c])return 2;
    int count=c->players?*(int *)(c->players+0x10):0;
    if(count<1||count>AGUfoMaxActorSlots)return 0x10000;
    for(int i=0;i<count;i++){
        uint8_t *p=*(uint8_t **)(c->players+0x18+i*8);
        /* UFO gravity166 and item16a are not movement/flight predicates. */
        if(p&&*(int64_t *)(p+0x68)>0){if(p[0x167])return 4;if(p[0x14e])return 8;}
    }
    return 0;
}
static const uintptr_t changeTurn[6]={0x5126e8,0x600438,0x6e50fc,0x7c9dc0,0x8aea84,0x993748};
static const uintptr_t controllerClass[6]={0x2081150,0x20b0950,0x20de640,0x210c330,0x213a020,0x2167d10};
static const uintptr_t resetInput[6]={0x50c264,0x5fa2fc,0x6defc0,0x7c3c84,0x8a8948,0x98d60c};
typedef struct {int v,owner;Context c;} NativeChange;
static int changeNative(void *env,void *opaque){
    NativeChange *j=opaque;
    if(!active(&j->c)||effectsBusy(&j->c))return 0;
    if(j->c.playerGlobals)j->c.playerGlobals[0x1a7]=0;
    void (*change)(void *,int)=(void *)((uintptr_t)_dyld_get_image_header(0)+changeTurn[j->v]);
    change(env,j->owner);
    /* The original method may postpone changing turns while its native
     * status/chat string is nonempty. A returned call is not a handoff. */
    uint8_t *g=*(uint8_t **)((uintptr_t)_dyld_get_image_header(0)+AGTurnMaps[j->v].array_class);
    if(!g||(int8_t)g[0xd0]!=j->owner){
        if(j->c.playerGlobals)j->c.playerGlobals[0x1a7]=1;
        return 0;
    }
    /* The rest of command24 is deferred with ownership: resetting this
     * projectile/HUD counter early can restart the preceding UFO effect. */
    uint8_t *projectile=j->c.globals?*(uint8_t **)(j->c.globals+0xe0):NULL;
    if(projectile)*(int *)(projectile+0x4c)=0;
    uint8_t *controller=*(uint8_t **)((uintptr_t)_dyld_get_image_header(0)+controllerClass[j->v]);
    if(controller&&controller[0xb0]){
        controller[0xb0]=0;
        void (*reset)(void *)=(void *)((uintptr_t)_dyld_get_image_header(0)+resetInput[j->v]);reset(env);
    }
    return 1;
}
static void applyNativeTurn(void *env,int v){
    Context c={.v=v};if(getContext(env,&c)<=0||!active(&c)||effectsBusy(&c))return;
    uint64_t sequence;NativeChange job={.v=v,.c=c};
    pthread_mutex_lock(&autoMutex);NativeTurn *n=&nativeTurns[v];
    int ready=n->pending&&!n->applying&&n->connection==c.connection&&n->arena==(uintptr_t)c.arena;
    sequence=n->sequence;job.owner=n->owner;if(ready)n->applying=1;
    pthread_mutex_unlock(&autoMutex);if(!ready)return;
    int ok=AGWheelGuard(env,changeNative,&job,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));
    pthread_mutex_lock(&autoMutex);
    n->applying=0;
    if(n->sequence==sequence&&ok>0){n->pending=0;n->applied=sequence;}
    pthread_mutex_unlock(&autoMutex);
}
/* Replaces only the original command24 call to PlayerManager.changeTurn.
 * This defers the native HUD/input handoff too, not merely the auto packet.
 * The original method runs unchanged after the previous effects complete. */
__attribute__((visibility("default"))) int AGTurnChange(void *env,int owner,int v){
    if(!env||v<0||v>=6)return 1;Context c={.v=v};int ok=getContext(env,&c);
    pthread_mutex_lock(&autoMutex);int enabled=autos[v].enabled,ufo=c.ufo||autos[v].valid;
    pthread_mutex_unlock(&autoMutex);
    if(ok<=0||!active(&c)||!ufo||!enabled){
        void (*change)(void *,int)=(void *)((uintptr_t)_dyld_get_image_header(0)+changeTurn[v]);
        change(env,owner);
        pthread_mutex_lock(&autoMutex);nativeTurns[v].owner=owner;
        nativeTurns[v].applied=nativeTurns[v].sequence;pthread_mutex_unlock(&autoMutex);return 1;
    }
    pthread_mutex_lock(&autoMutex);NativeTurn *n=&nativeTurns[v];
    n->connection=c.connection;n->arena=(uintptr_t)c.arena;n->owner=owner;n->pending=1;
    pthread_mutex_unlock(&autoMutex);
    if(c.playerGlobals)c.playerGlobals[0x1a7]=1;
    /* An idle incoming UFO turn must be applied before the following fly/
     * shoot packet starts its animation. This is the original dispatcher
     * thread/Env. Busy handoffs remain queued for the game update. */
    applyNativeTurn(env,v);
    /* The complete tail was applied above or remains queued. Skip the
     * dispatcher's own tail so it cannot reset a running UFO effect. */
    return 0;
}
__attribute__((visibility("default"))) void AGTurnReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return;
    int cmd=*(int8_t *)((uint8_t *)message+0x30);if(cmd!=-115&&cmd!=24&&cmd!=20)return;
    pthread_mutex_lock(&autoMutex);AGUfoDiagnostic *dg=&diagnostics[v];
    dg->receives++;dg->receiveTime=now();dg->lastCommand=cmd;dg->lastLength=-1;
    if(cmd==20)dg->starts++;if(cmd==24)dg->turns++;
    pthread_mutex_unlock(&autoMutex);
    uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);if(!input)return;
    uint8_t *array=*(uint8_t **)(input+0x10);if(!array)return;
    int capacity=*(int *)(array+0x10),length=*(int *)(input+0x18),pos=*(int *)(input+0x20);
    if(capacity<0||length<0||length>capacity||pos<0||pos>length)return;
    const uint8_t *b=array+0x14+pos;size_t n=(size_t)(length-pos);
    pthread_mutex_lock(&autoMutex);dg->lastLength=(int)n;
    if(cmd==24)dg->last24Length=(int)n;
    if(cmd==-115){dg->last115Length=(int)n;dg->lastMagic=n>=4?be32(b):0;
        if(n==4)dg->modes++;
        if(n==21){dg->aims++;dg->lastAimTurn=(int32_t)be32(b);dg->lastAimOwner=b[4];}}
    pthread_mutex_unlock(&autoMutex);
    Context c={.v=v};if(getContext(env,&c)<=0)return;
    pthread_mutex_lock(&autoMutex);AGUfoAuto *a=&autos[v];
    if(a->connection!=c.connection){AGUfoReset(a,c.connection);nativeTurns[v]=(NativeTurn){0};}
    if(cmd==20){AGUfoStart(a);nativeTurns[v]=(NativeTurn){.sequence=nativeTurns[v].sequence+1};}
    else if(cmd==24){
        nativeTurns[v].sequence++;nativeTurns[v].pending=0;
        if(n==17&&be32(b+1)==1429485652U&&b[0]<AGUfoMaxActorSlots)AGUfoTurn(a,b[0],(int32_t)be32(b+5),be64(b+9));
        else AGUfoTurn(a,-1,-1,0);
    }else if(n==4){uint32_t mode=be32(b);if((mode&~1U)==0x55464f00U)AGUfoMode(a,mode&1U);}
    else if(n==21){
        AGUfoPlan p={.turn=(int32_t)be32(b),.owner=b[4],.ticket=be64(b+5),.angle=(b[13]<<8)|b[14],
            .force=b[15],.release=b[16],.x=short16(b+17),.y=short16(b+19)};
        if(p.owner==c.local&&AGUfoAim(a,&p))dg->accepted++;
    }
    pthread_mutex_unlock(&autoMutex);
}
__attribute__((visibility("default"))) void AGTurnManual(int v){
    if(v<0||v>=6)return;pthread_mutex_lock(&autoMutex);diagnostics[v].manuals++;AGUfoManual(&autos[v]);pthread_mutex_unlock(&autoMutex);
}
/* Same native mapper called by d0_.fire. Apa/Chicky keep the second force byte. */
static const uintptr_t bulletMap[6]={0x576cf8,0x660eec,0x745bb0,0x82a874,0x90f538,0x9f41fc};
typedef struct {Context context;AGUfoPlan plan;uint64_t revision;int powerSent;} Dispatch;
static int current(const Dispatch *d){
    pthread_mutex_lock(&autoMutex);const AGUfoAuto *a=&autos[d->context.v];
    int ok=a->revision==d->revision&&a->enabled&&a->claimed&&!a->sent&&
        a->connection==d->context.connection&&a->ticket==d->plan.ticket;
    pthread_mutex_unlock(&autoMutex);return ok;
}
/* Original Message constructor/writer/session: existing socket, framing and encryption. */
static int sendPacket(void *env,const Dispatch *d,int command,const uint8_t *bytes,size_t n){
    /* Auto can only issue a normal shot or the native POW skill token100.
     * It never selects or consumes an inventory item. */
    if(command!=22&&!(command==26&&n==1&&bytes&&bytes[0]==100))return 0;
    const Context *c=&d->context;
    uintptr_t base=(uintptr_t)_dyld_get_image_header(0);const AGNativeMap *m=&AGMaps[c->v];
    void *(*get)(void *)=(void *)(base+m->service);uint8_t *volatile service=get(env);
    if(!service||*(uintptr_t *)(service+0x10)!=c->connection)return 0;
    void *volatile session=*(void **)(service+0x10);
    void *(*alloc)(void *)=(void *)(base+m->alloc);
    void (*ctor)(void *,void *,int)=(void *)(base+m->ctor);
    void (*write)(void *,void *,int)=(void *)(base+0xa64a3c);
    void (*send)(void *,void *,void *)=(void *)(base+m->send);
    void *volatile message=alloc(env);if(!message)return 0;ctor(env,message,command);
    void *volatile writer=*(void **)((uint8_t *)message+0x18);if(!writer)return 0;
    for(size_t i=0;i<n;i++)write(env,writer,bytes[i]);
    if(!current(d)||*(uintptr_t *)(service+0x10)!=c->connection)return 0;
    send(env,session,message);return 1;
}
static int dispatch(void *env,void *opaque){
    Dispatch *d=opaque;Context *c=&d->context;
    int count=c->players?*(int *)(c->players+0x10):0;
    if(!current(d)||!active(c)||effectsBusy(c)||c->local!=d->plan.owner||c->owner!=d->plan.owner||
        count<1||count>AGUfoMaxActorSlots||c->local<0||c->local>=count)return 0;
    uint8_t *volatile p=*(uint8_t **)(c->players+0x18+c->local*8);
    if(!p||*(int64_t *)(p+0x68)<=0||*(int *)(p+0x114)!=d->plan.x||*(int *)(p+0x118)!=d->plan.y)return 0;
    int (*mapBullet)(void *,int)=(void *)((uintptr_t)_dyld_get_image_header(0)+bulletMap[c->v]);
    int bullet=mapBullet(env,(int8_t)p[0x16c])&255;
    /* Native POW callback5d9470: command26/item100 and these exact fields.
     * Rage172==100 is proved by setter59c14c. No inventory item is used. */
    if(!d->powerSent&&p[0x172]==100){
        uint8_t item=100;if(!sendPacket(env,d,26,&item,1))return 0;d->powerSent=1;
        p[0x168]=1;*(int *)(p+0x134)=100;p[0x174]=0;p[0x172]=0;p[0x169]=1;
    }
    uint8_t bytes[10];bytes[0]=(uint8_t)bullet;
    put16(bytes+1,d->plan.x);put16(bytes+3,d->plan.y);put16(bytes+5,d->plan.angle);bytes[7]=(uint8_t)d->plan.force;
    size_t n=8;if(bullet==17||bullet==19)bytes[n++]=(uint8_t)d->plan.release;bytes[n++]=1;
    if(!sendPacket(env,d,22,bytes,n))return 0;
    *(int *)(p+0xa4)=d->plan.angle;p[0x16d]=(uint8_t)d->plan.force;p[0x16e]=(uint8_t)d->plan.release;
    p[0x150]=0;p[0x157]=1;p[0x171]=1;p[0x170]=(uint8_t)bullet;
    *(int *)(p+0x13c)=d->plan.force;*(int *)(p+0x140)=d->plan.release;
    if(c->playerGlobals){c->playerGlobals[0x1a7]=1;c->playerGlobals[0x1a8]=1;}return 1;
}
void AGTurnTick(void *env,int v){
    if(!env||v<0||v>=6)return;
    pthread_mutex_lock(&autoMutex);AGUfoDiagnostic *dg=&diagnostics[v];dg->ticks++;dg->tickTime=now();pthread_mutex_unlock(&autoMutex);
    applyNativeTurn(env,v);
    Context c={.v=v};int contextOK=getContext(env,&c);
    pthread_mutex_lock(&autoMutex);dg->contextOK=contextOK;pthread_mutex_unlock(&autoMutex);
    if(contextOK<=0)return;
    AGUfoFrame f={.connection=c.connection,.arena=(uintptr_t)c.arena,.active=active(&c),.ufo=c.ufo,
        .local=c.local,.owner=c.owner,.now=now()};
    int count=c.players?*(int *)(c.players+0x10):0;
    pthread_mutex_lock(&autoMutex);dg->active=f.active;dg->ufo=f.ufo;dg->local=c.local;dg->owner=c.owner;dg->count=count;pthread_mutex_unlock(&autoMutex);
    if(count<1||count>AGUfoMaxActorSlots||c.local<0||c.local>=8||c.local>=count)return;
    uint8_t *p=*(uint8_t **)(c.players+0x18+c.local*8);if(!p)return;
    f.alive=*(int64_t *)(p+0x68)>0;f.state=p[0x16f];f.x=*(int *)(p+0x114);f.y=*(int *)(p+0x118);
    int effects=effectsBusy(&c),blockers=effects;
    if(p[0x166])blockers|=16;if(AGNotesBlocksAuto(v))blockers|=32;
    if(AGWheelSuppressFooter(v))blockers|=64;if(c.canvas&&*(void **)(c.canvas+0x108))blockers|=128;
    f.blocked=f.active&&blockers;
    Dispatch d={.context=c};uint64_t revision;
    pthread_mutex_lock(&autoMutex);AGUfoAuto *a=&autos[v];
    dg->alive=f.alive;dg->state=f.state;dg->x=f.x;dg->y=f.y;dg->effects=effects;dg->blocked=blockers;
    /* Only UFO map35 gets Auto31's trailer. It is also valid while the
     * native room screen is reconstructed, before its room fields settle. */
    f.ufo=f.ufo||(a->valid&&a->enabled);
    NativeTurn *native=&nativeTurns[v];
    f.blocked=f.blocked||native->pending||native->applying||native->sequence!=native->applied;
    int ready=AGUfoAcquire(a,&f,&d.plan);revision=a->revision;d.revision=revision;d.powerSent=a->powerSent;
    pthread_mutex_unlock(&autoMutex);if(!ready)return;
    int result=AGWheelGuard(env,dispatch,&d,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));
    pthread_mutex_lock(&autoMutex);if(a->revision==revision)a->powerSent=d.powerSent;
    if(result>0)dg->shots++;else dg->failures++;
    AGUfoComplete(a,revision,result,f.now);pthread_mutex_unlock(&autoMutex);
}
/* Match the reference JAR: an actual animation completion releases the
 * dispatcher. Elapsed time must never grant the next actor's turn. */
__attribute__((visibility("default"))) void AGTurnAwait(void *env,void *lock,int v,int kind,int actor){
    if(!env||!lock||v<0||v>=6)return;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    Context c={.v=v};int ok=getContext(env,&c);
    pthread_mutex_lock(&autoMutex);int ufo=c.ufo||(autos[v].enabled&&autos[v].valid);pthread_mutex_unlock(&autoMutex);
    if(!ufo){void (*wait)(void *,void *)=(void *)(base+0xaaa6e8);wait(env,lock);return;}
    if(ok<=0||!active(&c))return;uint8_t *arena=c.arena;
    pthread_mutex_lock(&autoMutex);AGUfoDiagnostic *dg=&diagnostics[v];dg->waits++;dg->waitActive=1;
    dg->waitKind=kind;dg->waitActor=actor;dg->waitSince=now();pthread_mutex_unlock(&autoMutex);
    for(;;){
        int busy=0;
        if(kind==0)busy=c.projectiles&&((volatile uint8_t *)c.projectiles)[0x118];
        else if(kind==1)busy=((volatile uint8_t *)c.canvas)[0x13c];
        else if((kind==2||kind==3)&&c.players){int count=*(int *)(c.players+0x10);
            if(actor>=0&&actor<count&&count<=AGUfoMaxActorSlots){uint8_t *p=*(uint8_t **)(c.players+0x18+actor*8);busy=p&&((volatile uint8_t *)p)[kind==2?0x167:0x14e];}}
        if(!busy)break;
        void (*wait)(void *,void *,int64_t)=(void *)(base+0xaaa730);wait(env,lock,16);
        c=(Context){.v=v};if(getContext(env,&c)<=0||!active(&c)||c.arena!=arena)break;
    }
    pthread_mutex_lock(&autoMutex);dg->waitActive=0;pthread_mutex_unlock(&autoMutex);
}
