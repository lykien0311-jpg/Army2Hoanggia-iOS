#include "RoomNames.h"
#include <string.h>
int AGRoomParse(const uint8_t *data,size_t length,AGRoomNames *out) {
    if(!data||!out||length<1||length>65535)return 0;
    memset(out,0,sizeof *out);size_t p=1;unsigned count=data[0];
    for(unsigned i=0;i<count;i++){
        if(length-p<3)return 0;
        unsigned id=data[p++];size_t n=((size_t)data[p]<<8)|data[p+1];p+=2;
        if(id==255||out->present[id]||n>length-p||length-p-n<1)return 0;
        size_t end=p+n;unsigned units=0;
        while(p<end){
            unsigned a=data[p++],u;
            if(a>0&&a<128)u=a;
            else if((a&0xe0)==0xc0){
                if(p>=end||(data[p]&0xc0)!=0x80)return 0;
                u=((a&31)<<6)|(data[p++]&63);if(u<128&&u!=0)return 0;
            }else if((a&0xf0)==0xe0){
                if(end-p<2||(data[p]&0xc0)!=0x80||(data[p+1]&0xc0)!=0x80)return 0;
                u=((a&15)<<12)|((data[p]&63)<<6)|(data[p+1]&63);p+=2;if(u<2048)return 0;
            }else return 0;
            if(units>=AG_ROOM_CHARS)return 0;
            out->text[id][units++]=(uint16_t)u;
        }
        // RoomRoutes56 / current JAR: unsigned actual room ID, UTF, marker -1.
        // Other protocol revisions go through the game's existing handler.
        if(data[p++]!=255)return 0;
        out->present[id]=1;out->length[id]=(uint16_t)units;
    }
    return p==length;
}
int AGRoomApply(void *screen,const AGRoomNames *names,AGMakeString make,AGReleaseString release,void *context) {
    if(!screen||!names||!make||!release)return 0;
    uint8_t *vector=*(uint8_t **)((uint8_t *)screen+0x48);if(!vector)return 0;
    uint8_t *array=*(uint8_t **)(vector+0x18);if(!array)return 0;
    int32_t count=*(int32_t *)(vector+0x24),capacity=*(int32_t *)(array+0x10);
    if(count<0||capacity<0||count>capacity||count>4096)return 0;
    int changed=0;
    for(int32_t i=0;i<count;i++){
        uint8_t *room=*(uint8_t **)(array+0x18+(size_t)i*8);if(!room)continue;
        unsigned id=room[0x18];if(id==255)continue;
        // The legacy renderer compares the empty-string constant by identity,
        // not by length. A freshly allocated empty String would render a blank
        // row. NULL explicitly selects its built-in "Phòng <id>" fallback.
        int custom=names->present[id]&&names->length[id]>0;
        void *title=custom?make(context,names->text[id],names->length[id]):NULL;
        if(custom&&!title)return -1;
        *(void **)(room+0x10)=title;changed++;
        if(title)release(context,title);
    }
    return changed;
}
