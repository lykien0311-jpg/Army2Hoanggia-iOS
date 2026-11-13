#pragma once
#include <stddef.h>
#include <stdint.h>
int AGNativeWatchAvailable(void);
int AGNativeWatchFree(int variant);
int AGNativeWatchPacket(void *env,int variant,const uint8_t *data,size_t length);
void AGNativeWatchEnd(void *env,int variant);
void AGNativeWatchCamera(int variant,int kind,int code);
void AGNativeWatchTick(void *env,int variant);
int AGViewerActive(int variant);
