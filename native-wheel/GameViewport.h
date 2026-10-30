#import <UIKit/UIKit.h>
void AGViewportCapture(int variant);
CGRect AGGameRect(UIView *view);
@interface AGGameWindow : UIWindow
@property(nonatomic) CGFloat gameBottom;
@property(nonatomic) BOOL passesGameKeys;
@end
#ifdef AG_WHEEL_PREVIEW
void AGViewportPreview(CGFloat fraction);
#endif
