#include <stdint.h>
#include <stddef.h>
#include <mach-o/dyld.h>
#include "NotesMap.h"
#include "GridMap.h"
static int larger(int a,int b){return a>b?a:b;}
static int smaller(int a,int b){return a<b?a:b;}
typedef struct {int w,h,columns,cell,decor;} Grid;
static Grid dimensions(uint8_t *canvas){
    int w=canvas?*(int *)(canvas+0x130):432,h=canvas?*(int *)(canvas+0x128):640;
    if(w<160||w>4096)w=432;if(h<160||h>4096)h=640;
    Grid g;g.decor=larger(3,(w-80)/32);g.w=g.decor*32+56;g.h=larger(136,h-44);
    g.columns=smaller(7,larger(3,(g.w-24)/40));g.cell=(g.w-24)/g.columns;return g;
}
static void layout(uintptr_t base,int v,int kind,uint8_t *screen,Grid g,int width){
    if(!screen)return;
    *(int *)(screen+0x50)=(width-g.w)/2+7;*(int *)(screen+0x54)=8;
    *(int *)(screen+0x58)=g.w;*(int *)(screen+0x5c)=g.h;*(int *)(screen+0x60)=g.decor;
    int resized=0;
    for(int i=1;i<=2;i++){
        uint8_t *c=*(uint8_t **)(base+gridClasses[v][i]);if(!c)continue;
        if(i==kind)resized=*(int *)(c+0xb0)!=g.columns||*(int *)(c+0xb8)!=g.cell;
        *(int *)(c+0xb0)=g.columns;*(int *)(c+0xb8)=g.cell;
        *(int *)(c+0xbc)=g.cell/2-10;*(int *)(c+0xc0)=g.cell/2-14;
    }
    if(kind==0){
        *(int *)(screen+0xc0)=g.columns;*(int *)(screen+0xb8)=g.cell;
        uint8_t *vec=*(uint8_t **)(screen+0x70);int count=vec?*(int *)(vec+0x24):0;
        if(count>=0&&count<100000)*(int *)(screen+0xcc)=(count+g.columns-1)/g.columns;
    }else{
        uint8_t *c=*(uint8_t **)(base+gridClasses[v][kind]);
        uint8_t *vec=*(uint8_t **)(screen+(kind==1?0x70:0x78));
        int count=vec?*(int *)(vec+0x24):0;
        if(c&&count>=0&&count<100000){
            int rows=(count+g.columns-1)/g.columns,limit=larger(0,rows*g.cell-(g.h-110));
            *(int *)(c+0xb4)=rows;*(int *)(c+0xd4)=limit;
            for(int off=0xc4;off<=0xc8;off+=4)*(int *)(c+off)=smaller(limit,larger(0,*(int *)(c+off)));
            if(resized){int selected=*(int *)(screen+(kind==1?0xa8:0xb0));
                if(selected>=0&&selected<count){int bottom=(selected/g.columns+1)*g.cell;
                    if(bottom>*(int *)(c+0xc4)+g.h-110)*(int *)(c+0xc4)=smaller(limit,larger(0,bottom-(g.h-110)));
                }}
        }
    }
}
void AGInventoryTick(int v){
#ifndef AG_WHEEL_PREVIEW
    if(v<0||v>=6)return;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);
    uint8_t *canvas=*(uint8_t **)(base+AGNotesMaps[v].canvas);if(!canvas)return;
    uint8_t *screen=*(uint8_t **)(canvas+0xb8);if(!screen)return;
    for(int i=0;i<3;i++){void *clazz=*(void **)(base+gridClasses[v][i]);if(clazz&&*(void **)screen==clazz){layout(base,v,i,screen,dimensions(canvas),*(int *)(canvas+0x130));break;}}
#endif
}
static int metric(Grid g,int id){switch(id){
case GM_COLS:return g.columns;case GM_CELL:return g.cell;
case GM_ICON_X:return g.cell/2-10;case GM_ICON_Y:return g.cell/2-14;
case GM_HALF_INNER:return g.w/2-7;case GM_HALF_ICON:return g.w/2-14;case GM_HALF_CLIP:return g.w/2-12;case GM_HALF_TEXT:return g.w/2-13;
case GM_INNER_W:return g.w-14;case GM_HIT_W:return g.w-24;
case GM_INV_BG:return g.h-65;case GM_INV_CLIP:return g.h-75;case GM_INV_SCROLL:return g.h-70;
case GM_INV_FOCUS:return 84+(g.h-180)/2;case GM_SHOP_FOCUS:return 49+(g.h-180)/2;
case GM_INV_NAME:return g.h-32;case GM_INV_MONEY:return g.h-14;
case GM_SHOP_BG:return g.h-102;case GM_SHOP_CLIP:return g.h-108;case GM_SHOP_SCROLL:return g.h-110;case GM_SHOP_SCROLL_NEG:return -(49+(g.h-180)/2);
case GM_SHOP_MONEY:return g.h-78;case GM_SHOP_MONEY2:return g.h-77;
case GM_BAR1:return g.h-63;case GM_BAR2:return g.h-43;case GM_BAR3:return g.h-23;
case GM_TEXT1:return g.h-62;case GM_TEXT2:return g.h-42;case GM_TEXT3:return g.h-22;
case GM_HIGHLIGHT:return (g.cell-16)/2;case GM_NEG_HIGHLIGHT:return -(g.cell-16)/2;
default:return 0;}}
// Every call replaces one audited native instruction. No runtime code writes.
__attribute__((visibility("default"))) void AGGridAdjust(uint64_t *r,uintptr_t pc){
    uintptr_t base=(uintptr_t)_dyld_get_image_header(0);uint32_t off=(uint32_t)(pc-base);
    size_t lo=0,hi=sizeof(gridSites)/sizeof(gridSites[0]);
    while(lo<hi){size_t mid=(lo+hi)/2;if(gridSites[mid].site<off)lo=mid+1;else hi=mid;}
    if(lo>=sizeof(gridSites)/sizeof(gridSites[0])||gridSites[lo].site!=off)return;
    AGGridSite s=gridSites[lo];uint8_t *canvas=*(uint8_t **)(base+AGNotesMaps[s.variant].canvas);Grid g=dimensions(canvas);
    if(s.metric==GM_LAYOUT){layout(base,s.variant,s.kind,(uint8_t *)r[1],g,canvas?*(int *)(canvas+0x130):432);return;}
    uint32_t value=(uint32_t)metric(g,s.metric),word=s.word;int rd=word&31,rn=(word>>5)&31;
    if((word&0xffc00000)==0xb9000000){*(uint32_t *)(r[rn]+((word>>10)&4095)*4)=value;return;}
    if((word&0x7f000000)==0x11000000)value=(uint32_t)r[rn]+value;
    else if((word&0x7f000000)==0x51000000)value=(uint32_t)r[rn]-value;
    r[rd]=value;
}

