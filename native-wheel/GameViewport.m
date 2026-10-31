#import "GameViewport.h"
#include <mach-o/dyld.h>
#include <pthread.h>
#include <math.h>
#include "NotesMap.h"
static pthread_mutex_t viewportLock=PTHREAD_MUTEX_INITIALIZER;
static double keyboardPerWidth;
static double keypadTopFraction=-1;
#ifdef AG_WHEEL_PREVIEW
static double previewFraction=.30;
void AGViewportPreview(CGFloat fraction){previewFraction=fraction;keypadTopFraction=-1;}
#endif
// Capture the native N/d keypad's height on the original game thread.
void AGViewportCapture(int variant){
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
#endif
}
// Called by the original N/d keypad painter with its actual SpriteBatch.
// N/a's camera is the Java canvas camera, not necessarily the keypad camera.
// Use the batch's combined matrix so insets, zoom and native margins agree.
__attribute__((visibility("default"))) void AGViewportKeypad(void *env,void *opaqueKeys,void *opaqueBatch){
    uint8_t *keys=opaqueKeys,*batch=opaqueBatch;if(!keys||!batch||!batch[0x85])return;
    int keyHeight=*(int *)(keys+0x28);if(keyHeight<1||keyHeight>4096)return;
    uint8_t *matrix=*(uint8_t **)(batch+0x20);
    uint8_t *values=matrix?*(uint8_t **)(matrix+0x10):NULL;
    if(!values||*(int *)(values+0x10)!=16)return;
    const float *m=(const float *)(values+0x14);
    double first=1;
    for(int corner=0;corner<2;corner++){
        double y=corner?keyHeight+.5:16;
        double w=m[7]*y+m[15];if(!isfinite(w)||fabs(w)<1e-6)return;
        double top=(1-(m[5]*y+m[13])/w)/2;
        if(!isfinite(top))return;if(top<first)first=top;
    }
    if(first>.1&&first<1){pthread_mutex_lock(&viewportLock);keypadTopFraction=first;pthread_mutex_unlock(&viewportLock);}
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

