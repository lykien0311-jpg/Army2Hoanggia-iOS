#pragma once
#include <stddef.h>
#include <stdint.h>
int AGViewerReceive(void *env,void *message,int variant);
void AGViewerTick(void *env,int variant);
void AGViewerExpectBattlefield(int variant,uintptr_t connection);
uintptr_t AGViewerConnection(void *env,int variant);
int AGViewerSend(void *env,int variant,uintptr_t connection,int command,const uint8_t *bytes,size_t length);
