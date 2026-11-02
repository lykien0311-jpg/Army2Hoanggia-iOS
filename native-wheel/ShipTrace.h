#ifndef AG_SHIP_TRACE_H
#define AG_SHIP_TRACE_H
#include <stdint.h>
enum { AGShipTraceActors=16,AGShipTraceEvents=16 };
typedef struct {int slot,index,character,state,visible,gravity,walk,flight,x,y;int64_t hp;} AGShipActor;
typedef struct {int command,length,first;uint64_t serial;} AGShipEvent;
typedef struct {
    int variant,contextOK,active,room,local,owner,cameraActor,cameraMode,cameraX,cameraY,count;
    int projectileBusy,completionReady,canvasBusy,pending,notified,waitActive,waitKind,waitActor;
    int serverOwner,serverTurn,lastCommand,lastLength,actorCount,eventCount;
    int corpseIndex,corpseCharacter,corpseHandled,corpsePacketActor,corpseTargetX,corpseTargetY,corpseRemove;
    uint64_t samples,pulses,receives,turns,flights,corpseUpdates,corpseRejected,match,eventSerial;
    double sampleTime,pulseTime,receiveTime,waitSince,corpseTime;
    AGShipActor actors[AGShipTraceActors];AGShipEvent events[AGShipTraceEvents];
} AGShipTrace;
void AGShipTraceTick(void *env,int variant,int source);
void AGShipTraceReceive(void *env,void *message,int variant);
void AGShipTraceWait(int variant,int kind,int actor,int active);
void AGShipTraceCorpse(int variant,int index,int character,int handled);
int AGShipTraceGet(int variant,AGShipTrace *out);
#endif
