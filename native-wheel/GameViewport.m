#import "GameViewport.h"
#include <mach-o/dyld.h>
#include <pthread.h>
#include "NotesMap.h"
static pthread_mutex_t viewportLock=PTHREAD_MUTEX_INITIALIZER;
static double keyboardPerWidth;
#ifdef AG_WHEEL_PREVIEW
static double previewFraction=.30;
void AGViewportPreview(CGFloat fraction){previewFraction=fraction;}
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
    pthread_mutex_lock(&viewportLock);keyboardPerWidth=ratio;pthread_mutex_unlock(&viewportLock);
#endif
}
CGRect AGGameRect(UIView *view){
    UIEdgeInsets safe=view.safeAreaInsets;CGRect bounds=view.bounds;
    pthread_mutex_lock(&viewportLock);double ratio=keyboardPerWidth;pthread_mutex_unlock(&viewportLock);
    CGFloat reserved=bounds.size.width*ratio;
#ifdef AG_WHEEL_PREVIEW
    reserved=bounds.size.height*previewFraction;
#endif
    CGFloat bottom=reserved>0?bounds.size.height-reserved:bounds.size.height-safe.bottom;
    bottom=MAX(safe.top+60,MIN(bounds.size.height,bottom));
    return CGRectMake(safe.left,safe.top,MAX(1,bounds.size.width-safe.left-safe.right),MAX(1,bottom-safe.top));
}
@implementation AGGameWindow
- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event{
    if(self.passesGameKeys&&!self.rootViewController.presentedViewController&&point.y>=self.gameBottom)return nil;
    return [super hitTest:point withEvent:event];
}
@end
