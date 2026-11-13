/* Decode the ordinary PvP spectator stream emitted by SpectatorFight53. */
'use strict';
class ArmyReader {
    constructor(bytes) {
        this.bytes = bytes;
        this.view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        this.pos = 0;
    }
    take(n) {
        if (n < 0 || n > this.bytes.length - this.pos) throw Error('Gói tin thiếu dữ liệu');
        const at = this.pos;
        this.pos += n;
        return at;
    }
    u8() { return this.view.getUint8(this.take(1)); }
    i8() { return this.view.getInt8(this.take(1)); }
    u16() { return this.view.getUint16(this.take(2)); }
    i16() { return this.view.getInt16(this.take(2)); }
    i32() { return this.view.getInt32(this.take(4)); }
    hp() {
        const hi = this.i32(), lo = this.view.getUint32(this.take(4));
        if (hi !== 0) throw Error('HP ngoài phạm vi server');
        return lo;
    }
    utf() {
        const n = this.u16(), end = this.pos + n;
        if (end > this.bytes.length) throw Error('Tên quá dài');
        let out = '';
        while (this.pos < end) {
            const a = this.u8();
            if (a < 128) { out += String.fromCharCode(a); continue; }
            const three = (a & 240) === 224;
            if (!three && (a & 224) !== 192) throw Error('UTF');
            if (this.pos + (three ? 2 : 1) > end) throw Error('UTF');
            const b = this.u8();
            if ((b & 192) !== 128) throw Error('UTF');
            if (!three) out += String.fromCharCode((a & 31) << 6 | b & 63);
            else {
                const c = this.u8();
                if ((c & 192) !== 128) throw Error('UTF');
                out += String.fromCharCode((a & 15) << 12 | (b & 63) << 6 | c & 63);
            }
        }
        return out;
    }
    end() { if (this.pos !== this.bytes.length) throw Error('Gói tin thừa dữ liệu'); }
}

function readArmyShot(r) {
    const format = r.u8(), pow = r.u8(), player = r.u8(), bullet = r.u8();
    if (format > 1) throw Error('Dạng quỹ đạo chưa hỗ trợ');
    const x = r.i16(), y = r.i16(), angle = r.i16();
    if (bullet === 17 || bullet === 19) r.take(1);
    if (bullet === 14 || bullet === 40) r.take(2);
    if ([44,45,47].includes(bullet)) r.take(1);
    r.u8();
    const count = r.u8(), paths = [];
    for (let i = 0; i < count; i++) {
        const n = r.u16(), points = [];
        let px = x, py = y;
        for (let j = 0; j < n; j++) {
            if (!j || format === 1 || (bullet === 49 && j === n - 1)) {
                px = r.i16(); py = r.i16();
                if (format === 0 && j > 0 && bullet === 49 && j === n - 1) r.take(2);
            } else {
                px += r.i8(); py += r.i8();
            }
            points.push([px,py]);
        }
        paths.push(points);
        if (bullet === 48) r.take(r.u8() * 4);
    }
    const impacts=[];
    const effect = r.u8();
    if (effect === 1 || effect === 2) r.take(4);
    if (r.pos < r.bytes.length) {
        if (r.i32() !== 1112552752) throw Error('Phần mở rộng đạn chưa hỗ trợ');
        const count=r.u16();
        if(count>128)throw Error('Quá nhiều điểm sát thương');
        for(let i=0;i<count;i++)impacts.push({projectile:r.u8(),sample:r.u16(),slot:r.u8(),delta:r.i32(),max:r.i32()});
    }
    r.end();
    return {player,bullet,pow,x,y,angle,paths,impacts};
}

class ArmySpectator {
    constructor(onTile) {
        this.onTile = onTile;
        this.phase = 'waiting';
        this.players = [];
        this.nextTile = 0;
        this.buffer = null;
        this.imagePixels = 0;
        this.turn = -1;
        this.wind = [0,0];
    }
    setHealth(slot, hp, max) {
        const actor=this.players[slot];
        if(!actor)return;
        const before=actor.hp;
        if(max>0)actor.max=max;
        actor.hp=Math.max(0,hp);
        if(this.phase==='live'&&before!==undefined&&before!==actor.hp)
            this.onHealth?.(actor,actor.hp-before);
    }
    receive(cmd, bytes) {
        const r = new ArmyReader(bytes);
        if (cmd === -102) return this.control(r);
        if (this.phase === 'waiting') return;
        if (cmd === 8 && this.phase === 'terrain') {
            r.take(10);
            for (let i = 0; i < 8; i++) {
                const id=r.i32();if (id === -1) continue;
                const clan=r.i16();
                const name = r.utf();
                r.take(16);
                const character = r.u8();
                const parts=Array.from({length:5},()=>r.i16());
                r.take(2);
                this.players[i] = {id,clan,name,character,parts};
            }
            r.end();
        } else if (cmd === 89) {
            const n = r.u8(), spawned = [];
            for (let i = 0; i < n; i++) {
                r.i32();
                const name = r.utf(), max = r.hp(), character = r.u8();
                spawned.push({name, character, max, hp:max, x:r.i16(), y:r.i16()});
            }
            let slot = Math.max(8,this.players.length);
            if (n === 1 && r.bytes.length - r.pos === 5 && r.i32() === 1379154225) slot = r.u8();
            r.end();
            for (const actor of spawned) this.players[slot++] = actor;
        } else if (cmd === 21 || cmd === 93) {
            const actor = this.players[r.u8()], x = r.i16(), y = r.i16();
            if (actor) Object.assign(actor,{x,y});
        } else if (cmd === 51) {
            const slot = r.u8(), hp = r.hp();
            r.i8(); r.end();
            this.setHealth(slot,hp);
        } else if (cmd === 106 || cmd === 107) {
            const ending=r.u8(),actor=this.players[r.u8()];r.end();
            if(actor)actor[cmd===106?'blind':'frozen']=!ending;
        } else if (cmd === 108) {
            const actor=this.players[r.u8()];if(actor)actor.poison=true;
        } else if (cmd === 24) {
            this.turn = r.u8();
            this.seconds = r.pos<r.bytes.length?r.u8():40;
        } else if (cmd === 25) {
            this.wind = [r.i8(),r.i8()];
        } else if ((cmd === 22 || cmd === 84) && this.phase === 'live') {
            return readArmyShot(r);
        }
    }
    control(r) {
        if (r.u16() !== 21328 || r.u8() !== 1) throw Error('Phiên bản Xem trận');
        const op = r.u8();
        if (op === 3) {
            if (this.phase !== 'waiting') throw Error('Trùng đầu trận');
            this.room = r.u8(); this.area = r.u8(); r.take(8);
            this.map = r.u8(); this.width = r.u16(); this.height = r.u16(); this.tiles = r.u16();
            if (this.room > 1 || !this.width || !this.height || this.tiles > 4096) throw Error('Kích thước bản đồ');
            this.phase = 'terrain';
        } else if (op === 4) {
            if (this.phase !== 'terrain') throw Error('Ảnh ngoài phiên');
            const index = r.u16(), id = r.i32(), x = r.i16(), y = r.i16(), solid = r.u8();
            const total = r.i32(), offset = r.i32(), size = r.u16();
            if (index !== this.nextTile || index >= this.tiles || total < 24 || total > 8000000 ||
                !size || size > 24000 || size !== r.bytes.length - r.pos || offset < 0 || size > total-offset)
                throw Error('Mảnh địa hình không hợp lệ');
            if (offset === 0) {
                if (this.buffer) throw Error('Ảnh trước chưa đủ');
                this.buffer = {id,x,y,solid,bytes:new Uint8Array(total),received:0};
            }
            const b = this.buffer;
            if (!b || b.id !== id || b.x !== x || b.y !== y || b.solid !== solid ||
                b.bytes.length !== total || b.received !== offset) throw Error('Sai thứ tự ảnh');
            b.bytes.set(r.bytes.subarray(r.take(size)), offset); b.received += size;
            if (b.received === total) {
                const png = new DataView(b.bytes.buffer);
                if (png.getUint32(0) !== 0x89504e47 || png.getUint32(4) !== 0x0d0a1a0a ||
                    png.getUint32(12) !== 0x49484452) throw Error('Ảnh địa hình');
                const pixels = png.getUint32(16) * png.getUint32(20);
                this.imagePixels += pixels;
                if (!pixels || this.imagePixels > 16000000) throw Error('Ảnh địa hình quá lớn');
                if (this.onTile) this.onTile(b);
                this.buffer = null; this.nextTile++;
            }
        } else if (op === 5) {
            if (this.phase !== 'terrain' || this.buffer || this.nextTile !== this.tiles) throw Error('Thiếu địa hình');
            this.seconds = r.u8();
            for (let i=0; i<8; i++) {
                const x = r.i16();
                if (x === -1) continue;
                if (!this.players[i]) throw Error('Thiếu người chơi');
                const y = r.i16(), max = r.hp();
                Object.assign(this.players[i],{x,y,max,hp:max});
            }
            this.phase = 'positions';
        } else if (op === 7) {
            if (this.phase !== 'positions') throw Error('Thứ tự đồng bộ trận');
            this.seconds = r.u8(); this.phase = 'live';
        } else { throw Error('Gói điều khiển Xem trận'); }
        r.end();
    }
}
if (typeof module !== 'undefined') module.exports = {ArmyReader, ArmySpectator, readArmyShot};
