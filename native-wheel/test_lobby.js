'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
const {ArmyWriter}=require('./viewer/market.js');
const root=path.join(__dirname,'build');fs.mkdirSync(root,{recursive:true});
const w=()=>new ArmyWriter();
const png=fs.readFileSync(path.join(__dirname,'viewer/art/b.png'));
function item(out,i){out.utf('M:'+i).utf('Trang bị '+i).utf('Trang bị').byte(i%10).int(123+i).long(100000).utf('QA').utf('Đồ thử\u001e119,1,0,1,0,'+(i%17)).short(png.length);for(const b of png)out.byte(b);}
(async()=>{
 const browser=await chromium.launch({args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:390,height:592},deviceScaleFactor:2});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.sent=[];window.webkit={messageHandlers:{lobby:{postMessage:a=>sent.push(a)}}};});
 await page.goto(pathToFileURL(path.join(__dirname,'viewer/lobby.html')).href);
 await page.evaluate(()=>openTab('field'));
 assert.deepEqual(await page.evaluate(()=>sent[0]),[-120,Buffer.from([67,84,52,54,1,0,0,0,1,49]).toString('base64')]);
 const rows=[{id:1,rank:1,name:'striker',level:999,hero:0,parts:[54,52,53,55,56],aura:240},{id:2,rank:2,name:'chanbongayde',level:999,hero:1,parts:[51,49,50,52,53],aura:208},{id:3,rank:3,name:'gaplachen',level:808,hero:2,parts:[51,49,50,53,52],aura:176},...Array.from({length:10},(_,i)=>({id:20+i,rank:201+i,name:['outrinh','hiconcho','proivip','querty','chapcasever','obito'][i%6],level:100+i,hero:i%10,parts:[0,0,0,0,0],aura:0}))];
 const board=w().int(1129591862).byte(1).int(1).int(211).int(29).byte(rows.length);
 for(const r of rows)board.int(r.rank).int(r.id).utf(r.name).int(r.level);
 for(const r of rows){board.byte(r.hero);r.parts.forEach(p=>board.short(p));board.byte(48).int(r.aura);}
 board.int(1397050438).int(211).int(29).utf('obito').int(142).byte(1);[51,49,50,52,53].forEach(p=>board.short(p));board.byte(95).int(240);
 await page.evaluate(b=>receiveFrame(-120,b),Buffer.from(board.bytes).toString('base64'));
 await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete));
 await page.waitForTimeout(900);
 await page.screenshot({path:path.join(root,'lobby-battlefield.png')});
 const first=await page.locator('canvas').screenshot();await page.waitForTimeout(400);const second=await page.locator('canvas').screenshot();assert.notDeepEqual(first,second,'Animated aura must advance');
 await page.evaluate(()=>profile());
 const profileWire=w().int(1129591862).byte(2).int(2).int(1).utf('striker').int(999).utf('Gunner').byte(5);for(const v of [50000,1000,900,80,100])profileWire.int(v);
 for(let i=0;i<5;i++)profileWire.short(rows[0].parts[i]).utf('Trang bị '+i).byte(16).byte(7).byte(0);
 profileWire.byte(0);rows[0].parts.forEach(v=>profileWire.short(v));profileWire.byte(1).byte(48).long(20000000).long(2000).int(240).byte(0).int(1145394248).byte(6);
 for(let i=0;i<6;i++){profileWire.byte(i<5?1:0);if(i<5){profileWire.byte(5);for(let j=0;j<5;j++)profileWire.int(j+1);profileWire.byte(5);for(let j=0;j<5;j++)profileWire.int(j);profileWire.int(7).byte(3);}}
 profileWire.int(1195724105).byte(6);for(let i=0;i<6;i++){profileWire.byte(i<5?1:0);if(i<5)profileWire.utf('Ngọc 11').utf('Tăng chỉ số tổng 2%');}
 await page.evaluate(b=>receiveFrame(-120,b),Buffer.from(profileWire.bytes).toString('base64'));
 await page.waitForTimeout(150);await page.screenshot({path:path.join(root,'lobby-profile.png')});
 await page.evaluate(()=>lobbyKey(-5));assert.equal(await page.evaluate(()=>modal.lines.includes('Ngọc 11')),true,'Equipment details preserve inserted gems');await page.evaluate(()=>{lobbyKey(-7);lobbyKey(-7);});
 await page.evaluate(()=>{lobbyKey(-6);lobbyKey(-2);lobbyKey(-5);});
 assert.equal(await page.evaluate(()=>new ArmyReader(Uint8Array.from(atob(sent.at(-1)[1]),c=>c.charCodeAt(0))).bytes[4]),5,'Native keypad menu opens match list');
 await page.evaluate(()=>{unlock();openTab('market');});
 const stock=w().byte(1).utf('test-stock-token').byte(0).short(22);for(let i=0;i<22;i++)item(stock,i);
 await page.evaluate(b=>receiveFrame(-121,b),Buffer.from(stock.bytes).toString('base64'));
 await page.waitForTimeout(300);await page.screenshot({path:path.join(root,'lobby-market.png')});
 await page.evaluate(()=>lobbyKey(-3));assert.equal(await page.evaluate(()=>focus),6,'Chest wraps horizontally within the row');
 await page.evaluate(()=>{focus=21;lobbyKey(-2);});assert.equal(await page.evaluate(()=>focus),0,'Chest wraps vertically to first valid cell');
 await page.evaluate(()=>lobbyKey(-5));assert.equal(await page.locator('#edit input').first().inputValue(),'1');
 await page.evaluate(()=>lobbyKey(-7));assert.equal(await page.locator('#edit').isVisible(),false,'Cancel quantity returns to chest');
 await page.evaluate(()=>{unlock();openTab('event');});
 const event=w().byte(3).byte(0).utf('BXH Sự kiện').int(7).utf('QA1').byte(6).short(0).long(999).byte(50).byte(1);for(let i=0;i<5;i++)event.short(0);event.utf('42');
 await page.evaluate(b=>receiveFrame(-14,b,[240]),Buffer.from(event.bytes).toString('base64'));
 assert.equal(await page.evaluate(()=>reply.rows[0].parts.length),5);assert.equal(await page.evaluate(()=>reply.rows[0].aura),240);
 await page.waitForTimeout(150);await page.screenshot({path:path.join(root,'lobby-event.png')});
 await page.evaluate(()=>lobbyKey(-7));assert.deepEqual(await page.evaluate(()=>sent.at(-1)),['close',0]);
 await page.setViewportSize({width:320,height:240});await page.waitForTimeout(80);assert.equal(await page.evaluate(()=>PixelUI.canvas.width),320);
 assert.deepEqual(errors,[]);
 await browser.close();console.log('PASS lobby wire protocol, aura animation, native keypad, grid wrapping, quantity cancellation, event sprites, host return and compact layout');
})().catch(e=>{console.error(e);process.exitCode=1;});
