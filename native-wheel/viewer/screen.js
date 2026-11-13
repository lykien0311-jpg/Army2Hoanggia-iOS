'use strict';
// Read-only spectator: native keypad, bitmap fonts, real gear and world camera.
const ui=PixelUI,ctx=ui.g,state=document.getElementById('state');
const tiles=[],queue=[],images=new Map(),numbers=[],explosions=[];
const WORLD_SCALE=320/400,FRAME_MS=30;
let shot=null,failed=false,liveReported=false,lastTime=0,menuOpen=false,menuFocus=0;
let freeCamera=false,cameraX=0,cameraY=0,cameraReady=false,drag=null,clockAt=0,angle=0;
let phase=-1,question='',awaiting=false,showTeam=true,forceMax=false,watchNotice='';
function asset(name){let im=images.get(name);if(!im){im=new Image();im.src='art/'+name+'.png';images.set(name,im);}return im;}
for(const name of ['main-bar','main-no','projectile-dan','projectile-grenade','projectile-cannon','projectile-rocket2','projectile-laser'])asset(name);
const holeNames=['h32x26','smallhole','smallhole','h36x30','rocket','rangehole','hrangcua','hgrenade','h14x12','h55x50'];
const holeMap={0:3,1:1,2:0,3:9,6:6,7:7,9:5,10:4,11:2,12:6,15:7,17:2,18:2,19:2,20:0,21:2,22:7,24:3,25:8,27:1,30:0,31:7,32:3,35:3,37:7,40:2,41:2,42:7,43:7,44:2,45:7,47:8,48:3,52:3,57:7};
// Original game mask PNGs. Use data URLs so WKWebView can read their pixels
// from a file-backed bundle without a cross-origin canvas restriction.
const maskImages=[
 ['h32x26','iVBORw0KGgoAAAANSUhEUgAAACAAAAAaCAMAAADhRa4NAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURQAAAP8AAP///2cZZB4AAAADdFJOU///ANfKDUEAAABfSURBVHja1JMxDgAhCAQH///oi2JUjLi2t6UzjbBQlljP+sYOd4nAaQkGAxMyFM58GjjnEDdIeTfIuRtVgNwo2F0wbrwafxHEN+Wg9KjlsvS6dWF05XRpH2qfHs4nwAB4VwIRfCtHIgAAAABJRU5ErkJggg=='],
 ['smallhole','iVBORw0KGgoAAAANSUhEUgAAABYAAAAVCAMAAAB1/u6nAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURQAAAP8AAP///2cZZB4AAAADdFJOU///ANfKDUEAAABPSURBVHjatNE5FgAgCEPBj/c/tIq4PCWl6RwaDJSIeeaLE/eAhbSsAaFEwnHliDu3Du8MtxcsY+PV7p853UTsrX4pOlENqr7Vdd5bVgEGADskAU1yMKs0AAAAAElFTkSuQmCC'],
 ['h36x30','iVBORw0KGgoAAAANSUhEUgAAACQAAAAeCAMAAABzP0xhAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURQAAAP8AAP///2cZZB4AAAADdFJOU///ANfKDUEAAABwSURBVHja1NRBCsAgDETRH+9/6KKxoqbG2XaW8kCIGSlLrGc9JYII2QgtG2MiLJkYwxAyFN3wma7IzKscwVk5shxZRalxRclNuxC7I+NmqvozEkYgDVN7FumBtVXRlk5aX60IWqW0coo1zz6MR4ABAKzVAp0MmsLsAAAAAElFTkSuQmCC'],
 ['rocket','iVBORw0KGgoAAAANSUhEUgAAABkAAAAhCAMAAAAbHvCRAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURQAAAP8AAP///2cZZB4AAAADdFJOU///ANfKDUEAAACZSURBVHjavJNBEsUgCEMT7n/oVgIWqv93pou6wDFPGMUIuwbJskJoAjE3ci5JeOwEQwA0BVEB1xBRJeHJLgIR6eU9n1JzhCR4J5KzUEF4JpvxIbEtOhvzjuzQ6PJfsiJ/syTsTcvXHtcqREaYhPXy3TvlQbvfJul+M+YBx57qUXlOKd29lrfijtg81UKMWP/C71+SqC4OAQYAGFwC3+F/s6QAAAAASUVORK5CYII='],
 ['rangehole','iVBORw0KGgoAAAANSUhEUgAAACAAAAARCAMAAACLgl7OAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURQAAAP8AAP///2cZZB4AAAADdFJOU///ANfKDUEAAABmSURBVHjazJIxAoAwDALP/P/RSkJjHHTqIAslpUMhROEQkocQSFkj8xQyWAJFQ8iBh8CiIXRp+YKfGOLLoW9uMISDY2RlrqjT4XyfnIXhKqOfrIMLxWWPjn1w4USjd+BehgunAAMAaaQBcT4WR5IAAAAASUVORK5CYII='],
 ['hrangcua','iVBORw0KGgoAAAANSUhEUgAAACgAAAAjCAMAAADR57icAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURf8AAAAAAP///8qSw5kAAAADdFJOU///ANfKDUEAAADNSURBVHjanJRJFsQgCEQL7n/ofokixWBih40RfxBkgGbBJVrVmQAmmX4AU0NEhHYJZEJ8JRTGyRD7MM0iDZQCuqYFBXmdJkEOduCKyN7BTQa5D8ZrqcXXc4bfYLgygh7Q/tbkwRHnqTqj3kicmfvPyVOb367uecr4YwrFy9hS+AjObB+A2SKKfwuMZYYYAfs4CneBoL4KGqtwwRb0CqdeaEHvGVXwmeSNd+Fq1waUblIggVNXZ08BeUrlaTaBwinqELUZuR2kRvrC8hNgABXjBPQDIf5eAAAAAElFTkSuQmCC'],
 ['hgrenade','iVBORw0KGgoAAAANSUhEUgAAADcAAAAyCAMAAADPyLPHAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURf8AAAAAAP///8qSw5kAAAADdFJOU///ANfKDUEAAAEGSURBVHjavJZREsMgCER3vf+hO1EkGsEI7ZSfzLR5AVbURXEDV7h/mu8r5oIws6A+Seon3rgLYmNZOdiJV05er0/2TyygkY9T9B9crhWzcDdvc+hBj8OoD6b6fKx3ioXjW4g+Vj4ewEt//+O2QvpcABu5phNPORn1487GZdR8UTLD1SaRwCibknEuhQmYxDKyiC7hddA5C6r5FRevMzOf2l9eTzI3n1kuV2fJbCNZB4TOiWFezo8lOWAQOq5T98N0mUW5XD7+kGv3ZrTO0l2Dr/9kKh6+wAH18rd8iNgkd8dNjsLzL1Nqw6VZ/uwu7KnGzg/enVTQMYXY+U74XhJlF74B/QgwAAKDDBfY5U0XAAAAAElFTkSuQmCC'],
 ['h14x12','iVBORw0KGgoAAAANSUhEUgAAAA4AAAAMCAMAAABlXnzoAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAAlQTFRFAAAA/wAAAAAAZ6dCDAAAAAN0Uk5T//8A18oNQQAAADJJREFUeNpiYGJiYoQCIJMBwQPxGUA8BjAA8RngPDCfAcED8UnlohiFZhG6M1AcCRBgACxMAH18M4R6AAAAAElFTkSuQmCC'],
 ['h55x50','iVBORw0KGgoAAAANSUhEUgAAADcAAAAyCAMAAADPyLPHAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAAJUExURQAAAP////8AAM1et5wAAACsSURBVHja7NZLDsIwDEXRS/a/aAT9JASH2neAGOBxjp6iNra5hdV6xQf4aNaWheKohSRQzBVIrlUomRirmiA59SZJs1dIZ1xXh1TYAE8HSTi6VnCtuzw7IUV2QCqXG65INW4PpBy3BVKO2wKpxz0DtWvKNQR7wL/7Gee++7f/T/2O7LvVfcL2Jd0Hbd/VfV7PFT3H7NzUc1rvBXoP8XuP3rP8Xuf3yOTeehdgAKYlBQ2+B2QRAAAAAElFTkSuQmCC'],
];
const holes=new Map();
for(const [name,png] of maskImages){
 const im=new Image(),entry={image:im};holes.set(name,entry);
 im.onload=()=>{
  try{
   const c=document.createElement('canvas');c.width=im.width;c.height=im.height;
   const g=c.getContext('2d');g.drawImage(im,0,0);
   entry.pixels=g.getImageData(0,0,c.width,c.height).data;
   if(reportLive())pump();
  }catch(e){fail('Không đọc được mặt nạ phá đất.');}
 };
 im.onerror=()=>fail('Không tải được mặt nạ phá đất.');im.src='data:image/png;base64,'+png;
}
function terrainURL(bytes){
 let binary='';
 for(let i=0;i<bytes.length;i+=16384)binary+=String.fromCharCode(...bytes.subarray(i,i+16384));
 return 'data:image/png;base64,'+btoa(binary);
}
const game=new ArmySpectator(tile=>{
 const image=new Image();
 const entry={x:tile.x,y:tile.y,solid:!!tile.solid,ready:false,id:tile.id};tiles.push(entry);
 image.onload=()=>{const c=document.createElement('canvas');c.width=image.width;c.height=image.height;const g=c.getContext('2d',{willReadFrequently:true});g.drawImage(image,0,0);Object.assign(entry,{canvas:c,ctx:g,ready:true});if(reportLive())pump();};
 image.onerror=()=>fail('Không đọc được ảnh bản đồ.');image.src=terrainURL(tile.bytes);
});
game.onHealth=(actor,delta)=>numbers.push({x:actor.x,y:actor.y-38,delta,at:performance.now()});
function post(message){window.webkit.messageHandlers.viewer.postMessage(message);}
function reportLive(){
 if(failed||liveReported||game.phase!=='live'||tiles.some(t=>!t.ready)||[...holes.values()].some(mask=>!mask.pixels))return false;
 liveReported=true;clockAt=performance.now();state.textContent='Đang xem trận';post('live');return true;
}
function fail(message){if(failed)return;failed=true;queue.length=0;state.textContent=message;post('failed');}
function apply(frame){
 const bytes=Uint8Array.from(atob(frame[1]),c=>c.charCodeAt(0));
 if(frame[0]===-102&&bytes[3]===6){setTimeout(()=>post('ended'),550);return;}
 const previousTurn=game.turn,result=game.receive(frame[0],bytes);
 if(frame[0]===24||game.turn!==previousTurn)clockAt=performance.now();
 if(result?.paths){angle=result.angle;const actor=game.players[result.player];if(actor)actor.facing=result.angle>90&&result.angle<270?-1:1;}
 reportLive();return result;
}
function pump(){
 try{
  let count=0;
  while(queue.length&&!shot&&!failed&&(game.phase!=='live'||liveReported)){
   const next=apply(queue.shift());
   if(next?.paths.some(p=>p.length)){
    const impacts=next.impacts.filter(event=>event.sample<next.paths[event.projectile]?.length).sort((a,b)=>a.sample-b.sample);
    shot={...next,impacts,elapsed:0,sample:-1,impactIndex:0,samples:Math.max(...next.paths.map(p=>p.length))};
   }
   if(++count>=256){setTimeout(pump,0);break;}
  }
 }catch(e){fail(e.message);}
}
window.receiveArmyFrames=frames=>{if(failed)return;if(!Array.isArray(frames)||frames.length+queue.length>4096){fail('Phiên xem bị gián đoạn.');return;}for(const frame of frames)queue.push(frame);pump();};
function impact(x,y,bullet){
 explosions.push({x,y,at:performance.now()});
 if([4,5,13,14,16,23,26,28,34,36,51,57].includes(bullet))return;
 const mask=holes.get(holeNames[holeMap[bullet]??0]),w=mask.image.width,h=mask.image.height;
 for(const tile of tiles){
  if(!tile.ready||!tile.solid)continue;
  const ox=Math.trunc(x-tile.x-Math.floor(w/2)),oy=Math.trunc(y-tile.y-Math.floor(h/2));
  if(ox>=tile.canvas.width||oy>=tile.canvas.height||ox+w<=0||oy+h<=0)continue;
  const data=tile.ctx.getImageData(0,0,tile.canvas.width,tile.canvas.height);
  for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++){
   const tx=ox+xx,ty=oy+yy;if(tx<0||ty<0||tx>=data.width||ty>=data.height)continue;
   const m=(yy*w+xx)*4,p=(ty*data.width+tx)*4;
   if(mask.pixels[m+3]!==255||mask.pixels[m+1]||mask.pixels[m+2])continue;
   if(mask.pixels[m]===0)data.data[p+3]=0;
   else if(mask.pixels[m]===255&&data.data[p+3]){data.data[p]=data.data[p+1]=data.data[p+2]=0;data.data[p+3]=255;}
  }
  tile.ctx.putImageData(data,0,0);
 }
}
function updateShot(delta){
 if(!shot)return;
 shot.elapsed+=delta*(forceMax?2:1);
 const sample=Math.min(shot.samples-1,Math.floor(shot.elapsed/FRAME_MS));
 for(const path of shot.paths){
  const last=path.length-1;
  if(last>shot.sample&&last<=sample)impact(...path[last],shot.bullet);
 }
 while(shot.impactIndex<shot.impacts.length&&shot.impacts[shot.impactIndex].sample<=sample){
  const e=shot.impacts[shot.impactIndex++],actor=game.players[e.slot];
  if(actor&&actor.hp!==undefined)game.setHealth(e.slot,actor.hp+e.delta,e.max);
 }
 shot.sample=sample;
 if(sample===shot.samples-1){shot=null;pump();}
}
function camera(delta){
 const width=320/WORLD_SCALE,height=ui.height/WORLD_SCALE,actor=game.players[game.turn]??game.players.find(p=>p&&p.hp>0);
 let tx=actor?.x??width/2,ty=actor?.y??height/2;
 if(shot){const p=shot.paths.find(p=>p.length);if(p){const point=p[Math.min(p.length-1,Math.floor(shot.elapsed/FRAME_MS))];tx=point[0];ty=point[1];}}
 const maxX=Math.max(0,(game.width??width)-width),maxY=Math.max(0,(game.height??height)-height);
 if(!freeCamera){const x=Math.max(0,Math.min(maxX,tx-width/2)),y=Math.max(0,Math.min(maxY,ty-height/2)),k=cameraReady?Math.min(1,delta/100):1;cameraX+=(x-cameraX)*k;cameraY+=(y-cameraY)*k;cameraReady=true;}
 cameraX=Math.max(0,Math.min(maxX,cameraX));cameraY=Math.max(0,Math.min(maxY,cameraY));
}
function drawSprite(name,x,y,w,h,frame=0){const im=asset(name);if(!im.complete||!im.naturalWidth)return;const sw=w??im.width,sh=h??im.height;ctx.drawImage(im,0,Math.min(im.height-sh,frame*sh),sw,sh,Math.round(x),Math.round(y),sw,sh);}
function paintActor(actor,i){
 if(actor.x===undefined||actor.hp===undefined)return;const x=actor.x,y=actor.y;
 if(actor.hp<=0){ctx.save();ctx.globalAlpha=.6;ui.avatar(actor,x,y,1);ctx.restore();return;}
 ctx.save();ctx.translate(x,y);if(actor.facing===-1)ctx.scale(-1,1);ui.avatar({character:actor.character,parts:actor.parts,aura:actor.aura??0},0,0,1);ctx.restore();
 ui.text('HP: '+actor.hp+'/'+actor.max,x,y-59,{align:'center',color:'#d82532',shadow:true,max:170});
 ui.text(actor.name,x,y-42,{align:'center',color:showTeam&&i%2?'#8acbf1':'#ffe23c',shadow:true,max:100});
 ctx.fillStyle='#173448';ctx.fillRect(x-13,y-24,26,4);ctx.fillStyle='#4fff37';ctx.fillRect(x-12,y-23,24*Math.max(0,Math.min(1,actor.hp/Math.max(1,actor.max))),2);
 if(actor.frozen)ui.text('*',x,y-63,{align:'center',color:'#ffff30'});
 if(i===game.turn&&!shot)drawSprite('main-bar',x-5,y-20);
}
function paintProjectiles(){
 if(!shot)return;const sample=Math.floor(shot.elapsed/FRAME_MS);
 for(const p of shot.paths){if(!p.length||sample>=p.length)continue;const [x,y]=p[sample],old=p[Math.max(0,sample-1)];let name='projectile-dan',w=18;
  if([0,24,35,48,52].includes(shot.bullet)){name='projectile-grenade';w=20;}else if([2,3,10].includes(shot.bullet)){name='projectile-rocket2';w=15;}else if([11,12,18].includes(shot.bullet)){name='projectile-cannon';w=14;}else if([7,31,37].includes(shot.bullet)){name='projectile-laser';w=19;}
  ctx.save();ctx.translate(x,y);ctx.rotate(Math.atan2(y-old[1],x-old[0]));drawSprite(name,-w/2,-w/2,w,w);ctx.restore();
 }
}
function leave(){menuOpen=false;state.textContent='Đang rời chế độ xem…';post('leave');}
function toggleCamera(){menuOpen=false;freeCamera=!freeCamera;}
function showWatchNotice(label){menuOpen=false;watchNotice='Chưa mở được '+label+' khi xem trận.';}
const mainMenu=[
 ['TIẾP TỤC',()=>{menuOpen=false;}],
 ['LỰC MAX',()=>{forceMax=!forceMax;menuOpen=false;}],
 ['V9 MENU',()=>{menuOpen='camera';menuFocus=0;}],
 ['BẬT/TẮT ICON ĐỘI',()=>{showTeam=!showTeam;menuOpen=false;}],
 ['BẠN BÈ',()=>showWatchNotice('Bạn bè')],
 ['TIN NHẮN',()=>showWatchNotice('Tin nhắn')],
 ['RỜI TRẬN CHIẾN',leave],
];
const cameraMenu=[['CAMERA',toggleCamera],['TRỞ RA',()=>{menuOpen=true;menuFocus=0;}]];
function options(){return menuOpen==='camera'?cameraMenu:mainMenu;}
function answer(accept){
 if(phase!==0||awaiting)return;
 awaiting=true;
 post(accept?'accept':'decline');
}
window.setWatchPhase=(value,message)=>{
 phase=value;question=message;awaiting=false;
 state.textContent=value===0?question:value===1?'Đang tải trận đấu…':value===3?'Đang rời chế độ xem…':'Đang xem trận';
};
function key(code){
 if(failed)return;
 if([76,108,-21].includes(code))code=-6;
 if([82,114,-22,-11,27].includes(code))code=-7;
 if(phase===0){
  if([-6,-5,13,10,53,70,102].includes(code))answer(true);
  else if(code===-7)answer(false);
  return;
 }
 if(phase!==2)return;
 if(watchNotice){if([-7,-6,-5,13,10,53,70,102].includes(code))watchNotice='';return;}
 if(code===-6){if(menuOpen)options()[menuFocus]?.[1]();else{menuOpen=true;menuFocus=0;}return;}
 if(code===-7){if(menuOpen)menuOpen=false;else toggleCamera();return;}
 if(menuOpen){
  const list=options(),direction=([-1,50].includes(code)?-1:[-2,56].includes(code)?1:0);
  if(direction)menuFocus=(menuFocus+direction+list.length)%list.length;
  else if([-5,13,10,53,70,102].includes(code))list[menuFocus]?.[1]();
  return;
 }
 if(!freeCamera)return;if([-3,52].includes(code))cameraX-=20;if([-4,54].includes(code))cameraX+=20;if([-1,50].includes(code))cameraY-=20;if([-2,56].includes(code))cameraY+=20;
}
window.watchKey=key;
addEventListener('keydown',e=>{const code={ArrowUp:-1,ArrowDown:-2,ArrowLeft:-3,ArrowRight:-4,Enter:-5,Escape:-7,F1:-6,F2:-7}[e.key];if(code){e.preventDefault();key(code);}});
ui.canvas.addEventListener('pointerdown',e=>{if(freeCamera&&!menuOpen)drag={x:e.clientX,y:e.clientY,cx:cameraX,cy:cameraY};});
ui.canvas.addEventListener('pointermove',e=>{if(!drag)return;const scale=ui.canvas.clientWidth*WORLD_SCALE/320;cameraX=drag.cx-(e.clientX-drag.x)/scale;cameraY=drag.cy-(e.clientY-drag.y)/scale;});
for(const event of ['pointerup','pointercancel','pointerleave'])ui.canvas.addEventListener(event,()=>{drag=null;});
function clock(seconds){
 const center=160,y=15,radius=11;
 ctx.save();ctx.translate(center,y);
 for(let segment=0;segment<12;segment++){
  const a=segment*Math.PI/6-Math.PI/2,b=a+Math.PI/6;
  ctx.beginPath();ctx.arc(0,0,radius,a,b);ctx.arc(0,0,5,b,a,true);ctx.closePath();
  ctx.fillStyle=segment/12<seconds/40?'#e5ac75':'#e2c995';ctx.fill();ctx.strokeStyle='#9a613b';ctx.lineWidth=.55;ctx.stroke();
 }
 ctx.restore();
 ui.text(seconds,center,y-5,{align:'center',color:'#fff',shadow:true,max:19});
}
function paintMenu(){
 const list=options(),w=136,h=22+list.length*22,x=92,y=Math.max(7,Math.floor((ui.height-h)/2));
 ui.zone(0,0,320,ui.height,()=>{menuOpen=false;});
 ui.stripedBox(x,y,w,h);
 list.forEach(([label,action],i)=>{
  const row=y+19+i*22;
  if(i===menuFocus)ui.rect(x+5,row,w-10,19,'#ffdf4e');
  ui.text(label,160,row+3,{title:true,align:'center',color:'#ffdf39',max:w-12});
  ui.zone(x+5,row,w-10,19,action);
 });
}
ui.start(()=>{
 if(phase===0||phase===1||phase===3){
  const message=phase===0?question:phase===1?'Đang tải trận đấu…':question||'Đang rời chế độ xem…';
  ui.bottomDialog(ui.wrapText(message,288));
  ui.footer(phase===0?'Có':'','',phase===0?'Không':'',()=>answer(true),null,()=>answer(false));
  return;
 }
 if(phase!==2)return;
 const now=performance.now(),delta=lastTime?Math.min(250,Math.max(0,now-lastTime)):0;lastTime=now;updateShot(delta);camera(delta);
 if(liveReported){
  ui.rect(0,0,320,ui.height,game.map===0?'#58e1e7':'#60cdf7');ctx.save();ctx.beginPath();ctx.rect(0,0,320,ui.height);ctx.clip();ctx.scale(WORLD_SCALE,WORLD_SCALE);ctx.translate(-Math.round(cameraX),-Math.round(cameraY));
  for(const t of tiles)if(t.ready)ctx.drawImage(t.canvas,t.x,t.y);
  game.players.forEach((p,i)=>{if(p)paintActor(p,i);});paintProjectiles();
  for(let i=explosions.length-1;i>=0;i--){const p=explosions[i],age=now-p.at;if(age>360){explosions.splice(i,1);continue;}const size=16+Math.sin(age/360*Math.PI)*18,im=asset('main-no');if(im.complete&&im.naturalWidth)ctx.drawImage(im,0,Math.floor(age/90)%2*10,10,10,p.x-size/2,p.y-size/2,size,size);}
  for(let i=numbers.length-1;i>=0;i--){const p=numbers[i],age=now-p.at;if(age>850){numbers.splice(i,1);continue;}ui.text((p.delta>0?'+':'')+p.delta,p.x,p.y-age/70,{color:p.delta>0?'#55ff44':'#ffff30',align:'center',shadow:true,max:180});}
  ctx.restore();
  ui.sprite('watch-iconmenu',18,4,10,6);ui.sprite('watch-iconChat',48,4,10,10);
  if(!freeCamera)ui.text('Đang xem',5,15,{max:100});
  const seconds=Math.max(0,(game.seconds??40)-Math.floor((now-clockAt)/1000));
  clock(seconds);
  ui.text('Góc '+angle,160,28,{align:'center',color:'#fff',shadow:true,max:105});
  ctx.save();ctx.translate(303,20);ctx.scale(1,-1);ui.sprite('watch-menu',-17,-16,34,32);ctx.restore();
  ui.zone(282,0,38,39,()=>showWatchNotice('Đổi PB'));
  ui.zone(0,0,44,40,()=>{menuOpen=true;menuFocus=0;});
  ui.zone(45,0,24,38,()=>showWatchNotice('Tin nhắn'));
  if(menuOpen)paintMenu();
  if(watchNotice){ui.zone(0,0,320,ui.height,()=>{});ui.bottomDialog(ui.wrapText(watchNotice,288));ui.footer('','OK','',null,()=>{watchNotice='';});}
 }else{ui.bottomDialog(['Đang tải trận đấu…']);}
},{transparent:true});
post('ready');
