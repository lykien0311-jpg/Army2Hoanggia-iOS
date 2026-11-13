'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
const trace=require('./testdata/watch-pvp.json');

function health(hp){
 const bytes=Buffer.alloc(10);bytes[0]=1;bytes.writeBigInt64BE(BigInt(hp),1);
 return [51,bytes.toString('base64')];
}
function shot(bullet,points,events=[]){
 const base=Buffer.alloc(15+4*points.length+(bullet===14?2:0));
 base[0]=1;base[3]=bullet;base.writeInt16BE(114,8);base[11]=1;
 const count=bullet===14?13:11;
 base[count]=1;base.writeUInt16BE(points.length,count+1);
 points.forEach(([x,y],i)=>{base.writeInt16BE(x,count+3+4*i);base.writeInt16BE(y,count+5+4*i);});
 if(!events.length)return [22,base.toString('base64')];
 const extension=Buffer.alloc(6+12*events.length);
 extension.writeUInt32BE(1112552752,0);extension.writeUInt16BE(events.length,4);
 events.forEach(([sample,delta],i)=>{
  const pos=6+i*12;extension.writeUInt16BE(sample,pos+1);extension[pos+3]=1;
  extension.writeInt32BE(delta,pos+4);extension.writeInt32BE(1000,pos+8);
 });
 return [22,Buffer.concat([base,extension]).toString('base64')];
}

(async()=>{
 const browser=await chromium.launch({args:['--no-sandbox'],executablePath:process.env.ARMY2_CHROMIUM});
 const page=await browser.newPage({viewport:{width:390,height:548}});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.addInitScript(()=>{
  window.reports=[];window.webkit={messageHandlers:{viewer:{postMessage:x=>reports.push(x)}}};
 });
 await page.goto(pathToFileURL(path.join(__dirname,'viewer/index.html')).href);
 const confirmation='Khu vực đang chiến đấu bạn có muốn xem';
 await page.evaluate(text=>setWatchPhase(0,text),confirmation);
 await page.waitForFunction(()=>PixelUI.frame>1);
 await page.keyboard.press('Enter');
 await page.waitForFunction(()=>reports.includes('accept'));
 await page.evaluate(()=>setWatchPhase(2,''));
 const snapshot=trace.filter(([cmd,payload])=>cmd!==22&&(cmd!==-102||[3,4,5,7].includes(Buffer.from(payload,'base64')[3])));
 await page.evaluate(frames=>receiveArmyFrames(frames),snapshot);
 await page.waitForFunction(()=>reports.includes('live'));
 const impactPoints=[[465,385],[493,448],[510,514]];
 const result=await page.evaluate(([projectile,hp])=>{
  const target=tiles.find(t=>t.x===501&&t.y===507&&t.solid);
  const pixels=(x,y)=>Array.from(target.ctx.getImageData(x,y,1,1).data);
  const sample=()=>[pixels(9,7),pixels(9,22),pixels(9,31),game.players[1].hp,numbers.map(v=>v.delta)];
  const before=sample();receiveArmyFrames([projectile,hp]);
  updateShot(30);const mid=sample();updateShot(30);return {before,mid,after:sample()};
 },[shot(0,impactPoints),health(770)]);
 assert.equal(result.before[0][3],255);
 assert.deepEqual(result.mid,result.before,'Unchanged while the projectile is airborne');
 assert.equal(result.after[0][3],0,'A real terrain pixel at the impact becomes transparent');
 assert.deepEqual(result.after[1],[0,0,0,255],'The server mask leaves a black rim');
 assert.deepEqual(result.after[2],result.before[2],'Pixels below the crater are undisturbed');
 assert.deepEqual(result.after.slice(3),[770,[-230]],'The server health update reduces the bar and displays damage at impact');

 const traceResult=await page.evaluate(([projectile,hp,laser])=>{
  const target=tiles.find(t=>t.x===541&&t.y===507&&t.solid);
  const center=()=>target.ctx.getImageData(10,7,1,1).data[3];
  const original=center();receiveArmyFrames([projectile,hp]);
  updateShot(30);const exact=game.players[1].hp;updateShot(30);
  const final=[game.players[1].hp,numbers.map(v=>v.delta)];
  receiveArmyFrames([laser]);updateShot(60);return [original,center(),exact,final];
 },[shot(0,[[465,385],[493,448],[705,480]],[[1,-170]]),health(600),shot(14,[[495,410],[510,458],[551,514]])]);
 assert.deepEqual(traceResult,[255,255,600,[600,[-230,-170]]],'Exact hit timestamps avoid double damage and a laser preserves terrain');
 const root=path.join(__dirname,'build');fs.mkdirSync(root,{recursive:true});
 await page.screenshot({path:path.join(root,'watch-impact.png')});
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('PASS spectator browser rendering: crater, black rim, real HP bar update and damage text, timed hits without duplication, laser preserves ground');
})().catch(error=>{console.error(error);process.exit(1);});
