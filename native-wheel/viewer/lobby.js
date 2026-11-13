'use strict';
const field=new ArmyBattlefield(),market=new ArmyMarket(),ui=PixelUI;
const names=['Gunner','Miss 6','Electrician','King Kong','Rocketer','Granos','Chicky','Tarzan','Apache','Magenta'];
let tab='',view='board',reply=null,focus=0,scroll=0,waiting=false,timeout,notice='',menuItems=null,menuFocus=0,eventRequest=0,filter=-1,modal=null,editSubmit=null,profileFocus=0,ownId=0,ownRank=0,character=-1,closed=false;
const icons=new Map();
function bytes64(bytes){return btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));}
function status(message){notice=String(message);document.getElementById('status').textContent=notice;}
function unlock(){clearTimeout(timeout);waiting=false;}
function guard(fn){try{fn();}catch(e){status(e.message);}}
function send(cmd,make){if(waiting)throw Error('Đang chờ phản hồi.');const data=make();waiting=true;status('Đang chờ…');window.webkit.messageHandlers.lobby.postMessage([cmd,bytes64(data)]);timeout=setTimeout(()=>{unlock();market.pending=false;market.token='';status('Chưa nhận kết quả. Bấm cập nhật để kiểm tra.');},12000);}
function close(){
    if(editSubmit){hideEdit();return;}
    if(modal){modal=null;return;}
    if(menuItems){menuItems=null;return;}
    if(closed)return;
    closed=true;
    unlock();
    window.webkit.messageHandlers.lobby.postMessage(['close',0]);
}
function reset(name){tab=name;focus=0;scroll=0;menuItems=null;modal=null;reply=null;hideEdit();view=name==='field'?'board':name==='event'?'event':'market';}
function board(){send(-120,()=>field.request(1));}
function browse(page=0,character=filter,own=false){send(-121,()=>market.browse(page,character,own));}
function stock(){send(-121,()=>market.inventory());}
function eventRank(page=0){send(-14,()=>[3,page]);eventRequest=page;}
function openTab(name,selected=-1,serial=0){
    if(tab||closed)return;
    reset(name);
    character=selected;
    if(name==='field'){field.serial=serial;board();}
    else if(name==='event')eventRank();
    else browse();
}
function profile(){const r=field.board[focus];if(r)send(-120,()=>field.request(2,r));}
function challenge(){
    if(waiting)return;
    if(!ownRank){board();return;}
    const row=field.board[focus];
    if(!row||row.id===ownId||(row.rank>=ownRank&&!(ownRank===1&&row.rank<=3))){
        status('Hạng này không thể thách đấu.');
        return;
    }
    modal={title:'Thách đấu hạng #'+row.rank+'?',lines:[row.name],yes:'Có',no:'Không',confirm:()=>{
        modal=null;
        send(-120,()=>field.request(3,row));
    }};
}
function menu(items){menuItems=items.map(([label,fn])=>[label,()=>{menuItems=null;guard(fn);}]);menuFocus=0;}
function fieldMenu(){menu([['Thông tin',profile],['Trận đấu',()=>send(-120,()=>field.request(5,null,0))],['Lịch sử',()=>send(-120,()=>field.request(4,null,0))],['Cập nhật',board]]);}
function filterMenu(){menu([['Tất cả',()=>applyFilter(-1)],...names.map((n,i)=>[n,()=>applyFilter(i)])]);}
function applyFilter(n){filter=n;focus=scroll=0;if(view==='stock')return;browse(0,filter,market.own);}
function marketMenu(){menu([['Lọc',filterMenu],['Gian hàng',()=>browse()],['Rương gian hàng',stock],['Đồ của tôi',()=>browse(0,filter,true)]]);}
function hideEdit(){const e=document.getElementById('edit');for(const n of e.querySelectorAll('input'))n.value='';e.replaceChildren();e.style.display='none';editSubmit=null;}
function edit(title,[field],submit){
    hideEdit();
    const form=document.getElementById('edit');
    const heading=document.createElement('label');
    heading.textContent=title;
    heading.htmlFor='lobby-input';
    form.append(heading);
    if(field.label){
        const detail=document.createElement('div');
        detail.textContent=field.label;
        form.append(detail);
    }
    const input=document.createElement('input');
    input.id='lobby-input';
    input.type=field.type||'text';
    input.autocomplete='off';
    input.inputMode=field.type?'text':'numeric';
    input.maxLength=field.max?String(field.max).length:field.type==='password'?40:120;
    input.value=field.value??'';
    form.append(input);
    const complete=editSubmit=()=>guard(()=>{
        if(waiting)return;
        submit([input.value]);
        if(editSubmit===complete)hideEdit();
    });
    input.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();complete();}
        else if(e.key==='Escape'){e.preventDefault();hideEdit();}
    });
    form.style.display='block';
    if(field.type)input.focus();
}
function marketSelect(){
    if(waiting)return;
    const item=currentItems()[focus];
    if(!item)return;
    const action=view==='stock'?'Bán':market.own?'Rút':'Mua';
    menu([[action,()=>{
        if(view==='stock'){sell(item);return;}
        if(market.own){lotConfirm(item,true);return;}
        if(item.equipment&&character>=0&&names[item.nv]&&character!==item.nv){
            modal={title:'Gian hàng',lines:['Chọn nhân vật '+names[item.nv]+' để mua']};
            return;
        }
        modal={title:'Mua món này?',lines:[item.name,'Số lượng: '+item.quantity],yes:'Mua',no:'Không',confirm:()=>lotConfirm(item,false)};
    }],['Chi tiết',()=>{
        const lines=[item.name,'Số lượng: '+item.quantity,...item.detail.split('; ').filter(s=>s&&s!==item.name)];
        if(view!=='stock')lines.push('Người bán: '+item.seller);
        modal={title:'Chi tiết',lines};
    }]]);
}
function lotConfirm(item,own){
    const lines=[item.name,'Số lượng: '+item.quantity];
    if(!own)lines.push('Giá cả lô: '+item.price+' xu');
    modal={title:own?'Rút đồ về rương?':'Xác nhận mua',lines,highlight:own?null:2,yes:'Có',no:'Không',confirm:()=>{
        modal=null;
        send(-121,()=>market.takeLot(item.key,own));
    }};
}
function sell(item){
    edit('Nhập Số Lượng',[{max:item.quantity,value:'1'}],([qty])=>{
        const count=Number(qty);
        if(!Number.isSafeInteger(count)||count<1||count>item.quantity)throw Error('Số lượng không hợp lệ');
        edit('Giá cả lô (xu)',[{label:item.name+' × '+count,max:999000000000}],([value])=>{
            const price=Number(value);
            if(!Number.isSafeInteger(price)||price<1||price>999000000000)throw Error('Giá xu không hợp lệ');
            edit('Mật khẩu cấp 2',[{type:'password'}],([password])=>send(-121,()=>market.post(item.key,price,count,password)));
        });
    });
}
function messagePlayer(){const person=reply?.rows?.[focus];if(!person)return;edit('Nhắn tin: '+person.name,[{label:'Nội dung',type:'text'}],([text])=>{text=text.trim();if(!text||text.length>120)throw Error('Nhập từ 1 đến 120 ký tự');send(5,()=>new ArmyWriter().int(person.id).utf(text).bytes);});}
window.lobbyMessageSent=()=>{unlock();status('Đã gửi tin nhắn.');};
function currentItems(){
    const items=view==='stock'?market.stock:market.list;
    const now=Date.now();
    return items.filter(i=>(!i.expiresAt||i.expiresAt>now)&&(view!=='stock'||filter===-1||i.nv===filter));
}
function wrap(f,d,n,cols){if(n<=1)return 0;if(Math.abs(d)===1){const first=Math.floor(f/cols)*cols,last=Math.min(n-1,first+cols-1);return d<0?(f===first?last:f-1):(f===last?first:f+1);}const first=f%cols,last=first+Math.floor((n-1-first)/cols)*cols;return d<0?(f===first?last:f-cols):(f===last?first:f+cols);}
function move(delta){if(menuItems){menuFocus=(menuFocus+delta+menuItems.length)%menuItems.length;return;}const n=tab==='field'&&view==='board'?field.board.length:tab==='market'?currentItems().length:reply?.rows?.length||0;if(n)focus=(focus+delta+n)%n;}
const gameKeys={[-22]:-7,[-11]:-7,27:-7,35:-7,82:-7,114:-7,[-21]:-6,76:-6,108:-6,10:-5,13:-5,53:-5,70:-5,102:-5,50:-1,56:-2,52:-3,54:-4};
function fieldBack(){view='board';focus=scroll=0;}
function key(code){
 if(closed||!tab)return;
 if(editSubmit){
    const action=gameKeys[code]??code;
    if(action===-7)hideEdit();
    else if(action===-5)editSubmit();
    return;
 }
 code=gameKeys[code]??code;
 if(modal){if(code===-1){modal.offset=Math.max(0,(modal.offset||0)-1);return;}if(code===-2){modal.offset=Math.min(modal.lines.length-1,(modal.offset||0)+1);return;}if(code===-7)modal=null;else if(code===-5||code===-6)guard(modal.confirm??(()=>{modal=null;}));return;}
 if(menuItems){if(code===-1||code===-3)move(-1);else if(code===-2||code===-4)move(1);else if(code===-5||code===-6)menuItems[menuFocus][1]();else if(code===-7)menuItems=null;return;}
 if(code===-7){if(tab==='field'&&view!=='board')fieldBack();else close();return;}
 if(code===-6){if(tab==='market')marketMenu();else if(tab==='event')guard(()=>eventRank(eventRequest));else if(view==='board'||view==='profile')fieldMenu();else refreshFieldList();return;}
 if(tab==='field'&&view==='profile'){if([-1,-2,-3,-4].includes(code)){const n=reply.items.length+(reply.display?.outfit?1:0);profileFocus=(profileFocus+(code===-1?-2:code===-2?2:code===-3?-1:1)+n)%n;return;}if(code===-5||code===13){profileDetails();return;}}
 if(code===-5||code===13){guard(()=>tab==='market'?marketSelect():tab==='field'?(view==='board'?challenge():view==='matches'?watch():profile()):messagePlayer());return;}
 if(tab==='market'){
    if(code===49){guard(()=>browse());return;}
    if(code===51){guard(stock);return;}
    if(code===55){guard(()=>browse(0,filter,true));return;}
    const items=currentItems(),d=code===-1?-7:code===-2?7:code===-3?-1:code===-4?1:0;
    if(!d||waiting)return;
    if(view!=='stock'&&((d===1&&focus===items.length-1&&market.more)||(d===-1&&focus===0&&market.page>0))){page(d);return;}
    focus=wrap(focus,d,items.length,7);
    return;
 }
 if(code===-1)move(-1);else if(code===-2)move(1);else if(code===-3||code===-4)page(code===-3?-1:1);
}
function page(delta){guard(()=>{if(tab==='event'){const p=eventRequest+delta;if(p>=0&&p<=9)eventRank(p);}else if(tab==='market'&&view==='market'){const p=market.page+delta;if(p>=0&&(delta<0||market.more))browse(p,filter,market.own);}else if(tab==='field'&&(view==='matches'||view==='history')){const p=reply.page+delta;if(p>=0&&(delta<0||reply.more))send(-120,()=>field.request(view==='matches'?5:4,null,p));}});}
function refreshFieldList(){guard(()=>send(-120,()=>field.request(view==='matches'?5:4,null,reply?.page??0)));}
function watch(){
    const row=reply?.rows[focus];
    if(!row||waiting)return;
    modal={title:'Vào xem trận đấu?',lines:[row.title],yes:'Có',no:'Không',confirm:()=>{
        modal=null;
        send(-120,()=>field.request(6,row));
    }};
}
function row(r,y,selected,top=false){ui.rect(1,y,318,35,selected?'#ffe277':top?'#254c6d':'#d4e3ee');ui.rect(2,y+34,316,1,'#81b5d3');ui.avatar(r,21,y+32);const white=top&&!selected;ui.text(r.name,41,y+2,{max:205,color:white?'#fff':'#1c3b4e',shadow:white});ui.text('Lv '+r.level+' '+(r.percent??0)+'%',41,y+13,{max:205,scale:.8,color:white?'#fff':'#1c3b4e',shadow:white});const prize=r.rank===1?'20tr xu + 2.000 lượng/ngày':r.rank===2?'15tr xu + 1.500 lượng/ngày':r.rank===3?'10tr xu + 1.000 lượng/ngày':'';if(prize)ui.text(prize,41,y+23,{max:205,scale:.78,color:white?'#fff':'#1c3b4e',shadow:white});ui.rank(r.rank,317,y+3,28);}
function drawField(){ui.heading(view==='board'?'Chiến trường':view==='profile'?'Trang bị':view==='matches'?'Trận đấu':'Lịch sử');
 if(view==='board'){
  ui.rect(0,53,320,16,'#1478ad');ui.text('Tên',8,55,{color:'#ffe270',scale:.75});ui.text('Hạng',314,55,{color:'#ffe270',align:'right',scale:.75});
  const boardRows=field.board,top=boardRows.filter(r=>r.rank<=3),rest=boardRows.filter(r=>r.rank>3);top.forEach((r,i)=>{const y=72+i*37,index=boardRows.indexOf(r);row(r,y,focus===index,true);ui.zone(0,y,320,36,()=>{focus=index;});});
  const start=top.length?215:72,bottom=ui.height-64,capacity=Math.max(1,Math.floor((bottom-start)/37)),index=rest.indexOf(boardRows[focus]);if(index>=0){if(index<scroll)scroll=index;if(index>=scroll+capacity)scroll=index-capacity+1;}if(top.length)ui.text('...',160,190,{align:'center',scale:.8});
  rest.slice(scroll,scroll+capacity).forEach((r,i)=>{const y=start+i*37,index=boardRows.indexOf(r);row(r,y,focus===index);ui.zone(0,y,320,36,()=>{focus=index;});});
  if(!boardRows.length&&!waiting)ui.text('Chưa có người chơi.',160,95,{align:'center'});
  if(field.self){const self=field.self,y=ui.height-62;ui.rect(0,y,320,38,'#9be0ef');ui.avatar(self,21,y+34);ui.text(self.name,42,y+2,{max:190});ui.text('Lv '+self.level+' '+self.percent+'%',42,y+15,{scale:.85,max:190});ui.rank(self.rank,316,y+3,28);}
  ui.footer('Menu','Thách đấu','Đóng',fieldMenu,()=>guard(challenge),close);
 }else if(view==='profile'&&reply){drawProfile();ui.footer('Menu','Chọn','Đóng',fieldMenu,profileDetails,fieldBack);}
 else{
    const rows=reply?.rows||[],height=28,capacity=Math.max(1,Math.floor((ui.height-81)/height));
    ui.frameBox(5,22,310,ui.height-53);
    ui.text(view==='matches'?'Trận đấu':'Lịch sử',160,27,{align:'center',title:true});
    if(focus<scroll)scroll=focus;
    if(focus>=scroll+capacity)scroll=focus-capacity+1;
    rows.slice(scroll,scroll+capacity).forEach((r,i)=>{
        const y=48+i*height;
        ui.rect(9,y,302,height-1,i+scroll===focus?'#ffdf4e':i%2?'#ced9ec':'#d7e3f1');
        ui.text(r.title,12,y+1,{max:295});ui.text(r.detail,12,y+14,{max:295});
        const index=i+scroll;
        ui.zone(9,y,302,height,()=>{focus=index;});
    });
    if(!rows.length&&!waiting)ui.text(view==='matches'?'Chưa có trận đang diễn ra':'Chưa có lịch sử.',160,48,{align:'center'});
    ui.footer('Cập nhật',view==='matches'?'Xem':'','Đóng',refreshFieldList,()=>guard(watch),fieldBack);
 }
}
function profileDetails(){const r=reply,p=r.items.concat(r.display?.outfit||[])[profileFocus],d=r.details?.[profileFocus];if(!p)return;const lines=[p.name+' +'+p.upgrade];if(d){lines.push('Chỉ số: '+d.flat.join(' / '),'Phần trăm: '+d.percent.join(' / '),'Hạn: '+d.days+' ngày · '+d.slots+' ô ngọc');}for(const gem of r.gems?.[profileFocus]||[])lines.push(gem.name,gem.detail);modal={title:'Thông tin trang bị',lines};}
function drawProfile(){const r=reply,gear=r.items.concat(r.display?.outfit||[]),x=68,y=Math.max(30,Math.floor((ui.height-24-170)/2));
 ui.rect(x,y,184,170,'#304860');ui.rect(x+2,y+2,180,166,'#c5d5ef');ui.rect(x+3,y+2,178,15,'#244866');for(let n=0;n<178;n+=24){ui.g.fillStyle='#ffdc54';ui.g.beginPath();ui.g.moveTo(x+3+n,y+2);ui.g.lineTo(x+15+n,y+2);ui.g.lineTo(x+7+n,y+17);ui.g.lineTo(x-5+n,y+17);ui.g.fill();}ui.rect(x+61,y+2,62,15,'#c5d5ef');ui.text('Trang bị',x+92,y+3,{align:'center',max:60});
 ui.avatar({...r.avatar,aura:r.display?.aura??0},x+40,y+71);const sx=[40,15,65,55,25],sy=[33,55,55,83,83];for(let i=0;i<5;i++){if(gear[i])ui.gear(r.avatar.character,i,gear[i].id,x+sx[i],y+sy[i],gear[i].upgrade);ui.zone(x+sx[i]-10,y+sy[i]-10,20,20,()=>{profileFocus=i;});}
 ui.rect(x+6,y+96,72,67,'#3d6d9d');const start=Math.floor(profileFocus/4)*4;for(let i=0;i<4&&start+i<gear.length;i++){const slot=start+i,gx=x+27+i%2*30,gy=y+115+Math.floor(i/2)*30;ui.gear(r.avatar.character,slot,gear[slot].id,gx,gy,gear[slot].upgrade);if(slot===profileFocus){ui.g.strokeStyle='#ffd34e';ui.g.strokeRect(gx-9,gy-9,18,18);}ui.zone(gx-10,gy-10,20,20,()=>{if(profileFocus===slot)profileDetails();else profileFocus=slot;});}
 ui.text(start===0?'>':'<',x+71,y+151,{align:'center',color:'#ffff30'});ui.zone(x+65,y+150,13,13,()=>{profileFocus=start===0?4:0;});ui.text('Level: '+r.level,x+88,y+22,{max:66,scale:.85});ui.text((r.display?.percent??0)+'%',x+177,y+22,{align:'right',max:24,scale:.85});
 for(let i=0;i<5;i++){const yy=y+38+18*i;ui.statsIcon(i,x+83,yy);ui.rect(x+101,yy,35,16,'#24486d');ui.rect(x+138,yy,18,16,'#24486d');ui.rect(x+158,yy,19,16,'#24486d');ui.text(r.abilities[i]??0,x+119,yy+1,{align:'center',max:34,color:'#ffff30',scale:.8});ui.text('0',x+147,yy+1,{align:'center',color:'#ffff30'});ui.text('0',x+168,yy+1,{align:'center',color:'#ffff30'});}
 ui.rect(x+83,y+130,95,16,'#17313e');ui.rect(x+83,y+148,95,16,'#17313e');ui.text(r.display?r.display.xu+'xu-'+r.display.luong+'lg':'--',x+84,y+131,{max:93,color:'#ffff30',scale:.8});ui.text(gear[profileFocus]?.name||'',x+84,y+149,{max:93,color:'#00bc28',scale:.8});
}
function itemImage(item,x,y,side){if(item.icon.length&&!icons.has(item.key)){const im=new Image();im.src='data:image/png;base64,'+bytes64(item.icon);icons.set(item.key,im);}const im=icons.get(item.key);if(im?.complete&&im.naturalWidth){const size=Math.min(15,side-8),scale=Math.min(size/im.width,size/im.height);ui.g.drawImage(im,Math.round(x+(side-im.width*scale)/2),Math.round(y+(side-im.height*scale)/2),im.width*scale,im.height*scale);}else ui.text(item.name,x+side/2,y+10,{align:'center',max:side-4});
 const up=item.enhancement||0;if(up){const rgb=up<=4?'#164dff':up<=8?'#00b300':up<=11?'#ff7f00':up<=14?'#ce00ff':'#ff0019';ui.text('+'+up,x+2,y+1,{color:rgb,scale:.75,shadow:true});if(up>=12){for(let i=0;i<4;i++){const a=ui.frame*.15+i*Math.PI/2,xx=x+side/2+Math.cos(a)*(side/2-3),yy=y+side/2+Math.sin(a)*(side/2-3);ui.rect(xx-2,yy,5,1,rgb);ui.rect(xx,yy-2,1,5,'#fff');}}}if(item.quantity>1)ui.text(item.quantity,x+side-2,y+side-10,{align:'right',color:'#fff27a',shadow:true,max:side-4,scale:.65});}
function drawMarket(){
    ui.panel(view==='stock'?'Rương gian hàng':market.own?'Đồ của tôi':'Gian hàng');
    const items=currentItems(),cell=41,capacity=Math.max(1,Math.floor((ui.height-124)/cell));
    focus=Math.max(0,Math.min(items.length-1,focus));
    const selectedRow=Math.floor(focus/7);
    if(selectedRow<scroll)scroll=selectedRow;
    if(selectedRow>=scroll+capacity)scroll=selectedRow-capacity+1;
    items.slice(scroll*7,(scroll+capacity)*7).forEach((item,i)=>{
        const x=17+i%7*cell,y=58+Math.floor(i/7)*cell,index=scroll*7+i;
        if(index===focus)ui.rect(x,y,cell-2,cell-2,'#ffde4d');
        itemImage(item,x,y,cell-2);
        ui.zone(x,y,cell,cell,()=>{if(focus===index)guard(marketSelect);else focus=index;});
    });
    if(!items.length&&!waiting)ui.text('Chưa có vật phẩm.',160,67,{align:'center'});
    if(filter!==-1)ui.text(names[filter],300,ui.height-41,{align:'right',max:85});
    const item=items[focus];
    if(item){
        ui.text(item.name,160,ui.height-56,{align:'center',max:285});
        if(view!=='stock')ui.text(item.price+' xu · '+item.seller,160,ui.height-43,{align:'center',max:285});
    }
    ui.footer('Menu','Chọn','Trở ra',marketMenu,()=>guard(marketSelect),close);
}
function drawEvent(){
    ui.text('BXH Sự kiện',160,25,{align:'center',title:true});
    ui.rect(0,41,320,14,'#1478ad');
    ui.text('Tên',8,41,{color:'#ffe270'});
    ui.text(reply?.heading||'BXH Sự kiện',312,41,{align:'right',color:'#ffe270',max:220});
    const rows=reply?.rows||[],height=30,capacity=Math.max(1,Math.floor((ui.height-86)/height));
    if(focus<scroll)scroll=focus;
    if(focus>=scroll+capacity)scroll=focus-capacity+1;
    rows.slice(scroll,scroll+capacity).forEach((r,i)=>{
        const y=56+i*height,index=i+scroll;
        if(index===focus)ui.rect(1,y,318,height-1,'#ffdf48');
        ui.avatar(r,18,y+height-1);
        ui.text(r.name,34,y+1,{max:205});
        ui.text('Lv '+r.level+' '+r.percent+'%',34,y+14,{max:205});
        ui.text(BigInt(r.score).toLocaleString('vi-VN'),313,y+9,{align:'right',max:78});
        ui.zone(1,y,318,height,()=>{focus=index;});
    });
    ui.footer('Cập nhật','Nhắn tin','Đóng',()=>guard(()=>eventRank(eventRequest)),()=>guard(messagePlayer),close);
}
function paint(){
    if(!tab||closed)return;
    if(tab==='field')drawField();else if(tab==='market')drawMarket();else drawEvent();
    if(notice&&!modal&&!editSubmit){
        ui.rect(5,ui.height-82,310,18,'#c7d5ed');
        ui.text(notice,160,ui.height-81,{align:'center',max:304});
    }
    if(editSubmit){
        ui.zone(0,0,320,ui.height,()=>{});
        ui.footer('Đóng','OK','Xoá',hideEdit,()=>editSubmit?.(),()=>{
            const input=document.getElementById('lobby-input');
            input.value=input.value.slice(0,-1);
        });
    }else if(menuItems){
        ui.zone(0,0,320,ui.height,()=>{menuItems=null;});
        ui.footer('Chọn','','Không',()=>menuItems?.[menuFocus][1](),null,()=>{menuItems=null;});
        ui.menu(menuItems,menuFocus);
    }else if(modal){
        ui.zone(0,0,320,ui.height,()=>{});
        const cap=Math.max(1,Math.floor((ui.height-90)/15)),start=modal.offset||0;
        const lines=modal.lines.slice(start,start+cap),h=38+lines.length*15,y=(ui.height-h)/2;
        ui.frameBox(24,y,272,h);
        ui.text(modal.title,160,y+8,{align:'center',max:256});
        lines.forEach((line,i)=>{
            if(modal.highlight===start+i)ui.rect(29,y+24+i*15,262,15,'#ffdf4e');
            ui.text(line,160,y+25+i*15,{align:'center',max:256});
        });
        const confirm=()=>guard(modal.confirm??(()=>{modal=null;}));
        const cancel=()=>{modal=null;};
        ui.footer(modal.yes||'',modal.yes?'':'OK',modal.no||'',modal.yes?confirm:null,modal.yes?null:confirm,cancel);
    }
}
window.receiveFrame=(cmd,encoded,auras=[])=>{
    if(closed)return;
    const bytes=Uint8Array.from(atob(encoded),s=>s.charCodeAt(0));
    try{
        if(cmd===-121&&tab==='market'){
            const result=market.receive(bytes);
            if(result==='inventory-part')return;
            unlock();status('');
            if(result==='reply'){
                modal={title:'Gian hàng',lines:[market.lastReply.notice]};
                return;
            }
            view=result==='inventory'?'stock':'market';
            focus=scroll=0;icons.clear();
        }else if(cmd===-14&&tab==='event'){
            const r=readEventRank(bytes);
            unlock();status('');
            if(r.page!==eventRequest){
                eventRequest=reply?.page??r.page;
                if(reply)return;
            }
            r.rows.forEach((p,i)=>p.aura=auras[i]||0);
            reply=r;focus=scroll=0;
        }else if(cmd===-120&&tab==='field'){
            const r=field.receive(bytes);
            if(r.type==='stale')return;
            unlock();status('');
            if(r.type==='notice'){status(r.text);return;}
            if(['board','profile','matches','history'].includes(r.type)){
                reply=r;
                if(r.type==='board'){ownId=r.id;ownRank=r.rank;}
                view=r.type;focus=scroll=profileFocus=0;
            }
        }
    }catch(e){unlock();market.pending=false;status(e.message);}
};
window.lobbyKey=key;
addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;const code={ArrowUp:-1,ArrowDown:-2,ArrowLeft:-3,ArrowRight:-4,Enter:-5,Escape:-7,F1:-6,F2:-7}[e.key];if(code){e.preventDefault();guard(()=>key(code));}});
ui.start(paint);
