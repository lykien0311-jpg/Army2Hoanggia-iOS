#import <UIKit/UIKit.h>
extern void AGWheelPreview(void);
extern void AGWheelPreviewShowInput(void);
extern void AGWheelPreviewCheckInterface(void);
extern void AGNotesPreviewCheck(void);
extern void AGUfoDiagnosticsPreviewCheck(void);
extern void AGShipDiagnosticsPreviewCheck(void);
@interface PreviewApp : UIResponder<UIApplicationDelegate>
@property(strong,nonatomic) UIWindow *window;
@end
@implementation PreviewApp
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];self.window.rootViewController=[UIViewController new];self.window.rootViewController.view.backgroundColor=UIColor.blackColor;[self.window makeKeyAndVisible];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{AGWheelPreview();});
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,2*NSEC_PER_SEC),dispatch_get_main_queue(),^{@try{AGWheelPreviewCheckInterface();AGNotesPreviewCheck();AGUfoDiagnosticsPreviewCheck();AGShipDiagnosticsPreviewCheck();}@catch(NSException *error){
        NSDictionary *result=@{@"name":error.name?:@"",@"reason":error.reason?:@""};
        NSString *dir=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
        [[NSJSONSerialization dataWithJSONObject:result options:0 error:nil]writeToFile:[dir stringByAppendingPathComponent:@"ui-error.json"] atomically:YES];
    }});
    if([NSProcessInfo.processInfo.arguments containsObject:@"--show-input"])
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW,3*NSEC_PER_SEC),dispatch_get_main_queue(),^{AGWheelPreviewShowInput();});
    return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(PreviewApp.class));}}


