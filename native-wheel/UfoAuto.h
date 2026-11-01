#ifndef AG_UFO_AUTO_H
#define AG_UFO_AUTO_H
#include <stdint.h>

/* The server supplies the same trajectories used by the reference JAR.
 * Rendering flags are deliberately absent from this controller. */
typedef struct {
    int turn, owner, angle, force, release, x, y;
    uint64_t ticket;
} AGUfoPlan;
typedef struct {
    uintptr_t connection, arena;
    uint64_t revision, ticket;
    int enabled, valid, turn, owner, sent, claimed, powerSent;
    int hasPlan, hasEarlyPlan, stable;
    double stableSince, retryAfter;
    AGUfoPlan plan, earlyPlan;
} AGUfoAuto;
typedef struct {
    uintptr_t connection, arena;
    int active, ufo, local, owner, alive, state, blocked, x, y;
    double now;
} AGUfoFrame;

void AGUfoReset(AGUfoAuto *, uintptr_t connection);
void AGUfoStart(AGUfoAuto *);
void AGUfoMode(AGUfoAuto *, int enabled);
void AGUfoTurn(AGUfoAuto *, int owner, int turn, uint64_t ticket);
int AGUfoAim(AGUfoAuto *, const AGUfoPlan *);
void AGUfoManual(AGUfoAuto *);
int AGUfoAcquire(AGUfoAuto *, const AGUfoFrame *, AGUfoPlan *);
void AGUfoComplete(AGUfoAuto *, uint64_t revision, int result, double now);
#endif
