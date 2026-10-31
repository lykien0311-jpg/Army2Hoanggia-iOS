#import "GameViewport.h"
#include <mach-o/dyld.h>
#include <pthread.h>
#include <math.h>
#include <stdatomic.h>
#include <string.h>
#include "NotesMap.h"
static pthread_mutex_t viewportLock=PTHREAD_MUTEX_INITIALIZER;
static double keyboardPerWidth;
static double keypadTopFraction=-1;
static atomic_int wheelVisible=0;
void AGViewportWheelVisible(int visible){atomic_store(&wheelVisible,visible);}
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
#ifdef AG_WHEEL_PREVIEW
static double previewFraction=.30;
void AGViewportPreview(CGFloat fraction){previewFraction=fraction;keypadTopFraction=-1;}
void AGViewportPreviewTop(CGFloat fraction){keypadTopFraction=fraction;}
#endif
// Capture the native N/d keypad's height on the original game thread.
void AGViewportCapture(void *env,int variant){
#ifndef AG_WHEEL_PREVIEW
    if(variant<0||variant>=6)return;
    uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    uint8_t *canvas=*(uint8_t **)(base+AGNotesMaps[variant].canvas);
    uint8_t *settings=*(uint8_t **)(base+0x1f71860);
    uint8_t *keyClass=*(uint8_t **)(base+0x1f75860);
    if(!canvas||!settings||!keyClass)return;
    uint8_t *keys=*(uint8_t **)(keyClass+0xa0);
    int width=*(int *)(canvas+0x130),height=keys?*(int *)(keys+0x28):0;
    if(width<160||width>4096||height<0||height>4096)return;
    double ratio=settings[0xc0]&&keys?(double)height/width:0;
    pthread_mutex_lock(&viewportLock);keyboardPerWidth=ratio;
    if(ratio<=0)keypadTopFraction=-1;
    pthread_mutex_unlock(&viewportLock);
    if(env&&ratio>0&&atomic_load(&wheelVisible)){
        uint8_t *renderer=*(uint8_t **)(base+0x1f73100);
        uint8_t *batch=renderer?*(uint8_t **)(renderer+0xa0):NULL;
        AGViewportKeypad(env,keys,batch);
    }
#endif
}
// Read the FINAL native key rectangles. N/h translates them after the
// constructor loop (1fd9b4..1fd9dc); pre-translation heights leave a gap.
// Reuse the exact List/Iterator entry points used by the original painter.
typedef struct { uint8_t *keys,*batch;double top; } AGKeyProjection;
static int AGProjectKeys(void *env,void *opaque){
    AGKeyProjection *job=opaque;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    uint8_t *matrix=*(uint8_t **)(job->batch+0x20);
    uint8_t *values=matrix?*(uint8_t **)(matrix+0x10):NULL;
    if(!values||*(int *)(values+0x10)!=16)return 0;
    float m[16];memcpy(m,values+0x14,sizeof m);
    uint8_t *layout=*(uint8_t **)(job->keys+0x20);
    uint8_t *list=layout?*(uint8_t **)(layout+0x18):NULL;if(!list)return 0;
    void *(*iterator)(void *,void *)=(void *)(base+0xbc5b20);
    int (*hasNext)(void *,void *)=(void *)(base+0xbc1f24);
    void *(*next)(void *,void *)=(void *)(base+0xbc1f78);
    void *volatile iter=iterator(env,list);if(!iter)return 0;
    double first=1;int count=0;
    while(count<32&&(hasNext(env,iter)&255)){
        uint8_t *volatile key=next(env,iter);if(!key)return 0;
        double x=*(float *)(key+0x50),y=*(float *)(key+0x54);
        double width=*(float *)(key+0x58),height=*(float *)(key+0x5c);
        if(!isfinite(x)||!isfinite(y)||!isfinite(width)||!isfinite(height)||width<=0||height<=0)return 0;
        for(int corner=0;corner<4;corner++){
            double px=x+((corner&1)?width:0),py=y+((corner&2)?height:0);
            double w=m[3]*px+m[7]*py+m[15];if(!isfinite(w)||fabs(w)<1e-6)return 0;
            double top=(1-(m[1]*px+m[5]*py+m[13])/w)/2;
            if(!isfinite(top))return 0;if(top<first)first=top;
        }
        count++;
    }
    if(count<1||first<=.1||first>=1)return 0;
    job->top=first;return 1;
}
__attribute__((visibility("default"))) void AGViewportKeypad(void *env,void *keys,void *batch){
    if(!env||!keys||!batch||!atomic_load(&wheelVisible))return;
    AGKeyProjection job={keys,batch,-1};
    if(AGWheelGuard(env,AGProjectKeys,&job,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54))>0){
        pthread_mutex_lock(&viewportLock);keypadTopFraction=job.top;pthread_mutex_unlock(&viewportLock);
    }
}
static UIView *AGRenderView(UIView *view){
    Class layer=NSClassFromString(@"CAEAGLLayer");
    if(layer&&[view.layer isKindOfClass:layer])return view;
    for(UIView *child in view.subviews){UIView *found=AGRenderView(child);if(found)return found;}
    return nil;
}
CGRect AGGameRect(UIView *view){
    UIEdgeInsets safe=view.safeAreaInsets;CGRect bounds=view.bounds;
    pthread_mutex_lock(&viewportLock);double ratio=keyboardPerWidth,top=keypadTopFraction;pthread_mutex_unlock(&viewportLock);
    CGFloat reserved=bounds.size.width*ratio;
#ifdef AG_WHEEL_PREVIEW
    reserved=bounds.size.height*previewFraction;
#endif
    CGFloat bottom=reserved>0?bounds.size.height-reserved:bounds.size.height-safe.bottom;
    if(top>0){
        CGRect surface=bounds;
        for(UIWindow *window in UIApplication.sharedApplication.windows){
            if(window.hidden||window.windowLevel!=UIWindowLevelNormal)continue;
            UIView *render=AGRenderView(window.rootViewController.view);
            if(render){surface=[render convertRect:render.bounds toView:view];break;}
        }
        bottom=CGRectGetMinY(surface)+surface.size.height*top;
    }
    bottom=MAX(safe.top+60,MIN(bounds.size.height,bottom));
    return CGRectMake(safe.left,safe.top,MAX(1,bounds.size.width-safe.left-safe.right),MAX(1,bottom-safe.top));
}
@implementation AGGameWindow
- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event{
    if(self.passesGameKeys&&!self.rootViewController.presentedViewController&&point.y>=self.gameBottom)return nil;
    return [super hitTest:point withEvent:event];
}
@end

