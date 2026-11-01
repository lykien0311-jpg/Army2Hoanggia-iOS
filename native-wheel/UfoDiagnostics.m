#import <UIKit/UIKit.h>
#include "UfoDiagnostics.h"

/* Diagnostic build only: UIKit consumes copied scalars, never Java objects.
 * This window does not become key and passes every touch to the game. */
@interface AGUfoDiagnosticWindow : UIWindow
@end
@implementation AGUfoDiagnosticWindow
- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event {return nil;}
@end
static NSString *reason(AGUfoDiagnostic d){
    if(d.contextOK<=0)return @"Chưa đọc được trạng thái trận";
    if(!d.active)return @"Chờ màn hình trận đấu";
    if(!d.enabled)return @"Chưa nhận lệnh bật auto";
    if(!d.valid)return @"Chưa nhận lượt bắn hợp lệ";
    if(d.nativePending||d.nativeApplying||d.sequence!=d.applied)return @"Chờ bàn giao lượt";
    if(d.serverOwner!=d.local||d.owner!=d.local)return @"Đang ở lượt UFO";
    if(d.sent)return @"Đã gửi bắn; chờ server";
    if(!d.hasPlan)return @"Chưa nhận góc bắn đúng lượt";
    if(d.blocked&1)return @"Chờ đạn kết thúc";
    if(d.blocked&2)return @"Chờ hiệu ứng kết thúc";
    if(d.blocked&4)return @"Chờ di chuyển kết thúc";
    if(d.blocked&8)return @"Chờ bay kết thúc";
    if(d.blocked&16)return @"Chờ nhân vật chạm đất";
    if(d.blocked&(32|64|128))return @"Đang bị hộp thoại chặn";
    if(!d.alive||d.state)return @"Nhân vật chưa sẵn sàng";
    if(d.x!=d.planX||d.y!=d.planY)return @"Tọa độ khác dữ liệu server";
    return @"Đang chuẩn bị bắn";
}
static NSString *statusText(AGUfoDiagnostic d){
    return [NSString stringWithFormat:@"B252 • %@ • %@\nV%d T%d/%d L%d #%d • rx %llu/%llu/%llu • bắn %llu\nfx=%x w=%d/%d S%d p%d e%d m%llu • (%d,%d)/(%d,%d) • n%d/%d",
        d.enabled?@"AUTO BẬT":@"AUTO TẮT",reason(d),d.variant+1,d.serverOwner,d.owner,d.local,d.turn,
        (unsigned long long)d.modes,(unsigned long long)d.turns,(unsigned long long)d.aims,
        (unsigned long long)d.shots,d.blocked,d.waitActive,d.waitKind,d.state,d.hasPlan,d.early,
        (unsigned long long)d.manuals,d.x,d.y,d.planX,d.planY,d.last24Length,d.last115Length];
}
static UILabel *makeLabel(void){
    UILabel *l=[UILabel new];l.numberOfLines=0;l.font=[UIFont monospacedDigitSystemFontOfSize:10 weight:UIFontWeightMedium];
    l.textColor=UIColor.whiteColor;l.backgroundColor=[UIColor.blackColor colorWithAlphaComponent:.80];
    l.layer.cornerRadius=5;l.clipsToBounds=YES;l.userInteractionEnabled=NO;
    l.accessibilityLabel=@"Trạng thái chẩn đoán Auto UFO Build252";return l;
}
static void logState(AGUfoDiagnostic d){
    static NSString *path;
#define DF(k) @#k:@(d.k)
    NSDictionary *record=@{DF(ticks),DF(receives),DF(starts),DF(turns),DF(aims),DF(modes),DF(accepted),DF(shots),DF(failures),DF(manuals),DF(waits),DF(tickTime),DF(receiveTime),DF(waitSince),DF(variant),DF(contextOK),DF(active),DF(ufo),DF(local),DF(owner),DF(count),DF(alive),DF(state),DF(x),DF(y),DF(effects),DF(blocked),DF(lastCommand),DF(lastLength),DF(last115Length),DF(last24Length),DF(lastAimOwner),DF(lastAimTurn),DF(lastMagic),DF(enabled),DF(valid),DF(hasPlan),DF(early),DF(sent),DF(claimed),DF(stable),DF(turn),DF(serverOwner),DF(planX),DF(planY),DF(angle),DF(nativePending),DF(nativeApplying),DF(nativeOwner),DF(waitActive),DF(waitKind),DF(waitActor),DF(ticket),DF(sequence),DF(applied)};
#undef DF
    NSMutableData *line=[[NSJSONSerialization dataWithJSONObject:record options:0 error:nil]mutableCopy];if(!line)return;
    [line appendData:[@"\n" dataUsingEncoding:NSUTF8StringEncoding]];
    if(!path)path=[NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject stringByAppendingPathComponent:@"AutoUFO-Build252.txt"];
    if(!path)return;
    if(![NSFileManager.defaultManager fileExistsAtPath:path])[NSFileManager.defaultManager createFileAtPath:path contents:nil attributes:nil];
    NSFileHandle *file=[NSFileHandle fileHandleForWritingAtPath:path];if(!file)return;
    @try{if([file seekToEndOfFile]>1024*1024){[file truncateFileAtOffset:0];[file seekToFileOffset:0];}
        [file writeData:line];[file closeFile];} @catch(NSException *e){[file closeFile];}
}
#if 0 /* Production overlay removed; no file-writing timer either. */
__attribute__((constructor)) static void installMonitor(void){
    dispatch_async(dispatch_get_main_queue(),^{
        static AGUfoDiagnosticWindow *window;static UILabel *status;
        [NSTimer scheduledTimerWithTimeInterval:.5 repeats:YES block:^(NSTimer *timer){
            AGUfoDiagnostic best={0};BOOL seen=NO;
            for(int v=0;v<6;v++){AGUfoDiagnostic d;if(!AGUfoDiagnosticsGet(v,&d)||!d.receives)continue;
                if(!seen||d.receiveTime>best.receiveTime){best=d;seen=YES;}}
            if(!seen){
                for(int v=0;v<6;v++){AGUfoDiagnostic d;if(AGUfoDiagnosticsGet(v,&d)&&(!seen||d.tickTime>best.tickTime)){best=d;seen=YES;}}
            }
            UIWindow *game=UIApplication.sharedApplication.keyWindow;
            if(!game||UIApplication.sharedApplication.applicationState!=UIApplicationStateActive){window.hidden=YES;return;}
            if(!window){
                if(@available(iOS 13.0,*)){if(game.windowScene)window=[[AGUfoDiagnosticWindow alloc]initWithWindowScene:game.windowScene];}
                if(!window)window=[[AGUfoDiagnosticWindow alloc]initWithFrame:game.bounds];
                window.opaque=NO;window.backgroundColor=UIColor.clearColor;window.windowLevel=UIWindowLevelNormal+3;
                window.userInteractionEnabled=NO;window.rootViewController=[UIViewController new];
                window.rootViewController.view.backgroundColor=UIColor.clearColor;status=makeLabel();[window.rootViewController.view addSubview:status];
            }
            window.frame=game.frame;status.text=seen?statusText(best):@"B252 • Đang chờ game khởi động\nChưa thấy callback dữ liệu/trận";
            CGFloat width=MAX(240,window.bounds.size.width-12),top=MAX(8,game.safeAreaInsets.top);
            CGSize size=[status sizeThatFits:CGSizeMake(width,140)];status.frame=CGRectMake(6,top,width,MIN(140,size.height+8));
            window.hidden=NO;if(seen)logState(best);
        }];
    });
}
#endif
#ifdef AG_WHEEL_PREVIEW
__attribute__((visibility("default"))) void AGUfoDiagnosticsPreviewCheck(void){
    AGUfoDiagnosticWindow *w=[[AGUfoDiagnosticWindow alloc]initWithFrame:CGRectMake(0,0,390,844)];
    w.rootViewController=[UIViewController new];w.rootViewController.view.backgroundColor=[UIColor colorWithRed:.03 green:.07 blue:.07 alpha:1];
    UILabel *l=makeLabel();AGUfoDiagnostic d={.contextOK=1,.active=1,.enabled=1,.valid=1,.nativePending=1,.serverOwner=0,.owner=8,.local=0,.turn=3,.modes=1,.turns=5,.aims=12,.blocked=8,.waitActive=1,.waitKind=3,.last24Length=17,.last115Length=21};
    l.text=statusText(d);[w.rootViewController.view addSubview:l];
    for(NSNumber *width in @[@320,@390,@844]){
        l.frame=CGRectMake(6,60,width.doubleValue-12,100);CGSize s=[l sizeThatFits:l.bounds.size];
        NSCAssert(s.height<100,@"Diagnostic label fits portrait and landscape widths");
        NSCAssert([w hitTest:CGPointMake(20,70) withEvent:nil]==nil,@"Diagnostic window passes all touches");
    }
    l.frame=CGRectMake(6,60,378,64);
    UIGraphicsBeginImageContextWithOptions(w.bounds.size,YES,2);[w.rootViewController.view.layer renderInContext:UIGraphicsGetCurrentContext()];
    UIImage *im=UIGraphicsGetImageFromCurrentImageContext();UIGraphicsEndImageContext();
    NSString *dir=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    [UIImagePNGRepresentation(im)writeToFile:[dir stringByAppendingPathComponent:@"ufo-diagnostics.png"] atomically:YES];
    NSDictionary *result=@{@"passed":@YES,@"touch_passthrough":@YES,@"widths":@[@320,@390,@844],@"game_packets_written":@0};
    [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil]writeToFile:[dir stringByAppendingPathComponent:@"ufo-diagnostics-check.json"] atomically:YES];
}
#endif
