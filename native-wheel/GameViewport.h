#import <UIKit/UIKit.h>
void AGViewportCapture(int variant);
void AGViewportKeypad(void *env,void *keys,void *batch);
CGRect AGGameRect(UIView *view);
@interface AGGameWindow : UIWindow
@property(nonatomic) CGFloat gameBottom;
@property(nonatomic) BOOL passesGameKeys;
@end
#ifdef AG_WHEEL_PREVIEW
void AGViewportPreview(CGFloat fraction);
#endif

