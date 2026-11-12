#pragma once
#include <stddef.h>
#include <stdint.h>
int AGLobbyOpened(int variant);
void AGLobbyOpenNative(void *env,int variant,int tab);
void AGLobbyTick(void *env,int variant,uintptr_t connection);
int AGLobbyReceive(void *env,void *message,int variant);
int AGLobbySend(void *env,int variant,uintptr_t connection,int command,const uint8_t *bytes,size_t length);
