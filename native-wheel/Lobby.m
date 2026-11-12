#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <stdatomic.h>
#include <string.h>
#include "Lobby.h"
#include "Spectator.h"

@interface AGLobby : UIViewController <WKScriptMessageHandler,WKNavigationDelegate>
@property(nonatomic,strong) UIWindow *overlay;
@property(nonatomic,weak) UIWindow *host;
@property(nonatomic,strong) WKWebView *web;
@property(nonatomic,strong) UIButton *entry;
@property(nonatomic) uintptr_t connection;
@property(nonatomic) int variant;
@property(nonatomic) int command;
@property(nonatomic) uint32_t watchSerial;
@property(nonatomic) uint32_t challengeSerial;
@property(nonatomic,strong) NSData *outgoing;
- (void)open;
- (void)close;
@end

static atomic_uintptr_t roomList[6];
static AGLobby *panel;
static int lobbyVariant=-1;
static uintptr_t lobbyConnection;
static BOOL lobbyVisible;
static uintptr_t battlefield[6];
void AGLobbyRemember(void *screen,int variant){atomic_store(&roomList[variant],(uintptr_t)screen);}
int AGLobbyKnown(int variant){return atomic_load(&roomList[variant])!=0;}

static void refreshEntry(void) {
    int v;uintptr_t connection;BOOL show;
    @synchronized(AGLobby.class){v=lobbyVariant;connection=lobbyConnection;show=lobbyVisible;}
    if(panel && (panel.variant!=v || panel.connection!=connection || !connection)){
        [panel close];[panel.entry removeFromSuperview];panel=nil;
    }
    if(!show){[panel.entry removeFromSuperview];return;}
    if(!panel){
        panel=[AGLobby new];panel.variant=v;panel.connection=connection;
        panel.entry=[UIButton buttonWithType:UIButtonTypeSystem];
        [panel.entry setTitle:@"Chiến trường · Gian hàng" forState:UIControlStateNormal];
        [panel.entry setTitleColor:UIColor.whiteColor forState:UIControlStateNormal];
        panel.entry.titleLabel.font=[UIFont boldSystemFontOfSize:13];
        panel.entry.backgroundColor=[UIColor colorWithRed:.07 green:.24 blue:.39 alpha:.94];
        panel.entry.layer.cornerRadius=5;
        [panel.entry addTarget:panel action:@selector(open) forControlEvents:UIControlEventTouchUpInside];
    }
    UIWindow *window=UIApplication.sharedApplication.keyWindow;
    if(panel.overlay || !window || window.windowLevel!=UIWindowLevelNormal || panel.entry.superview==window)return;
    UIButton *entry=panel.entry;[window addSubview:entry];entry.translatesAutoresizingMaskIntoConstraints=NO;
    [NSLayoutConstraint activateConstraints:@[
        [entry.trailingAnchor constraintEqualToAnchor:window.safeAreaLayoutGuide.trailingAnchor constant:-4],
        [entry.topAnchor constraintEqualToAnchor:window.safeAreaLayoutGuide.topAnchor constant:3],
        [entry.widthAnchor constraintEqualToConstant:166], [entry.heightAnchor constraintEqualToConstant:32]]];
}

// The game thread owns the session. UIKit only enqueues user actions for that session.
static AGLobby *activePanel;
void AGLobbyTick(void *env,int v,void *screen,int modal,uintptr_t connection){
    BOOL visible=connection && screen && !modal && atomic_load(&roomList[v])==(uintptr_t)screen;
    AGLobby *active;NSData *body;int cmd=0;
    @synchronized(AGLobby.class){
        if(battlefield[v]!=connection)battlefield[v]=0;
        if(visible || lobbyVariant==v){
            if(visible!=lobbyVisible || connection!=lobbyConnection || v!=lobbyVariant){
                lobbyVisible=visible;lobbyVariant=v;lobbyConnection=connection;
                dispatch_async(dispatch_get_main_queue(),^{refreshEntry();});
            }
        }
        active=activePanel;
        if(!active || active.variant!=v || active.connection!=connection)return;
        body=active.outgoing;cmd=active.command;active.outgoing=nil;
    }
    if(body && !AGLobbySend(env,v,connection,cmd,body.bytes,body.length)){
        dispatch_async(dispatch_get_main_queue(),^{[active close];});
    }
}

int AGLobbyReceive(void *env,void *message,int v){
    int cmd=*(int8_t *)((uint8_t *)message+0x30);
    if(cmd!=-120&&cmd!=-121)return 0;
    AGLobby *active;
    uintptr_t fight;
    @synchronized(AGLobby.class){active=activePanel;fight=battlefield[v];}
    uintptr_t connection=active&&active.variant==v?active.connection:fight;
    if(!connection || connection!=AGViewerConnection(env,v))return 0;
    uint8_t *in=*(uint8_t **)((uint8_t *)message+0x20);
    if(!in)return 1;
    uint8_t *array=*(uint8_t **)(in+0x10);
    if(!array)return 1;
    int count=*(int *)(in+0x18),pos=*(int *)(in+0x20);
    if(pos<0||count<=pos||count>*(int *)(array+0x10)||count-pos>65535)return 1;
    NSData *body=[NSData dataWithBytes:array+0x14+pos length:count-pos];
    const uint8_t *p=body.bytes;
    if(fight==connection && cmd==-120 && (body.length==9||body.length==10) && !memcmp(p,"CT46\x08\0\0\0\0",9)){
        @synchronized(AGLobby.class){battlefield[v]=0;}
        if(body.length==10){
            int outcome=(int8_t)p[9];
            NSString *text=outcome==1?@"Chiến thắng":outcome==-1?@"Thua trận":outcome==0?@"Hòa":@"Trận bị gián đoạn";
            dispatch_async(dispatch_get_main_queue(),^{
                UIViewController *top=UIApplication.sharedApplication.keyWindow.rootViewController;
                while(top.presentedViewController)top=top.presentedViewController;
                if(!top)return;
                UIAlertController *result=[UIAlertController alertControllerWithTitle:@"Chiến trường" message:text preferredStyle:UIAlertControllerStyleAlert];
                [result addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
                [top presentViewController:result animated:YES completion:nil];
            });
        }
        return 1;
    }
    if(!active || active.variant!=v || active.connection!=connection)return 0;
    if(cmd==-120 && body.length==9 && !memcmp(p,"CT46",4) && p[4]==6){
        uint32_t serial;memcpy(&serial,p+5,4);
        @synchronized(AGLobby.class){
            if(serial!=0 && active.watchSerial==serial)AGViewerExpectBattlefield(v,active.connection);
            if(serial!=0 && active.challengeSerial==serial)battlefield[v]=connection;
            active.watchSerial=0;
        }
        dispatch_async(dispatch_get_main_queue(),^{[active close];});return 1;
    }
    NSString *blob=[body base64EncodedStringWithOptions:0];
    dispatch_async(dispatch_get_main_queue(),^{
        if(!active.web)return;
        NSString *js=[NSString stringWithFormat:@"receiveFrame(%d,'%@')",cmd,blob];
        [active.web evaluateJavaScript:js completionHandler:^(id val,NSError *err){if(err)[active close];}];
    });
    return 1;
}

@implementation AGLobby
- (void)open{
    @synchronized(AGLobby.class){
        if(activePanel||!lobbyVisible||lobbyConnection!=self.connection||lobbyVariant!=self.variant)return;
        activePanel=self;
    }
    self.host=UIApplication.sharedApplication.keyWindow;
    if(!self.host){[self close];return;}
    NSURL *url=[[NSBundle bundleForClass:self.class] URLForResource:@"lobby" withExtension:@"html" subdirectory:@"viewer"];
    if(!url){[self close];return;}
    WKWebViewConfiguration *config=[WKWebViewConfiguration new];config.websiteDataStore=[WKWebsiteDataStore nonPersistentDataStore];
    [config.userContentController addScriptMessageHandler:self name:@"lobby"];
    self.web=[[WKWebView alloc] initWithFrame:CGRectZero configuration:config];self.web.navigationDelegate=self;
    self.view.backgroundColor=UIColor.whiteColor;
    [self.view addSubview:self.web];self.web.translatesAutoresizingMaskIntoConstraints=NO;
    UILayoutGuide *safe=self.view.safeAreaLayoutGuide;
    UIButton *back=[UIButton buttonWithType:UIButtonTypeSystem];[back setTitle:@"Về sảnh" forState:UIControlStateNormal];
    [back addTarget:self action:@selector(close) forControlEvents:UIControlEventTouchUpInside];
    back.translatesAutoresizingMaskIntoConstraints=NO;[self.view addSubview:back];
    [NSLayoutConstraint activateConstraints:@[[self.web.topAnchor constraintEqualToAnchor:safe.topAnchor],
        [self.web.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor],[self.web.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor],
        [self.web.bottomAnchor constraintEqualToAnchor:back.topAnchor],[back.heightAnchor constraintEqualToConstant:44],
        [back.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor],[back.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor]]];
    if(@available(iOS 13.0,*)){if(self.host.windowScene)self.overlay=[[UIWindow alloc] initWithWindowScene:self.host.windowScene];}
    if(!self.overlay)self.overlay=[[UIWindow alloc] initWithFrame:self.host.bounds];
    self.overlay.rootViewController=self;self.overlay.windowLevel=UIWindowLevelAlert;
    [self.overlay makeKeyAndVisible];[self.web loadFileURL:url allowingReadAccessToURL:url.URLByDeletingLastPathComponent];
}
- (void)close{
    @synchronized(AGLobby.class){if(activePanel==self)activePanel=nil;self.outgoing=nil;self.watchSerial=0;}
    BOOL restore=self.overlay.isKeyWindow;
    [self.web.configuration.userContentController removeScriptMessageHandlerForName:@"lobby"];
    [self.web stopLoading];self.web.navigationDelegate=nil;[self.web removeFromSuperview];self.web=nil;
    self.overlay.hidden=YES;self.overlay.rootViewController=nil;self.overlay=nil;
    if(self.isViewLoaded)self.view=nil;
    if(restore && !self.host.hidden)[self.host makeKeyWindow];
}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView{[self close];}
- (void)webView:(WKWebView *)web decidePolicyForNavigationAction:(WKNavigationAction *)action decisionHandler:(void (^)(WKNavigationActionPolicy))decision{
    NSURL *allowed=[[NSBundle bundleForClass:self.class] URLForResource:@"lobby" withExtension:@"html" subdirectory:@"viewer"];
    decision([action.request.URL isEqual:allowed]?WKNavigationActionPolicyAllow:WKNavigationActionPolicyCancel);
}
- (void)userContentController:(WKUserContentController *)ctrl didReceiveScriptMessage:(WKScriptMessage *)message{
    if(message.webView!=self.web||!message.frameInfo.isMainFrame||![message.body isKindOfClass:NSArray.class])return;
    NSArray *args=message.body;
    if(args.count!=2||![args[0] isKindOfClass:NSNumber.class]||![args[1] isKindOfClass:NSString.class]||[args[1] length]>1400)return;
    int cmd=[args[0] intValue];NSData *data=[[NSData alloc]initWithBase64EncodedString:args[1] options:0];
    if(!data.length||(cmd!=-120&&cmd!=-121))return;
    @synchronized(AGLobby.class){
        if(activePanel!=self||self.outgoing)return;
        self.watchSerial=0;self.challengeSerial=0;
        if(cmd==-120 && (data.length==17||data.length==18)){
            const uint8_t *p=data.bytes;
            uint32_t serial;memcpy(&serial,p+5,4);
            if(p[4]==6)self.watchSerial=serial;
            if(p[4]==3)self.challengeSerial=serial;
        }
        self.command=cmd;self.outgoing=data;
    }
}
@end
