#include "RoomNames.h"
#include "Lobby.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <mach-o/dyld.h>
#include "NativeMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static AGRoomNames cache[6];
static int loaded[6];
typedef struct {void *screen;int variant;} RoomJob;
// Verified JNI function slots against RoboVM 2.3.26's JNINativeInterface.
static void *makeString(void *env,const uint16_t *chars,int length){
    void **jni=*(void ***)env;
    void *(*make)(void *,const uint16_t *,int)=(void *)jni[163];
    void *s=make(env,chars,length);
    if(!s){void (*clear)(void *)=(void *)jni[17];clear(env);}
    return s;
}
static void releaseString(void *env,void *string){
    void **jni=*(void ***)env;void (*release)(void *,void *)=(void *)jni[23];release(env,string);
}
static int apply(void *env,void *context){
    RoomJob *job=context;void *screen=job->screen;
    if(!screen){void *(*get)(void *)=(void *)((uintptr_t)_dyld_get_image_header(0)+AGMaps[job->variant].room_get);screen=get(env);}
    return AGRoomApply(screen,&cache[job->variant],makeString,releaseString,env);
}
__attribute__((visibility("default"))) int AGRoomReceive(void *env,void *message,int variant){
    if(!env||!message||variant<0||variant>=6)return 0;
    uint8_t *input=*(uint8_t **)((uint8_t *)message+0x20);if(!input)return 0;
    uint8_t *array=*(uint8_t **)(input+0x10);if(!array)return 0;
    int length=*(int32_t *)(array+0x10),count=*(int32_t *)(input+0x18),pos=*(int32_t *)(input+0x20);
    if(length<0||count<0||count>length||pos<0||pos>count||count-pos>65535)return 0;
    AGRoomNames *names=malloc(sizeof *names);if(!names)return 0;
    if(!AGRoomParse(array+0x14+pos,(size_t)(count-pos),names)){free(names);return 0;}
    pthread_mutex_lock(&mutex);cache[variant]=*names;loaded[variant]=1;free(names);
    RoomJob job={NULL,variant};
    AGWheelGuard(env,apply,&job,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));
    pthread_mutex_unlock(&mutex);return 1;
}
__attribute__((visibility("default"))) void AGRoomRebuild(void *env,void *screen,int variant){
    if(!env||!screen||variant<0||variant>=6)return;
    AGLobbyRemember(screen,variant);
    pthread_mutex_lock(&mutex);
    if(loaded[variant]){RoomJob job={screen,variant};AGWheelGuard(env,apply,&job,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));}
    pthread_mutex_unlock(&mutex);
}
