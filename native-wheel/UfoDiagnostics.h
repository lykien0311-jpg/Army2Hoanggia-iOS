#ifndef AG_UFO_DIAGNOSTICS_H
#define AG_UFO_DIAGNOSTICS_H
#include <stdint.h>
/* Scalars copied on the game/network threads. UIKit never reads Java objects. */
typedef struct {
    uint64_t ticks,receives,starts,turns,aims,modes,accepted,shots,failures,manuals,waits;
    double tickTime,receiveTime,waitSince;
    int variant,contextOK,active,ufo,local,owner,count,alive,state,x,y,effects,blocked;
    int lastCommand,lastLength,last115Length,last24Length,lastAimOwner,lastAimTurn;
    uint32_t lastMagic;
    int enabled,valid,hasPlan,early,sent,claimed,stable,turn,serverOwner,planX,planY,angle;
    int nativePending,nativeApplying,nativeOwner,waitActive,waitKind,waitActor;
    uint64_t ticket,sequence,applied;
} AGUfoDiagnostic;
int AGUfoDiagnosticsGet(int variant,AGUfoDiagnostic *out);
#endif
