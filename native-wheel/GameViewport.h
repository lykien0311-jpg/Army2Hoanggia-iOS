#import <UIKit/UIKit.h>
void AGViewportCapture(void *env,int variant);
void AGViewportWheelVisible(int visible);
void AGViewportKeypad(void *env,void *keys,void *batch);
CGRect AGGameRect(UIView *view);
@interface AGGameWindow : UIWindow
@property(nonatomic) CGFloat gameBottom;
@property(nonatomic) BOOL passesGameKeys;
@property(nonatomic) BOOL passesGameTouches;
@end
#ifdef AG_WHEEL_PREVIEW
void AGViewportPreview(CGFloat fraction);
void AGViewportPreviewTop(CGFloat fraction);
#endif

