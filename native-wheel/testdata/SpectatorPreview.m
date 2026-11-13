/* Simulator-only application. Feed the native receiver an ordinary match trace,
 * with the same input stream layout as build 269 and synthetic wire transport. */
#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <string.h>
#include "../Spectator.h"
#include "../SpectatorWait.h"
#include "../Lobby.h"
int AGWheelGuard(void *env,int (*fn)(void *,void *),void *context,void *trap){return 0;}
static NSMutableArray *sent;
static NSMutableArray *frames;
static UIWindow *host;
static int lobbyCommand;
static NSData *lobbyPayload;
static uintptr_t canvas[0x110 / sizeof(uintptr_t)];
static uintptr_t waitDialog[6];
static void save(NSString *result) {
    NSURL *dir=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
    [result writeToURL:[dir URLByAppendingPathComponent:@"viewer-result.txt"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
}
uintptr_t AGViewerConnection(void *env,int v) { return 44; }
int AGLobbyReadAccount(void *env,int v,AGLobbyAccount *account) {
    *account=(AGLobbyAccount){.character=6,.xu=520490301781,.luong=49618047296};
    return 1;
}
int AGAuraRank(int v,uintptr_t connection,uint32_t id,unsigned hero){return id==7&&hero==6?240:0;}
uintptr_t AGViewerWaitToken(int v){return AGSpectatorWaitToken(canvas);}
void AGViewerDismissWait(int v,uintptr_t token){AGSpectatorClearWait(canvas,token);}
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
        AGLobbyOpenNative((void *)1,0,2);step++;
    }else if(step==1){
        AGLobbyTick((void *)1,0,44);
        const uint8_t expected[]={0,0,0,0,0,255,0};
        if(lobbyCommand==-121 && [lobbyPayload isEqual:[NSData dataWithBytes:expected length:sizeof expected]]){
            const uint8_t empty[]={0,0,0,0,0,255,0,0,0,0};
            deliver(-121,[NSData dataWithBytes:empty length:sizeof empty]);step++;
            const uint8_t money[]={0,0,0,0,0,0,0,12,0,0,0,0,0,0,0,34};
            NSCAssert(!deliver(105,[NSData dataWithBytes:money length:sizeof money]),@"wallet packet also reaches the game");
        }
    }else if(step==2 && web){
        [web evaluateJavaScript:@"tab==='market' && !waiting && character===6 && balance==='Tiền: 12 xu - 34 lượng' && (marketMenu(), menuItems.map(x=>x[0]).join('|')==='Lọc|Gian hàng|Rương gian hàng|Đồ của tôi')" completionHandler:^(id v,NSError *err){
            BOOL done=[v isEqual:@YES];
            if(done){AGLobbyInput(0,0,-22,0);AGLobbyInput(0,0,-22,0);}
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{testLobby(done?3:2,tries-1);});
        }];return;
    }else if(step==3 && window==host){
        NSCAssert(!AGLobbyOpened(0)&&AGLobbyInput(0,1,-22,0),@"close restores the host and consumes the trailing key release");
        AGLobbyOpenNative((void *)1,0,1);step++;
    }else if(step==4){
        AGLobbyTick((void *)1,0,44);
        const uint8_t expected[]={0x43,0x54,0x34,0x36,1,0,0,0,1,49};
        if(lobbyCommand==-120 && [lobbyPayload isEqual:[NSData dataWithBytes:expected length:sizeof expected]]){
            const uint8_t reply[]={0x43,0x54,0x34,0x36,1,0,0,0,1,0,0,0,2,0,0,0,7,0};
            deliver(-120,[NSData dataWithBytes:reply length:sizeof reply]);step++;
        }
    }else if(step==5 && web){
        [web evaluateJavaScript:@"tab==='field' && view==='board' && !waiting"
            completionHandler:^(id v,NSError *err){
                if([v isEqual:@YES])AGLobbyInput(0,0,-7,0);
                dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{testLobby([v isEqual:@YES]?6:5,tries-1);});
            }];return;
    }else if(step==6 && window==host){
        AGLobbyOpenNative((void *)1,0,3);step++;
    }else if(step==7){
        AGLobbyTick((void *)1,0,44);
        const uint8_t expected[]={3,0};
        if(lobbyCommand==-14 && [lobbyPayload isEqual:[NSData dataWithBytes:expected length:sizeof expected]]){
            const uint8_t head[]={3,0,0,3,'B','X','H'};
            const uint8_t row[]={0,0,0,7,0,3,'Q','A','1',6,0,0,0,0,0,0,0,0,3,231,0,1,0,0,0,0,0,0,0,0,0,0,0,2,'4','2'};
            NSMutableData *reply=[NSMutableData dataWithBytes:head length:sizeof head];
            [reply appendBytes:row length:sizeof row];deliver(-14,reply);step++;
        }
    }else if(step==8 && web){
        [web evaluateJavaScript:@"tab==='event' && reply?.rows[0]?.name==='QA1' && reply.rows[0].score==='42' && reply.rows[0].aura===240 && ArmyArt.geometry[2].length===384" completionHandler:^(id v,NSError *err){
            if([v isEqual:@YES]){
                [web evaluateJavaScript:@"close()" completionHandler:nil];
                AGLobbyTick((void *)1,0,44);
            }
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{testLobby([v isEqual:@YES]?9:8,tries-1);});
        }];return;
    }else if(step==9 && window==host && !AGLobbyOpened(0)){
        save(@"PASS spectator lifecycle, native marketplace and battlefield menu callbacks, event leaderboard, return to host");return;
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
        if(step==0){
            canvas[0xc8/sizeof(uintptr_t)]=(uintptr_t)waitDialog;
            canvas[0x108/sizeof(uintptr_t)]=(uintptr_t)waitDialog;
            waitDialog[5]=81;
            NSCAssert(deliver(-102,prompt)==1,@"receive prompt");
            AGViewerTick((void *)1,0);
            NSCAssert(!canvas[0x108/sizeof(uintptr_t)],@"close native wait for incoming invitation");
            step++;
        }
        else if(step==1 && (button=(UIButton *)find(window,UIButton.class,@"Không"))){
            [button sendActionsForControlEvents:UIControlEventTouchUpInside];AGViewerTick((void *)1,0);
            NSCAssert([sent.lastObject[0] intValue]==7,@"decline refresh");step++;
        }else if(step==2&&window==host){
            [sent removeAllObjects];
            canvas[0x108/sizeof(uintptr_t)]=(uintptr_t)waitDialog;
            waitDialog[5]=82;
            deliver(-102,prompt);
            waitDialog[5]=83;
            AGViewerTick((void *)1,0);
            NSCAssert(canvas[0x108/sizeof(uintptr_t)]==(uintptr_t)waitDialog,@"preserve a replacement dialog");
            canvas[0x108/sizeof(uintptr_t)]=0;
            step++;
        }
        else if(step==3 && (button=(UIButton *)find(window,UIButton.class,@"Có"))){
            [button sendActionsForControlEvents:UIControlEventTouchUpInside];AGViewerTick((void *)1,0);
            NSData *payload=sent.lastObject[1];const uint8_t *s=payload.bytes;
            NSCAssert([sent.lastObject[0] intValue]==-102&&payload.length==14&&s[3]==1&&!memcmp(p+4,s+4,10),@"confirm wire");
            for(NSUInteger i=1;i<frames.count;i++) {
                NSArray *f=frames[i];NSData *b=f[1];int c=[f[0] intValue];
                if(c==-102 && ((const uint8_t *)b.bytes)[3]==6)break;
                deliver(c,b);
            }
            NSCAssert([[window.rootViewController valueForKey:@"deadline"] doubleValue]>0,@"keep timeout until the map is visible");
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
            deliver(-102,prompt);step++;
        }else if(step==6 && (button=(UIButton *)find(window,UIButton.class,@"Có"))){
            [button sendActionsForControlEvents:UIControlEventTouchUpInside];AGViewerTick((void *)1,0);
            for(NSArray *f in frames){
                NSData *body=f[1];
                if([f[0] intValue]==-102&&((const uint8_t *)body.bytes)[3]==3){deliver(-102,body);break;}
            }
            UIViewController *watch=window.rootViewController;
            NSNumber *past=@(NSProcessInfo.processInfo.systemUptime-1);
            [watch setValue:past forKey:@"deadline"];AGViewerTick((void *)1,0);
            NSData *payload=sent.lastObject[1];
            NSCAssert([sent.lastObject[0] intValue]==-102&&payload.length==12&&((const uint8_t *)payload.bytes)[3]==2,@"timeout leaves the match");
            [watch setValue:past forKey:@"deadline"];AGViewerTick((void *)1,0);
            NSCAssert([sent.lastObject[0] intValue]==7,@"refresh if the leave reply never arrives");
            step++;
        }else if(step==7&&window==host){
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
