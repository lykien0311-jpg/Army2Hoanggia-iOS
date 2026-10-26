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

static UIColor *AGGold(void){return [UIColor colorWithRed:1 green:.79 blue:.29 alpha:1];}
static UIColor *AGBlue(void){return [UIColor colorWithRed:.035 green:.095 blue:.18 alpha:1];}
static UIColor *AGColour(int i){return [UIColor colorWithHue:fmod(.53+i*.137,1) saturation:.63 brightness:.85 alpha:1];}

@interface AGWheelCanvas : UIView {
    AGSnapshot _current,_shown;
    CADisplayLink *_display;
    double _rotation,_from,_to,_animationStart,_lastFrame;
    int64_t _seenResult;
    BOOL _initialized,_settling,_locked;
}
- (void)update:(AGSnapshot)s locked:(BOOL)locked;
@end
@implementation AGWheelCanvas
- (instancetype)initWithFrame:(CGRect)frame {
    if((self=[super initWithFrame:frame])){self.opaque=NO;self.accessibilityLabel=@"Vòng xoay theo tỷ lệ xu tham gia";self.isAccessibilityElement=YES;}
    return self;
}
- (void)didMoveToWindow {
    [super didMoveToWindow];[_display invalidate];_display=nil;
    if(self.window){_display=[CADisplayLink displayLinkWithTarget:self selector:@selector(frame:)];_display.preferredFramesPerSecond=30;[_display addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];}
}
- (void)frame:(CADisplayLink *)link {
    double now=AGNow(),dt=_lastFrame?fmin(.1,now-_lastFrame):0;_lastFrame=now;
    if(_settling){double t=fmin(1,(now-_animationStart)/3.2);_rotation=_from+(_to-_from)*(1-pow(1-t,3));if(t>=1){_settling=NO;_shown=_current;_rotation=0;}}
    else if(_locked)_rotation=fmod(_rotation+dt*3,M_PI*2);
    [self setNeedsDisplay];
}
- (void)update:(AGSnapshot)s locked:(BOOL)locked {
    _locked=locked;
    if(!_initialized){_seenResult=s.resultRound;_initialized=YES;}
    if(s.hasResult && s.resultRound>_seenResult && _current.round==s.resultRound && _current.total>0) {
        _shown=_current;double start=0,mid=-1;
        for(int i=0;i<_shown.rows;i++){double share=(double)_shown.entries[i].amount/_shown.total;if(strcmp(_shown.entries[i].name,s.winner)==0)mid=start+share/2;start+=share;}
        if(mid<0 && start<1)mid=start+(1-start)/2;
        if(mid>=0){_from=_rotation;double target=fmod(-mid*M_PI*2+M_PI*4,M_PI*2);_to=_from+M_PI*8+fmod(target-fmod(_from,M_PI*2)+M_PI*2,M_PI*2);_animationStart=AGNow();_settling=YES;}
    }
    if(s.hasResult)_seenResult=s.resultRound;
    _current=s;if(!_settling)_shown=s;[self setNeedsDisplay];
}
- (void)drawRect:(CGRect)rect {
    CGContextRef c=UIGraphicsGetCurrentContext();CGFloat radius=fmin(self.bounds.size.width,self.bounds.size.height)/2-15;
    CGPoint center=CGPointMake(CGRectGetMidX(self.bounds),CGRectGetMidY(self.bounds)+4);
    double a=-M_PI_2+_rotation,used=0;
    int sectors=_shown.total>0?_shown.rows:8;
    for(int i=0;i<=sectors;i++) {
        double share;
        if(_shown.total<=0){if(i==sectors)break;share=1.0/sectors;}
        else {share=i<sectors?(double)_shown.entries[i].amount/_shown.total:fmax(0,1-used);if(share<=0)continue;}
        double b=a+share*M_PI*2;
        UIColor *colour=(i==sectors)?[UIColor colorWithWhite:.33 alpha:1]:AGColour(i);
        CGContextSetFillColorWithColor(c,colour.CGColor);CGContextMoveToPoint(c,center.x,center.y);CGContextAddArc(c,center.x,center.y,radius,a,b,0);CGContextClosePath(c);CGContextFillPath(c);
        CGContextSetStrokeColorWithColor(c,[UIColor colorWithWhite:1 alpha:.3].CGColor);CGContextSetLineWidth(c,1);CGContextMoveToPoint(c,center.x,center.y);CGContextAddLineToPoint(c,center.x+cos(a)*radius,center.y+sin(a)*radius);CGContextStrokePath(c);
        if(share>.035 && _shown.total>0){NSString *label=i<sectors?[NSString stringWithFormat:@"%d",i+1]:@"+";NSDictionary *attrs=@{NSFontAttributeName:[UIFont boldSystemFontOfSize:13],NSForegroundColorAttributeName:UIColor.whiteColor};CGSize sz=[label sizeWithAttributes:attrs];double mid=(a+b)/2;[label drawAtPoint:CGPointMake(center.x+cos(mid)*radius*.73-sz.width/2,center.y+sin(mid)*radius*.73-sz.height/2) withAttributes:attrs];}
        used+=share;a=b;
    }
    CGContextSetStrokeColorWithColor(c,AGGold().CGColor);CGContextSetLineWidth(c,5);CGContextStrokeEllipseInRect(c,CGRectMake(center.x-radius,center.y-radius,radius*2,radius*2));
    [AGBlue()setFill];UIBezierPath *hub=[UIBezierPath bezierPathWithOvalInRect:CGRectMake(center.x-39,center.y-39,78,78)];[hub fill];
    NSString *title=_settling?@"KẾT QUẢ":(_locked?@"ĐANG QUAY":@"MAY MẮN");NSDictionary *at=@{NSFontAttributeName:[UIFont boldSystemFontOfSize:10],NSForegroundColorAttributeName:AGGold()};CGSize z=[title sizeWithAttributes:at];[title drawAtPoint:CGPointMake(center.x-z.width/2,center.y-z.height/2) withAttributes:at];
    [AGGold()setFill];UIBezierPath *pointer=[UIBezierPath bezierPath];[pointer moveToPoint:CGPointMake(center.x-10,center.y-radius-10)];[pointer addLineToPoint:CGPointMake(center.x+10,center.y-radius-10)];[pointer addLineToPoint:CGPointMake(center.x,center.y-radius+12)];[pointer closePath];[pointer fill];
}
@end

@interface AGWheelController : UIViewController
@property(nonatomic,strong) UIScrollView *scroll;
@property(nonatomic,strong) UIStackView *stack,*body,*left,*right;
@property(nonatomic,strong) AGWheelCanvas *canvas;
@property(nonatomic,strong) UILabel *roundLabel,*poolLabel,*balanceLabel,*statusLabel,*playersLabel,*resultLabel,*pageLabel;
@property(nonatomic,strong) UIButton *betButton,*previousButton,*nextButton;
@property(nonatomic,strong) NSTimer *timer;
@end
static UIWindow *AGWindow;
static __weak UIWindow *AGPreviousWindow;
static AGWheelController *AGController;

static UILabel *AGLabel(CGFloat size, BOOL bold) {
    UILabel *l=[UILabel new];l.font=bold?[UIFont boldSystemFontOfSize:size]:[UIFont systemFontOfSize:size];l.textColor=UIColor.whiteColor;l.numberOfLines=0;return l;
}
static UIButton *AGButton(NSString *title,id target,SEL action,BOOL filled) {
    UIButton *b=[UIButton buttonWithType:UIButtonTypeSystem];[b setTitle:title forState:UIControlStateNormal];b.titleLabel.font=[UIFont boldSystemFontOfSize:15];b.layer.cornerRadius=10;b.contentEdgeInsets=UIEdgeInsetsMake(12,14,12,14);
    [b setTitleColor:filled?AGBlue():AGGold() forState:UIControlStateNormal];[b setTitleColor:[UIColor colorWithWhite:.5 alpha:1]forState:UIControlStateDisabled];b.backgroundColor=filled?AGGold():[UIColor colorWithWhite:1 alpha:.08];[b addTarget:target action:action forControlEvents:UIControlEventTouchUpInside];return b;
}
@implementation AGWheelController
- (UIInterfaceOrientationMask)supportedInterfaceOrientations {return UIInterfaceOrientationMaskAllButUpsideDown;}
- (BOOL)prefersStatusBarHidden{return YES;}
- (void)viewDidLoad {
    [super viewDidLoad];self.view.backgroundColor=AGBlue();
    UILabel *title=AGLabel(18,YES);title.text=@"VÒNG XOAY MAY MẮN";title.textColor=AGGold();
    UIButton *close=AGButton(@"Đóng",self,@selector(close),NO);
    UIStackView *header=[[UIStackView alloc]initWithArrangedSubviews:@[title,close]];header.axis=UILayoutConstraintAxisHorizontal;header.spacing=12;header.alignment=UIStackViewAlignmentCenter;
    [title setContentHuggingPriority:UILayoutPriorityDefaultLow forAxis:UILayoutConstraintAxisHorizontal];[close setContentHuggingPriority:UILayoutPriorityRequired forAxis:UILayoutConstraintAxisHorizontal];
    self.scroll=[UIScrollView new];self.scroll.alwaysBounceVertical=YES;
    self.stack=[UIStackView new];self.stack.axis=UILayoutConstraintAxisVertical;self.stack.spacing=16;
    self.body=[UIStackView new];self.body.axis=UILayoutConstraintAxisVertical;self.body.spacing=20;
    self.left=[UIStackView new];self.left.axis=UILayoutConstraintAxisVertical;self.left.spacing=8;
    self.right=[UIStackView new];self.right.axis=UILayoutConstraintAxisVertical;self.right.spacing=12;
    self.canvas=[AGWheelCanvas new];[self.canvas.heightAnchor constraintEqualToConstant:238].active=YES;
    self.roundLabel=AGLabel(16,YES);self.roundLabel.textAlignment=NSTextAlignmentCenter;
    self.poolLabel=AGLabel(15,NO);self.poolLabel.textAlignment=NSTextAlignmentCenter;
    [self.left addArrangedSubview:self.canvas];[self.left addArrangedSubview:self.roundLabel];[self.left addArrangedSubview:self.poolLabel];
    self.balanceLabel=AGLabel(17,YES);self.statusLabel=AGLabel(13,NO);self.statusLabel.textColor=[UIColor colorWithWhite:.8 alpha:1];
    self.betButton=AGButton(@"THAM GIA BẰNG XU",self,@selector(bet),YES);
    UIButton *refresh=AGButton(@"Tải lại",self,@selector(refresh),NO);
    UILabel *rules=AGLabel(12,NO);rules.text=@"Từ 1.000.000 xu/lượt · Tối đa 50.000.000 xu/vòng. Khóa đặt xu trong 10 giây cuối. Kết quả và phần thưởng do máy chủ trả về.";rules.textColor=[UIColor colorWithWhite:.65 alpha:1];
    [self.right addArrangedSubview:self.balanceLabel];[self.right addArrangedSubview:self.betButton];[self.right addArrangedSubview:refresh];[self.right addArrangedSubview:self.statusLabel];[self.right addArrangedSubview:rules];
    [self.body addArrangedSubview:self.left];[self.body addArrangedSubview:self.right];[self.stack addArrangedSubview:self.body];
    self.resultLabel=AGLabel(14,YES);self.resultLabel.textColor=AGGold();[self.stack addArrangedSubview:self.resultLabel];
    UILabel *playersTitle=AGLabel(16,YES);playersTitle.text=@"NGƯỜI THAM GIA";[self.stack addArrangedSubview:playersTitle];
    self.playersLabel=AGLabel(14,NO);[self.stack addArrangedSubview:self.playersLabel];
    self.previousButton=AGButton(@"‹ Trước",self,@selector(previous),NO);self.nextButton=AGButton(@"Sau ›",self,@selector(next),NO);self.pageLabel=AGLabel(12,NO);self.pageLabel.textAlignment=NSTextAlignmentCenter;
    UIStackView *pages=[[UIStackView alloc]initWithArrangedSubviews:@[self.previousButton,self.pageLabel,self.nextButton]];pages.spacing=8;pages.distribution=UIStackViewDistributionFillEqually;[self.stack addArrangedSubview:pages];
    [self.view addSubview:header];[self.view addSubview:self.scroll];[self.scroll addSubview:self.stack];
    header.translatesAutoresizingMaskIntoConstraints=NO;self.scroll.translatesAutoresizingMaskIntoConstraints=NO;self.stack.translatesAutoresizingMaskIntoConstraints=NO;
    UILayoutGuide *safe=self.view.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
      [header.topAnchor constraintEqualToAnchor:safe.topAnchor constant:8],[header.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:14],[header.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-14],
      [self.scroll.topAnchor constraintEqualToAnchor:header.bottomAnchor constant:10],[self.scroll.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor],[self.scroll.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor],[self.scroll.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor],
      [self.stack.topAnchor constraintEqualToAnchor:self.scroll.contentLayoutGuide.topAnchor constant:8],[self.stack.leadingAnchor constraintEqualToAnchor:self.scroll.contentLayoutGuide.leadingAnchor constant:16],[self.stack.trailingAnchor constraintEqualToAnchor:self.scroll.contentLayoutGuide.trailingAnchor constant:-16],[self.stack.bottomAnchor constraintEqualToAnchor:self.scroll.contentLayoutGuide.bottomAnchor constant:-20],[self.stack.widthAnchor constraintEqualToAnchor:self.scroll.frameLayoutGuide.widthAnchor constant:-32]]];
    __weak AGWheelController *weakSelf=self;
    self.timer=[NSTimer scheduledTimerWithTimeInterval:.3 repeats:YES block:^(NSTimer *t){[weakSelf render];}];[self render];
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];BOOL wide=self.view.bounds.size.width>650;
    self.body.axis=wide?UILayoutConstraintAxisHorizontal:UILayoutConstraintAxisVertical;
    self.body.distribution=wide?UIStackViewDistributionFillEqually:UIStackViewDistributionFill;
    self.body.alignment=wide?UIStackViewAlignmentTop:UIStackViewAlignmentFill;
}
- (void)render {
    AGModel m=AGCopy();AGSnapshot s=m.snapshot;double age=AGNow()-m.receivedAt;BOOL fresh=m.loaded&&age<6;
    int64_t now=AGServerNow(m),remain=s.ends>now?(s.ends-now+999)/1000:0;BOOL locked=s.ends>0&&now>=s.ends-10000;
    if(m.loaded){
        self.roundLabel.text=[NSString stringWithFormat:@"Vòng #%lld · %@",(long long)s.round,remain?[NSString stringWithFormat:@"%lld:%02lld",(long long)(remain/60),(long long)(remain%60)]:@"Chờ vòng mới"];
        self.poolLabel.text=[NSString stringWithFormat:@"Tổng: %@ xu\n%d người · Phí %d%%",AGMoney(s.total),s.count,s.tax];
        self.balanceLabel.text=[NSString stringWithFormat:@"Số dư: %@ xu\nĐã tham gia: %@ xu%@",AGMoney(s.balance),AGMoney(s.own),s.pending?[NSString stringWithFormat:@"\nChờ nhận: %@ xu",AGMoney(s.pending)]:@""];
        [self.canvas update:s locked:locked&&fresh];
    }else {self.roundLabel.text=@"Đang tải vòng xoay…";self.poolLabel.text=@"Chờ dữ liệu từ máy chủ";self.balanceLabel.text=@"Số dư: —\nĐã tham gia: —";}
    self.betButton.enabled=fresh&&!m.waiting&&!locked&&s.balance>=AG_MIN_STAKE&&s.own<=AG_MAX_STAKE-AG_MIN_STAKE;
    if(m.waiting)self.statusLabel.text=@"Đang chờ máy chủ xác nhận lượt đặt. Bạn chưa thể đặt thêm lượt lúc này.";
    else if(m.notice[0]&&AGNow()<m.noticeUntil)self.statusLabel.text=AGString(m.notice);
    else if(!fresh)self.statusLabel.text=AGNow()-m.openedAt>10?@"Chưa nhận được dữ liệu. Máy chủ hiện tại có thể chưa hỗ trợ vòng xoay hoặc kết nối đang gián đoạn.":@"Đang kết nối với vòng xoay…";
    else self.statusLabel.text=locked?@"Đã khóa đặt xu. Đang chờ kết quả máy chủ.":@"Chọn Tham gia bằng xu để nhập số xu.";
    NSMutableAttributedString *rows=[NSMutableAttributedString new];
    if(m.loaded){for(int i=0;i<s.rows;i++){
        double pct=s.total>0?100.0*(double)s.entries[i].amount/s.total:0;
        NSString *line=[NSString stringWithFormat:@"%d. %@%@ — %@ xu (%.2f%%)\n",i+1,AGString(s.entries[i].name),s.entries[i].own?@" · Bạn":@"",AGMoney(s.entries[i].amount),pct];
        [rows appendAttributedString:[[NSAttributedString alloc]initWithString:line attributes:@{NSForegroundColorAttributeName:s.entries[i].own?AGGold():UIColor.whiteColor}]];
    }}
    if(!rows.length)[rows appendAttributedString:[[NSAttributedString alloc]initWithString:m.loaded?@"Chưa có người tham gia vòng này.":@"Đang tải danh sách…"]];
    self.playersLabel.attributedText=rows;
    self.resultLabel.hidden=!m.loaded||!s.hasResult;
    self.resultLabel.text=s.hasResult?[NSString stringWithFormat:@"Vòng #%lld: %@ thắng %@ xu\nTổng vòng: %@ xu · Phí %d%%",(long long)s.resultRound,AGString(s.winner),AGMoney(s.resultPrize),AGMoney(s.resultPool),s.resultTax]:@"";
    self.pageLabel.text=[NSString stringWithFormat:@"Trang %d / %d",s.page+1,MAX(1,(int)(((int64_t)s.count+19)/20))];
    self.previousButton.enabled=fresh&&s.page>0;self.nextButton.enabled=fresh&&((int64_t)s.page+1)*20<s.count;
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
    AGState.loaded=1;AGState.receivedAt=AGNow();AGState.snapshot=(AGSnapshot){.version=2,.serverTime=1800000000000LL,.round=52,.ends=1800000090000LL,.total=25000000,.own=5000000,.balance=88000000,.count=4,.tax=5,.rows=4,.hasResult=1,.resultRound=51,.resultPool=30000000,.resultPrize=28500000,.resultTax=5};
    const char *names[]={"Kiên","Hoàng Gia","Minh Anh","Ngọc"};int64_t stakes[]={5000000,10000000,3000000,7000000};
    for(int i=0;i<4;i++){snprintf(AGState.snapshot.entries[i].name,AG_NAME,"%s",names[i]);AGState.snapshot.entries[i].amount=stakes[i];AGState.snapshot.entries[i].own=i==0;}
    snprintf(AGState.snapshot.winner,AG_NAME,"Hoàng Gia");pthread_mutex_unlock(&AGMutex);
    [NSTimer scheduledTimerWithTimeInterval:2 repeats:YES block:^(NSTimer *timer){
        pthread_mutex_lock(&AGMutex);AGState.snapshot.serverTime+=2000;AGState.receivedAt=AGNow();pthread_mutex_unlock(&AGMutex);
    }];
}
void AGWheelPreviewShowInput(void) { [AGController bet]; }
#endif
