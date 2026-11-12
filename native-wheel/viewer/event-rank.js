'use strict';
const RankReader=typeof ArmyReader==='undefined'?require('./protocol.js').ArmyReader:ArmyReader;

function readEventRank(bytes){
    const reader=new RankReader(bytes);
    if(reader.u8()!==3)throw Error('Gói tin BXH Sự kiện');
    const page=reader.u8(), heading=reader.utf(), rows=[];
    if(page>9)throw Error('Trang BXH Sự kiện không hợp lệ');
    while(reader.pos<bytes.length){
        if(rows.length===10)throw Error('Trang BXH có quá nhiều người chơi');
        const id=reader.i32(),name=reader.utf(),hero=reader.u8();
        reader.i16(); // clan
        const level=reader.view.getBigInt64(reader.take(8)).toString();
        const percent=reader.u8(),rank=reader.u8();
        reader.take(10); // five equipment IDs
        const score=reader.utf();
        if(id<=0||hero>9||rank!==page*10+rows.length+1||!/^\d+$/.test(score))throw Error('Dữ liệu BXH Sự kiện không hợp lệ');
        rows.push({id,name,hero,level,percent,rank,score});
    }
    return {page,heading,rows};
}
if(typeof module!=='undefined')module.exports={readEventRank};
