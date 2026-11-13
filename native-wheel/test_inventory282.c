#define AG_WHEEL_PREVIEW 1
#include "Inventory.c"
#include <assert.h>
#include <stdio.h>
static Entry row(uint64_t id,int64_t qty,int group,int rank){return (Entry){.key=id,.quantity=qty,.item=(void *)(uintptr_t)(id+4096),.group=group,.id=(int)id,.rank=rank};}
int main(void){
 InventoryState state={0};Entry initial[]={row(103,5,2,0),row(1,1,0,1),row(7,20,1,2),row(120,1,3,3)};
 assert(arrange(&state,initial,4,1));assert(initial[0].key==1&&initial[1].key==7&&initial[2].key==103);remember(&state,initial,4);
 Entry crafted[]={row(1,1,0,0),row(7,20,1,1),row(104,1,2,2),row(120,1,3,3)};
 assert(arrange(&state,crafted,4,0));assert(crafted[0].key==104);remember(&state,crafted,4);
 assert(!arrange(&state,crafted,4,0));
 Entry reload[]={row(1,1,0,0),row(7,20,1,1),row(104,1,2,2),row(120,1,3,3)};
 for(int i=0;i<4;i++)reload[i].item=(void *)((uintptr_t)reload[i].item+10000);
 assert(arrange(&state,reload,4,0));assert(reload[0].key==104);remember(&state,reload,4);
 Entry stack[]={row(1,1,0,0),row(7,21,1,1),row(104,1,2,2),row(120,1,3,3)};
 assert(arrange(&state,stack,4,0));assert(stack[0].key==7);remember(&state,stack,4);
 for(int i=0;i<4;i++)stack[i].rank=i;
 assert(arrange(&state,stack,4,1));assert(stack[0].key==1&&stack[1].key==7&&stack[2].key==104);
 for(int turn=0;turn<500;turn++){for(int i=0;i<4;i++)stack[i].rank=i;stack[2].quantity++;assert(arrange(&state,stack,4,0));remember(&state,stack,4);}
 free(state.previous);puts("PASS inventory: craft result first, stack gains, refreshed objects, reopen groups and 500 consecutive updates");
}
