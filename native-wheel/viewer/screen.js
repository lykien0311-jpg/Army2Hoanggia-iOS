'use strict';
const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('2d');
const state = document.getElementById('state');
const tiles = [], queue = [];
let shot = null, failed = false, lastTime = 0, liveReported = false;
const game = new ArmySpectator(tile => {
    const image = new Image();
    const url = URL.createObjectURL(new Blob([tile.bytes], {type:'image/png'}));
    const entry = {image,x:tile.x,y:tile.y,ready:false};
    tiles.push(entry);
    image.onload = () => { URL.revokeObjectURL(url); entry.ready = true; reportLive(); };
    image.onerror = () => { URL.revokeObjectURL(url); fail('Không đọc được ảnh bản đồ.'); };
    image.src = url;
});
function reportLive() {
    if (failed || liveReported || game.phase !== 'live' || tiles.some(tile => !tile.ready)) return;
    liveReported = true;
    window.webkit.messageHandlers.viewer.postMessage('live');
}
function fail(message) {
    if (failed) return;
    failed = true;
    queue.length = 0;
    state.textContent = message;
    window.webkit.messageHandlers.viewer.postMessage('failed');
}
function apply(frame) {
    const bin = atob(frame[1]), bytes = new Uint8Array(bin.length);
    for (let i=0; i<bytes.length; i++) bytes[i] = bin.charCodeAt(i);
    const result = game.receive(frame[0], bytes);
    reportLive();
    return result;
}
function pump() {
    try {
        while (queue.length && !shot && !failed) {
            const next = apply(queue.shift());
            if (next && next.paths.some(p=>p.length)) {
                const samples = Math.max(...next.paths.map(p=>p.length));
                shot = {paths:next.paths,samples,elapsed:0};
            }
        }
    } catch (e) { fail(e.message); }
}
window.receiveArmyFrames = frames => {
    if (frames.length + queue.length > 4096) { fail('Phiên xem bị gián đoạn.'); return; }
    for (const frame of frames) queue.push(frame);
    pump();
};
function paint(time) {
    const delta = lastTime ? Math.max(0,time-lastTime) : 0;
    lastTime = time;
    if (shot) {
        shot.elapsed += delta;
        if (shot.elapsed >= shot.samples*28+150) { shot=null; pump(); }
    }
    const w = Math.max(1,canvas.clientWidth), h = Math.max(1,canvas.clientHeight);
    const d = Math.min(devicePixelRatio || 1,2);
    if (canvas.width !== Math.round(w*d) || canvas.height !== Math.round(h*d)) {
        canvas.width=Math.round(w*d); canvas.height=Math.round(h*d);
    }
    ctx.setTransform(d,0,0,d,0,0);
    ctx.clearRect(0,0,w,h);
    if (game.width && game.height) {
        const zoom=Math.min(w/game.width,h/game.height);
        ctx.translate((w-game.width*zoom)/2,(h-game.height*zoom)/2); ctx.scale(zoom,zoom);
        ctx.imageSmoothingEnabled=false;
        for(const t of tiles) if(t.ready)ctx.drawImage(t.image,t.x,t.y);
        ctx.textAlign='center';
        for(let i=0;i<game.players.length;i++) {
            const a=game.players[i]; if(!a || a.x===undefined || a.hp<=0) continue;
            ctx.fillStyle=i%2?'#9e2228':'#194882';
            ctx.beginPath();ctx.arc(a.x,a.y-5,5,0,2*Math.PI);ctx.fill();
            ctx.font='bold 11px -apple-system,sans-serif';
            ctx.lineWidth=2;ctx.strokeStyle='#152637';ctx.fillStyle='white';
            ctx.strokeText(a.name,a.x,a.y-15);ctx.fillText(a.name,a.x,a.y-15);
            ctx.fillStyle='#283544';ctx.fillRect(a.x-12,a.y-12,24,3);
            ctx.fillStyle='#64de7b';ctx.fillRect(a.x-12,a.y-12,24*Math.min(1,a.hp/Math.max(1,a.max)),3);
        }
        if (shot) for (const path of shot.paths) {
            if(!path.length)continue;
            const sample=Math.floor(shot.elapsed/28);
            const [x,y]=path[Math.min(path.length-1,sample)];
            if(sample>path.length+5)continue;
            ctx.beginPath();ctx.fillStyle=sample>=path.length?'#ffb52b':'#3d331a';
            ctx.arc(x,y,sample>=path.length?6:2,0,2*Math.PI);ctx.fill();
        }
        document.getElementById('room').textContent='Phòng '+game.room+' · Khu '+game.area;
        const current=game.players[game.turn];
        document.getElementById('turn').textContent=current?'Lượt '+current.name:'';
        if(!failed)state.textContent=game.phase==='live'?
            game.players.filter(p=>p&&p.hp!==undefined).map(a=>a.name+' '+a.hp+'/'+a.max+' HP').join('  ·  '):
            'Đang nhận bản đồ '+game.nextTile+'/'+game.tiles;
    }
    if(!failed)requestAnimationFrame(paint);
}
requestAnimationFrame(paint);
window.webkit.messageHandlers.viewer.postMessage('ready');
