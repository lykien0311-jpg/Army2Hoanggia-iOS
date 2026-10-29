#include "NotesProtocol.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct { const uint8_t *p; size_t n; int ok; } Reader;
static uint64_t readN(Reader *r, unsigned n) {
    if (!r->ok || r->n<n) { r->ok=0; return 0; }
    uint64_t v=0; for(unsigned i=0;i<n;i++) v=(v<<8)|*r->p++;
    r->n-=n; return v;
}
static int unit(Reader *r) {
    unsigned a=(unsigned)readN(r,1), b, c;
    if (a && a<128) return a;
    if ((a&0xe0)==0xc0) {
        b=(unsigned)readN(r,1); if((b&0xc0)!=0x80) r->ok=0;
        unsigned v=((a&31)<<6)|(b&63);
        if(v<128 && v!=0) r->ok=0;
        return (int)v;
    }
    if ((a&0xf0)==0xe0) {
        b=(unsigned)readN(r,1); c=(unsigned)readN(r,1);
        if((b&0xc0)!=0x80 || (c&0xc0)!=0x80) r->ok=0;
        unsigned v=((a&15)<<12)|((b&63)<<6)|(c&63);
        if(v<2048) r->ok=0;
        return (int)v;
    }
    r->ok=0; return 0;
}
static void utf(Reader *r, char *out, size_t cap) {
    size_t n=(size_t)readN(r,2); out[0]=0;
    if(!r->ok || n>r->n) { r->ok=0; return; }
    Reader s={r->p,n,1}; r->p+=n; r->n-=n;
    size_t j=0;
    while(s.n && s.ok) {
        unsigned u=(unsigned)unit(&s);
        if(u>=0xd800 && u<=0xdbff) {
            unsigned v=(unsigned)unit(&s);
            if(v<0xdc00||v>0xdfff) { s.ok=0; break; }
            u=0x10000+((u-0xd800)<<10)+(v-0xdc00);
        } else if(u>=0xdc00&&u<=0xdfff) { s.ok=0; break; }
        // Avoid embedded NUL truncating the displayed name/message.
        if(u==0) u=0xfffd;
        uint8_t bytes[4]; size_t k;
        if(u<128) {bytes[0]=u;k=1;}
        else if(u<2048) {bytes[0]=0xc0|(u>>6);bytes[1]=0x80|(u&63);k=2;}
        else if(u<65536) {bytes[0]=0xe0|(u>>12);bytes[1]=0x80|((u>>6)&63);bytes[2]=0x80|(u&63);k=3;}
        else {bytes[0]=0xf0|(u>>18);bytes[1]=0x80|((u>>12)&63);bytes[2]=0x80|((u>>6)&63);bytes[3]=0x80|(u&63);k=4;}
        if(j+k>=cap) {s.ok=0;break;} memcpy(out+j,bytes,k);j+=k;
    }
    out[j]=0; if(!s.ok) r->ok=0;
}
static int png(const uint8_t *p,size_t n,int width,int height) {
    static const uint8_t sig[]={137,80,78,71,13,10,26,10};
    if(n<33||memcmp(p,sig,8)||memcmp(p+12,"IHDR",4))return 0;
    uint32_t w=((uint32_t)p[16]<<24)|((uint32_t)p[17]<<16)|(p[18]<<8)|p[19];
    uint32_t h=((uint32_t)p[20]<<24)|((uint32_t)p[21]<<16)|(p[22]<<8)|p[23];
    return w==(uint32_t)width&&h==(uint32_t)height;
}
static int rect(const uint16_t *g,int k) {return g[k+2]>0&&g[k+3]>0&&g[k]+g[k+2]<=g[0]&&g[k+1]+g[k+3]<=g[1];}
int AGNotesParse(const uint8_t *data,size_t length,int command,AGCaptchaPacket *p) {
    if(!data||!p||length>65535)return 0;
    memset(p,0,sizeof *p);Reader r={data,length,1};int v=readN(&r,1);
    if(command==-122){if(v!=1)return 0;p->kind=4;p->status=readN(&r,1);if(p->status>1)return 0;utf(&r,p->text,sizeof p->text);return r.ok&&!r.n;}
    if(command!=-123||(v!=1&&v!=2))return 0;
    p->kind=readN(&r,1);
    if(p->kind==0)return r.ok&&!r.n;
    if(p->kind==3){p->boss=readN(&r,1);return r.ok&&!r.n&&p->boss<=1;}
    if(p->kind==2){p->status=readN(&r,1);utf(&r,p->text,sizeof p->text);return r.ok&&!r.n;}
    if(p->kind!=1)return 0;
    if(r.n<2)return 0;
    unsigned nl=(r.p[0]<<8)|r.p[1];if(!nl||nl>AG_CAP_NONCE||r.n<nl+2)return 0;
    p->nonceLength=nl;memcpy(p->nonce,r.p+2,nl);
    char nonceText[AG_CAP_NONCE*2];utf(&r,nonceText,sizeof nonceText);
    p->expires=readN(&r,8);p->type=v==2?readN(&r,1):1;
    for(int i=0;i<22;i++)p->g[i]=readN(&r,2);
    int columns=readN(&r,1),rows=readN(&r,1);p->required=readN(&r,1);p->failures=readN(&r,1);
    p->imageLength=readN(&r,4);int type=p->type,isGrid=type==1||type==2||type==4,aux=type==3||type==5||type==6;
    const uint16_t *a=p->g;
    if(!r.ok||type<1||type>6||columns!=3||rows!=(isGrid?3:1)||
       (type==1&&p->required!=4)||(type==2&&p->required!=2&&p->required!=3)||
       (type==4&&(p->required<1||p->required>8))||(aux&&p->required!=1)||
       !p->imageLength||p->imageLength>AG_CAP_IMAGE||p->imageLength>r.n||
       !a[0]||a[0]>480||!a[1]||a[1]>640||!a[4]||a[21]>64||
       !rect(a,9)||!rect(a,13)||!rect(a,17)||a[6]>=a[0]||a[7]>=a[1]||a[8]>=a[1])return 0;
    if((isGrid||type==3)&&(a[2]+a[4]*3+a[5]*2>a[0]||a[3]+a[4]*rows+a[5]*(rows-1)>a[1]))return 0;
    memcpy(p->image,r.p,p->imageLength);r.p+=p->imageLength;r.n-=p->imageLength;
    if(!png(p->image,p->imageLength,a[0],a[1]))return 0;
    int hasAux=v==2?readN(&r,1):0;if(hasAux!=aux)return 0;
    if(hasAux){
        for(int i=0;i<7;i++)p->d[i]=readN(&r,2);
        p->pieceLength=readN(&r,4);const uint16_t *d=p->d;
        if(!r.ok||!p->pieceLength||p->pieceLength>(type==6?AG_CAP_IMAGE:4096)||p->pieceLength>r.n||
           !d[2]||d[2]>96||d[0]+d[2]>a[0]||d[1]+d[2]>a[1])return 0;
        if(type!=6&&(d[3]>d[5]||d[4]>d[6]||d[5]+d[2]>a[0]||d[6]+d[2]>a[1]))return 0;
        if(type==6&&(d[3]+a[4]>a[0]||d[5]+a[4]>a[0]||d[4]+a[4]>a[1]||d[6]+a[4]>a[1]))return 0;
        memcpy(p->piece,r.p,p->pieceLength);r.p+=p->pieceLength;r.n-=p->pieceLength;
        if(!png(p->piece,p->pieceLength,d[2],d[2]*(type==6?8:1)))return 0;
    }
    return r.ok&&!r.n;
}
static int grid(const AGCaptchaState *s){return s->packet.type==1||s->packet.type==2||s->packet.type==4;}
static int movable(const AGCaptchaState *s){return s->packet.type==3||s->packet.type==5;}
void AGCaptchaInit(AGCaptchaState *s){memset(s,0,sizeof *s);s->op=-1;s->down=-1;s->lastKey=-10000;}
void AGCaptchaClose(AGCaptchaState *s){s->active=0;s->waiting=0;s->used=0;s->placed=0;s->dragging=0;s->rotationTouch=0;s->op=-1;s->down=-1;s->lastKey=-10000;s->serial++;}
void AGCaptchaContext(AGCaptchaState *s,int boss,int room){s->boss=!!boss;s->inRoom=!!room;if((s->active&&(!boss||!room))||(!boss&&s->op>=0))AGCaptchaClose(s);}
int AGCaptchaReceive(AGCaptchaState *s,const AGCaptchaPacket *p,double now){
    if(p->kind==3){AGCaptchaContext(s,p->boss,s->inRoom);return 1;}
    if(p->kind==0){if(s->boss)s->op=0;return 1;}
    if(p->kind==2){s->waiting=0;snprintf(s->notice,sizeof s->notice,"%s",p->text);if(p->status<=2)AGCaptchaClose(s);return 1;}
    if(p->kind!=1||!s->boss||!s->inRoom)return 0;
    s->packet=*p;s->active=1;s->waiting=0;s->used=0;s->focus=0;s->x=p->d[0];s->y=p->d[1];s->placed=0;s->rotation=0;s->dragging=0;s->rotationTouch=0;s->rotationMoved=0;s->op=-1;s->down=-1;s->lastKey=-10000;s->blinkSince=now;s->serial++;
    if(p->failures)snprintf(s->notice,sizeof s->notice,"Đã sai %d/3 lần",p->failures);
    else snprintf(s->notice,sizeof s->notice,"%s",p->type==6?"Trái/phải hoặc vuốt để xoay":movable(s)?"Giữ, kéo hình rồi xác nhận":p->type==4?"Chọn đúng theo câu hỏi ở trên":"Chọn đủ hình rồi xác nhận");return 1;
}
int AGCaptchaSelected(const AGCaptchaState *s,int cell){for(int i=0;i<s->used;i++)if(s->selected[i]==cell)return i+1;return 0;}
static void choose(AGCaptchaState *s,int cell,double now){
    s->focus=cell;if(s->waiting)return;s->blinkSince=now;
    int old=AGCaptchaSelected(s,cell);if(old){for(int i=old-1;i<s->used-1;i++)s->selected[i]=s->selected[i+1];s->used--;return;}
    if(s->used>=s->packet.required){snprintf(s->notice,sizeof s->notice,"Đã chọn đủ. Xóa để chọn lại.");return;}
    s->selected[s->used++]=cell;snprintf(s->notice,sizeof s->notice,"%s",s->used==s->packet.required?"Bấm Xác nhận để kiểm tra":"Chọn tiếp theo yêu cầu ở trên");
}
void AGCaptchaAction(AGCaptchaState *s,int action,double now){
    if(!s->active||!s->boss||!s->inRoom)return;
    if(s->waiting&&now-s->waitSince>10){s->waiting=0;snprintf(s->notice,sizeof s->notice,"Chưa có phản hồi. Bấm Đổi hình.");}
    if(s->waiting)return;
    if(action==0){s->used=0;s->placed=0;s->rotation=0;s->dragging=0;s->x=s->packet.d[0];s->y=s->packet.d[1];s->blinkSince=now;snprintf(s->notice,sizeof s->notice,"Đã đặt lại");}
    else if(action==1){if((movable(s)&&!s->placed)||(grid(s)&&s->used!=s->packet.required)){snprintf(s->notice,sizeof s->notice,"%s",movable(s)?"Kéo hình vào chỗ đúng rồi xác nhận":"Chọn đủ hình trước khi xác nhận");return;}s->op=1;s->waiting=1;s->waitSince=now;snprintf(s->notice,sizeof s->notice,"Đang kiểm tra...");}
    else if(action==2){s->op=2;s->waiting=1;s->waitSince=now;snprintf(s->notice,sizeof s->notice,"Đang đổi hình...");}
    else if(action==3){if(s->used||s->placed||s->rotation)AGCaptchaAction(s,0,now);else {AGCaptchaClose(s);s->op=3;}}
    else if(action==4||action==5){s->rotation=(s->rotation+(action==4?7:1))%8;snprintf(s->notice,sizeof s->notice,"Xoay cho khớp mẫu rồi xác nhận");}
}
static void move(AGCaptchaState *s,int x,int y){const uint16_t *d=s->packet.d;s->x=x<d[3]?d[3]:x>d[5]?d[5]:x;s->y=y<d[4]?d[4]:y>d[6]?d[6]:y;}
void AGCaptchaKey(AGCaptchaState *s,int code,int released,double now){
    if(!s->active)return;if(released){s->lastKey=-10000;return;}if(s->lastKey==code)return;s->lastKey=code;
    if(s->packet.type==6&&(code==-3||code==52))AGCaptchaAction(s,4,now);
    else if(s->packet.type==6&&(code==-4||code==54||code==-5||code==10||code==13))AGCaptchaAction(s,5,now);
    else if(movable(s)&&(code>=-4&&code<=-1)){if(!s->waiting){move(s,s->x+(code==-3?-4:code==-4?4:0),s->y+(code==-1?-4:code==-2?4:0));s->placed=1;}}
    else if(grid(s)&&code>=49&&code<=57)choose(s,code-49,now);
    else if(code==48||code==-6)AGCaptchaAction(s,1,now);
    else if(code==42)AGCaptchaAction(s,0,now);
    else if(code==35)AGCaptchaAction(s,2,now);
    else if(grid(s)&&(code>=-4&&code<=-1)){int delta=code==-1?6:code==-2?3:code==-3?8:1;s->focus=(s->focus+delta)%9;s->blinkSince=now;}
    else if(code==-5||code==10||code==13){if(movable(s)){if(!s->waiting)s->placed=1;}else if(grid(s))choose(s,s->focus,now);}
    else if(code==-7||code==27)AGCaptchaAction(s,3,now);
}
static int inside(int x,int y,int a,int b,int w,int h){return x>=a&&y>=b&&x<a+w&&y<b+h;}
static int hit(AGCaptchaState *s,int x,int y){const uint16_t *a=s->packet.g,*d=s->packet.d;int tile=a[4],step=tile+a[5];
    if(grid(s))for(int i=0;i<9;i++)if(inside(x,y,a[2]+(i%3)*step,a[3]+(i/3)*step,tile,tile))return i;
    if(s->packet.type==6)for(int i=0;i<2;i++)if(inside(x,y,d[3+i*2],d[4+i*2],tile,tile))return 20+i;
    for(int i=0;i<3;i++)if(inside(x,y,a[9+i*4],a[10+i*4],a[11+i*4],a[12+i*4]))return 10+i;return -1;}
void AGCaptchaTouch(AGCaptchaState *s,int phase,int x,int y,double now){
    if(!s->active)return;const uint16_t *d=s->packet.d;
    if(phase==0){s->down=hit(s,x,y);s->rotationTouch=0;s->rotationMoved=0;
        if(movable(s)&&!s->waiting&&inside(x,y,s->x,s->y,d[2],d[2])){s->dragging=1;s->grabX=x-s->x;s->grabY=y-s->y;s->down=-1;}
        else if(s->packet.type==6&&!s->waiting&&inside(x,y,d[0],d[1],d[2],d[2])){s->rotationTouch=1;s->rotationX=x;s->down=-1;}
        else if(grid(s)&&s->down>=0&&s->down<9){s->focus=s->down;s->blinkSince=now;}return;
    }
    if(phase==1){if(s->dragging&&!s->waiting){move(s,x-s->grabX,y-s->grabY);return;}
        if(s->rotationTouch&&!s->waiting){if(abs(x-s->rotationX)>=10){AGCaptchaAction(s,x>s->rotationX?5:4,now);s->rotationX=x;s->rotationMoved=1;}return;}if(hit(s,x,y)!=s->down)s->down=-1;return;}
    if(phase==3){s->dragging=0;s->rotationTouch=0;s->down=-1;return;}
    if(s->dragging){if(!s->waiting){move(s,x-s->grabX,y-s->grabY);s->placed=1;snprintf(s->notice,sizeof s->notice,"Đã thả hình. Bấm Xác nhận.");}s->dragging=0;s->down=-1;return;}
    if(s->rotationTouch){if(!s->rotationMoved)AGCaptchaAction(s,5,now);s->rotationTouch=0;s->down=-1;return;}
    int h=hit(s,x,y);if(h==s->down){if(h>=0&&h<9&&grid(s))choose(s,h,now);else if(h>=10&&h<=12)AGCaptchaAction(s,h-10,now);else if(h==20||h==21)AGCaptchaAction(s,h-16,now);}s->down=-1;
}
static void put16(uint8_t *out,int n){out[0]=(uint8_t)(n>>8);out[1]=(uint8_t)n;}
size_t AGCaptchaSend(const AGCaptchaState *s,int op,int width,int height,uint8_t out[AG_CAP_NONCE+16]){
    if(op<0||op>3)return 0;out[0]=2;out[1]=(uint8_t)op;
    if(op==0){if(width<1||width>480||height<1||height>640)return 0;put16(out+2,width);put16(out+4,height);return 6;}
    if(op==3)return 2;
    size_t n=s->packet.nonceLength;if(!n||n>AG_CAP_NONCE)return 0;put16(out+2,n);memcpy(out+4,s->packet.nonce,n);n+=4;
    if(op==2)return n;
    if(movable(s)){out[n++]=4;put16(out+n,s->x+s->packet.d[2]/2);put16(out+n+2,s->y+s->packet.d[2]/2);return n+4;}
    if(s->packet.type==6){out[n++]=1;out[n++]=s->rotation;return n;}
    out[n++]=s->used;for(int i=0;i<s->used;i++)out[n++]=s->selected[i];return n;
}
