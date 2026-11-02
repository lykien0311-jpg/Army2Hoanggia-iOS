#include "UfoAuto.h"
#include <string.h>

static int same(const AGUfoAuto *a, const AGUfoPlan *p) {
    return a->valid && p->owner == a->owner && p->turn == a->turn &&
        p->ticket == a->ticket;
}
static int valid(const AGUfoPlan *p) {
    return p->owner >= 0 && p->owner < 8 && p->ticket &&
        p->angle >= 0 && p->angle < 360 && p->force >= 1 &&
        p->force <= 30 && p->release >= 0 && p->release <= 30;
}
void AGUfoReset(AGUfoAuto *a, uintptr_t connection) {
    uint64_t revision = a->revision + 1;
    memset(a, 0, sizeof *a);
    a->connection = connection;
    a->revision = revision;
    a->owner = -1;
}
void AGUfoStart(AGUfoAuto *a) {
    int enabled = a->enabled;
    AGUfoReset(a, a->connection);
    a->enabled = enabled;
}
void AGUfoMode(AGUfoAuto *a, int enabled) {
    a->enabled = !!enabled;
    if (!enabled) {
        a->revision++;
        a->hasPlan = a->hasEarlyPlan = a->claimed = a->stable = 0;
    }
}
void AGUfoTurn(AGUfoAuto *a, int owner, int turn, uint64_t ticket) {
    /* Repeated turn notifications must not re-arm a completed shot. */
    if (a->valid && a->owner == owner && a->turn == turn && a->ticket == ticket)
        return;
    AGUfoPlan early = a->earlyPlan;
    int useEarly = a->hasEarlyPlan;
    a->revision++;
    a->arena = 0;
    a->owner = owner;
    a->turn = turn;
    a->ticket = ticket;
    a->valid = owner >= 0 && owner < 8 && ticket != 0;
    a->sent = a->claimed = a->powerSent = a->hasPlan = a->stable = 0;
    a->retryAfter = 0;
    a->hasEarlyPlan = 0;
    if (useEarly && same(a, &early)) { a->plan = early; a->hasPlan = 1; }
}
int AGUfoAim(AGUfoAuto *a, const AGUfoPlan *p) {
    if (!a->enabled || !valid(p)) return 0;
    if (!same(a, p)) {
        /* Keep at most one not-yet-dispatched turn; never fire it by itself. */
        a->earlyPlan = *p;
        a->hasEarlyPlan = 1;
        return 0;
    }
    if (a->sent || a->claimed) return 0;
    if (!a->hasPlan || a->plan.angle != p->angle || a->plan.force != p->force ||
        a->plan.release != p->release || a->plan.x != p->x || a->plan.y != p->y)
        a->stable = 0;
    a->plan = *p;
    a->hasPlan = 1;
    return 1;
}
void AGUfoManual(AGUfoAuto *a) {
    a->sent = 1;
    a->hasPlan = a->claimed = a->stable = 0;
    a->revision++;
}
int AGUfoAcquire(AGUfoAuto *a, const AGUfoFrame *f, AGUfoPlan *out) {
    if (a->connection != f->connection) { AGUfoReset(a, f->connection); return 0; }
    if (!f->active || !f->ufo) { a->stable = 0; return 0; }
    if (a->arena && a->arena != f->arena) { AGUfoStart(a); return 0; }
    if (!a->enabled || !a->valid || !a->hasPlan || a->sent || a->claimed ||
        f->local != a->owner || f->owner != a->owner || !f->alive ||
        f->state || f->blocked || f->x != a->plan.x || f->y != a->plan.y ||
        f->now < a->retryAfter) {
        a->stable = 0;
        return 0;
    }
    if (!a->stable) { a->stable = 1; a->stableSince = f->now; return 0; }
    /* Two entry points can pulse in the same frame. Use elapsed game time,
     * not a pulse count, to let the original turn/position update finish. */
    if (f->now - a->stableSince < 0.06) return 0;
    a->arena = f->arena;
    a->claimed = 1;
    *out = a->plan;
    return 1;
}
void AGUfoComplete(AGUfoAuto *a, uint64_t revision, int result, double now) {
    if (a->revision != revision) return;
    a->claimed = 0;
    if (result > 0) {
        a->sent = 1;
        a->hasPlan = 0;
    } else {
        /* A Java allocation/send exception must not consume the turn. The
         * original session remains responsible for packet framing/queueing. */
        a->retryAfter = now + 0.25;
        a->stable = 0;
    }
}
