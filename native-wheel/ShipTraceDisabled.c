/* Release ABI: retain existing call sites without sampling, timers or logs. */
#include "ShipTrace.h"
void AGShipTraceTick(void *env,int variant,int source){(void)env;(void)variant;(void)source;}
void AGShipTraceReceive(void *env,void *message,int variant){(void)env;(void)message;(void)variant;}
void AGShipTraceWait(int variant,int kind,int actor,int active){(void)variant;(void)kind;(void)actor;(void)active;}
void AGShipTraceCorpse(int variant,int index,int character,int handled){(void)variant;(void)index;(void)character;(void)handled;}
__attribute__((visibility("default"))) int AGShipTraceGet(int variant,AGShipTrace *out){(void)variant;(void)out;return 0;}
