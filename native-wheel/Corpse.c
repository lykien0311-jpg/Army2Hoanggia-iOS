/* Corpse497's command93 extension, matching the working JAR's Client497.
 * Corpses move on the game update; they never enter the live flight wait.
 */
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <mach-o/dyld.h>
#include "NativeMap.h"
#include "NotesMap.h"
#include "TurnMap.h"
#include "ShipTrace.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {
    uintptr_t connection;
    uint8_t *arena,*canvas,*players;
    int variant,room,count;
} CorpseContext;
typedef struct {
    uintptr_t connection;
    uint8_t *arena,*player;
    int targetX,targetY,y,speed,remove;
} CorpseMotion;
static CorpseMotion motions[6][127];
static pthread_mutex_t corpseMutex=PTHREAD_MUTEX_INITIALIZER;
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
static int context(void *env,void *opaque){
    CorpseContext *c=opaque;uintptr_t b=base();int v=c->variant;
    uint8_t *(*getService)(void *)=(void *)(b+AGMaps[v].service);
    uint8_t *s=getService(env);if(!s)return 0;
    c->connection=*(uintptr_t *)(s+0x10);if(!c->connection)return 0;
    uint8_t *g=*(uint8_t **)(b+AGTurnMaps[v].arena_class);
    uint8_t *a=*(uint8_t **)(b+AGTurnMaps[v].array_class);
    uint8_t *r=*(uint8_t **)(b+AGNotesMaps[v].room_class);
    c->arena=g?*(uint8_t **)(g+0xe8):0;
    c->canvas=*(uint8_t **)(b+AGNotesMaps[v].canvas);
    c->players=a?*(uint8_t **)(a+0xa0):0;
    c->count=c->players?*(int *)(c->players+0x10):0;
    c->room=r?r[0x130]:-1;
    return c->arena&&c->canvas&&*(uint8_t **)(c->canvas+0xb8)==c->arena&&c->count>0&&c->count<=127;
}
static int getContext(void *env,CorpseContext *c){return AGWheelGuard(env,context,c,(void *)(base()+0x1300d54));}
static int airshipRoom(const CorpseContext *c){return c->room==10||c->room==14||c->room==15;}
static int airshipPart(const uint8_t *p){return p&&p[0x16c]>=17&&p[0x16c]<=21;}
static int shortBE(const uint8_t *p){return (int16_t)((p[0]<<8)|p[1]);}
__attribute__((visibility("default"))) int AGCorpseReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return 0;
    AGShipTraceReceive(env,message,v);
    int command=*(int8_t *)((uint8_t *)message+0x30);
    if(command==20){pthread_mutex_lock(&corpseMutex);memset(motions[v],0,sizeof(motions[v]));pthread_mutex_unlock(&corpseMutex);return 0;}
    if(command!=93)return 0;
    uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);
    uint8_t *array=input?*(uint8_t **)(input+0x10):0;if(!array)return 0;
    int capacity=*(int *)(array+0x10),length=*(int *)(input+0x18),pos=*(int *)(input+0x20);
    if(capacity<0||length<0||length>capacity||pos<0||pos>length||length-pos!=10)return 0;
    const uint8_t *p=array+0x14+pos;
    if(p[5]!=0x43||p[6]!=0x50||p[7]!=0x52||p[8]!=0x39)return 0;
    CorpseContext c={.variant=v};if(getContext(env,&c)<=0||!airshipRoom(&c))return 0;
    int actor=p[0];if(actor<8||actor>=c.count)return 1;
    uint8_t *player=*(uint8_t **)(c.players+0x18+actor*8);
    if(!airshipPart(player))return 0;
    // Like Client497.move, a stale corpse packet cannot move a live actor.
    if(*(int64_t *)(player+0x68)>0)return 1;
    pthread_mutex_lock(&corpseMutex);CorpseMotion *m=&motions[v][actor];
    if(m->connection!=c.connection||m->arena!=c.arena||m->player!=player){
        *m=(CorpseMotion){.connection=c.connection,.arena=c.arena,.player=player,.y=*(int *)(player+0x118)};
    }
    m->targetX=shortBE(p+1);m->targetY=shortBE(p+3);m->remove=!!p[9];
    pthread_mutex_unlock(&corpseMutex);
    return 1;
}
__attribute__((visibility("default"))) int AGCorpseUpdate(void *env,void *actor,int v){
    if(!env||!actor||v<0||v>=6)return 0;
    uint8_t *p=actor;
    if(!airshipPart(p))return 0;
    if(*(int64_t *)(p+0x68)>0){
        int i=(int8_t)p[0x16b];
        if(i>=8&&i<127){pthread_mutex_lock(&corpseMutex);
            if(motions[v][i].player==p)memset(&motions[v][i],0,sizeof(motions[v][i]));
            pthread_mutex_unlock(&corpseMutex);
        }return 0;
    }
    CorpseContext c={.variant=v};if(getContext(env,&c)<=0||!airshipRoom(&c))return 0;
    int index=(int8_t)p[0x16b];
    int belongs=index>=8&&index<c.count&&*(uint8_t **)(c.players+0x18+index*8)==p;
    AGShipTraceCorpse(v,index,p[0x16c],belongs);
    if(!belongs)return 0;
    // A native turn handoff can reset death5 to idle0 if it targets a part
    // whose death arrived earlier. Bypassing Player.update then preserves that
    // stale live state. The arena counts gravity && state!=5 as an active actor
    // and withholds endShoot23. Keep a confirmed corpse in native death state,
    // including the death frame/status cleanup, on every update.
    if(p[0x16f]!=5){p[0x16f]=5;*(int *)(p+0xbc)=7;p[0x15f]=0;p[0x160]=0;}
    // A corpse has no live-flight/walking completion branch. Only the marked
    // server destination controls its animation; landed corpses are settled.
    p[0x14e]=0;p[0x167]=0;p[0x166]=0;
    pthread_mutex_lock(&corpseMutex);CorpseMotion *m=&motions[v][index];
    if(m->connection==c.connection&&m->arena==c.arena&&m->player==p){
        if(m->y<m->targetY){m->speed+=2;if(m->speed>24)m->speed=24;
            m->y=m->targetY-m->y<m->speed?m->targetY:m->y+m->speed;
        }else m->y=m->targetY;
        *(int *)(p+0x114)=m->targetX;*(int *)(p+0x118)=m->y;
        p[0x166]=m->y!=m->targetY;
        if(m->remove&&m->y==m->targetY)p[0x159]=0;
    }
    pthread_mutex_unlock(&corpseMutex);return 1;
}
