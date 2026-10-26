#import <UIKit/UIKit.h>
extern void AGWheelPreview(void);
@interface PreviewApp : UIResponder<UIApplicationDelegate>
@property(strong,nonatomic) UIWindow *window;
@end
@implementation PreviewApp
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];self.window.rootViewController=[UIViewController new];self.window.rootViewController.view.backgroundColor=UIColor.blackColor;[self.window makeKeyAndVisible];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{AGWheelPreview();});return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(PreviewApp.class));}}
