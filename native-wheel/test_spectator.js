'use strict';
const assert = require('node:assert/strict');
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
console.log('PASS spectator: 2 fighters, 52 terrain tiles, live shot, invalid sequence, missing data and offsets');
