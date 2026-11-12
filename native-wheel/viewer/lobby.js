'use strict';
const field = new ArmyBattlefield();
const market = new ArmyMarket();
const main = document.getElementById('body');
const notice = document.getElementById('notice');
let tab = '', waiting = false, timeout;

function el(tag, text, parent=main) {
    const node = document.createElement(tag);
    if(text!==undefined) node.textContent=text;
    parent.appendChild(node);
    return node;
}
function action(parent,title,run) {
    const button=el('button',title,parent);
    button.onclick=()=>{try{run();}catch(error){notice.textContent=error.message;}};
    return button;
}
function title(text){main.textContent='';el('h1',text);}
function controls(){const div=el('div');div.className='buttons';return div;}
function row(){const div=el('section');div.className='row';return div;}
function input(label,type){
    const node=el('input',undefined,el('label',label));
    node.type=type;node.autocomplete='off';
    if(type==='number'){node.min='1';node.step='1';node.inputMode='numeric';}
    return node;
}
function bytes64(bytes){
    return btoa(Array.from(bytes, b=>String.fromCharCode(b)).join(''));
}
function unlock(){clearTimeout(timeout);waiting=false;}
function send(cmd,make) {
    if(waiting)throw Error('Đang chờ phản hồi.');
    const data=make();
    const wire=bytes64(data);
    window.webkit.messageHandlers.lobby.postMessage([cmd,wire]);
    waiting=true;notice.textContent='Đang chờ…';
    timeout=setTimeout(()=>{
        unlock();
        market.pending=false;market.token='';
        notice.textContent='Chưa nhận được kết quả. Hãy tải lại danh sách để kiểm tra.';
    },12000);
}
const board=()=>send(-120,()=>field.request(1));
const browse=(page=0,character=-1,own=false)=>send(-121,()=>market.browse(page,character,own));
const stock=()=>send(-121,()=>market.inventory());
function openTab(name){
    if(waiting)return;
    tab=name;
    if(name==='market')browse();else board();
}
document.getElementById('market').onclick=()=>openTab('market');
document.getElementById('field').onclick=()=>openTab('field');

function marketNav(){
    const div=controls();
    action(div,'Đang bán',()=>browse());action(div,'Rương Gian hàng',stock);action(div,'Đồ đã đăng',()=>browse(0,-1,true));
}
function itemView(item,div) {
    if(item.icon.length){
        const img=el('img',undefined,div);img.alt='';img.src='data:image/png;base64,'+bytes64(item.icon);
    }
    el('strong',item.name,div);
    el('p',item.category+' · Số lượng '+item.quantity,div);
    if(item.detail)el('p',item.detail,div);
}
function listMarket(){
    title(market.own?'Đồ đã đăng':'Gian hàng');marketNav();
    const label=el('label','Lọc theo nhân vật '),filter=el('select',undefined,label);
    const names=['Tất cả','Gunner','Miss 6','Electrician','King Kong','Rocketer','Granos','Chicky','Tarzan','Apache','Magenta'];
    names.forEach((name,i)=>{const option=el('option',name,filter);option.value=String(i-1);});
    filter.value=String(market.character);filter.onchange=()=>{if(!waiting)browse(0,Number(filter.value),market.own);};
    if(!market.list.length)el('p','Chưa có món đang bán.');
    for(const item of market.list){
        const div=row();itemView(item,div);
        el('p','Giá cả lô '+item.price+' xu · '+item.seller,div);
        action(div,market.own?'Rút về rương':'Mua',()=>{
            if(waiting)return;
            title(market.own?'Xác nhận rút':'Xác nhận mua');
            itemView(item,main);el('p','Giá cả lô '+item.price+' xu · '+item.seller);
            action(main,'Xác nhận',()=>send(-121,()=>market.takeLot(item.key,market.own)));
            action(main,'Quay lại',listMarket);
        });
    }
    const div=controls();
    if(market.page>0)action(div,'Trang trước',()=>browse(market.page-1,market.character,market.own));
    if(market.more)action(div,'Trang sau',()=>browse(market.page+1,market.character,market.own));
}
function listStock(){
    title('Rương Gian hàng');marketNav();
    if(!market.stock.length)el('p','Rương chưa có món đủ điều kiện bán.');
    for(const item of market.stock){
        const div=row();itemView(item,div);
        action(div,'Đăng bán',()=>{
            if(waiting)return;
            title('Đăng bán');itemView(item,main);
            const price=input('Giá xu cho cả lô','number');
            const count=input('Số lượng','number');count.value='1';count.max=String(item.quantity);
            const password=input('Mật khẩu cấp 2','password');
            action(main,'Xác nhận đăng bán',()=>{
                send(-121,()=>market.post(item.key,Number(price.value),Number(count.value),password.value));
                password.value='';
            });
            action(main,'Quay lại',listStock);
        });
    }
}
function fieldNav(){
    const div=controls();action(div,'Bảng hạng',board);
    action(div,'Lịch sử',()=>send(-120,()=>field.request(4,null,0)));
    action(div,'Trận đang đấu',()=>send(-120,()=>field.request(5,null,0)));
}
function showField(reply){
    if(reply.type==='board'){
        title('Chiến trường');fieldNav();
        if(field.self)el('p',field.self.name+' · Hạng '+field.self.rank+' · Cấp '+field.self.level);
        for(const target of reply.board){
            const div=row();el('strong','#'+target.rank+' '+target.name,div);el('p','Cấp '+target.level,div);
            action(div,'Chi tiết',()=>send(-120,()=>field.request(2,target)));
            if(target.id!==reply.id)
                action(div,'Thách đấu',()=>send(-120,()=>field.request(3,target)));
        }
    }else if(reply.type==='profile'){
        title(reply.name);fieldNav();el('p',reply.character+' · Cấp '+reply.level+' · Hạng '+reply.rank);
        el('p','Chỉ số '+reply.abilities.join(' / '));
        const pieces=reply.items.concat(reply.display && reply.display.outfit || []);
        pieces.forEach((piece,i)=>{
            if(!piece.name)return;
            const div=row();el('strong',piece.name+' +'+piece.upgrade,div);
            for(const gem of reply.gems[i]||[])el('p',gem.name+' '+gem.detail,div);
        });
    }else if(reply.type==='history'||reply.type==='matches'){
        const live=reply.type==='matches',op=live?5:4;
        title(live?'Trận đang đấu':'Lịch sử Chiến trường');fieldNav();
        if(!reply.rows.length)el('p',live?'Chưa có trận đang đấu.':'Chưa có lịch sử.');
        for(const item of reply.rows){
            const div=row();el('strong',item.title,div);el('p',item.detail,div);
            if(live)action(div,'Xem trận',()=>send(-120,()=>field.request(6,item)));
        }
        if(reply.page>0)action(main,'Trang trước',()=>send(-120,()=>field.request(op,null,reply.page-1)));
        if(reply.more)action(main,'Trang sau',()=>send(-120,()=>field.request(op,null,reply.page+1)));
    }else if(reply.type==='notice'){notice.textContent=reply.text;}
}
window.receiveFrame=(cmd,encoded)=>{
    const bytes=Uint8Array.from(atob(encoded),s=>s.charCodeAt(0));
    try{
        if(cmd===-121 && tab==='market'){
            const result=market.receive(bytes);
            if(result==='inventory-part')return;
            unlock();
            if(result==='reply'){notice.textContent=market.lastReply.notice;return;}
            if(notice.textContent==='Đang chờ…')notice.textContent='';
            if(result==='browse')listMarket();else if(result==='inventory')listStock();
        }else if(cmd===-120 && tab==='field'){
            const reply=field.receive(bytes);
            if(reply.type==='stale')return;
            unlock();notice.textContent='';showField(reply);
        }
    }catch(e){unlock();notice.textContent=e.message;}
};
