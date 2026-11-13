'use strict';
// Only spectator controls are overlaid. The native game owns every fight pixel.
let phase=0,message='',free=false;
const send=value=>window.webkit.messageHandlers.viewer.postMessage(value);
window.setWatchPhase=(p,text)=>{phase=p;message=text||'';};
window.watchKey=code=>{
 if(phase===0&&[-6,-5,13,53].includes(code))send('accept');
 else if(phase===0&&[-7,27].includes(code))send('decline');
 else if(phase===2&&code===-7){free=!free;send('camera');}
 else if(phase===2&&code===-6)send('leave');
};
PixelUI.start(()=>{
 if(phase===2){PixelUI.text('Đang xem',4,15);PixelUI.footer('Rời trận','',free?'Theo dõi':'Camera',()=>send('leave'),null,()=>{free=!free;send('camera');});return;}
 PixelUI.rect(0,0,320,PixelUI.height,'rgba(25,53,78,.82)');
 const lines=PixelUI.wrapText(phase===0?message:phase===3?'Đang rời trận…':'Đang tải trận đấu…',270),h=28+lines.length*14,y=(PixelUI.height-h)/2;
 PixelUI.frameBox(12,y,296,h);lines.forEach((s,i)=>PixelUI.text(s,160,y+14+i*14,{align:'center',max:270}));
 PixelUI.footer(phase===0?'Có':'','',phase===0?'Không':'Hủy',()=>phase===0&&send('accept'),null,()=>send(phase===0?'decline':'leave'));
},{transparent:true});
let last=null,dragCode=0;
PixelUI.canvas.addEventListener('pointerdown',e=>{if(phase===2&&free&&e.clientY<innerHeight-30){last=[e.clientX,e.clientY];PixelUI.canvas.setPointerCapture(e.pointerId);}});
PixelUI.canvas.addEventListener('pointermove',e=>{if(!last)return;const dx=e.clientX-last[0],dy=e.clientY-last[1];const code=Math.abs(dx)>Math.abs(dy)?dx>0?-3:-4:dy>0?-1:-2;if(code!==dragCode){if(dragCode)send(['key',1,dragCode]);dragCode=code;send(['key',0,code]);}last=[e.clientX,e.clientY];});
for(const type of ['pointerup','pointercancel'])PixelUI.canvas.addEventListener(type,()=>{if(dragCode)send(['key',1,dragCode]);last=null;dragCode=0;});
send('ready');
