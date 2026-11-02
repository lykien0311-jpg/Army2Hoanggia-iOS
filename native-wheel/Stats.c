/* BalanceClient494's equipment summary. Combat actors remain server-owned. */
#include "Stats.h"
#include <limits.h>
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

#ifndef AG_STATS_HOST
#include <pthread.h>
#include <mach-o/dyld.h>
#include "NativeMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {int variant;uintptr_t connection;} StatsConnection;
typedef struct {uintptr_t connection;AGStatsRules rules;} StatsCache;
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
    if(!env||!message||v<0||v>=6||*(int8_t *)((uint8_t *)message+0x30)!=-110)return 0;
    uintptr_t id=currentConnection(env,v);if(!id)return 1;
    pthread_mutex_lock(&statsMutex);
    if(caches[v].connection!=id)caches[v]=(StatsCache){.connection=id};
    pthread_mutex_unlock(&statsMutex);
    uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);
    uint8_t *array=input?*(uint8_t **)(input+0x10):0;if(!array)return 1;
    int capacity=*(int *)(array+0x10),count=*(int *)(input+0x18),pos=*(int *)(input+0x20);
    if(capacity<0||count<0||count>capacity||pos<0||pos>count||count-pos!=AG_STATS_PACKET_SIZE)return 1;
    AGStatsRules rules;if(!AGStatsParse(array+0x14+pos,(size_t)(count-pos),&rules))return 1;
    pthread_mutex_lock(&statsMutex);caches[v]=(StatsCache){.connection=id,.rules=rules};pthread_mutex_unlock(&statsMutex);
    return 1;
}
static int64_t *array5(uint8_t *p){return p&&*(int *)(p+0x10)>=AG_STATS_COUNT?(int64_t *)(p+0x18):0;}
__attribute__((visibility("default"))) void AGStatsApply(void *env,int v,void *screen,void *player,void *flat,void *percent){
    if(!env||v<0||v>=6||!screen||!player)return;
    uintptr_t id=currentConnection(env,v);if(!id)return;
    AGStatsRules rules;pthread_mutex_lock(&statsMutex);
    int ready=caches[v].connection==id;
    if(ready)rules=caches[v].rules;
    pthread_mutex_unlock(&statsMutex);if(!ready)return;
    uint8_t *p=player,*s=screen;
    int64_t *points=array5(*(uint8_t **)(p+0x28));
    int64_t *out=array5(*(uint8_t **)(s+0xa0));
    AGStatsCalculate(&rules,p[0xd9],points,array5(flat),array5(percent),out);
}
#endif
