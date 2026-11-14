'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({args:['--no-sandbox'],executablePath:process.env.ARMY2_CHROMIUM});
 try{
  const page=await browser.newPage({viewport:{width:390,height:590}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{window.sent=[];window.webkit={messageHandlers:{viewer:{postMessage:value=>sent.push(value)}}};});
  await page.goto(pathToFileURL(path.join(__dirname,'viewer/native-watch.html')).href);
  const setPhase=(p,text='')=>page.evaluate(([p,text])=>setWatchPhase(p,text),[p,text]);
  const press=k=>page.evaluate(k=>watchKey(k),k);
  const last=()=>page.evaluate(()=>sent.at(-1));
  await setPhase(0,'Khu vực đang chiến đấu bạn có muốn xem');
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>PixelUI.g.getImageData(100,100,1,1).data[3]),0,'Area list remains visible');
  assert.equal(await page.evaluate(()=>PixelUI.g.getImageData(100,PixelUI.canvas.height-58,1,1).data[3]),255,'Dialog is at the bottom');
  await press(-22);assert.equal(await last(),'decline');
  await setPhase(-1);await setPhase(0);
  await press(13);assert.equal(await last(),'accept');
  await press(-6);assert.equal(await page.evaluate(()=>sent.filter(x=>x==='accept').length),1);
  await setPhase(2);await press(-21);assert.equal(await last(),'menuOpen');
  assert.deepEqual(await page.evaluate(()=>options().map(x=>x[0])),[
   'TIẾP TỤC','LỰC MAX','V9 MENU','BẬT/TẮT ICON ĐỘI','BẠN BÈ','TIN NHẮN','RỜI TRẬN CHIẾN']);
  assert.equal(await page.evaluate(()=>sent.includes('leave')),false);
  await press(13);assert.equal(await last(),'menuClosed');
  await press(-7);assert.equal(await last(),'camera');
  await press(-6);await press(-1);await press(-5);assert.equal(await last(),'leave');
  await setPhase(-1);await setPhase(2);await page.waitForTimeout(100);
  await page.mouse.click(360,16);assert.equal(await page.evaluate(()=>pbs),true);
  await page.waitForTimeout(70);await page.mouse.click(72*390/320+44,60);
  assert.deepEqual(await last(),['pb',2]);
  assert.deepEqual(errors,[]);
  console.log('PASS spectator controls: transparent confirmation, left/OK and decline, ordered in-match menu, camera, leave and PB selector.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
