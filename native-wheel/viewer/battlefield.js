'use strict';
const FieldReader=typeof ArmyReader!=='undefined'?ArmyReader:require('./protocol.js').ArmyReader;
const FieldWriter=typeof ArmyWriter!=='undefined'?ArmyWriter:require('./market.js').ArmyWriter;
const fieldMagic=1129591862;
function ints(r){const n=r.u8();if(n>64)throw Error('Bảng chỉ số quá dài');return Array.from({length:n},()=>r.i32());}
function gear(r){return {id:r.i16(),name:r.utf(),upgrade:r.u8(),tier:r.u8(),gems:ints(r)};}
function look(r){return {character:r.u8(),parts:Array.from({length:5},()=>r.i16())};}
function rankedLook(r){return {...look(r),percent:r.i8(),aura:r.i32()};}
function readWallet(r){
    const n=r.i32()*4294967296+r.view.getUint32(r.take(4));
    if(!Number.isSafeInteger(n))throw Error('Số dư vượt phạm vi hiển thị');return n;
}
class ArmyBattlefield {
    constructor(){this.serial=0;this.pending=0;this.board=[];this.matches=[];this.playback=null;}
    request(op,target,page=0){
        if(![1,2,3,4,5,6].includes(op))throw Error('Thao tác Chiến trường');
        if((op===2||op===3)&&!this.board.some(row=>row.id===target.id&&row.rank===target.rank))throw Error('Hãy cập nhật bảng hạng');
        const serial=this.serial=(this.serial%2147483647)+1;
        const w=new FieldWriter().int(fieldMagic).byte(op).int(serial);
        if(op===1)w.byte(49);
        if(op===2||op===3)w.int(target.rank).int(target.id).byte(op===2?49:47);
        if(op===4||op===5){if(!Number.isInteger(page)||page<0||page>65535)throw Error('Số trang không hợp lệ');w.short(page);}
        if(op===6){
            const match=this.matches.find(row=>row===target);
            if(!match)throw Error('Hãy cập nhật danh sách trận');
            for(const b of match.key)w.byte(b);
        }
        this.pending=serial;return w.bytes;
    }
    playbackFinished(){
        if(!this.playback)return null;
        const w=new FieldWriter().int(fieldMagic).byte(9).int(0);
        for(const b of this.playback)w.byte(b);
        this.playback=null;
        return w.bytes;
    }
    receive(bytes){
        const r=new FieldReader(bytes);
        if(r.i32()!==fieldMagic)throw Error('Phiên bản Chiến trường');
        const op=r.u8(),serial=r.i32();
        if(serial!==0&&serial!==this.pending)return {type:'stale'};
        if(op===7){const text=r.utf();r.end();return {type:'notice',text};}
        if(op===6){r.end();return {type:'enter'};}
        if(op===8){const outcome=r.pos<bytes.length?r.i8():null;r.end();this.playback=null;return {type:'ended',outcome};}
        if(op===9){
            const start=r.take(8);r.end();
            this.playback=r.bytes.slice(start,start+8);
            return {type:'playback'};
        }
        if(op===1){
            const rank=r.i32(),id=r.i32(),n=r.u8(),board=[];
            for(let i=0;i<n;i++)board.push({rank:r.i32(),id:r.i32(),name:r.utf(),level:r.i32()});
            for(const row of board)Object.assign(row,rankedLook(r));
            if(r.pos<bytes.length){
                if(r.i32()!==1397050438)throw Error('Phần mở rộng bảng hạng');
                this.self={rank:r.i32(),id:r.i32(),name:r.utf(),level:r.i32(),...rankedLook(r)};
            }
            r.end();this.board=board;return {type:'board',rank,id,board};
        }
        if(op===2){
            const rank=r.i32(),name=r.utf(),level=r.i32(),character=r.utf(),abilities=ints(r);
            const items=Array.from({length:5},()=>gear(r));
            const avatar=look(r);
            let display=null;
            if(r.u8()){
                display={percent:r.u8(),xu:readWallet(r),luong:readWallet(r),aura:r.i32()};
                if(r.u8())display.outfit=gear(r);
            }
            if(r.i32()!==1145394248||r.u8()!==6)throw Error('Chi tiết trang bị');
            const details=Array.from({length:6},()=>r.u8()?{flat:ints(r),percent:ints(r),days:r.i32(),slots:r.u8()}:null);
            const gems=[];
            if(r.pos<bytes.length){
                if(r.i32()!==1195724105||r.u8()!==6)throw Error('Chi tiết ngọc');
                for(let i=0;i<6;i++)gems.push(Array.from({length:r.u8()},()=>({name:r.utf(),detail:r.utf()})));
            }
            r.end();return {type:'profile',rank,name,level,character,abilities,items,avatar,display,details,gems};
        }
        if(op===4||op===5){
            const page=r.u16(),more=!!r.u8(),n=r.u8(),rows=[];
            for(let i=0;i<n;i++){
                const key=op===5?Array.from(r.bytes.slice(r.pos,r.pos+8)):null;
                if(key)r.take(8);
                rows.push({key,title:r.utf(),detail:r.utf()});
            }
            r.end();if(op===5)this.matches=rows;
            return {type:op===4?'history':'matches',page,more,rows};
        }
        return {type:'other',op};
    }
}
if(typeof module!=='undefined')module.exports={ArmyBattlefield};
