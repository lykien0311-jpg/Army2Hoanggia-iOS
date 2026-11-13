/* SP53 snapshot adapter. Actors, bullets, impacts, terrain destruction and
 * camera are rendered by the unchanged game engine, as on the APK. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include "SpectatorNative.h"
#ifdef AG_WHEEL_PREVIEW
int AGNativeWatchAvailable(void){return 0;}
int AGNativeWatchPacket(void *e,int v,const uint8_t *p,size_t n){return 0;}
void AGNativeWatchEnd(void *e,int v){}
void AGNativeWatchCamera(int v,int k,int c){}
void AGNativeWatchTick(void *e,int v){}
#else
#include <mach-o/dyld.h>
#include <pthread.h>
static pthread_mutex_t watchLock=PTHREAD_MUTEX_INITIALIZER;
#include "SpectatorNativeMap.h"
#include "TurnMap.h"
#include "NotesMap.h"
#include "BossNativeMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {
    int active,started,prepared,v,map,width,height,bricks,next,index,id,x,y,solid,total,received;
    uint8_t *bytes,*back,*oldMap,*oldTiles;
    int oldWidth,oldHeight;
    uint8_t oldLocal;
} Watch;
static Watch watches[6];
static atomic_int cameraKeys[6],freeCamera[6],cameraChanged[6];
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
static uint8_t *global(uintptr_t a){return *(uint8_t **)(base()+a);}
static int be16(const uint8_t *p){return (int16_t)((p[0]<<8)|p[1]);}
static unsigned u16(const uint8_t *p){return (p[0]<<8)|p[1];}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3];}
static int64_t be64(const uint8_t *p){uint64_t n=0;for(int i=0;i<8;i++)n=n<<8|p[i];return (int64_t)n;}
static void *pin(void *e,void *p){return p?((void *(*)(void *,void *))(*(void ***)e)[21])(e,p):NULL;}
static void unpin(void *e,void *p){if(p)((void (*)(void *,void *))(*(void ***)e)[22])(e,p);}
static void *newVector(void *e){void *p=((void *(*)(void *))(base()+0xbe3f1c))(e);((void (*)(void *,void *))(base()+0xbe6b7c))(e,p);return p;}
__attribute__((noinline,optnone)) static int prepare(void *e,void *opaque){
    Watch *w=opaque;int v=w->v;uintptr_t b=base();const AGSpectatorMap *m=&AGSpectatorMaps[v];
    /* The allocator performs the normal RoboVM class initialization. */
    uint8_t *a=global(AGTurnMaps[v].arena_class);
    if(!a||!*(void **)(a+0xe8)){
        void *p=((void *(*)(void *))(b+m->arenaNew))(e);
        ((void (*)(void *,void *))(b+m->arenaInit))(e,p);
        a=global(AGTurnMaps[v].arena_class);*(void **)(a+0xe8)=p;
    }
    uint8_t *canvas=global(AGNotesMaps[v].canvas);
    w->back=pin(e,*(void **)(canvas+0xb8));
    w->oldLocal=a[0x266];w->oldMap=pin(e,*(void **)(a+0xc8));
    uint8_t *map=((void *(*)(void *))(b+m->mapNew))(e);
    ((void (*)(void *,void *))(b+m->mapInit))(e,map);
    uint8_t *g=global(AGBossNativeMaps[v].mapClass);
    w->oldTiles=pin(e,*(void **)(g+0xb8));
    w->oldWidth=*(int *)(g+0xd8);w->oldHeight=*(int *)(g+0xdc);w->prepared=1;
    *(void **)(a+0xc8)=map;*(int *)(map+0x10)=w->map;
    *(int *)(g+0xd8)=w->width;*(int *)(g+0xdc)=w->height;
    *(void **)(g+0xb8)=newVector(e);g[0xe0]=0;
    return 1;
}
__attribute__((noinline,optnone)) static int buildTile(void *e,void *opaque){
    Watch *w=opaque;uintptr_t b=base();void **jni=*(void ***)e;
    void *raw=((void *(*)(void *,int))jni[176])(e,w->total);
    ((void (*)(void *,void *,int,int,const uint8_t *))jni[208])(e,raw,0,w->total,w->bytes);
    void *image=((void *(*)(void *,void *,int,int))(b+0xc46e04))(e,raw,0,w->total);
    ((void (*)(void *,void *))jni[23])(e,raw);
    if(!image)return 0;
    int width=((int (*)(void *,void *))(b+0x1c61b0))(e,image);
    int height=((int (*)(void *,void *))(b+0x1c61a0))(e,image);
    if(width<1||height<1||width>4096||height>4096||(int64_t)width*height>4000000)return 0;
    const AGBossNativeMap *m=&AGBossNativeMaps[w->v];
    uint8_t *tile=((void *(*)(void *))(b+m->tileNew))(e);
    ((void (*)(void *,void *,int64_t,int,int,void *,int))(b+m->tileInit))(e,tile,w->id,w->x,w->y,NULL,w->solid);
    void *pixels=((void *(*)(void *,int))(b+0x12e7d28))(e,width*height);
    ((void (*)(void *,void *,void *,int,int,int,int,int,int))(b+0x1c61a4))(e,image,pixels,0,width,0,0,width,height);
    *(void **)(tile+0x10)=pixels;*(void **)(tile+0x18)=image;
    *(int *)(tile+0x28)=width;*(int *)(tile+0x2c)=height;
    uint8_t *g=global(m->mapClass);
    ((void (*)(void *,void *,void *))(b+0x1dfcac))(e,*(void **)(g+0xb8),tile);
    return 1;
}
typedef struct {Watch *w;int clock,first;int64_t x[8],y[8],hp[8];} Start;
__attribute__((noinline,optnone)) static int start(void *e,void *opaque){
    Start *s=opaque;Watch *w=s->w;int v=w->v;uintptr_t b=base();
    const AGSpectatorMap *m=&AGSpectatorMaps[v];uint8_t *g=global(AGTurnMaps[v].arena_class);
    void *arrays[3];const int64_t *data[3]={s->x,s->y,s->hp};
    for(int i=0;i<3;i++){arrays[i]=((void *(*)(void *,int))(b+0x12e7d88))(e,8);memcpy((uint8_t *)arrays[i]+0x18,data[i],64);}
    g[0x266]=s->first;
    ((void (*)(void *,void *,int,void *,void *,void *,int64_t))(b+m->start))
        (e,*(void **)(g+0xe8),s->clock,arrays[0],arrays[1],arrays[2],0);
    g[0x266]=s->first;
    /* Read-only controls are supplied by the spectator overlay. */
    uint8_t *arena=*(void **)(g+0xe8);
    *(void **)(arena+0x18)=NULL;*(void **)(arena+0x20)=NULL;*(void **)(arena+0x28)=NULL;
    ((void (*)(void *,void *,void *))(b+m->show))(e,arena,w->back);
    ((void (*)(void *))(b+AGBossNativeMaps[v].resetInput))(e);
    atomic_store(&freeCamera[v],0);atomic_store(&cameraKeys[v],0);
    return 1;
}
static int restore(void *e,void *opaque){
    Watch *w=opaque;int v=w->v;uint8_t *a=global(AGTurnMaps[v].arena_class);
    uint8_t *g=global(AGBossNativeMaps[v].mapClass);
    if(a){a[0x266]=w->oldLocal;*(void **)(a+0xc8)=w->oldMap;}
    if(g){*(void **)(g+0xb8)=w->oldTiles;*(int *)(g+0xd8)=w->oldWidth;*(int *)(g+0xdc)=w->oldHeight;}
    ((void (*)(void *))(base()+AGBossNativeMaps[v].resetInput))(e);
    uint8_t *canvas=global(AGNotesMaps[v].canvas);
    if(w->started&&w->back&&canvas&&a&&*(void **)(canvas+0xb8)==*(void **)(a+0xe8))
        ((void (*)(void *,void *))(base()+AGSpectatorMaps[v].restore))(e,w->back);
    return 1;
}
static int guard(void *e,int (*fn)(void *,void *),void *j){return AGWheelGuard(e,fn,j,(void *)(base()+0x1300d54));}
int AGNativeWatchAvailable(void){return 1;}
static void endNative(void *e,int v){
    if(v<0||v>=6)return;Watch *w=&watches[v];
    if(w->prepared)guard(e,restore,w);
    unpin(e,w->back);unpin(e,w->oldMap);unpin(e,w->oldTiles);free(w->bytes);memset(w,0,sizeof *w);
    atomic_store(&freeCamera[v],0);atomic_store(&cameraKeys[v],0);
}
typedef struct {Watch *w;int seconds;} Clock;
static int resetClock(void *e,void *opaque){
    Clock *j=opaque;int v=j->w->v;uint8_t *a=global(AGTurnMaps[v].arena_class);
    void *clock=a?*(void **)(a+0x110):NULL;if(!clock)return 0;
    const AGSpectatorMap *m=&AGSpectatorMaps[v];
    ((void (*)(void *,void *,int))(base()+m->clockSet))(e,clock,j->seconds);
    ((void (*)(void *,void *))(base()+m->clockReset))(e,clock);
    return 1;
}
static int packetNative(void *e,int v,const uint8_t *p,size_t n){
    if(v<0||v>=6||n<4)return 0;Watch *w=&watches[v];
    if(p[3]==3){
        if(n!=21||w->active||!u16(p+15)||!u16(p+17)||u16(p+19)>4096)return 0;
        *w=(Watch){.active=1,.v=v,.map=p[14],.width=u16(p+15),.height=u16(p+17),.bricks=u16(p+19)};
        return guard(e,prepare,w)>0;
    }
    if(!w->active)return 0;
    if(p[3]==4){
        if(w->started||n<25)return 0;
        int index=u16(p+4),id=u32(p+6),x=be16(p+10),y=be16(p+12),solid=p[14];
        uint32_t total=u32(p+15),offset=u32(p+19);int size=u16(p+23);
        if(index!=w->next||index>=w->bricks||!total||total>8000000||size>24000||n!=25+(size_t)size||offset>total||size>total-offset)return 0;
        if(!offset){if(w->bytes)return 0;w->bytes=malloc(total);if(!w->bytes)return 0;w->total=total;w->received=0;w->id=id;w->x=x;w->y=y;w->solid=solid;}
        if(!w->bytes||w->total!=(int)total||offset!=(unsigned)w->received||w->id!=id||w->x!=x||w->y!=y||w->solid!=solid)return 0;
        memcpy(w->bytes+offset,p+25,size);w->received+=size;
        if(w->received==w->total){if(guard(e,buildTile,w)<=0)return 0;free(w->bytes);w->bytes=NULL;w->next++;}
        return 1;
    }
    if(p[3]==5){
        if(w->started||w->bytes||w->next!=w->bricks||n<21)return 0;
        Start s={.w=w,.clock=p[4],.first=-1};size_t pos=5;
        for(int i=0;i<8;i++){if(n-pos<2)return 0;s.x[i]=be16(p+pos);pos+=2;if(s.x[i]==-1)continue;if(n-pos<10)return 0;s.y[i]=be16(p+pos);s.hp[i]=be64(p+pos+2);pos+=10;if(s.first<0)s.first=i;}
        if(pos!=n||s.first<0)return 0;
        w->started=1;return guard(e,start,&s)>0;
    }
    if(p[3]==7){Clock j={w,n==5?p[4]:0};return n==5&&w->started&&guard(e,resetClock,&j)>0;}
    return 0;
}
void AGNativeWatchCamera(int v,int kind,int code){
    if(v<0||v>=6)return;
    int bit=code==-3||code=='4'?1:code==-4||code=='6'?2:code==-1||code=='2'?4:code==-2||code=='8'?8:0;
    if(kind==0&&bit)atomic_fetch_or(&cameraKeys[v],bit);else if(kind==1&&bit)atomic_fetch_and(&cameraKeys[v],~bit);
    if(kind==0&&(code==-7||code=='R'||code=='r')){atomic_fetch_xor(&freeCamera[v],1);atomic_store(&cameraChanged[v],1);atomic_store(&cameraKeys[v],0);}
}
static void tickNative(void *e,int v){
    if(v<0||v>=6||!watches[v].started)return;Watch *w=&watches[v];
    uint8_t *g=global(AGSpectatorMaps[v].cameraClass);if(!g)return;
    if(atomic_exchange(&cameraChanged[v],0)&&!atomic_load(&freeCamera[v]))g[0xbc]=1;
    if(!atomic_load(&freeCamera[v]))return;
    g[0xbc]=0;*(int *)(g+0xb4)=0;*(int *)(g+0xb8)=0;
    int keys=atomic_load(&cameraKeys[v]),dx=((keys&2)!=0)-((keys&1)!=0),dy=((keys&8)!=0)-((keys&4)!=0);
    uint8_t *canvas=global(AGNotesMaps[v].canvas);
    int maxX=w->width-*(int *)(canvas+0x130),maxY=w->height-*(int *)(canvas+0x128);
    int x=*(int *)(g+0xa4)+dx*6,y=*(int *)(g+0xa8)+dy*6;
    x=x<0?0:x>maxX?(maxX>0?maxX:0):x;y=y<0?0:y>maxY?(maxY>0?maxY:0):y;
    *(int *)(g+0xa4)=*(int *)(g+0xac)=x;*(int *)(g+0xa8)=*(int *)(g+0xb0)=y;
}
void AGNativeWatchEnd(void *e,int v){pthread_mutex_lock(&watchLock);endNative(e,v);pthread_mutex_unlock(&watchLock);}
int AGNativeWatchPacket(void *e,int v,const uint8_t *p,size_t n){pthread_mutex_lock(&watchLock);int ok=packetNative(e,v,p,n);pthread_mutex_unlock(&watchLock);return ok;}
void AGNativeWatchTick(void *e,int v){if(pthread_mutex_trylock(&watchLock))return;tickNative(e,v);pthread_mutex_unlock(&watchLock);}
#endif
