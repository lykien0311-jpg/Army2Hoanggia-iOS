#pragma once
#include <stddef.h>
#include <stdint.h>
enum { AGLobbyField = 1, AGLobbyMarket, AGLobbyEvent };
typedef struct {
    int character;
    int canvasWidth;
    int inventoryGeometry[7];
    int64_t xu, luong;
} AGLobbyAccount;
int AGLobbyOpened(int variant);
int AGLobbyInput(int variant,int kind,int a,int b);
void AGLobbyOpenNative(void *env,int variant,int tab);
void AGLobbyTick(void *env,int variant,uintptr_t connection);
int AGLobbyReceive(void *env,void *message,int variant);
void AGLobbyWatchFinished(int variant,uintptr_t connection);
int AGLobbySend(void *env,int variant,uintptr_t connection,int command,const uint8_t *bytes,size_t length);
int AGLobbyReadAccount(void *env,int variant,AGLobbyAccount *account);


