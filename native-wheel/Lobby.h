#pragma once
#include <stddef.h>
#include <stdint.h>
void AGLobbyRemember(void *screen,int variant);
int AGLobbyKnown(int variant);
void AGLobbyTick(void *env,int variant,void *screen,int modal,uintptr_t connection);
int AGLobbyReceive(void *env,void *message,int variant);
int AGLobbySend(void *env,int variant,uintptr_t connection,int command,const uint8_t *bytes,size_t length);
