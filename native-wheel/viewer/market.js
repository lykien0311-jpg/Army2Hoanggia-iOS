'use strict';
const MarketReader = typeof ArmyReader !== 'undefined' ? ArmyReader : require('./protocol.js').ArmyReader;

class ArmyWriter {
    constructor() { this.bytes=[]; }
    byte(v) { this.bytes.push(v & 255); return this; }
    short(v) { return this.byte(v>>>8).byte(v); }
    int(v) { return this.short(v>>>16).short(v); }
    long(v) {
        if(!Number.isSafeInteger(v)||v<0)throw Error('Số tiền không hợp lệ');
        return this.int(Math.floor(v/4294967296)).int(v%4294967296);
    }
    utf(s) {
        const raw=[];
        for(let i=0;i<s.length;i++) {
            const c=s.charCodeAt(i);
            if(c>0&&c<128)raw.push(c);
            else if(c<2048)raw.push(192|(c>>6),128|(c&63));
            else raw.push(224|(c>>12),128|((c>>6)&63),128|(c&63));
        }
        if(raw.length>65535)throw Error('Chuỗi quá dài');
        this.short(raw.length);
        for(const b of raw)this.byte(b);
        return this;
    }
}
function marketItem(r) {
    const key=r.utf(),name=r.utf(),category=r.utf(),nv=r.i8(),quantity=r.i32();
    const high=r.i32(),low=r.view.getUint32(r.take(4)),price=high*4294967296+low;
    if(price<0||!Number.isSafeInteger(price)||quantity<1)throw Error('Số lượng hoặc giá không hợp lệ');
    const seller=r.utf(),description=r.utf(),size=r.u16(),start=r.take(size);
    const icon=r.bytes.slice(start,start+size);
    return {key,name,category,nv,quantity,price,seller,detail:description.split('\u001e')[0],icon};
}
class ArmyMarket {
    constructor(){this.list=[];this.stock=[];this.token='';this.staging=null;this.pending=false;}
    browse(page=0,character=-1,own=false){
        if(!Number.isInteger(page)||page<0||page>1000000||!Number.isInteger(character)||character< -1||character>9)
            throw Error('Trang hoặc nhân vật không hợp lệ');
        return new ArmyWriter().byte(0).int(page).byte(character).byte(own?1:0).bytes;
    }
    inventory(){return [1];}
    post(key,price,quantity,password) {
        const item=this.stock.find(x=>x.key===key);
        if(this.pending||!this.token||!item)throw Error('Hãy tải lại rương gian hàng');
        if(!Number.isSafeInteger(price)||price<1||price>999000000000)throw Error('Giá xu không hợp lệ');
        if(!Number.isSafeInteger(quantity)||quantity<1||quantity>item.quantity)throw Error('Số lượng không hợp lệ');
        if(!password||password.length>40)throw Error('Nhập mật khẩu cấp 2');
        const message=new ArmyWriter().byte(2).utf(this.token).byte(1).utf(key).long(price).int(quantity).utf(password);
        this.pending=true;
        return message.bytes;
    }
    takeLot(key,withdraw) {
        if(this.pending||!this.list.some(x=>x.key===key)||!/^[0-9a-f-]{36}$/.test(key)||this.own!==withdraw)
            throw Error('Hãy cập nhật danh sách gian hàng');
        this.pending=true;
        return new ArmyWriter().byte(withdraw?4:3).utf(key).bytes;
    }
    receive(bytes) {
        const r=new MarketReader(bytes),op=r.u8();
        if(op===0){
            const page=r.i32(),character=r.i8(),own=!!r.u8(),more=!!r.u8(),count=r.u16();
            if(count>10)throw Error('Danh sách gian hàng quá dài');
            const list=Array.from({length:count},()=>marketItem(r));r.end();
            Object.assign(this,{page,character,own,more,list});
            return 'browse';
        }
        if(op===1||op===5){
            const token=r.utf(),continued=!!r.u8(),count=r.u16();
            if(op===1){this.staging={token,items:[]};this.token='';this.stock=[];}
            if(!this.staging||this.staging.token!==token)throw Error('Rương gian hàng đã đổi');
            const chunk=Array.from({length:count},()=>marketItem(r));r.end();
            this.staging.items.push(...chunk);
            if(continued)return 'inventory-part';
            this.stock=this.staging.items;this.token=token;this.staging=null;
            return 'inventory';
        }
        if(op===3){
            const success=!!r.u8(),notice=r.utf();r.end();this.pending=false;
            if(success)this.token='';
            this.lastReply={success,notice};return 'reply';
        }
        throw Error('Phản hồi gian hàng chưa hỗ trợ');
    }
}
if(typeof module!=='undefined')module.exports={ArmyWriter,ArmyMarket};
