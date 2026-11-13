'use strict';
// Coordinates, bitmap fonts, sprite rectangles and gear layers follow the JAR painters.
const PixelUI=(()=>{
 const canvas=document.getElementById('game'),g=canvas.getContext('2d',{alpha:false}),images=new Map(),fonts=new Map();
 let height=480,frame=0,hits=[],raf;
 function image(name){if(!images.has(name)){const i=new Image();i.src='art/'+name+'.png';images.set(name,i);}return images.get(name);}
 for(const k of ['body','title','b','a','cl1','cl2','cl3','miniballoon'])image(k);
 for(let h=0;h<10;h++)image('hero'+h);
 function resize(){height=Math.max(220,Math.round(320*innerHeight/Math.max(1,innerWidth)));canvas.width=320;canvas.height=height;g.imageSmoothingEnabled=false;}
 addEventListener('resize',resize);resize();
 function rect(x,y,w,h,color){g.fillStyle=color;g.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));}
 function sprite(name,x,y,w,h){const im=image(name);if(im.complete&&im.naturalWidth)g.drawImage(im,Math.round(x),Math.round(y),w??im.naturalWidth,h??im.naturalHeight);}
 function font(kind,color){const key=kind+color;if(fonts.has(key))return fonts.get(key);const im=image(kind);if(!im.complete||!im.naturalWidth)return null;const c=document.createElement('canvas');c.width=im.width;c.height=im.height;const x=c.getContext('2d');x.drawImage(im,0,0);x.globalCompositeOperation='source-in';x.fillStyle=color;x.fillRect(0,0,c.width,c.height);fonts.set(key,c);return c;}
 function text(str,x,y,{color='#214e73',title=false,align='left',max=310,scale=1,shadow=false}={}){
  str=String(str??'').normalize('NFC');if(title)str=str.toUpperCase();const kind=title?'title':'body',f=ArmyArt[kind],pic=font(kind,color);if(!pic)return;
  const idx=[...str].map(c=>Math.max(0,f.chars.indexOf(c)));let w=idx.reduce((a,i)=>a+f.widths[i],0);scale=Math.min(scale,max/Math.max(1,w));if(align==='center')x-=w*scale/2;else if(align==='right')x-=w*scale;
  for(const i of idx){if(shadow){const black=font(kind,'#15232e');g.drawImage(black,0,i*f.height,pic.width,f.height,Math.round(x)+1,Math.round(y)+1,pic.width*scale,f.height*scale);}g.drawImage(pic,0,i*f.height,pic.width,f.height,Math.round(x),Math.round(y),pic.width*scale,f.height*scale);x+=f.widths[i]*scale;}
 }
 function zone(x,y,w,h,run){hits.push({x,y,w,h,run});}
 function sky(){rect(0,0,320,height,'#60cdf7');sprite('cl1',38,28);sprite('cl2',240,86);sprite('cl3',113,120);sprite('miniballoon',13,61);for(const [x,y]of [[33,height-56],[64,height-68],[96,height-45],[258,height-51],[280,height-39]]){for(let k=0;k<5;k++){rect(x+14,y+20+k*7,5,7,k%2?'#a87536':'#e6cb71');rect(x+14,y+20+k*7,1,7,'#71592a');}sprite('b',x,y,42,29);}}
 function aura(code,x,y,layer){const tier=code>>>5,level=code&31;if(tier<1||tier>7||level>16)return;
  if(tier>=5){const pal=level<1?0:level<=3?1:level===4?6:level<=7?2:level===8?7:level<=11?3:level<=14?4:5;
   const im=image('k'+(tier-4)+'-p'+pal),n=(((frame>>1)&31)*2+layer)*6,r=ArmyArt.geometry[tier-5];if(im.complete&&im.naturalWidth&&r[n+2]>0)g.drawImage(im,r[n],r[n+1],r[n+2],r[n+3],Math.round(x+r[n+4]),Math.round(y+r[n+5]),r[n+2],r[n+3]);return;}
  const c=level<=4?'#0048ff':level<=8?'#00b300':level<=11?'#ff7f00':level<=14?'#ce00ff':'#ff0019';g.strokeStyle=c;g.lineWidth=1;g.beginPath();for(let i=0;i<=24;i++){const a=i*Math.PI/12,z=Math.sin(a);if((z>=0)!==!!layer)continue;const px=x+Math.cos(a)*(12+tier*2),py=y+z*(3+tier/2);if(i===0||i===13)g.moveTo(px,py);else g.lineTo(px,py);}g.stroke();
 }
 function piece(hero,slot,id,pose,x,y){const r=ArmyArt.gear[hero+':'+slot+':'+id]??ArmyArt.gear[hero+':'+slot+':0'];if(!r||!r[2]||!r[3])return;const im=image('hero'+hero);if(!im.complete||!im.naturalWidth)return;const width=hero===3?30:hero===6?29:hero===7?32:24,h=hero===3||hero===7?32:24;g.drawImage(im,r[0],r[1],r[2],r[3],Math.round(x-Math.floor(width/2)+r[4]+18),Math.round(y-h+r[5]+40),r[2],r[3]);}
 function avatar(row,x,y){const hero=row.character??row.hero??0,parts=row.parts??[0,0,0,0,0];aura(row.aura??0,x,y,0);for(const k of [0,4,1,2,3])piece(hero,k,parts[k],0,x,y);aura(row.aura??0,x,y,1);}
 const digits=['0111110/1100011/1100111/1101011/1110011/1100011/1100011/1100011/0111110','0011000/0111000/0011000/0011000/0011000/0011000/0011000/0011000/0111100','0111110/1100011/0000011/0000011/0001110/0110000/1100000/1100000/1111111','1111110/0000011/0000011/0000011/0011110/0000011/0000011/0000011/1111110','0000110/0001110/0011110/0110110/1100110/1111111/0000110/0000110/0000110','1111111/1100000/1100000/1111110/0000011/0000011/0000011/1100011/0111110','0011110/0110000/1100000/1100000/1111110/1100011/1100011/1100011/0111110','1111111/0000011/0000110/0001100/0011000/0011000/0011000/0011000/0011000','0111110/1100011/1100011/1100011/0111110/1100011/1100011/1100011/0111110','0111110/1100011/1100011/1100011/0111111/0000011/0000011/0000110/0111100'];
 function rank(n,right,y,h=30){const s=String(n),unit=h/11,w=(s.length*8+1)*unit,x=right-w;const cells=[];for(let d=0;d<s.length;d++)digits[Number(s[d])].split('/').forEach((r,j)=>[...r].forEach((v,i)=>{if(v==='1')cells.push([x+(1+d*8+i)*unit,y+(j+1)*unit]);}));for(const [a,b]of cells)rect(a-1,b-1,Math.ceil(unit)+2,Math.ceil(unit)+2,'#101016');const gr=g.createLinearGradient(0,y,0,y+h);gr.addColorStop(0,n===2?'#eaf6ff':n===3?'#f2c69b':'#ff9400');gr.addColorStop(1,n===2?'#8ca5c0':n===3?'#a75d2d':'#ffff30');g.fillStyle=gr;for(const [a,b]of cells)g.fillRect(Math.round(a),Math.round(b),Math.ceil(unit),Math.ceil(unit));}
 function heading(title){rect(0,18,320,34,'#224768');rect(0,50,320,1,'#e1b84e');rect(0,51,320,1,'#87b5d5');text(title,160,25,{title:true,align:'center',color:'#ffdf39',shadow:true,max:305});}
 function panel(title){rect(7,39,306,height-64,'#c7d5ed');rect(8,40,304,height-66,'#284d70');rect(9,41,302,height-68,'#c7d5ed');rect(15,56,290,height-100,'#3e80b9');for(let x=9;x<311;x+=20){rect(x,40,20,11,'#294d70');g.fillStyle='#ffdf56';g.beginPath();g.moveTo(x+7,40);g.lineTo(x+18,40);g.lineTo(x+12,51);g.lineTo(x+1,51);g.fill();}rect(160-title.length*2.5,42,title.length*5,8,'#c7d5ed');text(title,160,42,{align:'center',scale:.65,color:'#1c3e55'});}
 function footer(left,center,right,onleft,oncenter,onright){const y=height-24;rect(0,y,320,24,'#c7d5ed');text(left,3,y+5,{max:104});text(center,160,y+5,{align:'center',max:103});text(right,317,y+5,{align:'right',max:104});zone(0,y,106,24,onleft);zone(106,y,108,24,oncenter);zone(214,y,106,24,onright);}
 function menu(items,focus=0){const w=Math.min(190,Math.max(98,...items.map(i=>i[0].length*6+13))),h=items.length*20+6,y=height-25-h;rect(1,y,w,h,'#315c80');rect(3,y+2,w-4,h-4,'#c7d5ed');items.forEach(([label,fn],i)=>{if(i===focus)rect(3,y+3+i*20,w-4,19,'#ffe270');text(label,8,y+7+i*20,{max:w-14});zone(3,y+3+i*20,w-4,20,fn);});}
 function start(paint){cancelAnimationFrame(raf);let last=-1;function tick(now){const f=Math.floor(now/42);if(f!==last){last=f;frame=f;hits=[];sky();paint();}raf=requestAnimationFrame(tick);}raf=requestAnimationFrame(tick);}
 canvas.addEventListener('pointerup',e=>{const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*320/r.width,y=(e.clientY-r.top)*height/r.height;for(let i=hits.length-1;i>=0;i--){const h=hits[i];if(x>=h.x&&x<h.x+h.w&&y>=h.y&&y<h.y+h.h){h.run?.();break;}}});
 return {g,text,rect,sprite,avatar,aura,rank,heading,panel,footer,menu,zone,start,get height(){return height;},get frame(){return frame;},canvas};
})();
