/* Rebuilt UFO session253. Server tickets own shot identity. Native command
 * processing owns actor changes; no separate deferred-turn queue exists. */
#include "UfoAuto.h"
#include <string.h>

static void discardShot(AGUfoAuto *s) {
    s->hasPlan=0;s->claimed=0;s->stable=0;
}
static int matches(const AGUfoAuto *s,const AGUfoPlan *p) {
    return s->valid&&s->turn==p->turn&&s->owner==p->owner&&s->ticket==p->ticket;
}
static int usable(const AGUfoPlan *p) {
    return p->ticket&&p->owner>=0&&p->owner<8&&p->angle>=0&&p->angle<360&&
        p->force>=1&&p->force<=30&&p->release>=0&&p->release<=30;
}
void AGUfoReset(AGUfoAuto *s,uintptr_t connection) {
    uint64_t revision=s->revision+1;
    memset(s,0,sizeof *s);s->connection=connection;s->revision=revision;
    s->owner=-1;s->turn=-1;
}
void AGUfoStart(AGUfoAuto *s) {
    int enabled=s->enabled;AGUfoReset(s,s->connection);s->enabled=enabled;
}
void AGUfoMode(AGUfoAuto *s,int enabled) {
    s->enabled=enabled!=0;
    if(!s->enabled){discardShot(s);s->hasEarlyPlan=0;s->revision++;}
}
void AGUfoTurn(AGUfoAuto *s,int owner,int turn,uint64_t ticket) {
    if(s->valid&&s->owner==owner&&s->turn==turn&&s->ticket==ticket)return;
    AGUfoPlan early=s->earlyPlan;int hadEarly=s->hasEarlyPlan;
    s->revision++;s->owner=owner;s->turn=turn;s->ticket=ticket;s->arena=0;
    s->valid=owner>=0&&owner<8&&ticket!=0;
    discardShot(s);s->sent=0;s->powerSent=0;s->retryAfter=0;s->hasEarlyPlan=0;
    if(hadEarly&&matches(s,&early)){s->plan=early;s->hasPlan=1;}
}
int AGUfoAim(AGUfoAuto *s,const AGUfoPlan *p) {
    if(!s->enabled||!usable(p))return 0;
    if(!matches(s,p)){s->earlyPlan=*p;s->hasEarlyPlan=1;return 0;}
    if(s->sent||s->claimed)return 0;
    if(!s->hasPlan||s->plan.x!=p->x||s->plan.y!=p->y||s->plan.angle!=p->angle||
       s->plan.force!=p->force||s->plan.release!=p->release)s->stable=0;
    s->plan=*p;s->hasPlan=1;return 1;
}
void AGUfoManual(AGUfoAuto *s) {
    discardShot(s);s->sent=1;s->revision++;
}
int AGUfoAcquire(AGUfoAuto *s,const AGUfoFrame *f,AGUfoPlan *out) {
    if(f->connection!=s->connection){AGUfoReset(s,f->connection);return 0;}
    if(!f->active||!f->ufo){s->stable=0;return 0;}
    if(s->arena&&s->arena!=f->arena){AGUfoStart(s);return 0;}
    int ready=s->enabled&&s->valid&&s->hasPlan&&!s->sent&&!s->claimed&&
        f->owner==s->owner&&f->local==s->owner&&f->alive&&!f->state&&!f->blocked&&
        f->x==s->plan.x&&f->y==s->plan.y&&f->now>=s->retryAfter;
    if(!ready){s->stable=0;return 0;}
    if(!s->stable){s->stable=1;s->stableSince=f->now;return 0;}
    if(f->now-s->stableSince<0.06)return 0;
    s->arena=f->arena;s->claimed=1;*out=s->plan;return 1;
}
void AGUfoComplete(AGUfoAuto *s,uint64_t revision,int result,double now) {
    if(s->revision!=revision)return;
    s->claimed=0;
    if(result>0){s->sent=1;s->hasPlan=0;}
    else{s->stable=0;s->retryAfter=now+0.25;}
}
