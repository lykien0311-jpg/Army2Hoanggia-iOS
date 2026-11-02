#include "WheelProtocol.h"
#include <string.h>
#include <limits.h>
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
int AGParse(const uint8_t *data, size_t length, AGSnapshot *out) {
    if(!data||!out||length>65535) return 0;
    Reader r={data,length,1}; AGSnapshot s={0};
    if(readN(&r,2)!=22354) return 0;
    s.version=(int)readN(&r,1); if(s.version!=1&&s.version!=2)return 0;
    s.status=(int)readN(&r,1); utf(&r,s.message,sizeof s.message);
    s.ack=(int64_t)readN(&r,8);s.serverTime=(int64_t)readN(&r,8);
    s.round=(int64_t)readN(&r,8);s.starts=(int64_t)readN(&r,8);s.ends=(int64_t)readN(&r,8);
    s.total=(int64_t)readN(&r,8);s.own=(int64_t)readN(&r,8);
    s.balance=(int64_t)readN(&r,8);s.pending=(int64_t)readN(&r,8);
    s.count=(int32_t)readN(&r,4);s.tax=(int)readN(&r,1);
    s.page=(int32_t)readN(&r,4);s.rows=(int)readN(&r,1);
    if(!r.ok||s.rows>AG_MAX_ROWS||s.count<0||s.rows>s.count||s.tax>10||s.page<0||
       s.total<0||s.own<0||s.own>s.total||s.own>AG_MAX_STAKE||s.balance<0||s.pending<0||
       s.serverTime<0||s.round<0||s.ends<0) return 0;
    int64_t rowTotal=0;
    for(int i=0;i<s.rows;i++) {
        utf(&r,s.entries[i].name,sizeof s.entries[i].name);
        s.entries[i].amount=(int64_t)readN(&r,8);s.entries[i].own=readN(&r,1)!=0;
        if(s.entries[i].amount<0||s.entries[i].amount>AG_MAX_STAKE)return 0;
        rowTotal+=s.entries[i].amount;
    }
    if(rowTotal>s.total)return 0;
    s.hasResult=readN(&r,1)!=0;
    if(s.hasResult) {
        s.resultRound=(int64_t)readN(&r,8);utf(&r,s.winner,sizeof s.winner);
        s.resultPool=(int64_t)readN(&r,8);s.resultTax=(int)readN(&r,1);
        s.resultPrize=(int64_t)readN(&r,8);
        if(s.version>=2)s.resultStake=(int64_t)readN(&r,8);
        if(s.resultRound<0||s.resultPool<0||s.resultTax>10||s.resultPrize<0||s.resultStake<0||s.resultStake>AG_MAX_STAKE)return 0;
    }
    if(!r.ok||r.n)return 0;
    *out=s;return 1;
}
static void put(uint8_t *out, uint64_t value, unsigned n) {
    for(unsigned i=0;i<n;i++)out[n-1-i]=(uint8_t)(value>>(8*i));
}
size_t AGPoll(uint8_t out[8], int32_t page) {
    if(page<0)return 0;
    out[0]=0x57;out[1]=0x52;out[2]=2;out[3]=0;put(out+4,(uint32_t)page,4);return 8;
}
size_t AGBet(uint8_t out[28], int64_t round, int64_t nonce, int64_t amount) {
    if(round<0||nonce<=0||amount<AG_MIN_STAKE||amount>AG_MAX_STAKE)return 0;
    out[0]=0x57;out[1]=0x52;out[2]=2;out[3]=1;
    put(out+4,(uint64_t)round,8);put(out+12,(uint64_t)nonce,8);put(out+20,(uint64_t)amount,8);return 28;
}
const char *AGValidateBet(const AGSnapshot *s, int64_t serverNow, int64_t amount) {
    if(amount<AG_MIN_STAKE||amount>AG_MAX_STAKE)return "Mỗi lượt từ 1.000.000 đến 50.000.000 xu.";
    if(s->own>AG_MAX_STAKE-amount)return "Tổng xu tham gia một vòng tối đa 50.000.000.";
    if(amount>s->balance)return "Bạn không đủ xu.";
    if(s->ends>0 && serverNow>=s->ends-10000)return "Đã khóa đặt xu trong 10 giây cuối vòng.";
    return NULL;
}
