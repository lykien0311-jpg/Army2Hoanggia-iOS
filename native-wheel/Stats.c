/* BalanceClient494's equipment summary. Combat actors remain server-owned. */
#include "Stats.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>
static uint32_t read32(const uint8_t **p){
    const uint8_t *b=*p;*p+=4;
    return (uint32_t)b[0]<<24|(uint32_t)b[1]<<16|(uint32_t)b[2]<<8|b[3];
}
int AGStatsParse(const uint8_t *bytes,size_t length,AGStatsRules *out){
    if(!bytes||!out||length!=AG_STATS_PACKET_SIZE)return 0;
    const uint8_t *p=bytes;
    /* Independent JAR/server constant:1379154228, not an invented version. */
    if(read32(&p)!=1379154228||*p++!=AG_STATS_CHARACTERS)return 0;
    AGStatsRules next={0};
    for(int c=0;c<AG_STATS_CHARACTERS;c++){
        next.enabled[c]=!!*p++;
        for(int j=0;j<AG_STATS_COUNT;j++){
            uint32_t n=read32(&p);if(n>INT32_MAX)return 0;next.base[c][j]=(int32_t)n;
        }
        for(int j=0;j<AG_STATS_COUNT;j++){
            uint32_t n=read32(&p);if(n<1||n>INT32_MAX)return 0;next.point[c][j]=(int32_t)n;
        }
        uint32_t n=read32(&p);if(n>INT32_MAX)return 0;next.attackGain[c]=(int32_t)n;
    }
    *out=next;return 1;
}
/* GEM1 follows the unchanged 455-byte Balance494 prefix. */
int AGStatsGemHeader(const uint8_t *bytes,size_t length,int32_t *base,uint32_t *count){
    if(!bytes||!base||!count||length<48)return 0;
    const uint8_t *p=bytes;int32_t next[10];
    if(read32(&p)!=0x47454d31)return 0;
    for(int c=0;c<10;c++){uint32_t n=read32(&p);if(n<1||n>INT32_MAX)return 0;next[c]=(int32_t)n;}
    uint32_t n=read32(&p);if(n>65536||length!=48+(size_t)n*5)return 0;
    memcpy(base,next,sizeof next);*count=n;return 1;
}
static int64_t read64(const uint8_t **p){uint64_t a=read32(p),b=read32(p);return (int64_t)(a<<32|b);}
int AGStatsSnapshotParse(const uint8_t *bytes,size_t length,AGStatsSnapshot *out){
    if(!bytes||!out||length<146)return 0;
    const uint8_t *p=bytes;AGStatsSnapshot next={0};
    if(read32(&p)!=0x47454d32||(next.hero=*p++)>=10)return 0;
    for(int j=0;j<5;j++){uint32_t n=read32(&p);if(n>INT32_MAX)return 0;next.points[j]=(int32_t)n;}
    next.count=*p++;if(next.count>6||length!=146+(size_t)next.count*4)return 0;
    for(int j=0;j<next.count;j++){uint32_t h=read32(&p);if((h&0xffff0000)!=0x10000)return 0;next.handles[j]=(int32_t)h;}
    for(int j=0;j<5;j++)next.flat[j]=read64(&p);
    for(int j=0;j<5;j++)next.percent[j]=read64(&p);
    for(int j=0;j<5;j++){int64_t n=read64(&p);if(n<0||n>INT32_MAX)return 0;next.values[j]=n;}
    next.valid=1;*out=next;return 1;
}
int AGStatsExact(const AGStatsSnapshot *s,int hero,const int64_t *points,const int64_t *flat,const int64_t *percent,const int32_t *handles,int count,int64_t *out){
    if(!s||!s->valid||hero!=s->hero||count!=s->count||count<0||count>6||!points||!flat||!percent||!handles||!out)return 0;
    for(int j=0;j<5;j++)if(points[j]!=s->points[j]||flat[j]!=s->flat[j]||percent[j]!=s->percent[j])return 0;
    uint8_t seen[6]={0};
    for(int i=0;i<count;i++){
        int found=-1;for(int j=0;j<count;j++)if(!seen[j]&&handles[i]==s->handles[j]){found=j;break;}
        if(found<0)return 0;
        seen[found]=1;
    }
    memcpy(out,s->values,sizeof s->values);return 1;
}
static int64_t add(int64_t a,int64_t b){
    int64_t out;if(!__builtin_add_overflow(a,b,&out))return out;
    return b<0?INT64_MIN:INT64_MAX;
}
static int64_t multiply(int64_t a,int64_t b){
    int64_t out;if(!__builtin_mul_overflow(a,b,&out))return out;
    return (a<0)!=(b<0)?INT64_MIN:INT64_MAX;
}
int AGStatsCalculate(const AGStatsRules *r,int c,const int64_t *points,const int64_t *flat,const int64_t *percent,int64_t *out){
    if(!r||c<0||c>=AG_STATS_CHARACTERS||!r->enabled[c]||!points||!flat||!percent||!out)return 0;
    int64_t next[AG_STATS_COUNT];
    for(int j=0;j<AG_STATS_COUNT;j++){
        if(r->base[c][j]<0||r->point[c][j]<1||r->attackGain[c]<0)return 0;
        int64_t n=add(points[j],flat[j]),value;
        if(j==1){
            int64_t gain=multiply(n,r->attackGain[c])/r->point[c][j];
            value=multiply(r->base[c][j],add(add(100,gain),percent[j]))/100;
        }else{
            int64_t base=add(r->base[c][j],multiply(n,r->point[c][j]));
            value=multiply(base,add(100,percent[j]))/100;
        }
        next[j]=value<0?0:value>INT32_MAX?INT32_MAX:value;
    }
    memcpy(out,next,sizeof next);return 1;
}
static int64_t safe(int64_t n){return n<0?0:n>INT32_MAX?INT32_MAX:n;}
/* Explicit wrapping reproduces Java int arithmetic in the legacy formula. */
static int32_t iadd(int32_t a,int32_t b){return (int32_t)((uint32_t)a+(uint32_t)b);}
static int32_t imul(int32_t a,int32_t b){return (int32_t)((uint32_t)a*(uint32_t)b);}
int AGStatsExtended(const AGStatsRules *r,int c,const int64_t *points,const int64_t *flat,const int64_t *percent,const int64_t *gems,int32_t nativeBase,int64_t *out){
    if(!r||c<0||c>=10||!points||!flat||!percent||!out)return 0;
    if(!gems)return AGStatsCalculate(r,c,points,flat,percent,out);
    if(nativeBase<1)return 0;
    int64_t next[5];
    for(int j=0;j<5;j++){
        int64_t sum=add(points[j],flat[j]),g=gems[j],p=add(percent[j],-g),value;
        if(r->enabled[c]){
            if(r->point[c][j]<1||r->base[c][j]<0||r->attackGain[c]<0)return 0;
            value=j==1?safe(add(add(100,multiply(sum,r->attackGain[c])/r->point[c][j]),p)):
                safe(multiply(add(r->base[c][j],multiply(sum,r->point[c][j])),add(100,p))/100);
            value=safe(multiply(value,add(100,g))/100);
            if(j==1)value=multiply(r->base[c][1],value)/100;
        }else{
            int32_t legacy;
            if(j==0){legacy=iadd(iadd(1000,imul((int32_t)points[0],10)),imul((int32_t)flat[0],10));legacy=iadd(legacy,imul(iadd(1000,(int32_t)points[0]),(int32_t)p)/100);}
            else if(j==1)legacy=imul(imul(nativeBase,iadd(iadd(100,(int32_t)sum/3),(int32_t)p))/100,100)/nativeBase;
            else{legacy=imul((int32_t)sum,10);legacy=iadd(legacy,imul(legacy,(int32_t)p)/100);}
            value=safe(multiply(legacy,add(100,g))/100);
            if(j==1)value=multiply(nativeBase,value)/100;
        }
        next[j]=safe(value);
    }
    memcpy(out,next,sizeof next);return 1;
}

#ifndef AG_STATS_HOST
#include <pthread.h>
#include <mach-o/dyld.h>
#include "NativeMap.h"
#include "StatsNativeMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {int variant;uintptr_t connection;} StatsConnection;
typedef struct {uintptr_t connection;AGStatsRules rules;AGStatsSnapshot snapshot;int32_t nativeBase[10];uint32_t count;uint8_t *gems;int extended;} StatsCache;
static StatsCache caches[6];
static pthread_mutex_t statsMutex=PTHREAD_MUTEX_INITIALIZER;
static int connection(void *env,void *opaque){
    StatsConnection *c=opaque;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    uint8_t *(*service)(void *)=(void *)(base+AGMaps[c->variant].service);
    uint8_t *s=service(env);c->connection=s?*(uintptr_t *)(s+0x10):0;
    return c->connection!=0;
}
static uintptr_t currentConnection(void *env,int v){
    StatsConnection c={.variant=v};
    return AGWheelGuard(env,connection,&c,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54))>0?c.connection:0;
}
int AGStatsReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return 0;
    int command=*(int8_t *)((uint8_t *)message+0x30);if(command!=-110&&command!=-124)return 0;
    uintptr_t id=currentConnection(env,v);if(!id)return 1;
    pthread_mutex_lock(&statsMutex);
    if(caches[v].connection!=id){free(caches[v].gems);caches[v]=(StatsCache){.connection=id};}
    pthread_mutex_unlock(&statsMutex);
    uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);
    uint8_t *array=input?*(uint8_t **)(input+0x10):0;if(!array)return 1;
    int capacity=*(int *)(array+0x10),count=*(int *)(input+0x18),pos=*(int *)(input+0x20);
    if(capacity<0||count<0||count>capacity||pos<0||pos>count)return 1;
    const uint8_t *bytes=array+0x14+pos;size_t length=(size_t)(count-pos);
    if(command==-124){
        AGStatsSnapshot s;if(!AGStatsSnapshotParse(bytes,length,&s))return 1;
        pthread_mutex_lock(&statsMutex);if(caches[v].connection==id)caches[v].snapshot=s;pthread_mutex_unlock(&statsMutex);return 1;
    }
    StatsCache next={.connection=id};
    if(length<455||!AGStatsParse(bytes,455,&next.rules))return 1;
    if(length>455){
        if(!AGStatsGemHeader(bytes+455,length-455,next.nativeBase,&next.count))return 1;
        next.extended=1;
        if(next.count){next.gems=malloc((size_t)next.count*5);if(!next.gems)return 1;memcpy(next.gems,bytes+455+48,(size_t)next.count*5);}
    }
    pthread_mutex_lock(&statsMutex);
    if(caches[v].connection==id){free(caches[v].gems);caches[v]=next;next.gems=0;}
    pthread_mutex_unlock(&statsMutex);free(next.gems);
    return 1;
}
static int64_t *array5(uint8_t *p){return p&&*(int *)(p+0x10)>=AG_STATS_COUNT?(int64_t *)(p+0x18):0;}
/* Item+0x80 is the native inventory handle. The caller passes the exact costume
 * selected by the original calculator, avoiding any extra Java method calls. */
static void collect(uint8_t *item,StatsCache *cache,int32_t *handles,int *count,int64_t *gems){
    if(!item)return;int64_t handle=*(int64_t *)(item+0x80);
    if(handle<65536||handle>131071)return;
    if(*count>=6){*count=7;return;}handles[(*count)++]=(int32_t)handle;
    uint32_t index=(uint32_t)handle&65535;
    if(cache->extended&&index<cache->count)for(int j=0;j<5;j++)gems[j]+=cache->gems[index*5+j];
}
static void applyValues(uintptr_t id,int v,void *screen,void *player,const int64_t *f,const int64_t *pct,void *costume){
    uint8_t *p=player,*s=screen;
    int64_t *points=array5(*(uint8_t **)(p+0x28));
    int64_t *out=array5(*(uint8_t **)(s+0xa0));
    if(!points||!out||!f||!pct)return;
    pthread_mutex_lock(&statsMutex);StatsCache *cache=&caches[v];
    if(cache->connection==id){
        int32_t handles[6]={0};int count=0;int64_t gems[5]={0};
        uint8_t *outfit=*(uint8_t **)(p+0x78),*slots=outfit?*(uint8_t **)(outfit+0x10):0;
        if(slots&&*(int32_t *)(slots+0x10)>=5){
            for(int i=0;i<5;i++)collect(*(uint8_t **)(slots+0x18+i*8),cache,handles,&count,gems);
            collect(costume,cache,handles,&count,gems);
            if(!AGStatsExact(&cache->snapshot,p[0xd9],points,f,pct,handles,count,out))
                AGStatsExtended(&cache->rules,p[0xd9],points,f,pct,cache->extended?gems:0,cache->nativeBase[p[0xd9]<10?p[0xd9]:0],out);
        }
    }
    pthread_mutex_unlock(&statsMutex);
}
__attribute__((visibility("default"))) void AGStatsApply(void *env,int v,void *screen,void *player,void *flat,void *percent,void *costume){
    if(!env||v<0||v>=6||!screen||!player)return;
    uintptr_t id=currentConnection(env,v);if(id)applyValues(id,v,screen,player,array5(flat),array5(percent),costume);
}
typedef struct {int variant;uint8_t *screen,*player,*costume;int64_t flat[5],percent[5];} StatsRefresh;
static int sumItem(StatsRefresh *r,uint8_t *item){
    if(!item)return 1;
    int64_t *flat=array5(*(uint8_t **)(item+0x48)),*pct=array5(*(uint8_t **)(item+0x50));
    if(!flat||!pct)return 0;
    for(int j=0;j<5;j++){r->flat[j]=add(r->flat[j],flat[j]);r->percent[j]=add(r->percent[j],pct[j]);}return 1;
}
static int refreshNative(void *env,void *opaque){
    StatsRefresh *r=opaque;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    const AGStatsNativeMap *m=&AGStatsMaps[r->variant];
    uint8_t *(*playerGet)(void *)=(void *)(base+m->player);
    uint8_t *(*flagsGet)(void *)=(void *)(base+m->flags);
    int64_t (*costumeGet)(void *)=(void *)(base+m->costume);
    r->player=playerGet(env);if(!r->player||r->player[0xd9]>=10)return 0;
    uint8_t *outfit=*(uint8_t **)(r->player+0x78),*slots=outfit?*(uint8_t **)(outfit+0x10):0;
    if(!slots||*(int32_t *)(slots+0x10)<5)return 0;
    for(int j=0;j<5;j++)if(!sumItem(r,*(uint8_t **)(slots+0x18+j*8)))return 0;
    uint8_t *flags=flagsGet(env);int hero=r->player[0xd9];
    if(!flags||*(int32_t *)(flags+0x10)<=hero)return 0;
    if(flags[0x14+hero]){
        uint8_t *vector=*(uint8_t **)(r->screen+0xb0),*items=vector?*(uint8_t **)(vector+0x18):0;
        int count=vector?*(int32_t *)(vector+0x24):0;
        if(count<0||count>65536||(!items&&count)||(items&&count>*(int32_t *)(items+0x10)))return 0;
        int64_t handle=costumeGet(env);
        for(int i=0;i<count;i++){
            uint8_t *item=*(uint8_t **)(items+0x18+i*8);
            if(item&&*(int64_t *)(item+0x80)==handle){r->costume=item;break;}
        }
        if(!sumItem(r,r->costume))return 0;
    }
    return 1;
}
/* A reply can arrive after the screen calculated its totals. Refresh the
 * display before paint, using C stack totals and the current selection only. */
__attribute__((visibility("default"))) void AGStatsRefresh(void *env,int v,void *screen){
    if(!env||v<0||v>=6||!screen)return;
    uintptr_t id=currentConnection(env,v);if(!id)return;
    StatsRefresh r={.variant=v,.screen=screen};
    if(AGWheelGuard(env,refreshNative,&r,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54))>0)
        applyValues(id,v,screen,r.player,r.flat,r.percent,r.costume);
}
#endif
