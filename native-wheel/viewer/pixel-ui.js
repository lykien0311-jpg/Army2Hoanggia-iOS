'use strict';
// Coordinates, bitmap fonts, sprite rectangles and gear layers follow the JAR painters.
const PixelUI=(()=>{
 const canvas=document.getElementById('game'),g=canvas.getContext('2d',{alpha:document.body.dataset.transparent==='true'}),images=new Map(),fonts=new Map();
 const nativeScale=450/320;let classicWidth=432;let height=480,frame=0,hits=[],raf,fontUnit=1/nativeScale;
 function image(name){const cached=images.get(name);if(cached){images.delete(name);images.set(name,cached);return cached;}const i=new Image();i.src='art/'+name+'.png';images.set(name,i);if(/^[kv][1-4]-/.test(name)){const auraKeys=[...images.keys()].filter(k=>/^[kv][1-4]-/.test(k));if(auraKeys.length>24)images.delete(auraKeys[0]);}return i;}
 for(const k of ['body','title','b','a','cl1','cl2','cl3','miniballoon'])image(k);

 function resize(){height=Math.max(220,Math.round(320*innerHeight/Math.max(1,innerWidth)));canvas.width=450;canvas.height=Math.round(height*nativeScale);g.setTransform(nativeScale,0,0,nativeScale,0,0);g.imageSmoothingEnabled=false;}
 addEventListener('resize',resize);resize();
 function rect(x,y,w,h,color){g.fillStyle=color;g.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));}
 function sprite(name,x,y,w,h){const im=image(name);if(im.complete&&im.naturalWidth)g.drawImage(im,Math.round(x),Math.round(y),w??im.naturalWidth,h??im.naturalHeight);}
 function font(kind,color){if(kind==='title'){const i=image(kind);return i.complete&&i.naturalWidth?i:null;}const key=kind+color;if(fonts.has(key))return fonts.get(key);const im=image(kind);if(!im.complete||!im.naturalWidth)return null;const c=document.createElement('canvas');c.width=im.width;c.height=im.height;const x=c.getContext('2d');x.drawImage(im,0,0);x.globalCompositeOperation='source-in';x.fillStyle=color;x.fillRect(0,0,c.width,c.height);fonts.set(key,c);return c;}
 function text(str,x,y,{color='#214e73',title=false,align='left',max=310,scale=1,shadow=false,outline=false}={}){
  // Keep every bitmap glyph at its native pixel size, then scale the complete
  // game surface. Downsampling individual glyphs erases their one-pixel strokes.
  scale=fontUnit;str=String(str??'').normalize('NFC');if(title)str=str.toUpperCase();const kind=title?'title':'body',f=ArmyArt[kind],pic=font(kind,color);if(!pic)return;
  let idx=[...str].map(c=>Math.max(0,f.chars.indexOf(c))),w=idx.reduce((a,i)=>a+f.widths[i],0);
  if(w*scale>max){const dot=f.chars.indexOf('.'),dots=3*f.widths[dot];while(idx.length&&(w+dots)*scale>max)w-=f.widths[idx.pop()];if(dots*scale<=max){idx.push(dot,dot,dot);w+=dots;}}
  if(align==='center')x-=w*scale/2;else if(align==='right')x-=w*scale;
  const t=g.getTransform(),pixelScale=scale*t.a;let px=t.a*x+t.e;const py=Math.round(t.d*y+t.f);
  g.save();g.setTransform(1,0,0,1,0,0);
  for(const i of idx){if(outline&&!title){const black=font(kind,'#15232e');for(const [dx,dy]of [[-1,0],[1,0],[0,-1],[0,1]])g.drawImage(black,0,i*f.height,pic.width,f.height,Math.round(px)+dx,py+dy,pic.width*pixelScale,f.height*pixelScale);}if(shadow&&!title){const black=font(kind,'#15232e');g.drawImage(black,0,i*f.height,pic.width,f.height,Math.round(px)+1,py+1,pic.width*pixelScale,f.height*pixelScale);}g.drawImage(pic,0,i*f.height,pic.width,f.height,Math.round(px),py,pic.width*pixelScale,f.height*pixelScale);px+=f.widths[i]*pixelScale;}
  g.restore();
 }
 function zone(x,y,w,h,run){const t=g.getTransform();hits.push({x:(t.a*x+t.e)/nativeScale,y:(t.d*y+t.f)/nativeScale,w:w*t.a/nativeScale,h:h*t.d/nativeScale,run});}
 function sky(){
  rect(0,0,320,height,'#60cdf7');
  sprite('cl1',38,52);sprite('cl2',240,61);sprite('cl3',113,71);
 }
 function aura(code,x,y,layer){const tier=code>>>5,level=code&31;if(tier<1||tier>7||level>16)return;
  if(tier>=5){const pal=level<1?0:level<=3?1:level===4?6:level<=7?2:level===8?7:level<=11?3:level<=14?4:5;
   const im=image('k'+(tier-4)+'-p'+pal),n=(((frame>>1)&31)*2+layer)*6,r=ArmyArt.geometry[tier-5];if(im.complete&&im.naturalWidth&&r[n+2]>0)g.drawImage(im,r[n],r[n+1],r[n+2],r[n+3],Math.round(x+r[n+4]),Math.round(y+r[n+5]),r[n+2],r[n+3]);return;}
  const im=image('v'+tier+'-l'+level),cell=(frame&63)*2+layer;
  if(im.complete&&im.naturalWidth)g.drawImage(im,cell%8*96,Math.floor(cell/8)*80,96,80,Math.round(x-48),Math.round(y-64),96,80);
 }
 function piece(hero,slot,id,pose,x,y){const r=ArmyArt.gear[hero+':'+slot+':'+id]??ArmyArt.gear[hero+':'+slot+':0'];if(!r||!r[2]||!r[3])return;const im=image('hero'+hero);if(!im.complete||!im.naturalWidth)return;const width=hero===3?30:hero===6?29:hero===7?32:24,h=hero===3||hero===7?32:24;g.drawImage(im,r[0],r[1],r[2],r[3],Math.round(x-Math.floor(width/2)+r[4]+18),Math.round(y-h+r[5]+40),r[2],r[3]);}
 function avatar(row,x,y,scale=.72){const hero=row.character??row.hero??0,parts=row.parts??[0,0,0,0,0];g.save();g.translate(x,y);g.scale(scale,scale);aura(row.aura??0,0,0,0);for(const k of [0,4])piece(hero,k,parts[k],0,0,0);const body=image('base'+hero);if(body.complete&&body.naturalWidth)g.drawImage(body,-Math.floor(body.width/2),-body.height);for(const k of [1,2,3])piece(hero,k,parts[k],0,0,0);aura(row.aura??0,0,0,1);g.restore();}
 let gearAtlas=null;
 function setGearAtlas(frames,src){
  const png=new Image();png.src=src;gearAtlas={frames,png};
 }
 function gearIcon(hero,slot,id,x,y,size=16,png=null,nativeIcon=false){
  if(png?.length){
   const key='icon:'+hero+':'+slot+':'+id+':'+Array.from(png).join(',');
   let im=images.get(key);
   if(!im){im=new Image();im.src='data:image/png;base64,'+btoa(Array.from(png,b=>String.fromCharCode(b)).join(''));images.set(key,im);}
   if(im.complete&&im.naturalWidth){const k=Math.min(size/im.width,size/im.height);const w=Math.round(im.width*k),h=Math.round(im.height*k);g.drawImage(im,Math.round(x-w/2),Math.round(y-h/2),w,h);return true;}
  }
  const key=hero+':'+slot+':'+id,row=gearAtlas?.frames.get(key),atlas=gearAtlas?.png;
  if(nativeIcon&&Number.isInteger(row)&&atlas.complete&&atlas.naturalWidth&&row*atlas.width+16<=atlas.height){
   g.drawImage(atlas,0,row*atlas.width,16,16,Math.round(x-size/2),Math.round(y-size/2),size,size);
   return true;
  }
  const r=ArmyArt.gear[key];
  if(!r||!r[2]||!r[3])return false;
  const im=image('hero'+hero);
  if(!im.complete||!im.naturalWidth)return false;
  const k=Math.min(size/r[2],size/r[3]);
  const w=Math.round(r[2]*k),h=Math.round(r[3]*k);
  g.drawImage(im,r[0],r[1],r[2],r[3],x-Math.floor(w/2),y-Math.floor(h/2),w,h);
  return true;
 }
 function gear(hero,slot,id,x,y,upgrade=0,png=null){
  if(upgrade>0){const color=upgrade<=4?'#0048ff':upgrade<=8?'#00b300':upgrade<=11?'#ff7f00':upgrade<=14?'#ce00ff':'#ff0019';g.strokeStyle=color;g.strokeRect(x-9,y-9,18,18);if(upgrade>=12)for(let i=0;i<4;i++){const t=frame*.15+i*Math.PI/2;rect(x+Math.cos(t)*10,y+Math.sin(t)*10,2,2,color);}text('+'+upgrade,x-8,y-14,{color,scale:.6,max:23,shadow:true});}
  gearIcon(hero,slot,id,x,y,16,png);
 }
 function nativePixels(draw){g.save();const old=fontUnit;g.scale(1/nativeScale,1/nativeScale);fontUnit=1;try{return draw(450,canvas.height);}finally{fontUnit=old;g.restore();}}
 function classicSize(width){if(Number.isInteger(width)&&width>=160&&width<=4096)classicWidth=width;}
 function classicPixels(draw){g.save();const old=fontUnit;g.scale(320/classicWidth,320/classicWidth);fontUnit=1;try{return draw(classicWidth,Math.round(height*classicWidth/320));}finally{fontUnit=old;g.restore();}}
 function classicFooter(width,height,left,center,right,onleft,oncenter,onright){const y=height-34;rect(0,y,width,34,'#c5d5ee');text(left,4,y+10,{max:width/3-8});text(center,width/2,y+10,{align:'center',max:width/3-8});text(right,width-4,y+10,{align:'right',max:width/3-8});zone(0,y,width/3,34,onleft);zone(width/3,y,width/3,34,oncenter);zone(width*2/3,y,width/3,34,onright);}
 function inventoryFrame(title,x,y,w,h,decor){
  rect(x,y+18,w,h-18,'#c5d5ee');
  sprite('tab_1',x,y);for(let i=0;i<decor;i++)sprite('tab_2',x+23+i*32,y);sprite('tab_3',x+w-32,y);
  rect(x,y+18,1,h-18,'#303030');rect(x+w-1,y+18,1,h-18,'#303030');rect(x,y+h-1,w,1,'#303030');
  roundRect(x+7,y+24,w-14,h-65,'#3b76b1',5);
  const tw=textWidth(title)+10;rect(x+(w-tw)/2,y+1,tw,18,'#c5d5ee');text(title,x+w/2,y+3,{align:'center',color:'#fff',outline:true});
 }
 function roundRect(x,y,w,h,color,r=3){x=Math.round(x);y=Math.round(y);w=Math.round(w);h=Math.round(h);r=Math.min(r,w/2,h/2);g.fillStyle=color;g.beginPath();g.moveTo(x+r,y);g.lineTo(x+w-r,y);g.quadraticCurveTo(x+w,y,x+w,y+r);g.lineTo(x+w,y+h-r);g.quadraticCurveTo(x+w,y+h,x+w-r,y+h);g.lineTo(x+r,y+h);g.quadraticCurveTo(x,y+h,x,y+h-r);g.lineTo(x,y+r);g.quadraticCurveTo(x,y,x+r,y);g.fill();}
 function line(x1,y1,x2,y2,color){rect(x1,y1,x2-x1+1,y2-y1+1,color);}
 function equipmentFrame(x,y){
  rect(x,y+20,183,145,'#c5d5ee');
  line(x,y+10,x+183,y+10,'#303030');line(x,y+10,x,y+165,'#303030');line(x+183,y+10,x+183,y+165,'#303030');
  sprite('tab_1',x,y);for(let i=0;i<4;i++)sprite('tab_2',x+23+i*32,y);sprite('tab_3',x+151,y);
  sprite('tab_4',x,y+150);sprite('tab_5',x+161,y+150);
  rect(x+23,y+165,138,5,'#c5d5ee');line(x+23,y+169,x+161,y+169,'#303030');line(x+23,y+168,x+161,y+168,'#83889c');
  line(x+1,y+20,x+1,y+165,'#83889c');line(x+182,y+20,x+182,y+165,'#83889c');
  const w=textWidth('Trang bị')+10,left=x+92-w/2;rect(left,y+1,w,18,'#c5d5ee');
  line(left,y+1,left+w,y+1,'#6a95bd');line(left,y+1,left,y+18,'#6a95bd');line(left+w,y+1,left+w,y+18,'#6a95bd');line(left,y+18,left+w,y+18,'#6a95bd');
  text('Trang bị',x+92,y+3,{align:'center',color:'#fff',outline:true});
 }
 const gearBackground=[0,0,0,0,600841,600841,667658,667658,3346944,3346688,4199680,5052928,3276851,3932211,4587571,5046280,6684682];
 const gearGlow=[[18687,16869,15052,13235,11161,9344],[45824,39168,32768,26112,19712,13056],[16744192,15037184,13395456,11753728,10046464,8404992],[13500671,12058853,10682572,9371827,7995545,6684800],[16711705,15007767,13369364,11730962,10027023,8388621]];
 function equipmentItem(hero,slot,id,x,y,upgrade,png,nativeIcon=false){
  if(upgrade>0){const u=Math.min(16,upgrade),color='#'+gearBackground[u].toString(16).padStart(6,'0');rect(x-9,y-7,17,17,color);
   const group=u<4?0:u<8?1:u<12?2:u<=14?3:4,tails=[1,4,8].includes(u)?1:[2,5,9,12].includes(u)?2:[3,6,10,13,15].includes(u)?3:4;
   for(let k=0;k<tails;k++)for(let i=5;i>=0;i--){const p=((frame-i*4-k*16)%64+64)%64,xx=p<16?p:p<32?16:p<48?48-p:0,yy=p<16?0:p<32?p-16:p<48?16:64-p,side=i===0?2:1;rect(x-9+xx-Math.floor(side/2),y-7+yy-Math.floor(side/2),side,side,'#'+gearGlow[group][i].toString(16).padStart(6,'0'));}
  }
  gearIcon(hero,slot,id,x,y,16,png,nativeIcon);
  if(upgrade>0)text('+'+upgrade,x+3,y-13,{color:'#fff',outline:true,max:30});
 }
 function marquee(value,x,y,width,color){g.save();g.beginPath();g.rect(x,y,width,16);g.clip();const span=textWidth(value)+16,offset=span>width?Math.floor(frame*.6)%span:0;text(value,x-offset,y+1,{color,max:10000});if(offset)text(value,x-offset+span,y+1,{color,max:10000});g.restore();}
 function statsIcon(index,x,y){const im=image('ability');if(im.complete&&im.naturalWidth)g.drawImage(im,0,index*16,16,16,x,y,16,16);}
 const digits=['0111110/1100011/1100111/1101011/1110011/1100011/1100011/1100011/0111110','0011000/0111000/0011000/0011000/0011000/0011000/0011000/0011000/0111100','0111110/1100011/0000011/0000011/0001110/0110000/1100000/1100000/1111111','1111110/0000011/0000011/0000011/0011110/0000011/0000011/0000011/1111110','0000110/0001110/0011110/0110110/1100110/1111111/0000110/0000110/0000110','1111111/1100000/1100000/1111110/0000011/0000011/0000011/1100011/0111110','0011110/0110000/1100000/1100000/1111110/1100011/1100011/1100011/0111110','1111111/0000011/0000110/0001100/0011000/0011000/0011000/0011000/0011000','0111110/1100011/1100011/1100011/0111110/1100011/1100011/1100011/0111110','0111110/1100011/1100011/1100011/0111111/0000011/0000011/0000110/0111100'];
 const rankCache=new Map();
 function rank(n,right,y,h=28){
  const str=String(n),height=Math.round(h*nativeScale),cells=str.length*8+1,width=Math.floor(cells*height/11),key=n+':'+height;
  let number=rankCache.get(key);
  if(!number){number=document.createElement('canvas');number.width=width;number.height=height;const ctx=number.getContext('2d'),image=ctx.createImageData(width,height),fill=new Uint8Array(width*height),pixels=image.data;
   for(let yy=0;yy<height;yy++)for(let xx=0;xx<width;xx++){const bx=Math.floor(xx*cells/width)-1,by=Math.floor(yy*11/height)-1;if(bx>=0&&by>=0&&by<9&&Math.floor(bx/8)<str.length&&bx%8<7)fill[yy*width+xx]=digits[Number(str[Math.floor(bx/8)])][by*8+bx%8]==='1'?1:0;}
   const outline=Math.max(1,Math.floor(height/22)),a=n===2?0xeaf6ff:n===3?0xf2c69b:0xff9400,b=n===2?0x8ca5c0:n===3?0xa75d2d:0xffff30;
   for(let yy=0;yy<height;yy++)for(let xx=0;xx<width;xx++){const pos=yy*width+xx,p=pos*4;if(fill[pos]){const t=Math.floor(yy*255/Math.max(1,height-1));for(let channel=0;channel<3;channel++){const shift=16-channel*8;let v=Math.floor((((a>>shift)&255)*(255-t)+((b>>shift)&255)*t)/255);if(yy>0&&!fill[(yy-1)*width+xx])v=Math.min(255,v+55);pixels[p+channel]=v;}pixels[p+3]=255;}else{let edge=false;for(let dy=-outline;dy<=outline&&!edge;dy++)for(let dx=-outline;dx<=outline;dx++){const nx=xx+dx,ny=yy+dy;if(nx>=0&&ny>=0&&nx<width&&ny<height&&fill[ny*width+nx]){edge=true;break;}}if(edge){pixels[p]=16;pixels[p+1]=16;pixels[p+2]=22;pixels[p+3]=255;}}}
   ctx.putImageData(image,0,0);rankCache.set(key,number);if(rankCache.size>64)rankCache.delete(rankCache.keys().next().value);
  }
  g.save();g.setTransform(1,0,0,1,0,0);g.drawImage(number,Math.round(right*nativeScale)-width,Math.round(y*nativeScale));g.restore();
 }
 function heading(title){rect(0,18,320,34,'#224768');rect(0,50,320,1,'#e1b84e');rect(0,51,320,1,'#87b5d5');text(title,160,25,{title:true,align:'center',color:'#ffdf39',shadow:true,max:305});}
 function textWidth(str){
  const f=ArmyArt.body;
  return [...String(str).normalize('NFC')].reduce((w,c)=>w+f.widths[Math.max(0,f.chars.indexOf(c))],0)*fontUnit;
 }
 function wrapText(str,width){
  const lines=[];
  for(const part of str.split('\n')){
   let line='';
   for(const word of part.split(/\s+/).filter(Boolean)){
    if(line&&textWidth(line+' '+word)>width){lines.push(line);line='';}
    line+=(line?' ':'')+word;
   }
   if(line)lines.push(line);
  }
  return lines;
 }
 function stripedBox(x,y,w,h){
  rect(x+2,y,w-4,h,'#2c475e');
  rect(x,y+2,w,h-4,'#2c475e');
  rect(x+2,y+2,w-4,h-4,'#c5d5ef');
  g.save();g.beginPath();g.rect(x+2,y+2,w-4,17);g.clip();
  rect(x,y,w,19,'#244866');
  for(let offset=-5;offset<w+14;offset+=27){
   g.fillStyle='#ffdc54';g.beginPath();g.moveTo(x+offset,y+2);
   g.lineTo(x+offset+13,y+2);g.lineTo(x+offset+5,y+19);
   g.lineTo(x+offset-8,y+19);g.fill();
  }
  g.restore();
 }
 function bottomDialog(lines,offset=0){
  const count=Math.min(Math.max(1,Math.floor((height-57)/12)),4,lines.length);
  const start=Math.min(offset,Math.max(0,lines.length-count));
  const h=Math.max(50,22+count*12),y=height-31-h;
  frameBox(6,y,308,h,true);
  lines.slice(start,start+count).forEach((t,i)=>text(t,160,y+(h-count*12)/2+i*12,{max:293,align:'center'}));
 }
 function frameBox(x,y,w,h,nativeFrame=false){
  rect(x+3,y,w-6,h,'#3c6381');rect(x,y+3,w,h-6,'#3c6381');
  if(nativeFrame){
   rect(x+2,y+2,w-4,h-4,'#6a93b7');
   rect(x+5,y+5,w-10,h-10,'#c5d5ee');
   const im=image('corner');
   if(im.complete&&im.naturalWidth){
    const side=8;
    for(const [dx,dy,sx,sy] of [[0,0,1,1],[w,0,-1,1],[0,h,1,-1],[w,h,-1,-1]]){
     g.save();g.translate(x+dx,y+dy);g.scale(sx,sy);g.drawImage(im,0,0,side,side);g.restore();
    }
    return;
   }
  }
  rect(x+3,y+3,w-6,h-6,'#c7d5ed');
  for(const [dx,dy,sx,sy] of [[1,1,1,1],[w-1,1,-1,1],[1,h-1,1,-1],[w-1,h-1,-1,-1]]){
   g.save();g.translate(x+dx,y+dy);g.scale(sx,sy);
   rect(2,0,7,2,'#ffdc41');rect(0,2,2,7,'#ffdc41');rect(2,2,2,2,'#ffef88');g.restore();
  }
 }
 function panel(title){
  const y=42,w=302,h=height-y-29,x=(320-w)/2;
  rect(x+3,y,w-6,h,'#284d70');rect(x,y+3,w,h-6,'#284d70');rect(x+1,y+1,w-2,h-2,'#c7d5ed');
  rect(x+7,y+16,w-14,h-48,'#397ab1');
  g.save();g.beginPath();g.rect(x+1,y+1,w-2,12);g.clip();
  rect(x,y,w,13,'#274968');
  for(let px=x-3;px<x+w+14;px+=26){
   g.fillStyle='#ffda49';g.beginPath();g.moveTo(px+9,y);g.lineTo(px+22,y);g.lineTo(px+13,y+14);g.lineTo(px,y+14);g.fill();
  }
  g.restore();
  rect(160-title.length*2.6,y+3,title.length*5.2,10,'#c7d5ed');
  text(title,160,y+2,{align:'center',color:'#273845'});
 }
 function footer(left,center,right,onleft,oncenter,onright){const y=height-24;rect(0,y,320,24,'#c7d5ed');text(left,3,y+5,{max:104});text(center,160,y+5,{align:'center',max:103});text(right,317,y+5,{align:'right',max:104});zone(0,y,106,24,onleft);zone(106,y,108,24,oncenter);zone(214,y,106,24,onright);}
 function menu(items,focus=0){
  const row=22,w=Math.min(145,Math.max(73,...items.map(i=>i[0].length*5+13)));
  const count=Math.min(items.length,Math.max(1,Math.floor((height-36)/row)));
  const first=Math.max(0,focus-count+1),h=count*row+6,y=height-25-h;
  frameBox(0,y,w,h);
  items.slice(first,first+count).forEach(([label,fn],i)=>{
   if(i+first===focus)rect(4,y+3+i*row,w-8,row,'#ffdf4e');
   text(label,6,y+5+i*row,{max:w-12});zone(4,y+3+i*row,w-8,row,fn);
  });
 }
 function start(paint,{transparent=false}={}){cancelAnimationFrame(raf);let last=-1;function tick(now){const f=Math.floor(now/42);if(f!==last){last=f;frame=f;hits=[];if(transparent)g.clearRect(0,0,320,height);else sky();paint();}raf=requestAnimationFrame(tick);}raf=requestAnimationFrame(tick);}
 canvas.addEventListener('pointerup',e=>{const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*320/r.width,y=(e.clientY-r.top)*height/r.height;for(let i=hits.length-1;i>=0;i--){const h=hits[i];if(x>=h.x&&x<h.x+h.w&&y>=h.y&&y<h.y+h.h){h.run?.();break;}}});
 return {g,classicSize,classicPixels,classicFooter,inventoryFrame,nativePixels,roundRect,equipmentFrame,equipmentItem,marquee,text,textWidth,wrapText,rect,sprite,avatar,aura,gear,gearIcon,setGearAtlas,statsIcon,rank,heading,panel,frameBox,stripedBox,bottomDialog,footer,menu,zone,start,get height(){return height;},get frame(){return frame;},canvas};
})();

