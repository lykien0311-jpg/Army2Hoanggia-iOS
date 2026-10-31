#import <UIKit/UIKit.h>
#import <QuartzCore/QuartzCore.h>
#include <mach-o/dyld.h>
#include <pthread.h>
#include <stdatomic.h>
#include <time.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
#include "WheelProtocol.h"
#include "NativeMap.h"
#include "Notes77.h"
#include "Turn33.h"
#import "GameViewport.h"
extern void AGInventoryTick(int);

// Exported release identity binds the Apple artifact to the native login patch.
__attribute__((visibility("default"))) const char *AGReleaseIdentity(void) { return "2.4.1-HG78-IPA"; }

// UI work stays on UIKit's main thread. Java calls stay on the original game
// thread with its Env, protected by RoboVM's catch-all exception context.
static pthread_mutex_t AGMutex=PTHREAD_MUTEX_INITIALIZER;
static atomic_int AGInterested=0, AGForeground=1;
typedef struct {
    AGSnapshot snapshot;
    int variant, visible, loaded, waiting, sendNow, page;
    uint64_t generation;
    uintptr_t connection;
    double openedAt, receivedAt, lastPoll, lastBet, noticeUntil;
    int64_t nonce, betRound, amount;
    char notice[AG_TEXT];
} AGModel;
static AGModel AGState={.variant=-1};
// Called from the game's original base-screen painter. Suppress its small
// command row while the UIKit wheel owns those commands; the native keypad
// is painted separately by GameCanvas and remains visible and interactive.
__attribute__((visibility("default"))) int AGWheelSuppressFooter(int variant) {
    pthread_mutex_lock(&AGMutex);
    int hide=AGState.visible&&AGState.variant==variant;
    pthread_mutex_unlock(&AGMutex);return hide;
}
static double AGNow(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9; }
// A device report must distinguish missing turn data from animation guards.
// Only atomics are touched on Java threads; UIKit polls on the main thread.
static atomic_int AGTurnReason=0, AGTurnDiagnosticVariant=-1;
static _Atomic(double) AGTurnUpdated=0;
static void AGInstallTurnStatus(void);
__attribute__((visibility("default"))) void AGTurnStatusUpdate(int variant,int reason) {
    atomic_store(&AGTurnDiagnosticVariant,variant);
    atomic_store(&AGTurnReason,reason);atomic_store(&AGTurnUpdated,AGNow());
    if(reason){static dispatch_once_t once;dispatch_once(&once,^{dispatch_async(dispatch_get_main_queue(),^{AGInstallTurnStatus();});});}
}
__attribute__((visibility("default"))) void AGTurnPulse(void *env,int variant) {
    if(atomic_load(&AGForeground))AGTurnTick(env,variant);
}
@interface AGTurnStatusWindow : UIWindow
@end
@implementation AGTurnStatusWindow
- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event{return nil;}
@end
static void AGInstallTurnStatus(void) {
    static AGTurnStatusWindow *window;static UILabel *label;static NSTimer *timer;
    timer=[NSTimer scheduledTimerWithTimeInterval:.25 repeats:YES block:^(NSTimer *t){
        int reason=atomic_load(&AGTurnReason);
        BOOL visible=reason>0&&reason<12&&AGNow()-atomic_load(&AGTurnUpdated)<2&&UIApplication.sharedApplication.applicationState==UIApplicationStateActive;
        if(!visible){window.hidden=YES;return;}
        UIWindow *game=nil;for(UIWindow *w in UIApplication.sharedApplication.windows)if(!w.hidden&&w.windowLevel==UIWindowLevelNormal){game=w;break;}
        if(!game)return;
        if(!window){
            if(@available(iOS 13.0,*)){if(game.windowScene)window=[[AGTurnStatusWindow alloc]initWithWindowScene:game.windowScene];}
            if(!window)window=[[AGTurnStatusWindow alloc]initWithFrame:game.frame];
            window.backgroundColor=UIColor.clearColor;window.opaque=NO;window.windowLevel=UIWindowLevelStatusBar+1;
            window.rootViewController=[UIViewController new];window.rootViewController.view.backgroundColor=UIColor.clearColor;
            label=[UILabel new];label.textColor=UIColor.whiteColor;label.backgroundColor=[UIColor colorWithWhite:0 alpha:.55];
            label.textAlignment=NSTextAlignmentCenter;label.font=[UIFont systemFontOfSize:11 weight:UIFontWeightMedium];label.adjustsFontSizeToFitWidth=YES;
            label.layer.cornerRadius=4;label.clipsToBounds=YES;label.isAccessibilityElement=YES;
            [window.rootViewController.view addSubview:label];
        }
        NSArray *reasons=@[@"",@"Chờ dữ liệu lượt",@"Chờ dữ liệu bắn",@"Chờ nhân vật sẵn sàng",@"Chờ kết thúc hiệu ứng",@"Chờ đúng vị trí",@"Chờ lượt của bạn",@"Đang mở hộp thoại",@"Đã gọi bắn",@"Dữ liệu trận đã đổi",@"Chưa bật auto",@"Chưa gọi được hàm bắn"];
        window.frame=game.frame;UIEdgeInsets safe=game.safeAreaInsets;
        label.frame=CGRectMake(safe.left+8,safe.top+2,MAX(1,game.bounds.size.width-safe.left-safe.right-16),19);
        label.text=[@"Auto UFO: " stringByAppendingString:reasons[reason]];window.hidden=NO;
    }];
    [[NSRunLoop mainRunLoop]addTimer:timer forMode:NSRunLoopCommonModes];
}
static NSString *AGString(const char *s) {return [NSString stringWithUTF8String:s]?:@"";}
static NSString *AGMoney(int64_t value) {
    static NSNumberFormatter *f; static dispatch_once_t once;
    dispatch_once(&once,^{f=[NSNumberFormatter new];f.locale=[[NSLocale alloc]initWithLocaleIdentifier:@"vi_VN"];f.numberStyle=NSNumberFormatterDecimalStyle;f.maximumFractionDigits=0;});
    return [f stringFromNumber:@(value)];
}
static AGModel AGCopy(void) {pthread_mutex_lock(&AGMutex);AGModel m=AGState;pthread_mutex_unlock(&AGMutex);return m;}
static int64_t AGServerNow(AGModel m) {
    double elapsed=fmax(0,AGNow()-m.receivedAt);
    if(elapsed>86400)elapsed=86400;
    if(m.snapshot.serverTime>INT64_MAX-(int64_t)(elapsed*1000))return INT64_MAX;
    return m.snapshot.serverTime+(int64_t)(elapsed*1000);
}
static void AGNotice(const char *text) {
    pthread_mutex_lock(&AGMutex);snprintf(AGState.notice,sizeof AGState.notice,"%s",text);AGState.noticeUntil=AGNow()+10;pthread_mutex_unlock(&AGMutex);
}
typedef struct {
    uintptr_t base, expectedConnection, connection;
    int variant;size_t length;uint8_t bytes[28];
} AGSendJob;
extern int AGWheelGuard(void *, int (*)(void *,void *),void *,void *);

// No Objective-C ownership or locks may cross this function: Java exceptions
// use longjmp. Volatile stack roots remain visible to RoboVM's conservative GC.
__attribute__((noinline,optnone)) static int AGSendNative(void *env, void *context) {
    AGSendJob *j=context; const AGNativeMap *map=&AGMaps[j->variant];
    void *(*get)(void *)=(void *)(j->base+map->service);
    void *volatile service=get(env);if(!service)return 0;
    void *volatile session=*(void **)((uint8_t *)service+0x10);if(!session)return 0;
    j->connection=(uintptr_t)session;
    if(j->expectedConnection && j->expectedConnection!=j->connection)return -2;
    void *(*allocate)(void *)=(void *)(j->base+map->alloc);
    void (*construct)(void *,void *,int)=(void *)(j->base+map->ctor);
    void (*writeByte)(void *,void *,int)=(void *)(j->base+0xa64a3c);
    void (*send)(void *,void *,void *)=(void *)(j->base+map->send);
    void *volatile message=allocate(env);if(!message)return 0;
    construct(env,message,-101);
    void *volatile writer=*(void **)((uint8_t *)message+0x18);if(!writer)return 0;
    for(size_t i=0;i<j->length;i++)writeByte(env,writer,j->bytes[i]);
    send(env,session,message);return 1;
}

__attribute__((visibility("default"))) void AGWheelTick(void *env, int variant) {
    if(env){AGViewportCapture(variant);AGInventoryTick(variant);}
    AGNotesTick(env,variant);
    if(atomic_load(&AGForeground))AGTurnTick(env,variant);
    if(!env || variant<0 || variant>=6 || !atomic_load(&AGInterested) || !atomic_load(&AGForeground))return;
    double now=AGNow();AGSendJob job={0};uint64_t generation;int isBet=0;
    pthread_mutex_lock(&AGMutex);
    if(AGState.variant!=variant || (!AGState.visible && !AGState.waiting)) {pthread_mutex_unlock(&AGMutex);return;}
    if(AGState.waiting && (AGState.sendNow || now-AGState.lastBet>=7)) {
        isBet=1;job.length=AGBet(job.bytes,AGState.betRound,AGState.nonce,AGState.amount);
        AGState.lastBet=now;AGState.sendNow=0;
    } else if(now-AGState.lastPoll>=2) {
        job.length=AGPoll(job.bytes,AGState.page);AGState.lastPoll=now;
    }
    generation=AGState.generation;job.expectedConnection=AGState.connection;
    pthread_mutex_unlock(&AGMutex);
    if(!job.length)return;
    job.variant=variant;job.base=(uintptr_t)_dyld_get_image_header(0);
    int result=AGWheelGuard(env,AGSendNative,&job,(void *)(job.base+0x1300d54));
    pthread_mutex_lock(&AGMutex);
    if(generation==AGState.generation) {
        if(result==-2) {
            AGState.loaded=0;AGState.waiting=0;AGState.nonce=0;AGState.connection=job.connection;AGState.lastPoll=0;
            snprintf(AGState.notice,sizeof AGState.notice,"Kết nối đã đổi. Đang tải lại dữ liệu vòng xoay.");AGState.noticeUntil=now+10;
        } else if(result<=0) {
            AGState.loaded=0;
            snprintf(AGState.notice,sizeof AGState.notice,"Chưa gửi được yêu cầu. Đang chờ kết nối game…");AGState.noticeUntil=now+8;
        } else {
            AGState.connection=job.connection;
            if(isBet && AGState.waiting)snprintf(AGState.notice,sizeof AGState.notice,"Đang chờ máy chủ xác nhận lượt đặt…");
        }
    }
    pthread_mutex_unlock(&AGMutex);
}

__attribute__((visibility("default"))) void AGWheelReceive(void *env, void *message, int variant) {
    (void)env;
    if(!message || variant<0 || variant>=6)return;
    const uint8_t *input=*(const uint8_t **)((uint8_t *)message+0x20);if(!input)return;
    const uint8_t *array=*(const uint8_t **)(input+0x10);if(!array)return;
    int32_t length=*(const int32_t *)(array+0x10),count=*(const int32_t *)(input+0x18),pos=*(const int32_t *)(input+0x20);
    if(length<0||count<0||count>length||pos<0||pos>count||count-pos>65535)return;
    AGSnapshot parsed;
    if(!AGParse(array+0x14+pos,(size_t)(count-pos),&parsed)) {
        pthread_mutex_lock(&AGMutex);
        if(variant==AGState.variant) {AGState.loaded=0;snprintf(AGState.notice,sizeof AGState.notice,"Gói vòng xoay không hợp lệ. Đang tải lại…");AGState.noticeUntil=AGNow()+8;}
        pthread_mutex_unlock(&AGMutex);return;
    }
    pthread_mutex_lock(&AGMutex);
    if(variant==AGState.variant) {
        if(!AGState.loaded || parsed.serverTime>=AGState.snapshot.serverTime) {
            AGState.snapshot=parsed;AGState.loaded=1;AGState.receivedAt=AGNow();AGState.page=parsed.page;
        }
        // An acknowledgement is still authoritative if a newer poll snapshot
        // has already arrived. Do not roll the displayed round backwards.
        if(parsed.ack && parsed.ack==AGState.nonce) {
            AGState.waiting=0;AGState.nonce=0;AGState.sendNow=0;
            snprintf(AGState.notice,sizeof AGState.notice,"%s",parsed.message[0]?parsed.message:(parsed.status?"Máy chủ từ chối lượt đặt.":"Đã xác nhận lượt tham gia."));
            AGState.noticeUntil=AGNow()+10;
        } else if(!AGState.waiting && parsed.status && parsed.message[0]) {
            snprintf(AGState.notice,sizeof AGState.notice,"%s",parsed.message);AGState.noticeUntil=AGNow()+10;
        }
        if(!AGState.visible&&!AGState.waiting)atomic_store(&AGInterested,0);
    }
    pthread_mutex_unlock(&AGMutex);
}

#include "ClassicWheelUI.inc"
@interface AGWheelController : UIViewController
@property(nonatomic,strong) AGClassicPanel *panel;
@property(nonatomic,strong) UIScrollView *panelScroll;
@property(nonatomic,strong) AGPixelButton *betButton,*middleButton,*exitButton;
@property(nonatomic,strong) UIStackView *controls;
@property(nonatomic,strong) AGAmountPanel *amountPanel;
@property(nonatomic,strong) UITextField *amountField;
@property(nonatomic,strong) NSTimer *timer;
@property(nonatomic,strong) UIView *backdrop;
@property(nonatomic) BOOL editingAmount;
@property(nonatomic) CGFloat keyboardInset;
- (void)primary;
- (void)secondary;
- (void)close;
- (void)endAmountEntry;
@end
static AGGameWindow *AGWindow;
static __weak UIWindow *AGPreviousWindow;
static AGWheelController *AGController;
// Capture presses and their releases; only forward to the active wheel UI.
int AGWheelInput(int variant,int kind,int code,int y){
    if(variant<0||variant>=6)return 0;
    static unsigned char held[6][256],pointer[6];
    int index=code+128,consumed;uint64_t generation;
    pthread_mutex_lock(&AGMutex);
    consumed=AGState.visible&&AGState.variant==variant;generation=AGState.generation;
    if(kind==1&&index>=0&&index<256&&held[variant][index]){held[variant][index]=0;consumed=1;}
    if(kind==4&&pointer[variant]){pointer[variant]=0;consumed=1;}
    if(consumed&&kind==0&&index>=0&&index<256)held[variant][index]=1;
    if(consumed&&kind==2)pointer[variant]=1;
    pthread_mutex_unlock(&AGMutex);
    if(consumed&&kind==0)dispatch_async(dispatch_get_main_queue(),^{
        AGModel m=AGCopy();AGWheelController *c=AGController;
        if(!m.visible||m.variant!=variant||m.generation!=generation||!c||c.presentedViewController)return;
        if(code==-6)[c primary];
        else if(code==-7||code==27){if(c.editingAmount)[c endAmountEntry];else [c close];}
        else if(code==-5||code==10||code==13)[c secondary];
        else if(c.editingAmount&&code>=48&&code<=57)c.amountField.text=[(c.amountField.text?:@"") stringByAppendingFormat:@"%c",code];
        else if(c.editingAmount&&(code==8||code==127))[c.amountField deleteBackward];
        else if(code==-1||code==-2){CGFloat limit=MAX(0,c.panelScroll.contentSize.height-c.panelScroll.bounds.size.height);CGPoint p=c.panelScroll.contentOffset;p.y=MAX(0,MIN(limit,p.y+(code==-1?-44:44)));[c.panelScroll setContentOffset:p animated:NO];}
    });
    return consumed;
}
@implementation AGWheelController
- (UIInterfaceOrientationMask)supportedInterfaceOrientations{return UIInterfaceOrientationMaskAllButUpsideDown;}
- (BOOL)prefersStatusBarHidden{return YES;}
- (AGPixelButton *)button:(NSString *)text action:(SEL)action{
    AGPixelButton *b=[AGPixelButton buttonWithType:UIButtonTypeCustom];b.accessibilityLabel=text;
    [b addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];return b;
}
- (void)viewDidLoad{
    [super viewDidLoad];self.view.backgroundColor=UIColor.clearColor;
    self.backdrop=[UIView new];self.backdrop.backgroundColor=[UIColor colorWithRed:87/255.0 green:201/255.0 blue:239/255.0 alpha:1];[self.view addSubview:self.backdrop];
    self.panel=[AGClassicPanel new];self.panel.opaque=NO;self.panel.isAccessibilityElement=YES;
    self.betButton=[self button:@"Tham gia" action:@selector(primary)];self.betButton.tag=1;
    self.middleButton=[self button:@"Cập nhật" action:@selector(secondary)];
    self.exitButton=[self button:@"Trở ra" action:@selector(tertiary)];self.exitButton.tag=2;
    self.controls=[[UIStackView alloc]initWithArrangedSubviews:@[self.betButton,self.middleButton,self.exitButton]];
    self.controls.axis=UILayoutConstraintAxisHorizontal;self.controls.distribution=UIStackViewDistributionFillEqually;self.controls.spacing=0;
    self.panelScroll=[UIScrollView new];self.panelScroll.alwaysBounceVertical=NO;
    self.controls.backgroundColor=AGPaper();[self.panelScroll addSubview:self.panel];[self.view addSubview:self.panelScroll];[self.view addSubview:self.controls];
    self.amountPanel=[AGAmountPanel new];self.amountPanel.opaque=NO;self.amountPanel.hidden=YES;
    self.amountField=[UITextField new];self.amountField.keyboardType=UIKeyboardTypeNumberPad;
    self.amountField.textColor=UIColor.whiteColor;self.amountField.tintColor=UIColor.whiteColor;
    self.amountField.backgroundColor=[UIColor colorWithRed:66/255.0 green:107/255.0 blue:146/255.0 alpha:1];
    self.amountField.borderStyle=UITextBorderStyleNone;self.amountField.accessibilityLabel=@"Số xu tham gia vòng xoay";
    self.amountField.autocorrectionType=UITextAutocorrectionTypeNo;self.amountField.spellCheckingType=UITextSpellCheckingTypeNo;
    [self.amountPanel addSubview:self.amountField];[self.view addSubview:self.amountPanel];
    [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(keyboardChanged:) name:UIKeyboardWillChangeFrameNotification object:nil];
    __weak AGWheelController *weakSelf=self;
    self.timer=[NSTimer scheduledTimerWithTimeInterval:.2 repeats:YES block:^(NSTimer *t){[weakSelf render];}];[self render];
}
- (void)viewDidLayoutSubviews{
    [super viewDidLayoutSubviews];UIEdgeInsets safe=self.view.safeAreaInsets;
    CGRect game=AGGameRect(self.view);
    CGFloat bottom=self.keyboardInset>0?self.view.bounds.size.height-safe.bottom-self.keyboardInset:CGRectGetMaxY(game);
    CGFloat width=game.size.width,height=MAX(1,bottom-safe.top);
    self.backdrop.frame=CGRectMake(0,0,self.view.bounds.size.width,bottom);
    AGWindow.gameBottom=bottom;AGWindow.passesGameKeys=self.keyboardInset<=0;
    CGFloat bar=MAX(44,MIN(64,width/7)),panelHeight=MAX(1,height-bar-8),panelWidth=MAX(1,width-8),s=AGPanelScale(panelWidth,panelHeight);
    self.panelScroll.frame=CGRectMake(safe.left+4,safe.top+4,panelWidth,panelHeight);
    CGFloat contentHeight=MAX(panelHeight,450*s);
    self.panel.frame=CGRectMake(0,0,panelWidth,contentHeight);self.panelScroll.contentSize=CGSizeMake(panelWidth,contentHeight);
    CGFloat controlsY=safe.top+MAX(0,height-bar);
    self.controls.frame=CGRectMake(safe.left,controlsY,width,bar);
    CGFloat inputHeight=MIN(MAX(80,75*s),MAX(0,controlsY-safe.top-4));
    CGFloat inputScale=MIN(s,inputHeight/75),fieldY=inputHeight<66?4:36*inputScale;
    self.amountPanel.layoutScale=inputScale;
    self.amountPanel.frame=CGRectMake(safe.left+4,controlsY-inputHeight,panelWidth,inputHeight);
    self.amountField.frame=CGRectMake(13*inputScale,fieldY,panelWidth-26*inputScale,MAX(0,MIN(MAX(28,27*inputScale),inputHeight-fieldY-4)));
    self.amountField.font=[UIFont monospacedDigitSystemFontOfSize:MAX(17,17*inputScale) weight:UIFontWeightBold];
    [self.panel setNeedsDisplay];[self.amountPanel setNeedsDisplay];
}
- (void)keyboardChanged:(NSNotification *)notification{
    CGRect screen=[notification.userInfo[UIKeyboardFrameEndUserInfoKey]CGRectValue];
    CGRect keyboard=[self.view convertRect:screen fromView:nil];
    CGFloat bottom=self.view.bounds.size.height-self.view.safeAreaInsets.bottom;
    self.keyboardInset=self.editingAmount&&CGRectIntersectsRect(self.view.bounds,keyboard)?MAX(0,bottom-CGRectGetMinY(keyboard)):0;
    [self.view setNeedsLayout];[self.view layoutIfNeeded];
}
- (void)dealloc{[NSNotificationCenter.defaultCenter removeObserver:self];}
- (void)primary{if(self.editingAmount)[self endAmountEntry];else [self bet];}
- (void)secondary{if(self.editingAmount)[self submitAmount];else [self refresh];}
- (void)tertiary{if(self.editingAmount)[self.amountField deleteBackward];else [self close];}
- (void)endAmountEntry{
    self.editingAmount=NO;self.amountPanel.hidden=YES;self.keyboardInset=0;
    [self.amountField resignFirstResponder];[self.view setNeedsLayout];[self render];
}
- (void)render{
    // Keypad projection can become available after the first wheel layout.
    [self.view setNeedsLayout];
    AGModel m=AGCopy();AGSnapshot s=m.snapshot;BOOL fresh=m.loaded&&AGNow()-m.receivedAt<6;
    int64_t now=AGServerNow(m),remain=s.ends>now?(s.ends-now+999)/1000:0;
    BOOL locked=s.ends>0&&now>=s.ends-10000;
    self.panel.snapshot=s;self.panel.loaded=m.loaded;self.panel.locked=locked;
    self.panel.remaining=m.loaded&&s.count<2?120:remain;
    self.betButton.enabled=self.editingAmount||(fresh&&!m.waiting&&!locked&&s.balance>=AG_MIN_STAKE&&s.own<=AG_MAX_STAKE-AG_MIN_STAKE);
    self.betButton.accessibilityLabel=self.editingAmount?@"Đóng":@"Tham gia";
    self.middleButton.accessibilityLabel=self.editingAmount?@"OK":@"Cập nhật";
    self.exitButton.accessibilityLabel=self.editingAmount?@"Xóa":@"Trở ra";
    NSString *notice=@"";
    if(m.waiting)notice=@"Đang xác nhận lượt tham gia";
    else if(!fresh)notice=m.loaded?@"Đang cập nhật kết nối":@"Đang tải dữ liệu";
    else if(m.notice[0]&&AGNow()<m.noticeUntil)notice=AGString(m.notice);
    self.panel.notice=notice;
    self.panel.accessibilityLabel=[NSString stringWithFormat:@"Vòng xoay may mắn. Quỹ %@ xu. %d người. Bạn đã tham gia %@ xu. Số dư %@ xu. %@",AGMoney(s.total),s.count,AGMoney(s.own),AGMoney(s.balance),notice];
    [self.panel setNeedsDisplay];[self.betButton setNeedsDisplay];[self.middleButton setNeedsDisplay];[self.exitButton setNeedsDisplay];
}
- (void)alert:(NSString *)text {
    UIAlertController *a=[UIAlertController alertControllerWithTitle:@"Vòng xoay may mắn" message:text preferredStyle:UIAlertControllerStyleAlert];[a addAction:[UIAlertAction actionWithTitle:@"Đã hiểu" style:UIAlertActionStyleDefault handler:nil]];[self presentViewController:a animated:YES completion:nil];
}
- (void)bet {
    AGModel m=AGCopy();if(!m.loaded||m.waiting||AGNow()-m.receivedAt>=6)return;
    self.editingAmount=YES;self.amountPanel.hidden=NO;self.amountField.text=@"";
    [self render];[self.view setNeedsLayout];[self.view layoutIfNeeded];[self.amountField becomeFirstResponder];
}
- (void)submitAmount {
    __weak AGWheelController *weakSelf=self;
        NSString *input=[self.amountField.text stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        if(!input.length||input.length>8||[input rangeOfCharacterFromSet:NSCharacterSet.decimalDigitCharacterSet.invertedSet].location!=NSNotFound){[weakSelf alert:@"Nhập số xu bằng chữ số, không dùng dấu chấm hoặc dấu phẩy."];return;}
        int64_t amount=input.longLongValue;AGModel current=AGCopy();const char *error=AGValidateBet(&current.snapshot,AGServerNow(current),amount);
        if(!current.loaded||current.waiting||AGNow()-current.receivedAt>=6){[weakSelf alert:@"Dữ liệu đang cập nhật. Vui lòng thử lại."];return;}
        if(error){[weakSelf alert:AGString(error)];return;}
        int64_t round=current.snapshot.round;uint64_t generation=current.generation;
        [self endAmountEntry];
        UIAlertController *confirm=[UIAlertController alertControllerWithTitle:@"Xác nhận tham gia" message:[NSString stringWithFormat:@"Dùng %@ xu để tham gia vòng #%lld?",AGMoney(amount),(long long)round]preferredStyle:UIAlertControllerStyleAlert];
        [confirm addAction:[UIAlertAction actionWithTitle:@"Hủy" style:UIAlertActionStyleCancel handler:nil]];
        [confirm addAction:[UIAlertAction actionWithTitle:@"Xác nhận" style:UIAlertActionStyleDefault handler:^(UIAlertAction *action){
            const char *failure=NULL;pthread_mutex_lock(&AGMutex);
            if(AGState.generation!=generation||AGState.snapshot.round!=round||!AGState.loaded||AGState.waiting||AGNow()-AGState.receivedAt>=6)failure="Vòng chơi hoặc dữ liệu đã đổi. Vui lòng thử lại.";
            else failure=AGValidateBet(&AGState.snapshot,AGServerNow(AGState),amount);
            if(!failure){uint64_t nonce;arc4random_buf(&nonce,sizeof nonce);nonce&=INT64_MAX;if(!nonce)nonce=1;AGState.nonce=(int64_t)nonce;AGState.betRound=round;AGState.amount=amount;AGState.waiting=1;AGState.sendNow=1;atomic_store(&AGInterested,1);}
            pthread_mutex_unlock(&AGMutex);if(failure)[weakSelf alert:AGString(failure)];[weakSelf render];
        }]];
        [weakSelf presentViewController:confirm animated:YES completion:nil];
}
- (void)refresh {pthread_mutex_lock(&AGMutex);AGState.lastPoll=0;pthread_mutex_unlock(&AGMutex);}
- (void)previous {pthread_mutex_lock(&AGMutex);if(AGState.page>0)AGState.page--;AGState.lastPoll=0;pthread_mutex_unlock(&AGMutex);}
- (void)next {pthread_mutex_lock(&AGMutex);if(((int64_t)AGState.page+1)*20<AGState.snapshot.count)AGState.page++;AGState.lastPoll=0;pthread_mutex_unlock(&AGMutex);}
- (void)close {
    pthread_mutex_lock(&AGMutex);AGState.visible=0;atomic_store(&AGInterested,AGState.waiting);pthread_mutex_unlock(&AGMutex);
    [self.amountField resignFirstResponder];[self.timer invalidate];self.timer=nil;AGWindow.hidden=YES;AGWindow.rootViewController=nil;[AGPreviousWindow makeKeyWindow];AGWindow=nil;AGController=nil;
}
@end

__attribute__((visibility("default"))) void AGWheelOpen(void *env, int variant) {
    if(variant<0||variant>=6)return;if(env){AGViewportCapture(variant);AGInventoryTick(variant);}
    pthread_mutex_lock(&AGMutex);
    if(AGState.variant!=variant){uint64_t generation=AGState.generation+1;memset(&AGState,0,sizeof AGState);AGState.generation=generation;AGState.variant=variant;}
    AGState.visible=1;AGState.loaded=0;AGState.openedAt=AGNow();AGState.lastPoll=0;atomic_store(&AGInterested,1);
    pthread_mutex_unlock(&AGMutex);
    dispatch_async(dispatch_get_main_queue(),^{
        static dispatch_once_t once;
        dispatch_once(&once,^{
            [NSNotificationCenter.defaultCenter addObserverForName:UIApplicationDidEnterBackgroundNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *n){atomic_store(&AGForeground,0);}];
            [NSNotificationCenter.defaultCenter addObserverForName:UIApplicationDidBecomeActiveNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *n){atomic_store(&AGForeground,1);}];
        });
        atomic_store(&AGForeground,UIApplication.sharedApplication.applicationState==UIApplicationStateActive);
        if(AGWindow){[AGWindow makeKeyAndVisible];return;}
        UIWindow *previous=UIApplication.sharedApplication.keyWindow;
        if(!previous){for(UIWindow *w in UIApplication.sharedApplication.windows)if(!w.hidden){previous=w;break;}}
        AGPreviousWindow=previous;
        if(@available(iOS 13.0,*)){if(previous.windowScene)AGWindow=[[AGGameWindow alloc]initWithWindowScene:previous.windowScene];}
        if(!AGWindow)AGWindow=[[AGGameWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];
        AGWindow.opaque=NO;AGWindow.backgroundColor=UIColor.clearColor;
        AGWindow.frame=previous?previous.frame:UIScreen.mainScreen.bounds;AGWindow.windowLevel=UIWindowLevelAlert+2;
        AGController=[AGWheelController new];AGWindow.rootViewController=AGController;[AGWindow makeKeyAndVisible];
    });
}

#ifdef AG_WHEEL_PREVIEW
// Simulator-only fixture; excluded from the device dylib.
int AGWheelGuard(void *env,int (*fn)(void *,void *),void *ctx,void *entry){return 0;}
__attribute__((visibility("default"))) void AGWheelPreview(void) {
    AGWheelOpen(NULL,0);
    pthread_mutex_lock(&AGMutex);
    AGState.loaded=1;AGState.receivedAt=AGNow();AGState.snapshot=(AGSnapshot){.version=2,.serverTime=1800000000000LL,.round=52,.ends=1800000090000LL,.total=25000000,.own=5000000,.balance=88000000,.count=4,.tax=5,.rows=4,.hasResult=1,.resultRound=51,.resultPool=30000000,.resultPrize=28500000,.resultStake=5000000,.resultTax=5};
    const char *names[]={"Kiên","Hoàng Gia","Minh Anh","Ngọc"};int64_t stakes[]={5000000,10000000,3000000,7000000};
    for(int i=0;i<4;i++){snprintf(AGState.snapshot.entries[i].name,AG_NAME,"%s",names[i]);AGState.snapshot.entries[i].amount=stakes[i];AGState.snapshot.entries[i].own=i==0;}
    snprintf(AGState.snapshot.winner,AG_NAME,"Hoàng Gia");
    if([NSProcessInfo.processInfo.arguments containsObject:@"--waiting"]){
        AGState.snapshot.ends=0;AGState.snapshot.count=0;AGState.snapshot.rows=0;
        AGState.snapshot.total=0;AGState.snapshot.own=0;AGState.snapshot.tax=0;
        AGState.snapshot.balance=49853387624LL;
        AGState.snapshot.resultPrize=50490000;AGState.snapshot.resultStake=50000000;
        snprintf(AGState.snapshot.winner,AG_NAME,"hoanganhpn");
    }
    if([NSProcessInfo.processInfo.arguments containsObject:@"--single"]){
        AGState.snapshot.ends=0;AGState.snapshot.count=1;AGState.snapshot.rows=1;
        AGState.snapshot.total=1000000;AGState.snapshot.own=1000000;AGState.snapshot.tax=0;
        AGState.snapshot.balance=8332878439LL;
        AGState.snapshot.entries[0].amount=1000000;AGState.snapshot.entries[0].own=1;
        AGState.snapshot.resultPrize=99000000;AGState.snapshot.resultStake=50000000;
        snprintf(AGState.snapshot.winner,AG_NAME,"triheoi111");
    }
    pthread_mutex_unlock(&AGMutex);
    [NSTimer scheduledTimerWithTimeInterval:2 repeats:YES block:^(NSTimer *timer){
        pthread_mutex_lock(&AGMutex);AGState.snapshot.serverTime+=2000;AGState.receivedAt=AGNow();pthread_mutex_unlock(&AGMutex);
    }];
}
__attribute__((visibility("default"))) void AGWheelPreviewShowInput(void) { [AGController bet]; }
__attribute__((visibility("default"))) void AGWheelPreviewCheckInterface(void){
    UIView *view=AGController.view;CGRect original=view.frame;
    NSArray<NSValue *> *sizes=@[[NSValue valueWithCGSize:CGSizeMake(320,480)],[NSValue valueWithCGSize:CGSizeMake(375,667)],[NSValue valueWithCGSize:CGSizeMake(390,844)],[NSValue valueWithCGSize:CGSizeMake(430,932)],[NSValue valueWithCGSize:CGSizeMake(768,1024)],[NSValue valueWithCGSize:CGSizeMake(844,390)]];
    NSMutableArray *checked=[NSMutableArray new];
    NSString *directory=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    for(NSValue *value in sizes){
        CGSize size=value.CGSizeValue;view.frame=CGRectMake(0,0,size.width,size.height);[view setNeedsLayout];[view layoutIfNeeded];
        CGFloat width=size.width-view.safeAreaInsets.left-view.safeAreaInsets.right;
        NSCAssert(fabs(CGRectGetMaxY(AGController.controls.frame)-CGRectGetMaxY(AGGameRect(view)))<.01,@"Footer above native keypad");
        NSCAssert([AGWindow hitTest:CGPointMake(size.width/2,AGWindow.gameBottom+10) withEvent:nil]==nil,@"Keypad receives touches");
        CGFloat s=AGPanelScale(AGController.panel.bounds.size.width,AGController.panel.bounds.size.height);
        NSCAssert(fabs(AGController.panelScroll.bounds.size.width-(width-8))<.01,@"Full width panel");
        NSCAssert(AGController.panel.bounds.size.height>=450*s-.01,@"Large text must scroll, never clip");
        NSCAssert(AGController.controls.bounds.size.height>=44,@"Readable controls");
        NSCAssert(CGRectGetMaxY(AGController.controls.frame)<=view.bounds.size.height+.01,@"Controls fit visible screen");
        // Simulate the original keypad's combined matrix after initial layout.
        // The whole footer and its touch boundary must move on the next render.
        uint8_t keys[48]={0},batch[144]={0},matrix[32]={0},values[84]={0};
        *(int *)(keys+0x28)=294;batch[0x85]=1;
        *(void **)(batch+0x20)=matrix;*(void **)(matrix+0x10)=values;*(int *)(values+0x10)=16;
        float *projection=(float *)(values+0x14);projection[5]=.002f;projection[13]=-1;projection[15]=1;
        AGViewportKeypad(NULL,keys,batch);[view setNeedsLayout];[view layoutIfNeeded];
        NSCAssert(fabs(CGRectGetMaxY(AGController.controls.frame)-size.height*.7055)<.001,@"Footer reaches projected keypad boundary");
        NSCAssert(fabs(AGWindow.gameBottom-CGRectGetMaxY(AGController.controls.frame))<.001,@"Touch boundary follows relocated controls");
        UIGraphicsBeginImageContextWithOptions(view.bounds.size,YES,2);
        [view.layer renderInContext:UIGraphicsGetCurrentContext()];
        UIImage *layout=UIGraphicsGetImageFromCurrentImageContext();UIGraphicsEndImageContext();
        NSString *name=[NSString stringWithFormat:@"wheel-layout-%.0fx%.0f.png",size.width,size.height];
        NSCAssert([UIImagePNGRepresentation(layout)writeToFile:[directory stringByAppendingPathComponent:name] atomically:YES],@"Write UIKit layout preview");
        AGController.keyboardInset=MIN(216,size.height*.5);[view setNeedsLayout];[view layoutIfNeeded];
        NSCAssert(CGRectGetMaxY(AGController.amountPanel.frame)<=CGRectGetMinY(AGController.controls.frame)+.01,@"Input does not overlap controls");
        NSCAssert(CGRectGetMinY(AGController.amountPanel.frame)>=view.safeAreaInsets.top-.01,@"Input stays below safe top");
        NSCAssert(CGRectGetMaxY(AGController.amountField.frame)<=AGController.amountPanel.bounds.size.height+.01,@"Input field remains visible with keyboard");
        AGController.keyboardInset=0;[view setNeedsLayout];[view layoutIfNeeded];
        [checked addObject:@{@"width":@(size.width),@"height":@(size.height),@"panel_width":@(AGController.panel.bounds.size.width),@"content_height":@(AGController.panel.bounds.size.height),@"scrolls":@(AGController.panel.bounds.size.height>AGController.panelScroll.bounds.size.height+.01),@"projected_footer":@YES}];
        AGViewportPreview(.30);
    }
    view.frame=original;[view setNeedsLayout];[view layoutIfNeeded];
    [AGController bet];NSCAssert(AGController.editingAmount&&!AGController.amountPanel.hidden,@"Amount panel opens");
    NSCAssert(AGController.amountField.text.length==0,@"New entry must be empty");
    NSCAssert([AGController.middleButton.accessibilityLabel isEqualToString:@"OK"],@"Amount confirm control");
    NSCAssert(CGRectGetMaxY(AGController.amountField.frame)<=AGController.amountPanel.bounds.size.height,@"Amount text fits");
    [AGController primary];NSCAssert(!AGController.editingAmount&&AGController.amountPanel.hidden,@"Cancel restores wheel");
    NSCAssert([AGController.betButton.accessibilityLabel isEqualToString:@"Tham gia"],@"Wheel controls restored");
    NSDictionary *report=@{@"passed":@YES,@"runtime":@"Apple iOS Simulator UIKit",@"sizes":checked,@"amount_open_cancel":@YES,@"keyboard_geometry":@YES,@"server_requests":@0};
    NSData *json=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];
    [json writeToFile:[directory stringByAppendingPathComponent:@"ui-check.json"] atomically:YES];
}
#endif



