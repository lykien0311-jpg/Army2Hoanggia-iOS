#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <string.h>
#include "Spectator.h"
#include "SpectatorNative.h"
#import "GameViewport.h"

typedef NS_ENUM(int, WatchPhase) { Offered, WaitingForMatch, InMatch, Leaving };
typedef NS_ENUM(int, WatchAction) { NoAction, Accept, Leave, Refresh };

@interface ArmyWatch : UIViewController <WKScriptMessageHandler, WKNavigationDelegate>
@property(nonatomic) int variant;
@property(nonatomic) uintptr_t connection;
@property(nonatomic) uint8_t room, area;
@property(nonatomic,copy) NSData *ticket;
@property(nonatomic,copy) NSString *question;
@property(nonatomic,copy) NSString *problem;
@property(nonatomic) WatchPhase phase;
@property(nonatomic) WatchAction action;
@property(nonatomic) NSTimeInterval deadline;
@property(nonatomic,strong) UIWindow *window;
@property(nonatomic,weak) UIWindow *previous;
@property(nonatomic,strong) WKWebView *web;
@property(nonatomic,strong) NSMutableArray *pending;
@property(nonatomic) NSUInteger pendingBytes;
@property(nonatomic) BOOL webReady, delivering, retryScheduled, snapshotReceived, endReceived;
- (void)show;
- (void)close;
- (void)flush;
- (void)accept;
- (void)cancel;
- (void)updatePhase;
@end

static ArmyWatch *current;
static atomic_bool active;
static atomic_int activeVariant;
static atomic_bool nativeCleanup[6];
int AGViewerActive(int v){return v>=0&&v<6&&atomic_load(&active)&&atomic_load(&activeVariant)==v;}
static bool heldKeys[6][256];
static atomic_uintptr_t nativeWait[6];
static uintptr_t battlefieldSession[6];
static NSTimeInterval battlefieldUntil[6];
static NSTimeInterval now(void) { return NSProcessInfo.processInfo.systemUptime; }

int AGViewerInput(int variant,int kind,int code) {
    if(variant<0||variant>=6)return 0;
    if((unsigned)kind>1)return AGViewerActive(variant);
    ArmyWatch *watch;
    const unsigned index=(unsigned)code+128;
    @synchronized(ArmyWatch.class){
        if(kind==1&&index<256&&heldKeys[variant][index]){
            heldKeys[variant][index]=false;
            if(AGNativeWatchAvailable())AGNativeWatchCamera(variant,kind,code);
            return 1;
        }
        watch=current;
        if(!watch||watch.variant!=variant)return 0;
        if(kind==0&&index<256)heldKeys[variant][index]=true;
    }
    if(AGNativeWatchAvailable()&&watch.phase==InMatch){
        int key=code==-21||code=='L'||code=='l'?-6:
            code==-22||code==-11||code=='R'||code=='r'||code==27||code==35?-7:code;
        AGNativeWatchCamera(variant,kind,key);
        if(kind==0&&key==-6)dispatch_async(dispatch_get_main_queue(),^{[watch cancel];});
        if(kind==0&&key==-7){int mode=AGNativeWatchFree(variant);dispatch_async(dispatch_get_main_queue(),^{
            [watch.web evaluateJavaScript:[NSString stringWithFormat:@"window.watchCameraMode(%d)",mode] completionHandler:nil];
        });}
        return 1;
    }
    if(kind==0)dispatch_async(dispatch_get_main_queue(),^{
        if(watch.webReady){
            [watch.web evaluateJavaScript:[NSString stringWithFormat:@"watchKey(%d)",code] completionHandler:nil];
        }else if(code==-6||code==-5||code==-21||code=='L'||code=='l'||code==13||code==10||code=='5'||code=='F'||code=='f'){
            [watch accept];
        }else if(code==-7||code==-22||code==-11||code=='R'||code=='r'||code==27){
            [watch cancel];
        }
    });
    return 1;
}
static UIWindow *visibleHost(void) {
    UIApplication *app=UIApplication.sharedApplication;
    UIWindow *key=app.keyWindow;
    if(key && !key.hidden && key.rootViewController)return key;
    if(@available(iOS 13.0,*)){
        for(UIScene *scene in app.connectedScenes){
            if(![scene isKindOfClass:UIWindowScene.class] || scene.activationState!=UISceneActivationStateForegroundActive)continue;
            for(UIWindow *window in ((UIWindowScene *)scene).windows)
                if(!window.hidden && window.rootViewController && window.windowLevel==UIWindowLevelNormal)return window;
        }
    }
    for(UIWindow *window in app.windows)
        if(!window.hidden && window.rootViewController && window.windowLevel==UIWindowLevelNormal)return window;
    return nil;
}
void AGViewerExpectBattlefield(int variant,uintptr_t connection) {
    if(variant<0||variant>=6||!connection)return;
    @synchronized(ArmyWatch.class){battlefieldSession[variant]=connection;battlefieldUntil[variant]=now()+15;}
}
static void screen(ArmyWatch *w) { dispatch_async(dispatch_get_main_queue(),^{ [w show]; }); }
static void finish(ArmyWatch *w) {
    if(current!=w)return;
    current=nil;atomic_store(&active,false);
    if(AGNativeWatchAvailable())atomic_store(&nativeCleanup[w.variant],true);
    dispatch_async(dispatch_get_main_queue(),^{[w close];});
}
static void leave(ArmyWatch *w) {
    if(w.phase==Leaving)return;
    if(w.endReceived){finish(w);return;}
    w.action = w.phase==Offered ? NoAction : (w.phase==WaitingForMatch && w.action==Accept) ? Refresh : Leave;
    if(w.action==NoAction){finish(w);return;}
    w.phase=Leaving;w.deadline=now()+5;
    [w.pending removeAllObjects];w.pendingBytes=0;
    screen(w);
}
static NSData *readBody(void *message) {
    // The same HG78 DataInputStream layout used by Notes77 and Corpse.
    const uint8_t *in=*(const uint8_t **)((uint8_t *)message+0x20);
    if(!in)return nil;
    const uint8_t *array=*(const uint8_t **)(in+0x10);
    if(!array)return nil;
    int capacity=*(const int *)(array+0x10),end=*(const int *)(in+0x18),pos=*(const int *)(in+0x20);
    if(pos<0 || pos>end || end>capacity || end-pos>65535)return nil;
    return [NSData dataWithBytes:array+0x14+pos length:(NSUInteger)(end-pos)];
}
static BOOL combatPacket(int cmd) {
    switch(cmd) {
        case 8: case 9: case 14: case 20: case 21: case 22: case 24: case 25: case 26:
        case 50: case 51: case 52: case 76: case 80: case 83: case 84: case 89: case 93:
        case 95: case 96: case 97: case 100: case 106: case 107: case 108: case 109:
        case 113: case 124: return YES;
        default:return NO;
    }
}
static int receiveState(void *env,void *message,int variant,NSData **nativePacket,ArmyWatch **owner) {
    if(!env||!message||variant<0||variant>=6)return 0;
    int cmd=*(const int8_t *)((const uint8_t *)message+0x30);
    if(cmd!=-102 && !atomic_load(&active))return 0;
    @autoreleasepool {
        @synchronized(ArmyWatch.class) {
            ArmyWatch *w=current;
            if(cmd!=-102 && (!w || w.variant!=variant))return 0;
            if(cmd==3 || cmd==-4){finish(w);return 0;}
            if(cmd==45 && w.phase==WaitingForMatch){finish(w);return 0;}
            if(cmd!=-102 && (!(w.phase==InMatch || w.phase==Leaving) || !combatPacket(cmd)))return 0;
            NSData *body=readBody(message);
            if(!body){if(w && w.variant==variant)leave(w);return 1;}
            const uint8_t *p=body.bytes;NSUInteger n=body.length;
            if(cmd==-102) {
                if(n<4||p[0]!=0x53||p[1]!=0x50||p[2]!=1)return 1;
                if(p[3]==0) {
                    if(n<16 || p[4]>1 || n!=16+(NSUInteger)(p[14]*256+p[15]))return 1;
                    if(w && w.phase!=Offered)return 1;
                    uintptr_t conn=AGViewerConnection(env,variant);
                    if(!conn)return 1;
                    uintptr_t wait=AGViewerWaitToken(variant);
                    if(wait)atomic_store(&nativeWait[variant],wait);
                    if(w)finish(w);
                    w=[ArmyWatch new];w.variant=variant;w.connection=conn;w.room=p[4];w.area=p[5];
                    w.ticket=[body subdataWithRange:NSMakeRange(6,8)];
                    w.question=[[NSString alloc] initWithBytes:p+16 length:n-16 encoding:NSUTF8StringEncoding]?:@"Bạn muốn xem trận đang diễn ra?";
                    w.pending=[NSMutableArray array];w.phase=Offered;w.deadline=now()+60;
                    current=w;atomic_store(&activeVariant,variant);atomic_store(&active,true);screen(w);return 1;
                }
                if(!w && p[3]==3 && n==21 && p[4]==0 && p[5]==0 &&
                   battlefieldUntil[variant]>now() && battlefieldSession[variant]==AGViewerConnection(env,variant)){
                    w=[ArmyWatch new];w.variant=variant;w.connection=battlefieldSession[variant];
                    w.room=p[4];w.area=p[5];w.ticket=[body subdataWithRange:NSMakeRange(6,8)];
                    w.pending=[NSMutableArray array];w.phase=WaitingForMatch;
                    w.deadline=now()+15;
                    current=w;atomic_store(&activeVariant,variant);atomic_store(&active,true);battlefieldUntil[variant]=0;
                }
                if(!w || w.variant!=variant)return 1;
                if(p[3]==6){
                    if(n!=12||memcmp(p+4,w.ticket.bytes,8)||w.endReceived)return 1;
                    if(w.phase!=InMatch||!w.snapshotReceived){finish(w);return 1;}
                    // Keep the last shot and its HP update in the same queue as earlier frames.
                    w.endReceived=YES;w.deadline=now()+10;
                }else if(p[3]==3){
                    if(n!=21||p[4]!=w.room||p[5]!=w.area||memcmp(p+6,w.ticket.bytes,8))return 1;
                    if(w.phase==Leaving){w.action=Leave;return 1;}
                    if(w.phase!=WaitingForMatch)return 1;
                    w.phase=InMatch;w.deadline=now()+20;screen(w);
                }else if(p[3]!=4&&p[3]!=5&&p[3]!=7)return 1;
                if(w.phase!=InMatch)return 1;
                if(!w.snapshotReceived)w.deadline=now()+20;
                if(p[3]==7)w.snapshotReceived=YES;
            }
            if(AGNativeWatchAvailable()){
                if(cmd==-102){
                    if(w.phase==Leaving&&p[3]!=6)return 1;
                    *nativePacket=body;*owner=w;return p[3]==6?3:2;
                }
                // SP3 has already saved the previous screen. The unmodified
                // cmd8 parser creates the same native player roster as APK.
                // Subsequent combat packets retain their original decoder,
                // renderer and animation timing; no JS physics is involved.
                return 0;
            }
            if(w.phase==Leaving)return 1;
            if(w.pending.count>=4096 || w.pendingBytes+n>24*1024*1024){leave(w);return 1;}
            [w.pending addObject:@[@(cmd),body]];
            w.pendingBytes+=n;
            if(w.pending.count==1)dispatch_async(dispatch_get_main_queue(),^{[w flush];});
            return 1;
        }
    }
}
int AGViewerReceive(void *env,void *message,int variant){
    @autoreleasepool {
        NSData *packet=nil;ArmyWatch *owner=nil;
        int result=receiveState(env,message,variant,&packet,&owner);
        if(result<2)return result;
        const uint8_t *p=packet.bytes;
        // Texture creation may hand off to the GDX render thread. Never hold
        // the UI/state monitor while waiting for the original game routines.
        if(result==3){
            AGNativeWatchEnd(env,variant);
            @synchronized(ArmyWatch.class){if(current==owner)finish(owner);}
        }else{
            if(p[3]==3&&atomic_exchange(&nativeCleanup[variant],false))AGNativeWatchEnd(env,variant);
            int ok=AGNativeWatchPacket(env,variant,p,packet.length);
            @synchronized(ArmyWatch.class){
                if(current==owner){if(!ok)leave(owner);else if(p[3]==7){owner.deadline=0;screen(owner);}}
            }
        }
        return 1;
    }
}
void AGViewerTick(void *env,int variant) {
    if(!env||variant<0||variant>=6)return;
    if(atomic_exchange(&nativeCleanup[variant],false))AGNativeWatchEnd(env,variant);
    AGNativeWatchTick(env,variant);
    uintptr_t wait=atomic_exchange(&nativeWait[variant],0);
    if(wait)AGViewerDismissWait(variant,wait);
    if(!atomic_load(&active))return;
    @autoreleasepool {
        ArmyWatch *w;WatchAction action;uintptr_t connection;
        @synchronized(ArmyWatch.class){w=current;if(!w||w.variant!=variant)return;}
        connection=AGViewerConnection(env,variant);
        @synchronized(ArmyWatch.class){
            if(current!=w)return;
            if(connection!=w.connection){finish(w);return;}
            if(w.deadline&&now()>w.deadline){
                if(w.endReceived){finish(w);return;}
                if(w.phase==Leaving)w.action=Refresh;
                else {
                    w.problem=w.phase==Offered?@"Lời mời xem đã hết hạn.":@"Chưa tải được trận. Đang trở lại danh sách khu vực…";
                    leave(w);
                }
            }
            action=w.action;w.action=NoAction;
        }
        if(action==NoAction)return;
        uint8_t data[14]={0x53,0x50,1,0};int cmd=-102;size_t len;
        if(action==Refresh){data[0]=w.room;cmd=7;len=1;}
        else if(action==Accept){data[3]=1;data[4]=w.room;data[5]=w.area;memcpy(data+6,w.ticket.bytes,8);len=14;}
        else{data[3]=2;memcpy(data+4,w.ticket.bytes,8);len=12;}
        int ok=AGViewerSend(env,variant,connection,cmd,data,len);
        @synchronized(ArmyWatch.class){if(!ok||action==Refresh)finish(w);}
    }
}

@implementation ArmyWatch
- (void)loadView {
    UIView *view=[UIView new];view.backgroundColor=UIColor.clearColor;self.view=view;
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    CGRect game=AGGameRect(self.view);
    self.web.frame=game;
    ((AGGameWindow *)self.window).gameBottom=CGRectGetMaxY(game);
}
- (void)show {
    @synchronized(ArmyWatch.class){if(current!=self)return;}
    if(!self.window){
        UIWindow *previous=visibleHost();
        if(!previous){
            if(!self.retryScheduled){
                self.retryScheduled=YES;
                dispatch_after(dispatch_time(DISPATCH_TIME_NOW,250*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
                    self.retryScheduled=NO;
                    [self show];
                });
            }
            return;
        }
        self.previous=previous;
        if(@available(iOS 13.0,*)){if(previous.windowScene)self.window=[[AGGameWindow alloc] initWithWindowScene:previous.windowScene];}
        if(!self.window)self.window=[[AGGameWindow alloc] initWithFrame:previous.bounds];
        ((AGGameWindow *)self.window).passesGameKeys=YES;
        ((AGGameWindow *)self.window).gameBottom=CGRectGetMaxY(AGGameRect(previous.rootViewController.view));
        AGViewportWheelVisible(1);
        self.window.windowLevel=UIWindowLevelAlert+1;
        self.window.rootViewController=self;[self.window makeKeyAndVisible];
    }
    if(!self.web){
        NSURL *html=[[NSBundle bundleForClass:ArmyWatch.class] URLForResource:(AGNativeWatchAvailable()?@"native-watch":@"index") withExtension:@"html" subdirectory:@"viewer"];
        if(!html){[self cancel];return;}
        WKWebViewConfiguration *config=[WKWebViewConfiguration new];
        config.websiteDataStore=[WKWebsiteDataStore nonPersistentDataStore];
        [config.userContentController addScriptMessageHandler:self name:@"viewer"];
        self.web=[[WKWebView alloc] initWithFrame:CGRectZero configuration:config];self.web.navigationDelegate=self;
        self.web.opaque=NO;
        self.web.backgroundColor=UIColor.clearColor;
        self.web.scrollView.backgroundColor=UIColor.clearColor;
        self.web.scrollView.scrollEnabled=NO;
        self.web.scrollView.bounces=NO;
        self.web.scrollView.contentInsetAdjustmentBehavior=UIScrollViewContentInsetAdjustmentNever;
        [self.view addSubview:self.web];
        [self.web loadFileURL:html allowingReadAccessToURL:html.URLByDeletingLastPathComponent];
    }
    [self.view setNeedsLayout];
    [self updatePhase];
}
- (void)updatePhase {
    if(!self.webReady)return;
    WatchPhase phase;
    NSString *message;
    @synchronized(ArmyWatch.class){
        if(current!=self)return;
        phase=self.phase;
        if(AGNativeWatchAvailable()&&phase==InMatch&&!self.snapshotReceived)phase=WaitingForMatch;
        message=phase==Offered?self.question:self.problem;
    }
    NSData *data=[NSJSONSerialization dataWithJSONObject:@[@(phase),message?:@""] options:0 error:nil];
    NSString *arg=[[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    if(arg)[self.web evaluateJavaScript:[NSString stringWithFormat:@"setWatchPhase(...%@)",arg] completionHandler:nil];
}
- (void)accept {
    @synchronized(ArmyWatch.class){
        if(current!=self||self.phase!=Offered)return;
        self.phase=WaitingForMatch;self.action=Accept;self.deadline=now()+15;
    }
    [self show];
}
- (void)cancel {@synchronized(ArmyWatch.class){if(current==self)leave(self);}}
- (void)close {
    [self.web.configuration.userContentController removeScriptMessageHandlerForName:@"viewer"];
    [self.web stopLoading];self.web.navigationDelegate=nil;
    BOOL restore=self.window.isKeyWindow;
    if(self.window)AGViewportWheelVisible(0);
    self.window.hidden=YES;self.window.rootViewController=nil;self.window=nil;
    if(restore){UIWindow *previous=self.previous;[(previous&&!previous.hidden?previous:visibleHost()) makeKeyWindow];}
}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message {
    if(message.webView!=self.web||!message.frameInfo.isMainFrame)return;
    if([message.body isEqual:@"ready"]){self.webReady=YES;[self updatePhase];[self flush];}
    else if([message.body isEqual:@"live"]){
        @synchronized(ArmyWatch.class){if(current==self&&self.phase==InMatch&&self.snapshotReceived&&!self.endReceived)self.deadline=0;}
    }else if([message.body isEqual:@"ended"]){
        @synchronized(ArmyWatch.class){if(current==self&&self.endReceived)finish(self);}
    }
    else if([message.body isEqual:@"camera"])AGNativeWatchCamera(self.variant,0,-7);
    else if([message.body isKindOfClass:NSArray.class]&&[message.body count]==3&&[message.body[0] isEqual:@"key"])AGNativeWatchCamera(self.variant,[message.body[1] intValue],[message.body[2] intValue]);
    else if([message.body isEqual:@"accept"])[self accept];
    else if([message.body isEqual:@"decline"]||[message.body isEqual:@"leave"]||[message.body isEqual:@"failed"])[self cancel];
}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView {[self cancel];}
- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)nav withError:(NSError *)error {[self cancel];}
- (void)flush {
    if(AGNativeWatchAvailable()||!self.webReady||self.delivering)return;
    NSMutableArray *batch=[NSMutableArray array];
    @synchronized(ArmyWatch.class){
        if(current!=self||self.phase!=InMatch)return;
        NSUInteger count=MIN(24,self.pending.count);
        for(NSUInteger i=0;i<count;i++){
            NSArray *row=self.pending[i];NSData *bytes=row[1];
            [batch addObject:@[row[0],[bytes base64EncodedStringWithOptions:0]]];
            self.pendingBytes-=bytes.length;
        }
        [self.pending removeObjectsInRange:NSMakeRange(0,count)];
    }
    if(!batch.count)return;
    NSData *json=[NSJSONSerialization dataWithJSONObject:batch options:0 error:nil];
    NSString *arg=[[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding];
    self.delivering=YES;
    [self.web evaluateJavaScript:[NSString stringWithFormat:@"window.receiveArmyFrames(%@)",arg] completionHandler:^(id result,NSError *error){
        self.delivering=NO;if(error){[self cancel];return;}[self flush];
    }];
}
@end

