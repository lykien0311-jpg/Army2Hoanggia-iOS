#ifndef AG_NOTES_PROTOCOL_H
#define AG_NOTES_PROTOCOL_H
#include <stdint.h>
#include <stddef.h>
#define AG_CAP_IMAGE 24000
#define AG_CAP_NONCE 1024
#define AG_NOTES_TEXT 4096
typedef struct {
    int kind,status,boss,type,required,failures;
    uint64_t expires;
    uint16_t g[22],d[7],nonceLength;
    uint8_t nonce[AG_CAP_NONCE];
    char text[AG_NOTES_TEXT];
    uint32_t imageLength,pieceLength;
    uint8_t image[AG_CAP_IMAGE],piece[AG_CAP_IMAGE];
} AGCaptchaPacket;
typedef struct {
    AGCaptchaPacket packet;
    int boss,inRoom,active,waiting,op,used,focus,selected[8];
    int x,y,placed,rotation,dragging,grabX,grabY,down,rotationTouch,rotationMoved,rotationX,lastKey;
    double waitSince,blinkSince;
    uint64_t serial;
    char notice[512];
} AGCaptchaState;
int AGNotesParse(const uint8_t *,size_t,int command,AGCaptchaPacket *);
void AGCaptchaInit(AGCaptchaState *);
void AGCaptchaClose(AGCaptchaState *);
void AGCaptchaContext(AGCaptchaState *,int boss,int room);
int AGCaptchaReceive(AGCaptchaState *,const AGCaptchaPacket *,double now);
int AGCaptchaSelected(const AGCaptchaState *,int cell);
void AGCaptchaAction(AGCaptchaState *,int action,double now);
void AGCaptchaKey(AGCaptchaState *,int code,int released,double now);
void AGCaptchaTouch(AGCaptchaState *,int phase,int x,int y,double now);
size_t AGCaptchaSend(const AGCaptchaState *,int op,int width,int height,uint8_t out[AG_CAP_NONCE+16]);
#endif
