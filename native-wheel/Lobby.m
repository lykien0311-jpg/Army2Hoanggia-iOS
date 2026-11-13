#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <string.h>
#include "Lobby.h"
#include "Spectator.h"
#include "Aura.h"
#import "GameViewport.h"

@interface AGLobby : UIViewController <WKScriptMessageHandler,WKNavigationDelegate>
@property(nonatomic,strong) UIWindow *overlay;
@property(nonatomic,weak) UIWindow *host;
@property(nonatomic,strong) WKWebView *web;
@property(nonatomic) uintptr_t connection;
@property(nonatomic) int variant;
@property(nonatomic) int tab;
@property(nonatomic) BOOL loaded;
@property(nonatomic) AGLobbyAccount account;
@property(nonatomic) uint32_t firstSerial;
@property(nonatomic) int command;
@property(nonatomic) uint32_t watchSerial;
@property(nonatomic) uint32_t challengeSerial;
@property(nonatomic) int fieldResult;
@property(nonatomic) BOOL closing;
@property(nonatomic,strong) NSData *outgoing;
- (void)open;
- (void)close;
@end

static atomic_bool opened[6];
static unsigned char held[6][256],pointer[6];
static BOOL opening;
static uintptr_t connections[6];
static uintptr_t battlefield[6];
static uintptr_t returnToBoard[6];
static int fieldResult[6];
static uint32_t nextFieldSerial;
static AGLobby *activePanel;
enum { NoFieldResult = 256 };

static NSString *eventAuras(NSData *body,int variant,uintptr_t connection){
    const uint8_t *p=body.bytes;
    size_t length=body.length;
    if(length<4)return @"[]";
    size_t pos=4+((p[2]<<8)|p[3]);
    NSMutableArray *codes=[NSMutableArray arrayWithCapacity:10];
    while(pos<length&&codes.count<10){
        if(length-pos<6)return @"[]";
        uint32_t id=(uint32_t)p[pos]<<24|(uint32_t)p[pos+1]<<16|(uint32_t)p[pos+2]<<8|p[pos+3];
        pos+=6+((p[pos+4]<<8)|p[pos+5]);
        if(pos>length||length-pos<25)return @"[]";
        [codes addObject:[NSString stringWithFormat:@"%d",AGAuraRank(variant,connection,id,p[pos])]];
        pos+=23;
        pos+=2+((p[pos]<<8)|p[pos+1]);
    }
    if(pos!=length)return @"[]";
    return [NSString stringWithFormat:@"[%@]",[codes componentsJoinedByString:@","]];
}

int AGLobbyOpened(int variant){return variant>=0&&variant<6?atomic_load(&opened[variant]):0;}
int AGLobbyInput(int variant,int kind,int code,int b){
    (void)b;
    if(variant<0||variant>=6)return 0;
    AGLobby *active;
    BOOL consumed;
    unsigned index=(unsigned)code+128;
    @synchronized(AGLobby.class){
        active=activePanel;
        consumed=atomic_load(&opened[variant]);
        if(kind==1&&index<256&&held[variant][index]){held[variant][index]=0;consumed=YES;}
        if(kind==4&&pointer[variant]){pointer[variant]=0;consumed=YES;}
        if(consumed&&kind==0&&index<256)held[variant][index]=1;
        if(consumed&&kind==2)pointer[variant]=1;
    }
    if(consumed&&kind==0)dispatch_async(dispatch_get_main_queue(),^{
        if(!active||active.variant!=variant||!active.web)return;
        BOOL back=code==-7||code==-22||code==-11||code==27||code==35||code=='R'||code=='r';
        NSString *script=[NSString stringWithFormat:@"typeof lobbyKey === 'function' && (lobbyKey(%d),true)",code];
        [active.web evaluateJavaScript:script completionHandler:^(id value,NSError *error){
            if(back&&(error||![value isEqual:@YES]))[active close];
        }];
    });
    return consumed;
}

static void openLobby(void *env,int variant,int tab,int outcome){
    if(!env||variant<0||variant>=6||tab<AGLobbyField||tab>AGLobbyEvent)return;
    uintptr_t connection=AGViewerConnection(env,variant);
    if(!connection)return;
    uint32_t serial=0;
    @synchronized(AGLobby.class){
        if(opening||activePanel)return;
        opening=YES;
        connections[variant]=connection;
        atomic_store(&opened[variant],1);
        if(tab==AGLobbyField){
            serial=nextFieldSerial;
            nextFieldSerial=(nextFieldSerial+100000)%2100000000;
        }
    }
    AGLobbyAccount account={.character=-1,.xu=-1,.luong=-1};
    if(tab==AGLobbyMarket)AGLobbyReadAccount(env,variant,&account);
    dispatch_async(dispatch_get_main_queue(),^{
        AGLobby *lobby=[AGLobby new];
        lobby.variant=variant;lobby.connection=connection;lobby.tab=tab;
        lobby.account=account;lobby.firstSerial=serial;lobby.fieldResult=outcome;
        [lobby open];
    });
}

__attribute__((visibility("default"))) void AGLobbyOpenNative(void *env,int variant,int tab){
    openLobby(env,variant,tab,NoFieldResult);
}

// The game thread owns the connection. UIKit enqueues requests against it.
void AGLobbyTick(void *env,int v,uintptr_t connection){
    AGLobby *active;NSData *body;int cmd=0,outcome=NoFieldResult;
    BOOL reopen=NO;
    @synchronized(AGLobby.class){
        connections[v]=connection;
        if(battlefield[v]!=connection)battlefield[v]=0;
        if(returnToBoard[v]!=connection)returnToBoard[v]=0;
        active=activePanel;
        if(!active&&!opening&&returnToBoard[v]){
            reopen=YES;
            outcome=fieldResult[v];
            returnToBoard[v]=0;
        }
        if(active&&active.variant==v&&!active.closing&&active.connection!=connection){
            active.closing=YES;
            dispatch_async(dispatch_get_main_queue(),^{[active close];});
            return;
        }
        if(active&&active.variant==v&&!active.closing){
            body=active.outgoing;cmd=active.command;active.outgoing=nil;
        }
    }
    if(reopen)openLobby(env,v,AGLobbyField,outcome);
    if(body && !AGLobbySend(env,v,connection,cmd,body.bytes,body.length)){
        dispatch_async(dispatch_get_main_queue(),^{
            if(cmd==-120){
                [active.web evaluateJavaScript:@"lobbyRequestFailed()" completionHandler:nil];
            }else [active close];
        });
    }else if(body&&cmd==5){
        dispatch_async(dispatch_get_main_queue(),^{if(active.web)[active.web evaluateJavaScript:@"lobbyMessageSent()" completionHandler:nil];});
    }
}

int AGLobbyReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return 0;
    int cmd=*(int8_t *)((uint8_t *)message+0x30);
    if(cmd!=-120&&cmd!=-121&&cmd!=-14&&cmd!=105)return 0;
    AGLobby *active;
    uintptr_t fight;
    @synchronized(AGLobby.class){active=activePanel;fight=battlefield[v];}
    if(cmd==105&&(!active||active.variant!=v||active.tab!=AGLobbyMarket))return 0;
    uintptr_t connection=active&&active.variant==v?active.connection:fight;
    if(!connection || connection!=AGViewerConnection(env,v))return 0;
    uint8_t *in=*(uint8_t **)((uint8_t *)message+0x20);
    if(!in)return cmd!=105;
    uint8_t *array=*(uint8_t **)(in+0x10);
    if(!array)return cmd!=105;
    int count=*(int *)(in+0x18),pos=*(int *)(in+0x20);
    if(pos<0||count<=pos||count>*(int *)(array+0x10)||count-pos>65535)return cmd!=105;
    NSData *body=[NSData dataWithBytes:array+0x14+pos length:count-pos];
    const uint8_t *p=body.bytes;
    if(cmd==105){
        if(body.length!=16)return 0;
        uint64_t xu=0,luong=0;
        for(int i=0;i<8;i++){xu=xu<<8|p[i];luong=luong<<8|p[8+i];}
        if(xu>INT64_MAX||luong>INT64_MAX)return 0;
        dispatch_async(dispatch_get_main_queue(),^{
            AGLobbyAccount next=active.account;
            next.xu=(int64_t)xu;next.luong=(int64_t)luong;
            active.account=next;
            if(active.loaded){
                NSString *js=[NSString stringWithFormat:@"lobbyBalance('%llu','%llu')",(unsigned long long)xu,(unsigned long long)luong];
                [active.web evaluateJavaScript:js completionHandler:nil];
            }
        });
        return 0;
    }
    if(cmd==-14&&p[0]!=3)return 0;
    if(fight==connection && cmd==-120 && (body.length==9||body.length==10) && !memcmp(p,"CT46\x08\0\0\0\0",9)){
        @synchronized(AGLobby.class){
            battlefield[v]=0;
            returnToBoard[v]=connection;
            fieldResult[v]=body.length==10?(int8_t)p[9]:NoFieldResult;
        }
        return 1;
    }
    if(!active||active.variant!=v||active.connection!=connection)return 0;
    if(cmd==-120 && body.length==9 && !memcmp(p,"CT46",4) && p[4]==6){
        uint32_t serial;memcpy(&serial,p+5,4);
        @synchronized(AGLobby.class){
            if(activePanel!=active||active.closing||!serial)return 1;
            if(active.watchSerial==serial)AGViewerExpectBattlefield(v,connection);
            else if(active.challengeSerial==serial)battlefield[v]=connection;
            else return 1;
            active.closing=YES;
            active.watchSerial=active.challengeSerial=0;
        }
        dispatch_async(dispatch_get_main_queue(),^{[active close];});return 1;
    }
    NSString *blob=[body base64EncodedStringWithOptions:0];
    NSString *auras=cmd==-14?eventAuras(body,v,connection):@"[]";
    dispatch_async(dispatch_get_main_queue(),^{
        if(!active.web)return;
        NSString *js=[NSString stringWithFormat:@"receiveFrame(%d,'%@',%@)",cmd,blob,auras];
        [active.web evaluateJavaScript:js completionHandler:^(id val,NSError *err){if(err)[active close];}];
    });
    return 1;
}

@implementation AGLobby
- (void)open{
    @synchronized(AGLobby.class){
        opening=NO;
        if(connections[self.variant]!=self.connection){atomic_store(&opened[self.variant],0);return;}
        activePanel=self;
    }
    self.host=UIApplication.sharedApplication.keyWindow;
    if(!self.host){[self close];return;}
    NSURL *url=[[NSBundle bundleForClass:self.class] URLForResource:@"lobby" withExtension:@"html" subdirectory:@"viewer"];
    if(!url){[self close];return;}
    WKWebViewConfiguration *config=[WKWebViewConfiguration new];config.websiteDataStore=[WKWebsiteDataStore nonPersistentDataStore];
    [config.userContentController addScriptMessageHandler:self name:@"lobby"];
    self.web=[[WKWebView alloc] initWithFrame:CGRectZero configuration:config];self.web.navigationDelegate=self;
    self.view.backgroundColor=UIColor.clearColor;
    self.web.opaque=NO;self.web.backgroundColor=UIColor.clearColor;
    self.web.scrollView.scrollEnabled=NO;self.web.scrollView.bounces=NO;
    self.web.scrollView.contentInsetAdjustmentBehavior=UIScrollViewContentInsetAdjustmentNever;
    [self.view addSubview:self.web];
    if(@available(iOS 13.0,*)){if(self.host.windowScene)self.overlay=[[AGGameWindow alloc] initWithWindowScene:self.host.windowScene];}
    if(!self.overlay)self.overlay=[[AGGameWindow alloc] initWithFrame:self.host.bounds];
    ((AGGameWindow *)self.overlay).passesGameKeys=YES;
    AGViewportWheelVisible(1);
    self.overlay.rootViewController=self;self.overlay.windowLevel=UIWindowLevelAlert;
    [self.overlay makeKeyAndVisible];[self.web loadFileURL:url allowingReadAccessToURL:url.URLByDeletingLastPathComponent];
}
- (void)viewDidLayoutSubviews{
    [super viewDidLayoutSubviews];
    CGRect game=AGGameRect(self.view);self.web.frame=game;
    ((AGGameWindow *)self.overlay).gameBottom=CGRectGetMaxY(game);
}
- (void)close{
    @synchronized(AGLobby.class){
        if(activePanel!=self)return;
        self.closing=YES;
        self.outgoing=nil;
        self.watchSerial=self.challengeSerial=0;
    }
    if(self.overlay)AGViewportWheelVisible(0);
    BOOL restore=self.overlay.isKeyWindow;
    [self.web.configuration.userContentController removeScriptMessageHandlerForName:@"lobby"];
    [self.web stopLoading];self.web.navigationDelegate=nil;[self.web removeFromSuperview];self.web=nil;
    self.overlay.hidden=YES;self.overlay.rootViewController=nil;self.overlay=nil;
    if(self.isViewLoaded)self.view=nil;
    if(restore && !self.host.hidden)[self.host makeKeyWindow];
    @synchronized(AGLobby.class){
        activePanel=nil;
        atomic_store(&opened[self.variant],0);
    }
}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView{[self close];}
- (void)webView:(WKWebView *)web didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error{[self close];}
- (void)webView:(WKWebView *)web didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error{[self close];}
- (void)webView:(WKWebView *)web didFinishNavigation:(WKNavigation *)navigation{
    if(web!=self.web||self.loaded)return;
    NSString *tab=self.tab==AGLobbyField?@"field":self.tab==AGLobbyMarket?@"market":@"event";
    AGLobbyAccount account=self.account;
    NSString *outcome=self.fieldResult==NoFieldResult?@"null":[NSString stringWithFormat:@"%d",self.fieldResult];
    NSString *start=[NSString stringWithFormat:@"lobbyViewport(%d);openTab('%@',%d,%u,%@);lobbyBalance('%lld','%lld')",
                     account.canvasWidth,tab,account.character,self.firstSerial,outcome,(long long)account.xu,(long long)account.luong];
    self.loaded=YES;
    [web evaluateJavaScript:start completionHandler:^(id value,NSError *error){if(error)[self close];}];
}
- (void)webView:(WKWebView *)web decidePolicyForNavigationAction:(WKNavigationAction *)action decisionHandler:(void (^)(WKNavigationActionPolicy))decision{
    NSURL *allowed=[[NSBundle bundleForClass:self.class] URLForResource:@"lobby" withExtension:@"html" subdirectory:@"viewer"];
    decision([action.request.URL isEqual:allowed]?WKNavigationActionPolicyAllow:WKNavigationActionPolicyCancel);
}
- (void)userContentController:(WKUserContentController *)ctrl didReceiveScriptMessage:(WKScriptMessage *)message{
    if(message.webView!=self.web||!message.frameInfo.isMainFrame||![message.body isKindOfClass:NSArray.class])return;
    NSArray *args=message.body;
    if(args.count==2&&[args[0] isKindOfClass:NSString.class]&&[args[0] isEqual:@"close"]){[self close];return;}
    if(args.count==2&&[args[0] isEqual:@"edit"]&&[args[1] isKindOfClass:NSDictionary.class]){
        NSDictionary *input=args[1];
        NSNumber *serial=input[@"serial"],*limit=input[@"maxLength"];
        NSString *value=input[@"value"],*type=input[@"type"];
        if(![serial isKindOfClass:NSNumber.class]||serial.longLongValue<1||serial.longLongValue>INT32_MAX||
           ![limit isKindOfClass:NSNumber.class]||limit.intValue<1||limit.intValue>100||
           ![value isKindOfClass:NSString.class]||value.length>100||![type isKindOfClass:NSString.class]||self.presentedViewController)return;
        __weak AGLobby *weakSelf=self;
        void (^result)(id)=^(id text){
            AGLobby *panel=weakSelf;if(!panel||panel.closing||!panel.web)return;
            NSData *data=[NSJSONSerialization dataWithJSONObject:@[serial,text?:NSNull.null] options:0 error:nil];
            NSString *json=[[NSString alloc]initWithData:data encoding:NSUTF8StringEncoding];
            [panel.web evaluateJavaScript:[NSString stringWithFormat:@"lobbyInputResult(...%@)",json] completionHandler:nil];
        };
        UIAlertController *alert=[UIAlertController alertControllerWithTitle:@"Nhập" message:nil preferredStyle:UIAlertControllerStyleAlert];
        [alert addTextFieldWithConfigurationHandler:^(UITextField *field){
            field.text=value;field.secureTextEntry=[type isEqual:@"password"];
            field.autocorrectionType=UITextAutocorrectionTypeNo;field.autocapitalizationType=UITextAutocapitalizationTypeNone;
            field.keyboardType=[input[@"numeric"] isEqual:@YES]?UIKeyboardTypeNumberPad:UIKeyboardTypeDefault;
            field.returnKeyType=UIReturnKeyDone;
        }];
        [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:^(UIAlertAction *action){
            NSString *text=alert.textFields.firstObject.text?:@"";
            if(text.length>limit.unsignedIntegerValue)text=[text substringToIndex:limit.unsignedIntegerValue];
            alert.textFields.firstObject.text=@"";result(text);
        }]];
        [alert addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:^(UIAlertAction *action){alert.textFields.firstObject.text=@"";result(nil);}]];
        [self presentViewController:alert animated:YES completion:nil];return;
    }
    if(args.count!=2||![args[0] isKindOfClass:NSNumber.class]||![args[1] isKindOfClass:NSString.class]||[args[1] length]>1400)return;
    int cmd=[args[0] intValue];NSData *data=[[NSData alloc]initWithBase64EncodedString:args[1] options:0];
    if(!data.length||(cmd!=-120&&cmd!=-121&&cmd!=-14&&cmd!=5))return;
    @synchronized(AGLobby.class){
        if(activePanel!=self||self.closing||self.outgoing)return;
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


