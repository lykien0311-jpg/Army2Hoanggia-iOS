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

typedef void (*Painter)(void *,void *,void *);
typedef void (*ShapeCall)(void *,void *);
typedef void (*ShapeColor)(void *,void *,float,float,float,float);
typedef void (*ShapeLine)(void *,void *,float,float,float,float);
typedef struct {
    uint8_t *graphics;
    void *shapes;
    int x,y,tier,level,layer,frame,tx,ty,started;
    ShapeColor color;
    ShapeLine line;
} Paint;

static void color(void *env,Paint *p,int rgb) {
    p->color(env,p->shapes,((rgb>>16)&255)/255.f,((rgb>>8)&255)/255.f,(rgb&255)/255.f,1.f);
}

static void line(void *env,Paint *p,int x,int y,int toX,int toY) {
    p->line(env,p->shapes,x+p->tx,y+p->ty,toX+p->tx,toY+p->ty);
}

static int mix(int rgb,int white) {
    int r=(rgb>>16)&255,g=(rgb>>8)&255,b=rgb&255;
    r+=(255-r)*white/255;g+=(255-g)*white/255;b+=(255-b)*white/255;
    return (r<<16)|(g<<8)|b;
}

static int palette(int level,int frame) {
    const int colors[]={0xdce8ff,0x0048ff,0x00b300,0xff7f00,0xcdffff,0xff0019};
    const int bands[]={0,1,1,1,1,2,2,2,2,3,3,3,4,4,3,5,5};
    const int pulse=level==4?2:level==8?3:level==14?5:bands[level];
    return colors[frame%40<20?bands[level]:pulse];
}

static void spark(void *env,Paint *p,int x,int y,int radius,int rgb) {
    color(env,p,mix(rgb,168));
    line(env,p,x-radius,y,x+radius,y);
    line(env,p,x,y-radius,x,y+radius);
}

static void ring(void *env,Paint *p,int rgb) {
    const int rx=12+p->tier*2,ry=3+p->tier/2;
    const int start=p->layer?0:12;
    for(int i=start;i<start+12;i++) {
        const float t=i*0.261799388f,u=(i+1)*0.261799388f;
        const int glow=40+(12-abs((i+24-p->frame%24)%24-12))*12;
        color(env,p,mix(rgb,glow));
        line(env,p,p->x+lroundf(cosf(t)*rx),p->y+lroundf(sinf(t)*ry),
             p->x+lroundf(cosf(u)*rx),p->y+lroundf(sinf(u)*ry));
    }
}

static void shards(void *env,Paint *p,int rgb) {
    const int count=p->tier>=5?4:2;
    for(int i=0;i<count;i++) {
        const float t=p->frame*0.08726646f+i*6.2831853f/count;
        const float depth=sinf(t);
        if((depth>=0)!=p->layer)continue;
        const int x=p->x+lroundf(cosf(t)*(10+p->tier*2));
        const int y=p->y-13+lroundf(depth*5)-(p->frame/2+i*7)%12;
        if(p->tier>=5){
            color(env,p,mix(rgb,100));
            line(env,p,x,y-5,x-3,y);
            line(env,p,x-3,y,x,y+5);
            line(env,p,x,y+5,x+3,y);
            line(env,p,x+3,y,x,y-5);
        }
        spark(env,p,x,y,p->tier>=3?2:1,rgb);
    }
}

static void flames(void *env,Paint *p,int rgb) {
    const int broad=p->tier==7;
    for(int side=-1;side<=1;side+=2) {
        for(int i=0;i<(broad?4:3);i++) {
            const int beat=(p->frame+i*5+(side<0?7:0))%16;
            const int wave=beat<8?beat:16-beat;
            const int x=p->x+side*(10+i*3+(broad?2:0));
            const int y=p->y-(p->layer?2:8)-i*2;
            const int span=(broad?17:11)+wave+i*2;
            color(env,p,mix(rgb,30+i*45));
            line(env,p,x,y,x+side*4,y-span/2);
            line(env,p,x+side*4,y-span/2,x+side*2,y-span);
            color(env,p,mix(rgb,190));
            line(env,p,x+side,y-3,x+side*3,y-span/2);
            if(p->layer&&i==1)spark(env,p,x+side*3,y-span-wave,2,rgb);
        }
    }
}

static int finish(void *env,void *opaque) {
    Paint *p=opaque;
    ((ShapeCall)(base()+0x1b5698))(env,p->shapes);
    p->started=0;
    return 1;
}

static int render(void *env,void *opaque) {
    Paint *p=opaque;
    uintptr_t image=base();
    // Same ShapeRenderer calls as Graphics.e, grouped into one batch per layer.
    if(p->graphics[0x51]&&p->graphics[0x52])((ShapeCall)(image+0xc44c88))(env,p->graphics);
    ((void (*)(void *,void *,int))(image+0x1b5634))(env,p->shapes,1);
    ((ShapeCall)(image+0x1b5638))(env,p->shapes);
    p->started=1;
    const int rgb=palette(p->level,p->frame);
    ring(env,p,rgb);
    if(p->tier>=2)shards(env,p,rgb);
    if(p->tier>=6)flames(env,p,rgb);
    return finish(env,p);
}

static int visible(Paint *p) {
    const uint8_t *g=p->graphics;
    if(!g[0x51])return 1;
    int x=p->x+p->tx,y=p->y+p->ty;
    int cx=*(int *)(g+0x38),cy=*(int *)(g+0x3c);
    int width=*(int *)(g+0x40),height=*(int *)(g+0x44);
    return width>0&&height>0&&x+40>=cx&&x-40<=cx+width&&y+10>=cy&&y-58<=cy+height;
}

static void draw(void *env,Paint *p) {
    const uint8_t *g=p->graphics;
    p->shapes=*(void **)(g+0x18);
    p->tx=g[0x50]?*(int *)(g+0x48):0;
    p->ty=g[0x50]?*(int *)(g+0x4c):0;
    if(!p->shapes||*(void **)((uint8_t *)p->shapes+0x30)||!visible(p))return;
    uint8_t *lineMode=(uint8_t *)p->shapes+0x4c;
    uint8_t savedMode=*lineMode;
    void *trap=(void *)(base()+0x1300d54);
    if(AGWheelGuard(env,render,p,trap)<=0 && p->started)AGWheelGuard(env,finish,p,trap);
    *lineMode=savedMode;
}

__attribute__((visibility("default"))) void AGAuraPaintActor(void *env,uint8_t *actor,uint8_t *graphics,int v,Painter nativePaint) {
    if(AGBossPaintActor(env,actor,graphics,v))return;
    const uint32_t id=*(uint32_t *)(actor+0x7c);
    const unsigned hero=actor[0x16c];
    int aura=0;
    if(hero<10 && id && id<=INT32_MAX && actor[0x159] && *(int64_t *)(actor+0x68)>0){
        pthread_mutex_lock(&lock);
        aura=AGAuraLookup(&states[v],id,hero,1);
        pthread_mutex_unlock(&lock);
    }
    if(!aura){nativePaint(env,actor,graphics);return;}
    uintptr_t image=base();
    Paint paint={.graphics=graphics,.x=*(int *)(actor+0x114),.y=*(int *)(actor+0x118),
                 .tier=aura>>5,.level=aura&31,.frame=(int)((uint64_t)(now()/0.042)%1440),
                 .color=(ShapeColor)(image+0x1b5624),.line=(ShapeLine)(image+0x3f3cb4)};
    draw(env,&paint);
    nativePaint(env,actor,graphics);
    paint.layer=1;draw(env,&paint);
}
