#import <UIKit/UIKit.h>
#include <mach-o/dyld.h>
#include <pthread.h>
#include <stdatomic.h>
#include <time.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "Notes77.h"
#include "Spectator.h"
#include "SpectatorWait.h"
#include "Lobby.h"
#include "NotesMap.h"
#include "NativeMap.h"
#include "Blind.h"
#include "Aura.h"
#include "Stats.h"
#include "NotesProtocol.h"
#import "GameViewport.h"
extern int AGWheelInput(int,int,int,int);
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static pthread_mutex_t NMutex=PTHREAD_MUTEX_INITIALIZER;
static atomic_int NInitialized=0,NCurrent=-1;
typedef struct {
    AGCaptchaState cap;
    uintptr_t connection,inboxDialog;
    int known,saved,draft,dirty,editing,pending,sendInvite,sendInviteValue,inboxVisible,inboxAction,heldCode,heldKey,heldPointer,deferred;
    double inviteSince;
    uint64_t generation,inboxSerial;
} NModel;
static NModel NModels[6];
static NSString *NInboxBodies[6];
static NSString *NAlert;
static void NUpdateUI(void);
static void NInboxKey(int code);
static uintptr_t NBase(void){return (uintptr_t)_dyld_get_image_header(0);}
static double NNow(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static NSString *NText(const char *s){return [NSString stringWithUTF8String:s]?:@"";}
static void NInit(void){
    if(atomic_load(&NInitialized))return;
    pthread_mutex_lock(&NMutex);if(!atomic_load(&NInitialized)){for(int i=0;i<6;i++){AGCaptchaInit(&NModels[i].cap);NModels[i].inboxAction=-1;}atomic_store(&NInitialized,1);}pthread_mutex_unlock(&NMutex);
    static dispatch_once_t once;dispatch_once(&once,^{dispatch_async(dispatch_get_main_queue(),^{
        [NSNotificationCenter.defaultCenter addObserverForName:UIApplicationDidBecomeActiveNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *notification){NUpdateUI();}];
    });});
}
static void *NCanvas(int variant){return *(void **)(NBase()+AGNotesMaps[variant].canvas);}
static int NRoom(int variant){
#ifdef AG_WHEEL_PREVIEW
    return 1;
#endif
    uint8_t *c=NCanvas(variant);if(!c)return 0;void *screen=*(void **)(c+0xb8);
    void *clazz=*(void **)(NBase()+AGNotesMaps[variant].room_class);return screen&&clazz&&*(void **)screen==clazz;
}
static void NClear(int variant){
#ifdef AG_WHEEL_PREVIEW
    return;
#endif
    uint8_t *c=NCanvas(variant);if(!c)return;
    for(int off=0xa0;off<=0xa8;off+=8){uint8_t *a=*(uint8_t **)(c+off);if(a){int n=*(int *)(a+0x10);if(n>=0&&n<=64)memset(a+0x14,0,n);}}
    c[0x140]=0;c[0x141]=0;
}
uintptr_t AGViewerWaitToken(int variant){return AGSpectatorWaitToken(NCanvas(variant));}
void AGViewerDismissWait(int variant,uintptr_t token){
    if(AGSpectatorClearWait(NCanvas(variant),token))NClear(variant);
}
static void NRefresh(void){dispatch_async(dispatch_get_main_queue(),^{NUpdateUI();});}
static void NNotice(const char *text){NAlert=NText(text);}
// All Java operations below run with the original Env on its game thread.
// The guard can longjmp: no ARC ownership or locks cross these callbacks.
typedef struct {uintptr_t connection,expected;int variant,command;size_t length;const uint8_t *payload;uint8_t bytes[AG_CAP_NONCE+16];} NJob;
__attribute__((noinline,optnone)) static int NNative(void *env,void *context){
    NJob *j=context;uintptr_t base=NBase();const AGNativeMap *m=&AGMaps[j->variant];
    void *(*get)(void *)=(void *)(base+m->service);void *volatile service=get(env);
    if(!service)return 0;void *volatile session=*(void **)((uint8_t *)service+0x10);j->connection=(uintptr_t)session;
    if(!session)return 0;if(j->expected&&j->expected!=j->connection)return -2;if(!j->length)return 1;
    void *(*allocate)(void *)=(void *)(base+m->alloc);void (*ctor)(void *,void *,int)=(void *)(base+m->ctor);
    void (*write)(void *,void *,int)=(void *)(base+0xa64a3c);void (*send)(void *,void *,void *)=(void *)(base+m->send);
    void *volatile message=allocate(env);if(!message)return 0;ctor(env,message,j->command);
    void *volatile writer=*(void **)((uint8_t *)message+0x18);if(!writer)return 0;
    const uint8_t *data=j->payload?j->payload:j->bytes;
    for(size_t i=0;i<j->length;i++)write(env,writer,data[i]);send(env,session,message);return 1;
}
static int NRun(void *env,int (*fn)(void *,void *),void *context){return AGWheelGuard(env,fn,context,(void *)(NBase()+0x1300d54));}
int AGLobbySend(void *env,int variant,uintptr_t connection,int command,const uint8_t *bytes,size_t length){
    if(!env||variant<0||variant>=6||!connection||!bytes||!length)return 0;
    if(command==-121){if(length>1024||bytes[0]>4)return 0;}
    else if(command==-120){if(length<9||length>18||memcmp(bytes,"CT46",4)||bytes[4]<1||bytes[4]>6)return 0;}
    else if(command==-14){if(length!=2||bytes[0]!=3||bytes[1]>9)return 0;}
    else return 0;
    NJob job={.variant=variant,.command=command,.expected=connection,.length=length,.payload=bytes};
    return NRun(env,NNative,&job)>0;
}
int AGAuraHello(void *env,int variant,uintptr_t connection){
    static const uint8_t hello[]={'C','T','4','6',11,0,0,0,1};
    NJob job={.variant=variant,.command=-120,.expected=connection,.length=sizeof hello,.payload=hello};
    return NRun(env,NNative,&job)>0;
}
uintptr_t AGViewerConnection(void *env,int variant){
    NJob probe={.variant=variant};
    return NRun(env,NNative,&probe)>0?probe.connection:0;
}

int AGNotesMapDenied(void *message,int variant){
    if(!NRoom(variant))return 0;
    uint8_t *room=*(uint8_t **)(NBase()+AGNotesMaps[variant].room_class);
    int id=room[0x130];
    if(id!=18&&id!=19)return 0;
    uintptr_t wait=AGViewerWaitToken(variant);
    if(!wait)return 0;
    uint8_t *in=*(uint8_t **)((uint8_t *)message+0x20);
    uint8_t *a=in?*(uint8_t **)(in+0x10):NULL;
    if(!a)return 0;
    int count=*(int *)(in+0x18),pos=*(int *)(in+0x20),capacity=*(int *)(a+0x10);
    if(pos<0||count<pos||count>capacity||count-pos<3||count-pos>512)return 0;
    const uint8_t *p=a+0x14+pos;
    size_t size=(p[0]<<8)|p[1];
    if(size!=(size_t)(count-pos-2))return 0;
    NSString *text=[[NSString alloc] initWithBytes:p+2 length:size encoding:NSUTF8StringEncoding];
    NSString *map=id==18?@"Thung Lũng Rồng":@"Kẻ Mạo Danh";
    BOOL version=[text hasPrefix:@"Phiên bản này chưa hỗ trợ phòng"]&&[text containsString:map];
    BOOL closed=[text isEqualToString:id==18?@"Phòng Rồng đang tạm đóng trong quản trị.":@"Phòng Kẻ Mạo Danh đang tạm đóng trong quản trị."];
    if(!version&&!closed)return 0;
    if(!AGSpectatorClearWait(NCanvas(variant),wait))return 0;
    NClear(variant);
    NInit();
    pthread_mutex_lock(&NMutex);
    NAlert=version?[NSString stringWithFormat:@"%@ chưa hỗ trợ iOS trên server hiện tại.",map]:text;
    atomic_store(&NCurrent,variant);
    pthread_mutex_unlock(&NMutex);
    NRefresh();
    return 1;
}
int AGViewerSend(void *env,int variant,uintptr_t connection,int command,const uint8_t *bytes,size_t length){
    if(!connection || !bytes || !((command==7 && length==1) || (command==-102 && (length==12 || length==14))))return 0;
    NJob job={.variant=variant,.command=command,.expected=connection,.length=length};
    memcpy(job.bytes,bytes,length);
    return NRun(env,NNative,&job)>0;
}
typedef struct {int variant,which;uintptr_t dialog;} NCallbackJob;
static int NCallback(void *env,void *context){
    NCallbackJob *j=context;uint8_t *c=NCanvas(j->variant);if(!c||*(uintptr_t *)(c+0x108)!=j->dialog)return 0;
    uint8_t *volatile dialog=(void *)j->dialog;
    void *volatile command=*(void **)(dialog+(j->which==0?0x10:0x20));if(!command)return 0;
    void *volatile callback=*(void **)((uint8_t *)command+0x18);if(!callback)return 0;
    void (*invoke)(void *,void *)=(void *)(NBase()+AGNotesMaps[j->variant].callback);invoke(env,callback);return 1;
}
void AGNotesTick(void *env,int variant){
    if(env&&variant>=0&&variant<6)AGViewerTick(env,variant);
    if(!env||variant<0||variant>=6)return;
    if(!atomic_load(&NInitialized)&&!AGLobbyOpened(variant)&&!AGAuraKnown(variant))return;
    if(!atomic_load(&NInitialized))NInit();
    double now=NNow();int changed=0;NJob probe={.variant=variant};int connected=NRun(env,NNative,&probe);
    uint8_t *canvas=NCanvas(variant);int room=NRoom(variant);NCallbackJob cb={.variant=variant,.which=-1};NJob job={.variant=variant};uint64_t generation;
    AGLobbyTick(env,variant,connected>0?probe.connection:0);
    AGAuraTick(env,variant,connected>0?probe.connection:0);
    pthread_mutex_lock(&NMutex);NModel *m=&NModels[variant];
    if(connected<=0||m->connection!=probe.connection){
        if(m->connection||m->known||m->cap.active||m->cap.boss||m->inboxVisible){AGCaptchaClose(&m->cap);m->cap.boss=0;m->deferred=0;m->known=0;m->pending=0;m->sendInvite=0;m->dirty=0;m->editing=0;m->inboxVisible=0;m->inboxDialog=0;m->inboxAction=-1;NInboxBodies[variant]=nil;m->generation++;changed=1;}
        m->connection=connected>0?probe.connection:0;
    }
    int was=m->cap.active;AGCaptchaContext(&m->cap,m->cap.boss,room);if(was!=m->cap.active){NClear(variant);changed=1;}
    if(m->deferred&&room&&m->cap.boss){m->deferred=0;AGCaptchaReceive(&m->cap,&m->cap.packet,now);NClear(variant);changed=1;}
    if(m->cap.waiting&&now-m->cap.waitSince>10){m->cap.waiting=0;snprintf(m->cap.notice,sizeof m->cap.notice,"Chưa có phản hồi. Bấm Đổi hình.");}
    if(m->inboxDialog){int visible=canvas&&*(uintptr_t *)(canvas+0x108)==m->inboxDialog;
        if(visible&&!m->inboxVisible){m->inboxVisible=1;NClear(variant);changed=1;}
        else if(!visible&&m->inboxVisible){m->inboxDialog=0;m->inboxVisible=0;NInboxBodies[variant]=nil;m->inboxAction=-1;changed=1;}}
    if(m->inboxVisible&&m->inboxAction>=0){cb.which=m->inboxAction;cb.dialog=m->inboxDialog;m->inboxAction=-1;m->inboxVisible=0;changed=1;}
    if(m->cap.active||m->inboxVisible)NClear(variant);
    if(m->sendInvite&&m->connection){job.command=-122;job.bytes[0]=1;job.bytes[1]=m->sendInviteValue;job.length=2;m->sendInvite=0;}
    else if(m->cap.op>=0&&m->connection&&(m->cap.op!=0||room||!m->cap.boss)){int op=m->cap.op;m->cap.op=-1;
        if(m->cap.boss&&room){
            int w=canvas?*(int *)(canvas+0x130):320,h=canvas?*(int *)(canvas+0x128):480;
            w=w<160?160:w>480?480:w;h=h<200?200:h>640?640:h;
            job.command=-123;job.length=AGCaptchaSend(&m->cap,op,w,h,job.bytes);
        }}
    generation=m->generation;job.expected=m->connection;
    pthread_mutex_unlock(&NMutex);
    if(cb.which>=0){NClear(variant);NRun(env,NCallback,&cb);pthread_mutex_lock(&NMutex);NModel *q=&NModels[variant];if(q->inboxDialog==cb.dialog){q->inboxDialog=0;NInboxBodies[variant]=nil;}pthread_mutex_unlock(&NMutex);}
    if(job.length){int result=NRun(env,NNative,&job);if(result<=0){pthread_mutex_lock(&NMutex);m=&NModels[variant];if(generation==m->generation){
        if(job.command==-122){m->pending=0;NNotice("Chưa lưu được chặn lời mời. Mở cấu hình và thử lại.");}
        else {m->cap.waiting=0;snprintf(m->cap.notice,sizeof m->cap.notice,"Chưa gửi được. Thử lại nhé.");}changed=1;}pthread_mutex_unlock(&NMutex);}}
    if(changed)NRefresh();
}
__attribute__((visibility("default"))) int AGNotesReceive(void *env,void *message,int variant){
    if(!env||!message||variant<0||variant>=6)return 0;int command=*(int8_t *)((uint8_t *)message+0x30);
    if(command==-110||command==-124)return AGStatsReceive(env,message,variant);
    if(command==106||command==20){AGBlindReceive(env,message,variant);return 0;}
    if(command!=-122&&command!=-123)return 0;NInit();
    uint8_t *in=*(uint8_t **)((uint8_t *)message+0x20);if(!in)return 1;uint8_t *a=*(uint8_t **)(in+0x10);if(!a)return 1;
    int length=*(int32_t *)(a+0x10),count=*(int32_t *)(in+0x18),pos=*(int32_t *)(in+0x20);
    if(length<0||count<0||count>length||pos<0||pos>count||count-pos>65535)return 1;
    AGCaptchaPacket *p=malloc(sizeof *p);if(!p)return 1;
    if(!AGNotesParse(a+0x14+pos,count-pos,command,p)){free(p);return 1;}
    NJob probe={.variant=variant};int connected=NRun(env,NNative,&probe);int room=NRoom(variant);
    pthread_mutex_lock(&NMutex);NModel *m=&NModels[variant];
    if(m->connection&&m->connection!=probe.connection){AGCaptchaClose(&m->cap);m->cap.boss=0;m->deferred=0;m->known=0;m->pending=0;m->dirty=0;m->editing=0;m->sendInvite=0;m->generation++;}
    m->connection=connected>0?probe.connection:0;AGCaptchaContext(&m->cap,m->cap.boss,room);
    if(command==-122){m->known=1;m->saved=p->status;m->pending=0;if(!m->editing||!m->dirty||p->text[0]){m->draft=m->saved;m->dirty=0;}if(p->text[0]){NNotice(p->text);atomic_store(&NCurrent,variant);}}
    else {
        if(p->kind==1&&m->cap.boss&&!room){m->cap.packet=*p;m->deferred=1;}
        else AGCaptchaReceive(&m->cap,p,NNow());
        if((p->kind==3&&!p->boss)||(p->kind==2&&p->status<=2))m->deferred=0;
        if(p->kind==3&&p->boss)atomic_store(&NCurrent,variant);if(p->kind==1&&m->cap.active){atomic_store(&NCurrent,variant);NClear(variant);}if(p->kind==2&&p->status==2&&p->text[0]){NNotice(p->text);atomic_store(&NCurrent,variant);}}
    pthread_mutex_unlock(&NMutex);free(p);NRefresh();return 1;
}
// Native input guards close the short interval before UIKit presents its modal.
__attribute__((visibility("default"))) int AGNotesInput(int variant,int kind,int a,int b){
    if(variant<0||variant>=6)return 0;
    if(AGLobbyInput(variant,kind,a,b)){NClear(variant);return 1;}
    if(!atomic_load(&NInitialized)){int wheel=AGWheelInput(variant,kind,a,b);if(wheel)NClear(variant);return wheel;}
    int room=NRoom(variant),consumed=0,inbox=0;pthread_mutex_lock(&NMutex);NModel *m=&NModels[variant];
    AGCaptchaContext(&m->cap,m->cap.boss,room);
    if(m->cap.active){consumed=1;if(kind<2)AGCaptchaKey(&m->cap,a,kind==1,NNow());}
    else if(m->inboxVisible){consumed=1;inbox=1;}
    if(kind==1&&m->heldKey&&m->heldCode==a){m->heldKey=0;consumed=1;}
    if(kind==4&&m->heldPointer){m->heldPointer=0;consumed=1;}
    if(consumed&&kind==0){m->heldCode=a;m->heldKey=1;}
    if(consumed&&kind==2)m->heldPointer=1;
    if(!consumed)consumed=AGWheelInput(variant,kind,a,b);
    if(consumed)NClear(variant);else atomic_store(&NCurrent,variant);
    pthread_mutex_unlock(&NMutex);if(inbox&&kind==0)dispatch_async(dispatch_get_main_queue(),^{NInboxKey(a);});return consumed;
}
typedef struct {int variant,x,y;void *graphics;char value[80];} NPaintJob;
static void NDraw(void *env,void *font,void *g,const char *text,int x,int y,int anchor,int variant){
    void **jni=*(void ***)env;void *(*make)(void *,const char *)=(void *)jni[167];void (*del)(void *,void *)=(void *)jni[23];
    void *volatile string=make(env,text);if(!string){((void (*)(void *))jni[17])(env);return;}
    void (*draw)(void *,void *,void *,void *,int,int,int)=(void *)(NBase()+AGNotesMaps[variant].font);draw(env,font,g,string,x,y,anchor);del(env,string);
}
__attribute__((noinline,optnone)) static int NPaint(void *env,void *context){
    NPaintJob *j=context;void *(*get)(void *)=(void *)(NBase()+AGNotesMaps[j->variant].font_get);void *volatile font=get(env);if(!font)return 0;
    NDraw(env,font,j->graphics,"Chặn lời mời:",j->x-50,j->y,0,j->variant);
    NDraw(env,font,j->graphics,j->value,j->x,j->y+14,2,j->variant);return 1;
}
__attribute__((visibility("default"))) int AGNotesSettings(void *env,void *screen,void *graphics,int variant,int action){
    if(!env||variant<0||variant>=6)return 1;NInit();uint8_t *c=NCanvas(variant);if(!c)return 1;int result=1;double now=NNow();
    NPaintJob paint={.variant=variant,.graphics=graphics,.x=*(int *)(c+0x130)/2,.y=*(int *)(c+0x120)-110+198};
    pthread_mutex_lock(&NMutex);NModel *m=&NModels[variant];
    if(action==0){m->draft=m->saved;m->dirty=0;m->editing=1;atomic_store(&NCurrent,variant);}
    else if(action==1&&screen){
        int *focus=(int *)((uint8_t *)screen+0x50);uint8_t *keys=*(uint8_t **)(c+0xa0);if(keys&&*(int *)(keys+0x10)>8){
            uint8_t *k=keys+0x14;
            if(k[8]){k[8]=0;*focus=(*focus+1)%7;}else if(k[2]){k[2]=0;*focus=(*focus+6)%7;}
            if(*focus==6&&(k[4]||k[6])){k[4]=k[6]=0;if(m->known){m->draft=!m->draft;m->dirty=m->draft!=m->saved;}else NNotice("Đăng nhập để đổi chặn lời mời.");}
        }
        if(c[0x140]){int x=*(int *)(c+0x110),y=*(int *)(c+0x138),origin=*(int *)(c+0x120)-110;
            int row=(y-origin)/33;if(y>=origin&&row==6&&y<origin+231){*focus=6;c[0x140]=0;
                int cx=*(int *)(c+0x130)/2;
                if(y>=origin+198+7&&y<origin+231&&((x>=cx-77&&x<=cx-45)||(x>=cx+43&&x<=cx+77))){if(m->known){m->draft=!m->draft;m->dirty=m->draft!=m->saved;}else NNotice("Đăng nhập để đổi chặn lời mời.");}
            }}
    }
    else if(action==2){snprintf(paint.value,sizeof paint.value,"%s",m->pending?"Đang lưu...":m->known?(m->draft?"Bật":"Tắt"):"Đăng nhập");}
    else if(action==3){
        // OK always follows the original native return action. Saving is queued
        // on the game thread and never holds this configuration screen open.
        if(m->dirty&&m->known&&(!m->pending||m->sendInviteValue!=m->draft||now-m->inviteSince>=10)){
            m->sendInviteValue=m->draft;m->sendInvite=1;m->pending=1;m->inviteSince=now;
        }
        m->editing=0;
    }
    pthread_mutex_unlock(&NMutex);if(action==2&&graphics)NRun(env,NPaint,&paint);if(action==1||action==3)NRefresh();return result;
}
typedef struct {void *body;uint16_t *chars;int length;} NStringJob;
__attribute__((noinline,optnone)) static int NCopyJava(void *env,void *context){
    NStringJob *j=context;if(!j->body)return 1;void **jni=*(void ***)env;
    int (*length)(void *,void *)=(void *)jni[164];const uint16_t *(*get)(void *,void *,void *)=(void *)jni[165];void (*release)(void *,void *,const uint16_t *)=(void *)jni[166];
    int n=length(env,j->body);if(n<0||n>1000000)return 0;j->length=n;
    j->chars=malloc((size_t)(n?n:1)*2);if(!j->chars)return 0;
    const uint16_t *chars=get(env,j->body,NULL);if(!chars)return 0;memcpy(j->chars,chars,(size_t)n*2);release(env,j->body,chars);return 1;
}
__attribute__((visibility("default"))) void AGNotesInbox(void *env,void *dialog,void *body,int variant){
    if(!env||!dialog||variant<0||variant>=6)return;NInit();NStringJob j={.body=body};int success=NRun(env,NCopyJava,&j);
    if(success<=0){free(j.chars);return;}NSString *text=[[NSString alloc]initWithCharacters:j.chars length:j.length];free(j.chars);
    pthread_mutex_lock(&NMutex);NModel *m=&NModels[variant];m->inboxDialog=(uintptr_t)dialog;m->inboxVisible=0;m->inboxSerial++;m->inboxAction=-1;NInboxBodies[variant]=text?:@"";atomic_store(&NCurrent,variant);pthread_mutex_unlock(&NMutex);
}

@interface AGCaptchaView : UIView
@property(nonatomic) int variant;
@property(nonatomic) CGRect imageRect;
@property(nonatomic) CGFloat imageScale;
@property(nonatomic,strong) UIImage *mainImage,*pieceImage;
@property(nonatomic) uint64_t imageSerial;
@property(nonatomic,strong) NSArray<UIButton *> *targets;
@end
@implementation AGCaptchaView
- (instancetype)initWithFrame:(CGRect)frame {
    if((self=[super initWithFrame:frame])){self.opaque=NO;self.backgroundColor=UIColor.clearColor;self.multipleTouchEnabled=NO;self.imageSerial=UINT64_MAX;
        NSMutableArray *buttons=[NSMutableArray new];for(int i=0;i<14;i++){UIButton *b=[UIButton buttonWithType:UIButtonTypeCustom];b.backgroundColor=UIColor.clearColor;b.tag=i;[b addTarget:self action:@selector(activate:) forControlEvents:UIControlEventTouchUpInside];[self addSubview:b];[buttons addObject:b];}self.targets=buttons;
    }return self;
}
- (void)activate:(UIButton *)button {
    pthread_mutex_lock(&NMutex);AGCaptchaState *s=&NModels[self.variant].cap;int tag=(int)button.tag;
    if(tag<9){const uint16_t *g=s->packet.g;int x=g[2]+(tag%3)*(g[4]+g[5])+g[4]/2,y=g[3]+(tag/3)*(g[4]+g[5])+g[4]/2;AGCaptchaTouch(s,0,x,y,NNow());AGCaptchaTouch(s,2,x,y,NNow());}
    else AGCaptchaAction(s,tag<12?tag-9:tag-8,NNow());pthread_mutex_unlock(&NMutex);[self setNeedsDisplay];
}
- (void)layoutSubviews{[super layoutSubviews];[self setNeedsDisplay];}
- (void)drawRect:(CGRect)rect {
    AGCaptchaState s;pthread_mutex_lock(&NMutex);s=NModels[self.variant].cap;pthread_mutex_unlock(&NMutex);if(!s.active)return;
    const uint16_t *a=s.packet.g,*d=s.packet.d;
    if(self.imageSerial!=s.serial){self.imageSerial=s.serial;self.mainImage=[UIImage imageWithData:[NSData dataWithBytes:s.packet.image length:s.packet.imageLength]];self.pieceImage=s.packet.pieceLength?[UIImage imageWithData:[NSData dataWithBytes:s.packet.piece length:s.packet.pieceLength]]:nil;}
    CGFloat scale=MIN((self.bounds.size.width-16)/a[0],(self.bounds.size.height-8)/a[1]);scale=MIN(2.6,MAX(.05,scale));
    CGRect frame=CGRectMake((self.bounds.size.width-a[0]*scale)/2,(self.bounds.size.height-a[1]*scale)/2,a[0]*scale,a[1]*scale);self.imageRect=frame;self.imageScale=scale;
    BOOL grid=s.packet.type==1||s.packet.type==2||s.packet.type==4;
    for(int i=0;i<14;i++){
        UIButton *button=self.targets[i];CGRect logical=CGRectZero;NSString *label=@"";
        if(i<9&&grid){logical=CGRectMake(a[2]+(i%3)*(a[4]+a[5]),a[3]+(i/3)*(a[4]+a[5]),a[4],a[4]);label=[NSString stringWithFormat:@"Ô %d%@",i+1,AGCaptchaSelected(&s,i)?@", đã chọn":@""];}
        else if(i>=9&&i<12){int k=9+(i-9)*4;logical=CGRectMake(a[k],a[k+1],a[k+2],a[k+3]);label=@[@"Đặt lại",@"Xác nhận",@"Đổi hình"][i-9];}
        else if(i>=12&&s.packet.type==6){int k=3+(i-12)*2;logical=CGRectMake(d[k],d[k+1],a[4],a[4]);label=i==12?@"Xoay trái":@"Xoay phải";}
        button.hidden=CGRectIsEmpty(logical);button.frame=CGRectMake(frame.origin.x+logical.origin.x*scale,frame.origin.y+logical.origin.y*scale,logical.size.width*scale,logical.size.height*scale);button.accessibilityLabel=label;button.enabled=!s.waiting;
    }
    CGContextRef c=UIGraphicsGetCurrentContext();CGContextSaveGState(c);CGContextTranslateCTM(c,frame.origin.x,frame.origin.y);CGContextScaleCTM(c,scale,scale);
    [self.mainImage drawInRect:CGRectMake(0,0,a[0],a[1])];
    if(!self.mainImage){[[UIColor colorWithRed:.08 green:.24 blue:.4 alpha:1]setFill];CGContextFillRect(c,CGRectMake(0,0,a[0],a[1]));}
    BOOL movable=s.packet.type==3||s.packet.type==5,blink=(((int)((NNow()-s.blinkSince)/.45))&1)==0;
    CGRect focus=CGRectZero;
    if(movable){[self.pieceImage drawInRect:CGRectMake(s.x,s.y,d[2],d[2])];focus=CGRectMake(s.x,s.y,d[2],d[2]);}
    else if(s.packet.type==6){focus=CGRectMake(d[0],d[1],d[2],d[2]);CGContextSaveGState(c);CGContextClipToRect(c,focus);[self.pieceImage drawInRect:CGRectMake(d[0],d[1]-s.rotation*d[2],d[2],d[2]*8)];CGContextRestoreGState(c);}
    else if(s.packet.type!=2||(!AGCaptchaSelected(&s,s.focus)&&blink))focus=CGRectMake(a[2]+s.focus%3*(a[4]+a[5]),a[3]+s.focus/3*(a[4]+a[5]),a[4],a[4]);
    if(!CGRectIsEmpty(focus)){[[UIColor colorWithRed:1 green:.12 blue:.12 alpha:1]setStroke];CGContextSetLineWidth(c,2);CGContextStrokeRect(c,CGRectInset(focus,-2,-2));}
    UIFont *font=[UIFont boldSystemFontOfSize:MAX(8,MIN(a[4]/2,a[21]+2))];
    for(int i=0;i<s.used;i++){int cell=s.selected[i];CGRect box=CGRectMake(a[2]+cell%3*(a[4]+a[5]),a[3]+cell/3*(a[4]+a[5]),a[4],a[4]);
        if(s.packet.type==2&&!blink){[[UIColor colorWithRed:.78 green:.85 blue:.94 alpha:1]setFill];CGContextFillRect(c,CGRectInset(box,2,2));}
        [[UIColor colorWithRed:.15 green:.9 blue:.49 alpha:1]setStroke];CGContextSetLineWidth(c,2);CGContextStrokeRect(c,CGRectInset(box,1,1));
        NSString *mark=s.packet.type==1?[NSString stringWithFormat:@"%d",i+1]:@"+";CGFloat side=font.pointSize+2;CGRect badge=CGRectMake(CGRectGetMaxX(box)-side,box.origin.y,side,side);[[UIColor colorWithRed:.07 green:.22 blue:.42 alpha:1]setFill];CGContextFillRect(c,badge);[mark drawAtPoint:CGPointMake(badge.origin.x+1,badge.origin.y) withAttributes:@{NSFontAttributeName:font,NSForegroundColorAttributeName:UIColor.whiteColor}];
    }
    NSString *count=s.packet.type==6?@"Trái / Phải để xoay":movable?(s.placed?@"Đã thả hình":@"Giữ và kéo hình"):[NSString stringWithFormat:@"Đã chọn: %d/%d",s.used,s.packet.required];
    if(s.waiting)count=@"Đang chờ...";
    UIFont *small=[UIFont systemFontOfSize:MAX(8,MIN(15,a[21])) weight:UIFontWeightSemibold];NSDictionary *attrs=@{NSFontAttributeName:small,NSForegroundColorAttributeName:[UIColor colorWithRed:.07 green:.22 blue:.42 alpha:1]};
    CGSize size=[count sizeWithAttributes:attrs];[count drawAtPoint:CGPointMake(a[6]-size.width/2,a[7]) withAttributes:attrs];
    CGContextRestoreGState(c);
}
- (void)touch:(NSSet<UITouch *> *)touches phase:(int)phase {
    UITouch *touch=touches.anyObject;if(!touch)return;CGPoint p=[touch locationInView:self];CGFloat scale=self.imageScale;if(scale<=0)return;
    int x=(int)floor((p.x-self.imageRect.origin.x)/scale),y=(int)floor((p.y-self.imageRect.origin.y)/scale);
    pthread_mutex_lock(&NMutex);AGCaptchaTouch(&NModels[self.variant].cap,phase,x,y,NNow());pthread_mutex_unlock(&NMutex);[self setNeedsDisplay];
}
- (void)touchesBegan:(NSSet<UITouch *> *)t withEvent:(UIEvent *)e{[self touch:t phase:0];}
- (void)touchesMoved:(NSSet<UITouch *> *)t withEvent:(UIEvent *)e{[self touch:t phase:1];}
- (void)touchesEnded:(NSSet<UITouch *> *)t withEvent:(UIEvent *)e{[self touch:t phase:2];}
- (void)touchesCancelled:(NSSet<UITouch *> *)t withEvent:(UIEvent *)e{[self touch:t phase:3];}
@end

@interface AGNotesController : UIViewController
@property(nonatomic) int variant,mode;
@property(nonatomic) uint64_t inboxSerial;
@property(nonatomic,strong) AGCaptchaView *captcha;
@property(nonatomic,strong) UILabel *status,*titleLabel;
@property(nonatomic,strong) UITextView *body;
@property(nonatomic,strong) UIButton *reply,*close;
@property(nonatomic,strong) NSTimer *timer;
- (void)render;
@end
static AGGameWindow *NWindow;
static __weak UIWindow *NPrevious;
static AGNotesController *NController;
static NSString *NActiveAlert,*NQueuedAlert;
@implementation AGNotesController
- (UIInterfaceOrientationMask)supportedInterfaceOrientations{return UIInterfaceOrientationMaskAllButUpsideDown;}
- (BOOL)prefersStatusBarHidden{return YES;}
- (BOOL)canBecomeFirstResponder{return YES;}
- (UIButton *)button:(NSString *)title action:(SEL)action {
    UIButton *b=[UIButton buttonWithType:UIButtonTypeSystem];[b setTitle:title forState:UIControlStateNormal];b.titleLabel.font=[UIFont boldSystemFontOfSize:18];[b setTitleColor:[UIColor colorWithRed:1 green:.84 blue:.32 alpha:1] forState:UIControlStateNormal];b.backgroundColor=[UIColor colorWithRed:.08 green:.23 blue:.4 alpha:1];b.layer.cornerRadius=6;[b addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];return b;
}
- (void)viewDidLoad {
    [super viewDidLoad];self.view.backgroundColor=UIColor.clearColor;self.captcha=[AGCaptchaView new];[self.view addSubview:self.captcha];
    self.status=[UILabel new];self.status.numberOfLines=2;self.status.textAlignment=NSTextAlignmentCenter;self.status.font=[UIFont systemFontOfSize:14 weight:UIFontWeightSemibold];self.status.textColor=UIColor.whiteColor;self.status.backgroundColor=[UIColor colorWithRed:.07 green:.2 blue:.34 alpha:.95];self.status.layer.cornerRadius=5;self.status.clipsToBounds=YES;[self.view addSubview:self.status];
    self.titleLabel=[UILabel new];self.titleLabel.text=@"TIN NHẮN";self.titleLabel.font=[UIFont boldSystemFontOfSize:23];self.titleLabel.textColor=[UIColor colorWithRed:1 green:.84 blue:.32 alpha:1];self.titleLabel.textAlignment=NSTextAlignmentCenter;[self.view addSubview:self.titleLabel];
    self.body=[UITextView new];self.body.editable=NO;self.body.selectable=YES;self.body.scrollEnabled=YES;self.body.alwaysBounceVertical=YES;self.body.textContainerInset=UIEdgeInsetsMake(16,14,16,14);self.body.backgroundColor=[UIColor colorWithRed:.78 green:.85 blue:.94 alpha:1];self.body.textColor=[UIColor colorWithRed:.07 green:.22 blue:.42 alpha:1];self.body.font=[UIFont systemFontOfSize:18];self.body.accessibilityLabel=@"Nội dung tin nhắn";[self.view addSubview:self.body];
    self.reply=[self button:@"Trả lời" action:@selector(replyMessage)];self.close=[self button:@"Đóng" action:@selector(closeModal)];[self.view addSubview:self.reply];[self.view addSubview:self.close];
    __weak AGNotesController *weakSelf=self;self.timer=[NSTimer scheduledTimerWithTimeInterval:.1 repeats:YES block:^(NSTimer *timer){if(weakSelf)NUpdateUI();}];
    [self becomeFirstResponder];
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];UIEdgeInsets s=self.view.safeAreaInsets;CGFloat w=self.view.bounds.size.width-s.left-s.right,h=self.view.bounds.size.height-s.top-s.bottom,x=s.left,y=s.top;
    self.captcha.frame=CGRectMake(x+4,y+4,w-8,MAX(30,h-108));self.status.frame=CGRectMake(x+8,y+h-100,w-16,44);self.close.frame=CGRectMake(x+w/2+4,y+h-50,w/2-12,44);self.reply.frame=CGRectMake(x+8,y+h-50,w/2-12,44);
    if(self.mode==1){CGRect game=AGGameRect(self.view);CGFloat bottom=CGRectGetMaxY(game);self.captcha.frame=CGRectMake(x+4,y+4,w-8,MAX(30,bottom-y-42));self.status.frame=CGRectMake(x+8,bottom-36,w-16,32);NWindow.gameBottom=bottom;}
    NWindow.passesGameKeys=self.mode==1;
    self.titleLabel.frame=CGRectMake(x+8,y+6,w-16,40);self.body.frame=CGRectMake(x+8,y+50,w-16,MAX(20,h-110));
}
- (void)render {
    if(self.variant<0||self.variant>=6)return;pthread_mutex_lock(&NMutex);NModel *m=&NModels[self.variant];int mode=m->cap.active?1:m->inboxVisible?2:0;uint64_t serial=m->inboxSerial;NSString *text=NInboxBodies[self.variant];NSString *notice=NText(m->cap.notice);uint64_t expires=m->cap.packet.expires;pthread_mutex_unlock(&NMutex);
    if(self.mode!=mode){self.mode=mode;[self.view setNeedsLayout];}
    self.view.backgroundColor=mode==2?[UIColor colorWithRed:.07 green:.22 blue:.39 alpha:1]:UIColor.clearColor;
    self.captcha.hidden=mode!=1;self.status.hidden=mode!=1;self.titleLabel.hidden=mode!=2;self.body.hidden=mode!=2;self.reply.hidden=mode!=2;self.close.hidden=mode!=2;
    if(mode==1){self.captcha.variant=self.variant;[self.captcha setNeedsDisplay];long long seconds=expires>(uint64_t)(NSDate.date.timeIntervalSince1970*1000)?(long long)((expires-(uint64_t)(NSDate.date.timeIntervalSince1970*1000)+999)/1000):0;self.status.text=[NSString stringWithFormat:@"%@ · %lld giây",notice,seconds];}
    else if(mode==2){if(self.inboxSerial!=serial){self.inboxSerial=serial;self.body.text=text?:@"";self.body.contentOffset=CGPointZero;}[self.close setTitle:@"Đóng" forState:UIControlStateNormal];}
    if(!mode&&!NActiveAlert)NUpdateUI();
}
- (void)replyMessage{pthread_mutex_lock(&NMutex);NModels[self.variant].inboxAction=0;pthread_mutex_unlock(&NMutex);self.reply.enabled=NO;self.close.enabled=NO;}
- (void)closeModal {
    pthread_mutex_lock(&NMutex);NModel *m=&NModels[self.variant];if(self.mode==1)AGCaptchaAction(&m->cap,3,NNow());else if(self.mode==2)m->inboxAction=1;pthread_mutex_unlock(&NMutex);NUpdateUI();
}
- (NSArray<UIKeyCommand *> *)keyCommands {
    NSMutableArray *a=[NSMutableArray new];for(NSString *key in @[UIKeyInputUpArrow,UIKeyInputDownArrow,UIKeyInputLeftArrow,UIKeyInputRightArrow,UIKeyInputEscape,@"\r",@"0",@"1",@"2",@"3",@"4",@"5",@"6",@"7",@"8",@"9",@"*",@"#"])[a addObject:[UIKeyCommand keyCommandWithInput:key modifierFlags:0 action:@selector(key:)]];return a;
}
- (void)key:(UIKeyCommand *)command {
    NSString *s=command.input;int code=[s isEqual:UIKeyInputUpArrow]?-1:[s isEqual:UIKeyInputDownArrow]?-2:[s isEqual:UIKeyInputLeftArrow]?-3:[s isEqual:UIKeyInputRightArrow]?-4:[s isEqual:UIKeyInputEscape]?27:(int)[s characterAtIndex:0];
    if(self.mode==1){pthread_mutex_lock(&NMutex);AGCaptchaKey(&NModels[self.variant].cap,code,0,NNow());AGCaptchaKey(&NModels[self.variant].cap,code,1,NNow());pthread_mutex_unlock(&NMutex);NUpdateUI();}else NInboxKey(code);
}
@end
static void NInboxKey(int code){
    if(!NController||NController.mode!=2)return;
    if(code==27||code==-7){[NController closeModal];return;}if(code==-6||code==10||code==13){[NController replyMessage];return;}
    CGFloat delta=code==-1||code==50?-34:code==-2||code==56?34:code==-3||code==52?-NController.body.bounds.size.height:code==-4||code==54?NController.body.bounds.size.height:0;
    CGFloat maximum=MAX(0,NController.body.contentSize.height-NController.body.bounds.size.height);CGPoint offset=NController.body.contentOffset;offset.y=MAX(0,MIN(maximum,offset.y+delta));[NController.body setContentOffset:offset animated:NO];
}
static void NUpdateUI(void){
    int variant=atomic_load(&NCurrent),mode=0;NSString *alert;
    pthread_mutex_lock(&NMutex);if(variant>=0&&variant<6){NModel *m=&NModels[variant];mode=m->cap.active?1:m->inboxVisible?2:0;}alert=NAlert;NAlert=nil;pthread_mutex_unlock(&NMutex);
    if(alert){if(NActiveAlert)NQueuedAlert=alert;else NActiveAlert=alert;}
    if(!mode&&!NActiveAlert){if(NWindow){[NController.timer invalidate];NController.timer=nil;NWindow.hidden=YES;NWindow.rootViewController=nil;NWindow=nil;NController=nil;UIWindow *previous=NPrevious;if(previous&&!previous.hidden)[previous makeKeyWindow];else for(UIWindow *w in UIApplication.sharedApplication.windows)if(!w.hidden){[w makeKeyWindow];break;}}return;}
    if(UIApplication.sharedApplication.applicationState!=UIApplicationStateActive)return;
    if(!NWindow){UIWindow *previous=UIApplication.sharedApplication.keyWindow;if(!previous)for(UIWindow *w in UIApplication.sharedApplication.windows)if(!w.hidden){previous=w;break;}NPrevious=previous;
        if([previous respondsToSelector:@selector(windowScene)]&&previous.windowScene)NWindow=[[AGGameWindow alloc]initWithWindowScene:previous.windowScene];if(!NWindow)NWindow=[[AGGameWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];NWindow.frame=previous?previous.frame:UIScreen.mainScreen.bounds;NWindow.windowLevel=UIWindowLevelAlert+4;NWindow.backgroundColor=UIColor.clearColor;NWindow.opaque=NO;NController=[AGNotesController new];NWindow.rootViewController=NController;[NWindow makeKeyAndVisible];}
    if(variant>=0&&variant<6){if(NController.variant!=variant){NController.variant=variant;NController.inboxSerial=UINT64_MAX;NController.captcha.imageSerial=UINT64_MAX;}NController.reply.enabled=YES;NController.close.enabled=YES;[NController render];[NController.view setNeedsLayout];}
    if(NActiveAlert&&!NController.presentedViewController){UIAlertController *a=[UIAlertController alertControllerWithTitle:@"Thông báo" message:NActiveAlert preferredStyle:UIAlertControllerStyleAlert];[a addAction:[UIAlertAction actionWithTitle:@"Đã hiểu" style:UIAlertActionStyleDefault handler:^(UIAlertAction *action){NActiveAlert=NQueuedAlert;NQueuedAlert=nil;dispatch_async(dispatch_get_main_queue(),^{NUpdateUI();});}]];[NController presentViewController:a animated:YES completion:nil];}
}

#ifdef AG_WHEEL_PREVIEW
__attribute__((visibility("default"))) void AGNotesPreviewCheck(void){
    NInit();NSData *data=[NSData dataWithContentsOfFile:[NSBundle.mainBundle pathForResource:@"captcha-preview-fixtures" ofType:@"json"]];
    NSDictionary *fixtures=[NSJSONSerialization JSONObjectWithData:data options:0 error:nil];NSCAssert(fixtures.count==6,@"Six server captcha fixtures");
    NSMutableArray *results=[NSMutableArray new];NSString *dir=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    for(NSString *name in fixtures){
        NSData *wire=[[NSData alloc]initWithBase64EncodedString:fixtures[name] options:0];AGCaptchaPacket packet;
        NSCAssert(AGNotesParse(wire.bytes,wire.length,-123,&packet),@"Server captcha packet parses");packet.expires=(uint64_t)(NSDate.date.timeIntervalSince1970*1000)+180000;
        pthread_mutex_lock(&NMutex);AGCaptchaInit(&NModels[0].cap);AGCaptchaContext(&NModels[0].cap,1,1);AGCaptchaReceive(&NModels[0].cap,&packet,NNow());atomic_store(&NCurrent,0);pthread_mutex_unlock(&NMutex);
        NUpdateUI();NController.captcha.imageSerial=UINT64_MAX;[NController.captcha setNeedsDisplay];[NController.view setNeedsLayout];[NController.view layoutIfNeeded];
        NSCAssert(NController.mode==1&&NController.close.hidden,@"No extra back/reset overlay");
        NSCAssert(CGRectGetMaxY(NController.status.frame)<=NWindow.gameBottom,@"Countdown above game keys");
        NSCAssert(CGRectGetMaxY(NController.captcha.frame)<NWindow.gameBottom,@"Captcha fits game region");
        NSCAssert([NWindow hitTest:CGPointMake(100,NWindow.gameBottom+10) withEvent:nil]==nil,@"Captcha passes keypad touches");
        NSCAssert(AGNotesInput(0,0,-4,0)&&AGNotesInput(0,1,-4,0),@"Existing native keypad drives captcha");
        UIGraphicsBeginImageContextWithOptions(NController.view.bounds.size,NO,2);[NController.view.layer renderInContext:UIGraphicsGetCurrentContext()];UIImage *image=UIGraphicsGetImageFromCurrentImageContext();UIGraphicsEndImageContext();
        [UIImagePNGRepresentation(image)writeToFile:[dir stringByAppendingPathComponent:[NSString stringWithFormat:@"captcha-%@.png",name]] atomically:YES];
        [results addObject:@{@"mode":name,@"passes_keys":@YES,@"extra_button_hidden":@YES}];
    }
    NSData *report=[NSJSONSerialization dataWithJSONObject:@{@"passed":@YES,@"modes":results,@"live_requests":@0} options:NSJSONWritingPrettyPrinted error:nil];
    [report writeToFile:[dir stringByAppendingPathComponent:@"captcha-ui-check.json"] atomically:YES];
    pthread_mutex_lock(&NMutex);AGCaptchaClose(&NModels[0].cap);pthread_mutex_unlock(&NMutex);NUpdateUI();
}
#endif


int AGNotesBlocksAuto(int v){if(v<0||v>=6)return 1;pthread_mutex_lock(&NMutex);int blocked=NModels[v].cap.active||NModels[v].inboxVisible;pthread_mutex_unlock(&NMutex);return blocked;}


