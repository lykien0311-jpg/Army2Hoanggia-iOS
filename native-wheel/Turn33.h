#ifndef AG_TURN33_H
#define AG_TURN33_H
void AGTurnTick(void *env,int variant);
void AGTurnReceive(void *env,void *message,int variant);
void AGTurnManual(int variant);
int AGTurnChange(void *env,int owner,int variant);
#endif
