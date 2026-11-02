/* Airship diagnostic: copy numeric observations only; never drive combat. */
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#include <mach-o/dyld.h>
#include "ShipTrace.h"
#include "TurnMap.h"
#include "NotesMap.h"
#include "ShipTraceMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static AGShipTrace traces[6];
static double nextSample[6];
static pthread_mutex_t traceMutex=PTHREAD_MUTEX_INITIALIZER;
static double clockNow(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static int shipRoom(int room){return room==10||room==14||room==15;}
static int part(int c){return c>=17&&c<=21;}
static int snapshot(void *env,void *opaque){
    (void)env;AGShipTrace *d=opaque;int v=d->variant;uintptr_t b=(uintptr_t)_dyld_get_image_header(0);
    uint8_t *volatile room=*(uint8_t **)(b+AGNotesMaps[v].room_class);
    d->room=room?room[0x130]:-1;if(!shipRoom(d->room))return 1;
    uint8_t *volatile g=*(uint8_t **)(b+AGTurnMaps[v].arena_class);
    uint8_t *volatile ag=*(uint8_t **)(b+AGTurnMaps[v].array_class);
    uint8_t *volatile canvas=*(uint8_t **)(b+AGNotesMaps[v].canvas);
    uint8_t *volatile arena=g?*(uint8_t **)(g+0xe8):0;
    d->active=arena&&canvas&&*(uint8_t **)(canvas+0xb8)==arena;
    if(!d->active)return 1;
    d->local=g?(int8_t)g[0x266]:-1;d->owner=ag?(int8_t)ag[0xd0]:-1;
    uint8_t *volatile cam=g?*(uint8_t **)(g+0xd8):0;
    uint8_t *volatile cg=*(uint8_t **)(b+AGShipCameraClass[v]);
    d->cameraActor=cam?*(int *)(cam+0x20):-1;d->cameraMode=cg?cg[0xbc]:-1;
    d->cameraX=cg?*(int *)(cg+0xa4):0;d->cameraY=cg?*(int *)(cg+0xa8):0;
    uint8_t *volatile pg=*(uint8_t **)(b+AGTurnMaps[v].player_class);
    uint8_t *volatile proj=*(uint8_t **)(b+AGTurnMaps[v].projectile_class);
    d->projectileBusy=proj?proj[0x118]:-1;d->completionReady=proj?proj[0x115]:-1;
    d->canvasBusy=canvas?canvas[0x13c]:-1;d->pending=pg?pg[0x1a7]:-1;d->notified=pg?pg[0x1a8]:-1;
    uint8_t *volatile players=ag?*(uint8_t **)(ag+0xa0):0;
    d->count=players?*(int *)(players+0x10):0;
    if(d->count<1||d->count>127)return 1;
    int hasShip=0;
    for(int i=0;i<d->count;i++){
        uint8_t *volatile p=*(uint8_t **)(players+0x18+i*8);if(!p)continue;
        int c=p[0x16c];if(part(c))hasShip=1;
        if(i>=8&&!part(c))continue;
        if(d->actorCount>=AGShipTraceActors)continue;
        AGShipActor *a=&d->actors[d->actorCount++];
        *a=(AGShipActor){.slot=i,.index=(int8_t)p[0x16b],.character=c,.state=p[0x16f],
            .visible=p[0x159],.gravity=p[0x166],.walk=p[0x167],.flight=p[0x14e],
            .x=*(int *)(p+0x114),.y=*(int *)(p+0x118),.hp=*(int64_t *)(p+0x68)};
    }
    if(d->room!=10&&!hasShip)d->active=0;
    return 1;
}
void AGShipTraceTick(void *env,int v,int source){
    if(!env||v<0||v>=6)return;
    double now=clockNow();
    pthread_mutex_lock(&traceMutex);
    if(source==1){traces[v].pulses++;traces[v].pulseTime=now;}
    int sample=now>=nextSample[v];if(sample)nextSample[v]=now+.2;
    pthread_mutex_unlock(&traceMutex);if(!sample)return;
    AGShipTrace d={.variant=v,.owner=-1,.local=-1,.cameraActor=-1};
    d.contextOK=AGWheelGuard(env,snapshot,&d,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));
    pthread_mutex_lock(&traceMutex);AGShipTrace *out=&traces[v];
    // Only the snapshot prefix is replaced. Event/wait/corpse observations
    // remain independently updated by their original native threads.
    out->variant=v;out->contextOK=d.contextOK;out->active=d.active;out->room=d.room;
    out->local=d.local;out->owner=d.owner;out->cameraActor=d.cameraActor;out->cameraMode=d.cameraMode;
    out->cameraX=d.cameraX;out->cameraY=d.cameraY;out->count=d.count;
    out->projectileBusy=d.projectileBusy;out->completionReady=d.completionReady;
    out->canvasBusy=d.canvasBusy;out->pending=d.pending;out->notified=d.notified;
    out->actorCount=d.actorCount;memcpy(out->actors,d.actors,sizeof d.actors);
    out->samples++;out->sampleTime=now;pthread_mutex_unlock(&traceMutex);
}
void AGShipTraceReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return;
    AGShipTraceTick(env,v,2);
    pthread_mutex_lock(&traceMutex);int room=traces[v].room;pthread_mutex_unlock(&traceMutex);
    if(!shipRoom(room))return;
    uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);
    uint8_t *array=input?*(uint8_t **)(input+0x10):0;if(!array)return;
    int cap=*(int *)(array+0x10),len=*(int *)(input+0x18),pos=*(int *)(input+0x20);
    if(cap<0||len<0||len>cap||pos<0||pos>len)return;
    const uint8_t *p=array+0x14+pos;int n=len-pos,cmd=*(int8_t *)((uint8_t *)message+0x30);
    pthread_mutex_lock(&traceMutex);AGShipTrace *d=&traces[v];
    if(cmd==20){d->match++;d->eventCount=0;d->serverOwner=-1;d->serverTurn=-1;}
    d->receives++;d->receiveTime=clockNow();d->lastCommand=cmd;d->lastLength=n;
    if(cmd==24&&n){d->turns++;d->serverOwner=p[0];d->serverTurn=-1;
        if(n==17&&p[1]==0x55&&p[2]==0x34&&p[3]==0x38&&p[4]==0x54)
            d->serverTurn=(int32_t)((uint32_t)p[5]<<24|(uint32_t)p[6]<<16|(uint32_t)p[7]<<8|p[8]);
    }
    if(cmd==93){d->flights++;
        if(n==10&&p[5]==0x43&&p[6]==0x50&&p[7]==0x34&&p[8]==0x39){
            d->corpsePacketActor=p[0];d->corpseTargetX=(int16_t)((p[1]<<8)|p[2]);
            d->corpseTargetY=(int16_t)((p[3]<<8)|p[4]);d->corpseRemove=!!p[9];
        }
    }
    if(d->eventCount==AGShipTraceEvents){memmove(d->events,d->events+1,sizeof(d->events[0])*(AGShipTraceEvents-1));d->eventCount--;}
    d->events[d->eventCount++]=(AGShipEvent){.command=cmd,.length=n,.first=n?p[0]:-1,.serial=++d->eventSerial};
    pthread_mutex_unlock(&traceMutex);
}
void AGShipTraceWait(int v,int kind,int actor,int active){
    if(v<0||v>=6)return;
    pthread_mutex_lock(&traceMutex);AGShipTrace *d=&traces[v];
    d->waitActive=active;d->waitKind=kind;d->waitActor=actor;
    if(active)d->waitSince=clockNow();
    pthread_mutex_unlock(&traceMutex);
}
void AGShipTraceCorpse(int v,int index,int character,int handled){
    if(v<0||v>=6)return;
    pthread_mutex_lock(&traceMutex);AGShipTrace *d=&traces[v];
    d->corpseUpdates++;d->corpseIndex=index;d->corpseCharacter=character;d->corpseHandled=handled;
    d->corpseTime=clockNow();if(!handled)d->corpseRejected++;pthread_mutex_unlock(&traceMutex);
}
__attribute__((visibility("default"))) int AGShipTraceGet(int v,AGShipTrace *out){
    if(v<0||v>=6||!out)return 0;
    pthread_mutex_lock(&traceMutex);*out=traces[v];pthread_mutex_unlock(&traceMutex);
    return out->samples>0;
}
