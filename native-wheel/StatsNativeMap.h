/* Read-only getters verified in the unchanged RoboVM executable. */
#ifndef AG_STATS_NATIVE_MAP_H
#define AG_STATS_NATIVE_MAP_H
#include <stdint.h>
typedef struct { uintptr_t player,flags,costume; } AGStatsNativeMap;
static const AGStatsNativeMap AGStatsMaps[6]={
    {0x56ff3c,0x56ff00,0x516cd4},
    {0x65a4f0,0x65a4b4,0x6047cc},
    {0x73f1b4,0x73f178,0x6e9490},
    {0x823e78,0x823e3c,0x7ce154},
    {0x908b3c,0x908b00,0x8b2e18},
    {0x9ed800,0x9ed7c4,0x997adc},
};
#endif
