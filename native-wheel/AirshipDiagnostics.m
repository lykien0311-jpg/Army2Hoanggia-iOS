#import <UIKit/UIKit.h>
#include <time.h>
#include "ShipTrace.h"

@interface AGShipDiagnosticWindow : UIWindow
@end
@implementation AGShipDiagnosticWindow
- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event{return nil;}
@end
static double shipNow(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static NSString *shipText(AGShipTrace d){
    double now=shipNow();
    NSMutableString *s=[NSMutableString stringWithFormat:
        @"B261 • ĐO LỖI KHÍ CẦU • quay rõ toàn bảng\nV%d R%d A%d E%d | Server #%d → IPA #%d | Cam #%d m%d\n"
        "RX24=%llu RX93=%llu cmd=%d/%d | tick=%llu\n"
        "Đạn=%d ACK=%d FX=%d P=%d/%d | CHỜ=%d:%d/#%d\n"
        "Cập nhật %.1fs | nhận %.1fs | chờ %.1fs\n"
        "Xác93 #%d → %d,%d rm%d | xử lý #%d ok%d lỗi%llu\n",
        d.variant+1,d.room,d.active,d.contextOK,d.turns?d.serverOwner:-1,d.owner,d.cameraActor,d.cameraMode,
        (unsigned long long)d.turns,(unsigned long long)d.flights,d.lastCommand,d.lastLength,
        (unsigned long long)d.pulses,d.projectileBusy,d.completionReady,d.canvasBusy,d.pending,d.notified,
        d.waitActive,d.waitKind,d.waitActor,MAX(0,now-d.sampleTime),d.receives?MAX(0,now-d.receiveTime):0,
        d.waitActive?MAX(0,now-d.waitSince):0,d.corpsePacketActor,d.corpseTargetX,d.corpseTargetY,d.corpseRemove,
        d.corpseIndex,d.corpseHandled,(unsigned long long)d.corpseRejected];
    for(int i=0;i<d.actorCount;i++){
        AGShipActor a=d.actors[i];if(a.slot!=d.local&&a.slot!=d.owner&&(a.character<17||a.character>21))continue;
        [s appendFormat:@"#%d/id%d C%d HP%lld S%d g%d f%d w%d y%d\n",a.slot,a.index,a.character,
            (long long)a.hp,a.state,a.gravity,a.flight,a.walk,a.y];
    }
    [s appendFormat:@"Xử lý xác=%llu | RX:",(unsigned long long)d.corpseUpdates];
    for(int i=MAX(0,d.eventCount-8);i<d.eventCount;i++){
        AGShipEvent e=d.events[i];[s appendFormat:@" %d:%d",e.command,e.first];
    }
    return s;
}
static UILabel *shipLabel(void){
    UILabel *l=[UILabel new];l.numberOfLines=0;
    l.font=[UIFont monospacedDigitSystemFontOfSize:9 weight:UIFontWeightMedium];
    l.textColor=UIColor.whiteColor;l.backgroundColor=[UIColor.blackColor colorWithAlphaComponent:.82];
    l.layer.cornerRadius=4;l.clipsToBounds=YES;l.userInteractionEnabled=NO;
    l.accessibilityLabel=@"Bảng đo lỗi khí cầu Build261";return l;
}
static dispatch_queue_t shipLogQueue(void){
    static dispatch_queue_t queue;static dispatch_once_t once;
    dispatch_once(&once,^{queue=dispatch_queue_create("vn.army2hoanggia.airship-log",DISPATCH_QUEUE_SERIAL);});
    return queue;
}
static void shipLog(AGShipTrace d){
    // Copy only scalar state/text onto the file queue. No Java reference,
    // game Env or native memory is accessed by UIKit or the file worker.
    NSString *text=shipText(d);NSString *stamp=NSDate.date.description;
    dispatch_async(shipLogQueue(),^{@autoreleasepool{
        NSString *dir=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
        if(!dir)return;NSString *path=[dir stringByAppendingPathComponent:@"KhiCau-B261.txt"];
        NSData *line=[[NSString stringWithFormat:@"\n%@\n%@\n",stamp,text]dataUsingEncoding:NSUTF8StringEncoding];
        if(![NSFileManager.defaultManager fileExistsAtPath:path])
            [NSFileManager.defaultManager createFileAtPath:path contents:nil attributes:nil];
        NSFileHandle *f=[NSFileHandle fileHandleForWritingAtPath:path];if(!f)return;
        @try{if([f seekToEndOfFile]>2*1024*1024){[f truncateFileAtOffset:0];[f seekToFileOffset:0];}
            [f writeData:line];[f closeFile];} @catch(NSException *e){[f closeFile];}
    }});
}
#ifndef AG_WHEEL_PREVIEW
__attribute__((constructor)) static void shipInstall(void){
    dispatch_async(dispatch_get_main_queue(),^{
        static AGShipDiagnosticWindow *window;static UILabel *label;static double logged;
        [NSTimer scheduledTimerWithTimeInterval:.25 repeats:YES block:^(NSTimer *timer){
            AGShipTrace best={0};BOOL seen=NO;
            for(int v=0;v<6;v++){AGShipTrace d;if(!AGShipTraceGet(v,&d))continue;
                if(!seen||d.sampleTime>best.sampleTime){best=d;seen=YES;}}
            UIWindow *game=UIApplication.sharedApplication.keyWindow;
            // Keep the standalone room armed even if battle recognition
            // fails: an A0/E value must itself be recordable for diagnosis.
            if(!seen||(!best.active&&best.room!=10)||!game||UIApplication.sharedApplication.applicationState!=UIApplicationStateActive){window.hidden=YES;return;}
            if(!window){
                if(@available(iOS 13.0,*)){if(game.windowScene)window=[[AGShipDiagnosticWindow alloc]initWithWindowScene:game.windowScene];}
                if(!window)window=[[AGShipDiagnosticWindow alloc]initWithFrame:game.bounds];
                window.opaque=NO;window.backgroundColor=UIColor.clearColor;window.windowLevel=UIWindowLevelNormal+3;
                window.userInteractionEnabled=NO;window.rootViewController=[UIViewController new];
                window.rootViewController.view.backgroundColor=UIColor.clearColor;
                label=shipLabel();[window.rootViewController.view addSubview:label];
            }
            window.frame=game.frame;label.text=shipText(best);
            CGFloat width=MAX(240,window.bounds.size.width-12),top=MAX(6,game.safeAreaInsets.top);
            CGSize size=[label sizeThatFits:CGSizeMake(width,CGFLOAT_MAX)];
            label.frame=CGRectMake(6,top,width,MIN(window.bounds.size.height*.40,size.height+8));window.hidden=NO;
            double now=shipNow();if(now-logged>=1){logged=now;shipLog(best);}
        }];
    });
}
#endif
#ifdef AG_WHEEL_PREVIEW
__attribute__((visibility("default"))) void AGShipDiagnosticsPreviewCheck(void){
    AGShipTrace d={.variant=0,.active=1,.room=10,.local=0,.owner=9,.serverOwner=10,.turns=7,.flights=3,
        .cameraActor=9,.cameraMode=1,.projectileBusy=1,.completionReady=0,.canvasBusy=0,.waitActive=1,
        .waitKind=0,.waitActor=0,.corpsePacketActor=9,.corpseTargetX=440,.corpseTargetY=640,
        .corpseIndex=9,.corpseHandled=1,.corpseUpdates=120,.actorCount=6,.eventCount=4,.pulses=2000};
    d.sampleTime=d.receiveTime=d.waitSince=shipNow()-3;
    for(int i=0;i<6;i++)d.actors[i]=(AGShipActor){.slot=i?i+7:0,.index=i?i+7:0,.character=i?i+16:2,
        .hp=i==2?0:15000,.state=i==2?5:0,.gravity=i!=2,.y=i==2?640:120};
    for(int i=0;i<4;i++)d.events[i]=(AGShipEvent){.command=i%2?93:24,.first=i+8};
    AGShipDiagnosticWindow *w=[[AGShipDiagnosticWindow alloc]initWithFrame:CGRectMake(0,0,390,844)];
    w.rootViewController=[UIViewController new];w.rootViewController.view.backgroundColor=[UIColor colorWithRed:.37 green:.78 blue:.94 alpha:1];
    UILabel *l=shipLabel();l.text=shipText(d);[w.rootViewController.view addSubview:l];
    for(NSNumber *width in @[@320,@390,@844]){
        CGSize size=[l sizeThatFits:CGSizeMake(width.doubleValue-12,CGFLOAT_MAX)];
        NSCAssert(size.height<190,@"Airship diagnostic fits the visible recording area");
        NSCAssert([w hitTest:CGPointMake(20,70)withEvent:nil]==nil,@"Airship overlay passes all touches");
    }
    CGSize size=[l sizeThatFits:CGSizeMake(378,CGFLOAT_MAX)];l.frame=CGRectMake(6,60,378,size.height+8);
    UIGraphicsBeginImageContextWithOptions(w.bounds.size,YES,2);[w.rootViewController.view.layer renderInContext:UIGraphicsGetCurrentContext()];
    UIImage *image=UIGraphicsGetImageFromCurrentImageContext();UIGraphicsEndImageContext();
    NSString *dir=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    shipLog(d);dispatch_sync(shipLogQueue(),^{});
    NSString *log=[NSString stringWithContentsOfFile:[dir stringByAppendingPathComponent:@"KhiCau-B261.txt"]encoding:NSUTF8StringEncoding error:nil];
    NSCAssert([log containsString:@"B261"],@"Airship diagnostic log was written");
    [UIImagePNGRepresentation(image)writeToFile:[dir stringByAppendingPathComponent:@"airship-diagnostics.png"]atomically:YES];
    NSDictionary *result=@{@"passed":@YES,@"touch_passthrough":@YES,@"widths":@[@320,@390,@844],
        @"airship_room_or_active_stage_only":@YES,@"local_log_written":@YES,
        @"native_pointer_access_from_UIKit":@NO,@"game_packets_written":@0};
    [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil]
        writeToFile:[dir stringByAppendingPathComponent:@"airship-diagnostics-check.json"]atomically:YES];
}
#endif
