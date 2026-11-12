#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <string.h>
#include "Spectator.h"

typedef NS_ENUM(int, WatchPhase) { Offered, WaitingForMatch, InMatch, Leaving };
typedef NS_ENUM(int, WatchAction) { NoAction, Accept, Leave, Refresh };

@interface ArmyWatch : UIViewController <WKScriptMessageHandler, WKNavigationDelegate>
@property(nonatomic) int variant;
@property(nonatomic) uintptr_t connection;
@property(nonatomic) uint8_t room, area;
@property(nonatomic,copy) NSData *ticket;
@property(nonatomic,copy) NSString *question;
@property(nonatomic) WatchPhase phase;
@property(nonatomic) WatchAction action;
@property(nonatomic) NSTimeInterval deadline;
@property(nonatomic,strong) UIWindow *window;
@property(nonatomic,weak) UIWindow *previous;
@property(nonatomic,strong) WKWebView *web;
@property(nonatomic,strong) UILabel *label;
@property(nonatomic,strong) UIButton *yes, *dismissButton;
@property(nonatomic,strong) NSMutableArray *pending;
@property(nonatomic) NSUInteger pendingBytes;
@property(nonatomic) BOOL webReady, delivering;
- (void)show;
- (void)close;
- (void)flush;
@end

static ArmyWatch *current;
static atomic_bool active;
static NSTimeInterval now(void) { return NSProcessInfo.processInfo.systemUptime; }
static void screen(ArmyWatch *w) { dispatch_async(dispatch_get_main_queue(),^{ [w show]; }); }
static void finish(ArmyWatch *w) {
    if(current!=w)return;
    current=nil;atomic_store(&active,false);
    dispatch_async(dispatch_get_main_queue(),^{[w close];});
}
static void leave(ArmyWatch *w) {
    if(w.phase==Leaving)return;
    w.action = w.phase==Offered || (w.phase==WaitingForMatch && w.action==Accept) ? Refresh : Leave;
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
int AGViewerReceive(void *env,void *message,int variant) {
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
                    if(w)finish(w);
                    w=[ArmyWatch new];w.variant=variant;w.connection=conn;w.room=p[4];w.area=p[5];
                    w.ticket=[body subdataWithRange:NSMakeRange(6,8)];
                    w.question=[[NSString alloc] initWithBytes:p+16 length:n-16 encoding:NSUTF8StringEncoding]?:@"Bạn muốn xem trận đang diễn ra?";
                    w.pending=[NSMutableArray array];w.phase=Offered;w.deadline=now()+60;
                    current=w;atomic_store(&active,true);screen(w);return 1;
                }
                if(!w || w.variant!=variant)return 1;
                if(p[3]==6){
                    if(n==12&&!memcmp(p+4,w.ticket.bytes,8))finish(w);
                    return 1;
                }
                if(p[3]==3){
                    if(n!=21||p[4]!=w.room||p[5]!=w.area||memcmp(p+6,w.ticket.bytes,8))return 1;
                    if(w.phase==Leaving){w.action=Leave;return 1;}
                    if(w.phase!=WaitingForMatch)return 1;
                    w.phase=InMatch;w.deadline=now()+20;screen(w);
                }else if(p[3]!=4&&p[3]!=5&&p[3]!=7)return 1;
                if(w.phase!=InMatch)return 1;
                if(p[3]==7)w.deadline=0;
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
void AGViewerTick(void *env,int variant) {
    if(!atomic_load(&active))return;
    @autoreleasepool {
        ArmyWatch *w;WatchAction action;uintptr_t connection;
        @synchronized(ArmyWatch.class){w=current;if(!w||w.variant!=variant)return;}
        connection=AGViewerConnection(env,variant);
        @synchronized(ArmyWatch.class){
            if(current!=w)return;
            if(connection!=w.connection){finish(w);return;}
            if(w.deadline&&now()>w.deadline){
                if(w.phase==Leaving)w.action=Refresh;
                else leave(w);
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
- (UIButton *)button:(NSString *)title action:(SEL)action {
    UIButton *button=[UIButton buttonWithType:UIButtonTypeSystem];
    [button setTitle:title forState:UIControlStateNormal];
    button.titleLabel.font=[UIFont boldSystemFontOfSize:17];
    [button addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];
    return button;
}
- (void)loadView {
    UIView *view=[UIView new];view.backgroundColor=[UIColor colorWithWhite:0.95 alpha:1];self.view=view;
    self.label=[UILabel new];self.label.textAlignment=NSTextAlignmentCenter;self.label.numberOfLines=0;
    self.yes=[self button:@"Có" action:@selector(accept)];
    self.dismissButton=[self button:@"Không" action:@selector(cancel)];
    for(UIView *child in @[self.label,self.yes,self.dismissButton])[view addSubview:child];
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    CGRect safe=UIEdgeInsetsInsetRect(self.view.bounds,self.view.safeAreaInsets);
    CGFloat x=CGRectGetMinX(safe),y=CGRectGetMinY(safe),width=safe.size.width,h=safe.size.height;
    if(self.web){
        self.web.frame=CGRectMake(x,y,width,MAX(1,h-48));
        self.dismissButton.frame=CGRectMake(x,y+h-48,width,48);
    }else{
        self.label.frame=CGRectMake(x+16,y+h*0.35,width-32,90);
        self.yes.frame=CGRectMake(x,y+h*0.35+96,width/2,54);
        self.dismissButton.frame=CGRectMake(x+(self.yes.hidden?0:width/2),y+h*0.35+96,self.yes.hidden?width:width/2,54);
    }
}
- (void)show {
    WatchPhase phase;
    @synchronized(ArmyWatch.class){if(current!=self)return;phase=self.phase;}
    if(!self.window){
        UIWindow *previous=UIApplication.sharedApplication.keyWindow;
        if(!previous)return;
        self.previous=previous;
        if(@available(iOS 13.0,*)){self.window=previous.windowScene?[[UIWindow alloc] initWithWindowScene:previous.windowScene]:[[UIWindow alloc] initWithFrame:previous.bounds];}
        else self.window=[[UIWindow alloc] initWithFrame:previous.bounds];
        self.window.windowLevel=UIWindowLevelAlert+1;
        self.window.rootViewController=self;[self.window makeKeyAndVisible];
    }
    self.yes.hidden=phase!=Offered;
    self.label.text=phase==Offered?self.question:(phase==Leaving?@"Đang rời trận…":@"Đang nhận trận đấu…");
    [self.dismissButton setTitle:phase==Offered?@"Không":@"Rời xem trận" forState:UIControlStateNormal];
    if(phase==InMatch&&!self.web){
        NSURL *html=[[NSBundle bundleForClass:ArmyWatch.class] URLForResource:@"index" withExtension:@"html" subdirectory:@"viewer"];
        if(!html){[self cancel];return;}
        WKWebViewConfiguration *config=[WKWebViewConfiguration new];
        config.websiteDataStore=[WKWebsiteDataStore nonPersistentDataStore];
        [config.userContentController addScriptMessageHandler:self name:@"viewer"];
        self.web=[[WKWebView alloc] initWithFrame:CGRectZero configuration:config];self.web.navigationDelegate=self;
        [self.view insertSubview:self.web belowSubview:self.dismissButton];
        [self.web loadFileURL:html allowingReadAccessToURL:html.URLByDeletingLastPathComponent];
    }
    [self.view setNeedsLayout];
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
    self.window.hidden=YES;self.window.rootViewController=nil;self.window=nil;
    if(restore)[self.previous makeKeyWindow];
}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message {
    if(message.webView!=self.web||!message.frameInfo.isMainFrame)return;
    if([message.body isEqual:@"ready"]){self.webReady=YES;[self flush];}
    else if([message.body isEqual:@"failed"])[self cancel];
}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView {[self cancel];}
- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)nav withError:(NSError *)error {[self cancel];}
- (void)flush {
    if(!self.webReady||self.delivering)return;
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
