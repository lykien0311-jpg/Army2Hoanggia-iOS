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
static double AGNow(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9; }
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
@property(nonatomic,strong) AGPixelButton *betButton;
@property(nonatomic,strong) UIStackView *controls;
@property(nonatomic,strong) NSTimer *timer;
@end
static UIWindow *AGWindow;
static __weak UIWindow *AGPreviousWindow;
static AGWheelController *AGController;
@implementation AGWheelController
- (UIInterfaceOrientationMask)supportedInterfaceOrientations{return UIInterfaceOrientationMaskAllButUpsideDown;}
- (BOOL)prefersStatusBarHidden{return YES;}
- (AGPixelButton *)button:(NSString *)text action:(SEL)action{
    AGPixelButton *b=[AGPixelButton buttonWithType:UIButtonTypeCustom];b.accessibilityLabel=text;
    [b addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];return b;
}
- (void)viewDidLoad{
    [super viewDidLoad];self.view.backgroundColor=[UIColor colorWithRed:87/255.0 green:201/255.0 blue:239/255.0 alpha:1];
    self.panel=[AGClassicPanel new];self.panel.opaque=NO;self.panel.isAccessibilityElement=YES;
    self.betButton=[self button:@"Tham gia" action:@selector(bet)];
    self.controls=[[UIStackView alloc]initWithArrangedSubviews:@[self.betButton,[self button:@"Cập nhật" action:@selector(refresh)],[self button:@"Trở ra" action:@selector(close)]]];
    self.controls.axis=UILayoutConstraintAxisHorizontal;self.controls.distribution=UIStackViewDistributionFillEqually;self.controls.spacing=1;
    self.controls.backgroundColor=AGInk();[self.view addSubview:self.panel];[self.view addSubview:self.controls];
    __weak AGWheelController *weakSelf=self;
    self.timer=[NSTimer scheduledTimerWithTimeInterval:.2 repeats:YES block:^(NSTimer *t){[weakSelf render];}];[self render];
}
- (void)viewDidLayoutSubviews{
    [super viewDidLayoutSubviews];UIEdgeInsets safe=self.view.safeAreaInsets;
    CGFloat width=self.view.bounds.size.width-safe.left-safe.right,height=self.view.bounds.size.height-safe.top-safe.bottom;
    CGFloat bar=MAX(44,MIN(64,width/6)),panelHeight=height-bar-12;
    // Keep the complete panel visible in either orientation without clipping.
    CGFloat panelWidth=MIN(width-12,panelHeight*240/280);
    self.panel.frame=CGRectMake(safe.left+(width-panelWidth)/2,safe.top+6,panelWidth,panelHeight);
    self.controls.frame=CGRectMake(safe.left,safe.top+height-bar,width,bar);
    [self.panel setNeedsDisplay];
}
- (void)render{
    AGModel m=AGCopy();AGSnapshot s=m.snapshot;BOOL fresh=m.loaded&&AGNow()-m.receivedAt<6;
    int64_t now=AGServerNow(m),remain=s.ends>now?(s.ends-now+999)/1000:0;
    BOOL locked=s.ends>0&&now>=s.ends-10000;
    self.panel.snapshot=s;self.panel.loaded=m.loaded;self.panel.locked=locked;
    self.panel.remaining=m.loaded&&s.count<2?120:remain;
    self.betButton.enabled=fresh&&!m.waiting&&!locked&&s.balance>=AG_MIN_STAKE&&s.own<=AG_MAX_STAKE-AG_MIN_STAKE;
    NSString *notice=@"";
    if(m.waiting)notice=@"Đang xác nhận lượt tham gia";
    else if(!fresh)notice=m.loaded?@"Đang cập nhật kết nối":@"Đang tải dữ liệu";
    else if(m.notice[0]&&AGNow()<m.noticeUntil)notice=AGString(m.notice);
    self.panel.notice=notice;
    self.panel.accessibilityLabel=[NSString stringWithFormat:@"Vòng xoay may mắn. Quỹ %@ xu. %d người. Bạn đã tham gia %@ xu. Số dư %@ xu. %@",AGMoney(s.total),s.count,AGMoney(s.own),AGMoney(s.balance),notice];
    [self.panel setNeedsDisplay];[self.betButton setNeedsDisplay];
}
- (void)alert:(NSString *)text {
    UIAlertController *a=[UIAlertController alertControllerWithTitle:@"Vòng xoay may mắn" message:text preferredStyle:UIAlertControllerStyleAlert];[a addAction:[UIAlertAction actionWithTitle:@"Đã hiểu" style:UIAlertActionStyleDefault handler:nil]];[self presentViewController:a animated:YES completion:nil];
}
- (void)bet {
    AGModel m=AGCopy();if(!m.loaded||m.waiting||AGNow()-m.receivedAt>=6)return;
    UIAlertController *a=[UIAlertController alertControllerWithTitle:@"Tham gia vòng xoay" message:[NSString stringWithFormat:@"Số dư: %@ xu\nNhập số xu bạn muốn tham gia.",AGMoney(m.snapshot.balance)]preferredStyle:UIAlertControllerStyleAlert];
    [a addTextFieldWithConfigurationHandler:^(UITextField *t){t.keyboardType=UIKeyboardTypeNumberPad;t.placeholder=@"Tối thiểu 1.000.000 xu";t.text=@"1000000";}];
    [a addAction:[UIAlertAction actionWithTitle:@"Hủy" style:UIAlertActionStyleCancel handler:nil]];
    __weak AGWheelController *weakSelf=self;
    [a addAction:[UIAlertAction actionWithTitle:@"Tiếp tục" style:UIAlertActionStyleDefault handler:^(UIAlertAction *action){
        NSString *input=[a.textFields.firstObject.text stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
        if(!input.length||input.length>8||[input rangeOfCharacterFromSet:NSCharacterSet.decimalDigitCharacterSet.invertedSet].location!=NSNotFound){[weakSelf alert:@"Nhập số xu bằng chữ số, không dùng dấu chấm hoặc dấu phẩy."];return;}
        int64_t amount=input.longLongValue;AGModel current=AGCopy();const char *error=AGValidateBet(&current.snapshot,AGServerNow(current),amount);
        if(!current.loaded||current.waiting||AGNow()-current.receivedAt>=6){[weakSelf alert:@"Dữ liệu đang cập nhật. Vui lòng thử lại."];return;}
        if(error){[weakSelf alert:AGString(error)];return;}
        int64_t round=current.snapshot.round;uint64_t generation=current.generation;
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
    }]];
    [self presentViewController:a animated:YES completion:nil];
}
- (void)refresh {pthread_mutex_lock(&AGMutex);AGState.lastPoll=0;pthread_mutex_unlock(&AGMutex);}
- (void)previous {pthread_mutex_lock(&AGMutex);if(AGState.page>0)AGState.page--;AGState.lastPoll=0;pthread_mutex_unlock(&AGMutex);}
- (void)next {pthread_mutex_lock(&AGMutex);if(((int64_t)AGState.page+1)*20<AGState.snapshot.count)AGState.page++;AGState.lastPoll=0;pthread_mutex_unlock(&AGMutex);}
- (void)close {
    pthread_mutex_lock(&AGMutex);AGState.visible=0;atomic_store(&AGInterested,AGState.waiting);pthread_mutex_unlock(&AGMutex);
    [self.timer invalidate];self.timer=nil;AGWindow.hidden=YES;AGWindow.rootViewController=nil;[AGPreviousWindow makeKeyWindow];AGWindow=nil;AGController=nil;
}
@end

__attribute__((visibility("default"))) void AGWheelOpen(void *env, int variant) {
    (void)env;if(variant<0||variant>=6)return;
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
        if(@available(iOS 13.0,*)){if(previous.windowScene)AGWindow=[[UIWindow alloc]initWithWindowScene:previous.windowScene];}
        if(!AGWindow)AGWindow=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];
        AGWindow.frame=previous?previous.frame:UIScreen.mainScreen.bounds;AGWindow.windowLevel=UIWindowLevelAlert+2;
        AGController=[AGWheelController new];AGWindow.rootViewController=AGController;[AGWindow makeKeyAndVisible];
    });
}

#ifdef AG_WHEEL_PREVIEW
// Simulator-only fixture; excluded from the device dylib.
int AGWheelGuard(void *env,int (*fn)(void *,void *),void *ctx,void *entry){return 0;}
void AGWheelPreview(void) {
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
    pthread_mutex_unlock(&AGMutex);
    [NSTimer scheduledTimerWithTimeInterval:2 repeats:YES block:^(NSTimer *timer){
        pthread_mutex_lock(&AGMutex);AGState.snapshot.serverTime+=2000;AGState.receivedAt=AGNow();pthread_mutex_unlock(&AGMutex);
    }];
}
void AGWheelPreviewShowInput(void) { [AGController bet]; }
#endif
