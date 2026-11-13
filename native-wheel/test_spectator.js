'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {ArmySpectator} = require('./viewer/protocol.js');
const trace = require('./testdata/watch-pvp.json').map(([c,b])=>[c,Buffer.from(b,'base64')]);
const packets = trace.filter(([c,b])=>c!==-102||![0,6].includes(b[3]));
const tiles = [], game = new ArmySpectator(tile=>tiles.push(tile));
const shots = [];
for(const [c,b] of packets) {
    const shot=game.receive(c,b);
    if(shot)shots.push(shot);
}
assert.equal(game.phase,'live');
assert.equal(tiles.length,52);
assert.equal(game.players.length,2);
assert.deepEqual(game.players.map(a=>a.name),['qahost','qaguest']);
assert.ok(game.players.every(a=>Number.isFinite(a.x)&&Number.isFinite(a.y)&&a.hp>0));
assert.ok(shots.length===1&&shots[0].paths[0].length>1);
const controls=packets.filter(([c])=>c===-102).map(([,b])=>b);
const begin=controls.find(b=>b[3]===3), tile=controls.find(b=>b[3]===4), positions=controls.find(b=>b[3]===5);
const incomplete=new ArmySpectator();
incomplete.receive(-102,begin);
assert.throws(()=>incomplete.receive(-102,positions));
const wrongOffset=Buffer.from(tile);wrongOffset.writeInt32BE(24000,19);
assert.throws(()=>incomplete.receive(-102,wrongOffset));
incomplete.receive(-102,tile);
assert.throws(()=>incomplete.receive(-102,tile));
assert.throws(()=>new ArmySpectator().receive(-102,begin.subarray(0,12)));
assert.throws(()=>game.receive(22,Buffer.from([0,1,2])));
const reports = [], images = [];
const timers=[];
const screen = vm.createContext({
    window:{webkit:{messageHandlers:{viewer:{postMessage:message=>reports.push(message)}}}},
    document:{getElementById:()=>({}),createElement:()=>({getContext:()=>({drawImage(){},putImageData(){},getImageData:()=>({data:new Uint8Array(4)})})})},
    PixelUI:{start(){},g:{},canvas:{addEventListener(){}}},
    addEventListener:()=>{},performance:{now:()=>0},
    setTimeout:fn=>timers.push(fn),
    Image:class { constructor(){this.width=1;this.height=1;images.push(this);} },
    atob,btoa,
});
for(const file of ['protocol.js','screen.js']) {
    vm.runInContext(fs.readFileSync(__dirname+'/viewer/'+file,'utf8'),screen,{filename:file});
}
const masks=images.filter(image=>image.src.startsWith('data:'));
const startingImages=images.length;
screen.window.receiveArmyFrames(packets.map(([command,bytes])=>[command,bytes.toString('base64')]));
const terrain=images.slice(startingImages);
assert.equal(terrain.length,52);
assert.equal(masks.length,9);
assert.deepEqual(reports,['ready']);
for(const image of terrain) image.onload();
assert.equal(vm.runInContext('shot',screen),null,'Shot waits until terrain and masks are ready');
assert.deepEqual(reports,['ready']);
for(const image of masks)image.onload();
assert.deepEqual(reports,['ready','live']);
const {setWatchPhase,watchKey}=screen.window;
setWatchPhase(0,'Khu vực đang chiến đấu bạn có muốn xem');
watchKey(-7);
watchKey(-6);
assert.equal(reports.at(-1),'decline');
setWatchPhase(0,'Khu vực đang chiến đấu bạn có muốn xem');
watchKey(-6);
assert.equal(reports.at(-1),'accept');
setWatchPhase(0,'Khu vực đang chiến đấu bạn có muốn xem');
watchKey(-5);
assert.deepEqual(reports.slice(-3),['decline','accept','accept']);
setWatchPhase(2,'');
watchKey(-6);
watchKey(-1);
watchKey(-5);
assert.equal(reports.at(-1),'leave');
const hit=Buffer.alloc(10);hit[0]=1;hit.writeBigUInt64BE(770n,1);
const end=Buffer.from([0x53,0x50,1,6]);
screen.window.receiveArmyFrames([[51,hit.toString('base64')],[-102,end.toString('base64')]]);
assert.equal(vm.runInContext('game.players[1].hp',screen),1000);
vm.runInContext('updateShot((shot.samples-1)*FRAME_MS)',screen);
assert.equal(vm.runInContext('game.players[1].hp',screen),770);
assert.equal(vm.runInContext('numbers.at(-1).delta',screen),-230);
assert.equal(reports.at(-1),'leave');
timers.at(-1)();assert.equal(reports.at(-1),'ended');
console.log('PASS spectator: await terrain and masks, enter with left/OK, decline, leave, HP change at impact without extra frame delay, final HP before returning');
