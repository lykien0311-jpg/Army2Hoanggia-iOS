#ifndef AG_STATS_H
#define AG_STATS_H
#include <stddef.h>
#include <stdint.h>
enum { AG_STATS_CHARACTERS=10, AG_STATS_COUNT=5, AG_STATS_PACKET_SIZE=455 };
typedef struct {
    uint8_t enabled[AG_STATS_CHARACTERS];
    int32_t base[AG_STATS_CHARACTERS][AG_STATS_COUNT];
    int32_t point[AG_STATS_CHARACTERS][AG_STATS_COUNT];
    int32_t attackGain[AG_STATS_CHARACTERS];
} AGStatsRules;
int AGStatsParse(const uint8_t *,size_t,AGStatsRules *);
int AGStatsCalculate(const AGStatsRules *,int,const int64_t *,const int64_t *,const int64_t *,int64_t *);
int AGStatsReceive(void *,void *,int);
void AGStatsApply(void *,int,void *,void *,void *,void *);
#endif
