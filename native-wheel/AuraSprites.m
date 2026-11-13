#import <Foundation/Foundation.h>
#include <mach-o/dyld.h>
#include "AuraGeometry.h"

extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
@interface AGAuraResources : NSObject @end
@implementation AGAuraResources @end
static void *atlases[27];
static int attempted[27];
typedef struct { void *graphics; int x,y,tier,level,layer,frame; } AGAuraSpriteJob;
static int palette(int level) {
    if(level<1)return 0;if(level<=3)return 1;if(level==4)return 6;
    if(level<=7)return 2;if(level==8)return 7;if(level<=11)return 3;
    if(level<=14)return 4;return 5;
}
static int sprite(void *env,void *opaque) {
    AGAuraSpriteJob *j=opaque;
    int key=(j->tier-5)*9+palette(j->level);
    uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    if(!atlases[key]&&!attempted[key]) {
        attempted[key]=1;
        NSBundle *bundle=[NSBundle bundleForClass:AGAuraResources.class];
        NSString *path=[bundle pathForResource:[NSString stringWithFormat:@"k%d-p%d",j->tier-4,palette(j->level)] ofType:@"png" inDirectory:@"viewer/art"];
        NSData *data=path?[NSData dataWithContentsOfFile:path]:nil;
        if(!data.length||data.length>1000000)return 0;
        void **jni=*(void ***)env;
        void *volatile bytes=((void *(*)(void *,int))jni[176])(env,(int)data.length);
        if(!bytes)return 0;
        ((void (*)(void *,void *,int,int,const uint8_t *))jni[208])(env,bytes,0,(int)data.length,data.bytes);
        void *volatile image=((void *(*)(void *,void *,int,int))(base+0xc46e04))(env,bytes,0,(int)data.length);
        if(image)atlases[key]=((void *(*)(void *,void *))jni[21])(env,image);
        ((void (*)(void *,void *))jni[23])(env,bytes);
        if(image)((void (*)(void *,void *))jni[23])(env,image);
    }
    if(!atlases[key])return 0;
    const short *r=AGAuraGeometry[j->tier-5]+(((j->frame>>1)&31)*2+j->layer)*6;
    if(r[2]>0&&r[3]>0)
        ((void (*)(void *,void *,void *,int,int,int,int,int,int,int,int))(base+0x1c6150))
            (env,j->graphics,atlases[key],r[0],r[1],r[2],r[3],0,j->x+r[4],j->y+r[5],20);
    return 1;
}
int AGAuraSpritePaint(void *env,void *graphics,int x,int y,int tier,int level,int layer,int frame) {
    if(!env||!graphics||tier<5||tier>7||level<0||level>16||layer<0||layer>1)return 0;
    AGAuraSpriteJob j={graphics,x,y,tier,level,layer,frame};
    return AGWheelGuard(env,sprite,&j,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54))>0;
}
