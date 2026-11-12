/* Simulator-only application. Feed the native receiver an ordinary match trace,
 * with the same input stream layout as build 269 and synthetic wire transport. */
#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <string.h>
#include "../Spectator.h"
#include "../Lobby.h"
static NSMutableArray *sent;
static NSMutableArray *frames;
static UIWindow *host;
static uint8_t lobbyScreen;
static int lobbyCommand;
static NSData *lobbyPayload;
static void save(NSString *result) {
    NSURL *dir=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
    [result writeToURL:[dir URLByAppendingPathComponent:@"viewer-result.txt"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
}
uintptr_t AGViewerConnection(void *env,int v) { return 44; }
int AGLobbySend(void *env,int v,uintptr_t connection,int command,const uint8_t *bytes,size_t length){
    if(v!=0||connection!=44)return 0;
    lobbyCommand=command;lobbyPayload=[NSData dataWithBytes:bytes length:length];return 1;
}
int AGViewerSend(void *env,int v,uintptr_t connection,int cmd,const uint8_t *bytes,size_t length) {
    if(connection!=44)return 0;
    [sent addObject:@[@(cmd),[NSData dataWithBytes:bytes length:length]]];return 1;
}
static int deliver(int cmd,NSData *body) {
    uint8_t msg[0x38]={0},input[0x30]={0};
    NSMutableData *array=[NSMutableData dataWithLength:0x14+body.length];
    uint8_t *storage=array.mutableBytes;
    int n=(int)body.length;
    memcpy(storage+0x10,&n,4);memcpy(storage+0x14,body.bytes,n);
    memcpy(input+0x10,&storage,sizeof storage);memcpy(input+0x18,&n,4);
    uint8_t *in=input;memcpy(msg+0x20,&in,sizeof in);msg[0x30]=(uint8_t)cmd;
    if(AGLobbyReceive((void *)1,msg,0))return 1;
    return AGViewerReceive((void *)1,msg,0);
}
static UIView *find(UIView *root,Class cls,NSString *title) {
    if([root isKindOfClass:cls]&&(!title||[[(UIButton *)root currentTitle] isEqual:title]))return root;
    for(UIView *child in root.subviews){UIView *v=find(child,cls,title);if(v)return v;}
    return nil;
}
static void testLobby(int step,int tries){
    if(tries<=0){save([NSString stringWithFormat:@"FAIL lobby timed out at %d",step]);return;}
    UIWindow *window=UIApplication.sharedApplication.keyWindow;
    WKWebView *web=(WKWebView *)find(window,WKWebView.class,nil);
    if(step==0){
        AGLobbyRemember(&lobbyScreen,0);AGLobbyTick((void *)1,0,&lobbyScreen,0,44);step++;
    }else if(step==1){
        UIButton *open=(UIButton *)find(host,UIButton.class,@"Chiến trường · Gian hàng");
        if(open){[open sendActionsForControlEvents:UIControlEventTouchUpInside];step++;}
    }else if(step==2 && web){
        [web evaluateJavaScript:@"typeof receiveFrame==='function' && (document.getElementById('market').click(),true)"
            completionHandler:^(id v,NSError *err){dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{testLobby([v isEqual:@YES]?3:2,tries-1);});}];return;
    }else if(step==3){
        AGLobbyTick((void *)1,0,&lobbyScreen,0,44);
        const uint8_t expected[]={0,0,0,0,0,255,0};
        if(lobbyCommand==-121 && [lobbyPayload isEqual:[NSData dataWithBytes:expected length:sizeof expected]]){
            const uint8_t empty[]={0,0,0,0,0,255,0,0,0,0};
            deliver(-121,[NSData dataWithBytes:empty length:sizeof empty]);step++;
        }
    }else if(step==4 && web){
        [web evaluateJavaScript:@"document.body.innerText.includes('Chưa có món đang bán.') && (document.getElementById('field').click(),true)"
            completionHandler:^(id v,NSError *err){dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{testLobby([v isEqual:@YES]?5:4,tries-1);});}];return;
    }else if(step==5){
        AGLobbyTick((void *)1,0,&lobbyScreen,0,44);
        const uint8_t expected[]={0x43,0x54,0x34,0x36,1,0,0,0,1,49};
        if(lobbyCommand==-120 && [lobbyPayload isEqual:[NSData dataWithBytes:expected length:sizeof expected]]){
            const uint8_t reply[]={0x43,0x54,0x34,0x36,1,0,0,0,1,0,0,0,2,0,0,0,7,0};
            deliver(-120,[NSData dataWithBytes:reply length:sizeof reply]);step++;
        }
    }else if(step==6 && web){
        [web evaluateJavaScript:@"document.body.innerText.includes('Trận đang đấu')" completionHandler:^(id v,NSError *err){
            if([v isEqual:@YES]){
                UIButton *back=(UIButton *)find(window,UIButton.class,@"Về sảnh");
                [back sendActionsForControlEvents:UIControlEventTouchUpInside];
                AGLobbyTick((void *)1,0,NULL,0,44);
            }
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{testLobby([v isEqual:@YES]?7:6,tries-1);});
        }];return;
    }else if(step==7 && window==host && !find(host,UIButton.class,@"Chiến trường · Gian hàng")){
        save(@"PASS prompt, decline, snapshot, live roster, leave; lobby entry, marketplace browse, battlefield board, restore game");return;
    }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{testLobby(step,tries-1);});
}
static void runStep(int step,int tries) {
    @try {
        if(tries<=0){save([NSString stringWithFormat:@"FAIL timeout at step %d",step]);return;}
        UIWindow *window=UIApplication.sharedApplication.keyWindow;
        UIButton *button;
        NSData *prompt=frames[0][1];
        const uint8_t *p=prompt.bytes;
        if(step==0){NSCAssert(deliver(-102,prompt)==1,@"receive prompt");step++;}
        else if(step==1 && (button=(UIButton *)find(window,UIButton.class,@"Không"))){
            [button sendActionsForControlEvents:UIControlEventTouchUpInside];AGViewerTick((void *)1,0);
            NSCAssert([sent.lastObject[0] intValue]==7,@"decline refresh");step++;
        }else if(step==2&&window==host){[sent removeAllObjects];deliver(-102,prompt);step++;}
        else if(step==3 && (button=(UIButton *)find(window,UIButton.class,@"Có"))){
            [button sendActionsForControlEvents:UIControlEventTouchUpInside];AGViewerTick((void *)1,0);
            NSData *payload=sent.lastObject[1];const uint8_t *s=payload.bytes;
            NSCAssert([sent.lastObject[0] intValue]==-102&&payload.length==14&&s[3]==1&&!memcmp(p+4,s+4,10),@"confirm wire");
            for(NSUInteger i=1;i<frames.count;i++) {
                NSArray *f=frames[i];NSData *b=f[1];int c=[f[0] intValue];
                if(c==-102 && ((const uint8_t *)b.bytes)[3]==6)break;
                deliver(c,b);
            }
            step++;
        }else if(step==4){
            WKWebView *web=(WKWebView *)find(window,WKWebView.class,nil);
            if(web){
                [web evaluateJavaScript:@"typeof game!=='undefined' && game.phase==='live' && game.nextTile===52 && game.players.filter(p=>p&&p.hp>0).length===2"
                       completionHandler:^(id v,NSError *e){if([v isEqual:@YES]){
                            UIButton *leave=(UIButton *)find(window,UIButton.class,@"Rời xem trận");
                            [leave sendActionsForControlEvents:UIControlEventTouchUpInside];AGViewerTick((void *)1,0);
                            NSData *body=sent.lastObject[1];const uint8_t *b=body.bytes;
                            if(!leave||body.length!=12||b[3]!=2||memcmp(b+4,p+6,8)){save(@"FAIL leave wire");return;}
                            uint8_t done[12]={0x53,0x50,1,6};memcpy(done+4,p+6,8);
                            deliver(-102,[NSData dataWithBytes:done length:12]);
                            dispatch_async(dispatch_get_main_queue(),^{runStep(5,tries-1);});
                       }else dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{runStep(4,tries-1);});}];
                return;
            }
        }else if(step==5&&window==host){
            if(deliver(24,[NSData dataWithBytes:"x" length:1])!=0){save(@"FAIL ordinary player intercepted");return;}
            testLobby(0,150);return;
        }
        int next=step;dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{runStep(next,tries-1);});
    }@catch(NSException *e){save([@"FAIL " stringByAppendingString:e.reason]);}
}
@interface Demo : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@end
@implementation Demo
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)opts {
    self.window=[[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];host=self.window;
    self.window.rootViewController=[UIViewController new];[self.window makeKeyAndVisible];
    NSData *data=[NSData dataWithContentsOfURL:[NSBundle.mainBundle URLForResource:@"watch-pvp" withExtension:@"json"]];
    NSArray *trace=[NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    frames=[NSMutableArray array];sent=[NSMutableArray array];
    for(NSArray *row in trace) [frames addObject:@[row[0],[[NSData alloc] initWithBase64EncodedString:row[1] options:0]]];
    dispatch_async(dispatch_get_main_queue(),^{runStep(0,160);});return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(Demo.class));}}
