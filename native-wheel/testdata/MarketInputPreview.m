#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#import "../Lobby.m"
int AGAuraRank(int v,uintptr_t c,uint32_t i,unsigned h){return 0;}
uintptr_t AGViewerConnection(void *e,int v){return 1;}
int AGViewerActive(int v){return 0;}
void AGViewerExpectBattlefield(int v,uintptr_t c){}
int AGLobbyReadAccount(void *e,int v,AGLobbyAccount *a){return 0;}
int AGLobbySend(void *e,int v,uintptr_t c,int cmd,const uint8_t *b,size_t n){return 1;}
int AGWheelGuard(void *e,int (*f)(void *,void *),void *c,void *t){return 0;}
@interface QAWeb : WKWebView
@property(nonatomic,strong) NSString *lastScript;
@end
@implementation QAWeb
- (void)evaluateJavaScript:(NSString *)script completionHandler:(void (^)(id,NSError *))handler{self.lastScript=script;if(handler)handler(@YES,nil);}
@end
@interface QAFrame : NSObject
@end
@implementation QAFrame
- (BOOL)isMainFrame{return YES;}
@end
@interface QAMessage : NSObject
@property(nonatomic,strong) WKWebView *webView;
@property(nonatomic,strong) id body;
@end
@implementation QAMessage
- (id)frameInfo{return [QAFrame new];}
@end
@interface App : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@property(nonatomic,strong) AGLobby *panel;
@property(nonatomic,strong) NSMutableArray *checks;
@end
@implementation App
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options{
 self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];self.panel=[AGLobby new];self.panel.web=[[QAWeb alloc]initWithFrame:CGRectMake(0,0,390,500)];self.window.rootViewController=self.panel;self.panel.view.backgroundColor=UIColor.cyanColor;[self.window makeKeyAndVisible];self.checks=[NSMutableArray new];
 dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{[self step:0];});return YES;
}
- (void)step:(int)index{
 NSString *directory=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
 if(index==4){NSDictionary *report=@{@"passed":@YES,@"checks":self.checks,@"physical_device":@NO};NSData *data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];[data writeToFile:[directory stringByAppendingPathComponent:@"input-282-check.json"] atomically:YES];return;}
 QAMessage *message=[QAMessage new];message.webView=self.panel.web;
 message.body=@[@"edit",@{@"serial":@(index+1),@"value":index==0?@"1":@"",@"type":index==2?@"password":@"text",@"numeric":@(index<2),@"maxLength":index==2?@40:@12}];
 [self.panel userContentController:nil didReceiveScriptMessage:(id)message];
 dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{
  @try{
   UIAlertController *alert=(id)self.panel.presentedViewController;NSCAssert([alert isKindOfClass:UIAlertController.class],@"Native input dialog opens");
   NSCAssert([alert.title isEqual:@"Nhập"],@"Input title follows APK");NSCAssert(alert.actions.count==2&&[alert.actions[0].title isEqual:@"OK"]&&[alert.actions[1].title isEqual:@"Cancel"],@"Input actions");
   UITextField *field=alert.textFields.firstObject;NSCAssert(field.secureTextEntry==(index==2),@"Password masking");NSCAssert(field.keyboardType==(index<2?UIKeyboardTypeNumberPad:UIKeyboardTypeDefault),@"Keyboard type");
   if(index==0){NSCAssert([field.text isEqual:@"1"],@"Initial quantity");UIGraphicsBeginImageContextWithOptions(self.window.bounds.size,YES,1);[self.window drawViewHierarchyInRect:self.window.bounds afterScreenUpdates:YES];UIImage *image=UIGraphicsGetImageFromCurrentImageContext();UIGraphicsEndImageContext();[UIImagePNGRepresentation(image)writeToFile:[directory stringByAppendingPathComponent:@"input-282-native.png"] atomically:YES];}
   NSString *expected=index==0?@"7":index==1?@"900":@"qa-test";field.text=expected;
   UIAlertAction *action=alert.actions[index==3?1:0];void (^handler)(UIAlertAction *)=[action valueForKey:@"handler"];NSCAssert(handler!=nil,@"Native alert action is bound");handler(action);
   NSString *script=((QAWeb *)self.panel.web).lastScript;NSString *prefix=@"lobbyInputResult(...";NSCAssert([script hasPrefix:prefix],@"Result callback");NSString *json=[script substringWithRange:NSMakeRange(prefix.length,script.length-prefix.length-1)];NSArray *result=[NSJSONSerialization JSONObjectWithData:[json dataUsingEncoding:NSUTF8StringEncoding] options:0 error:nil];NSCAssert([result[0] intValue]==index+1,@"Serial is preserved");NSCAssert(index==3?result[1]==NSNull.null:[result[1] isEqual:expected],@"Input value was returned and native field cleared");NSCAssert(field.text.length==0,@"Native field is cleared");
   [self.checks addObject:@{@"step":@(index),@"native_alert":@YES,@"masked":@(index==2),@"cancel":@(index==3)}];
   [alert dismissViewControllerAnimated:NO completion:^{dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC/3),dispatch_get_main_queue(),^{[self step:index+1];});}];
  }@catch(NSException *error){NSDictionary *report=@{@"passed":@NO,@"reason":error.reason?:@"error"};NSData *data=[NSJSONSerialization dataWithJSONObject:report options:0 error:nil];[data writeToFile:[directory stringByAppendingPathComponent:@"input-282-check.json"] atomically:YES];}
 });
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(App.class));}}

