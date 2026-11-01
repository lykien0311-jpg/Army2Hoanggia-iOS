#ifndef AG_ROOM_NAMES_H
#define AG_ROOM_NAMES_H
#include <stdint.h>
#include <stddef.h>
#define AG_ROOM_CHARS 256
typedef struct { uint8_t present[256];uint16_t length[256],text[256][AG_ROOM_CHARS]; } AGRoomNames;
int AGRoomParse(const uint8_t *,size_t,AGRoomNames *);
typedef void *(*AGMakeString)(void *,const uint16_t *,int);
typedef void (*AGReleaseString)(void *,void *);
int AGRoomApply(void *,const AGRoomNames *,AGMakeString,AGReleaseString,void *);
#endif
