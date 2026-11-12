#include "../BossMaps.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void be16(uint8_t *p, unsigned n) { p[0] = n >> 8; p[1] = n; }
static void be32(uint8_t *p, unsigned n) { be16(p, n >> 16); be16(p + 2, n); }
static void header(uint8_t *p, int map, int mode, int match) {
    be32(p, map == 41 ? 1146242894U : 1296649521U);
    p[4] = mode;
    be32(p + 5, 0);
    be32(p + 9, match);
}
static void dragon(void) {
    AGBossState s = {0};
    AGBossHole h;
    uint8_t p[94 + 13] = {0};
    header(p, 41, 1, 17);
    be32(p + 13, 1);
    p[22] = 1;
    p[23] = 8;
    p[24] = 2;
    be32(p + 27, 1500);
    be32(p + 31, 2000);
    be16(p + 35, 712);
    be16(p + 37, 255);
    p[47] = 1;
    p[48] = 3;
    p[95] = 21;
    p[106] = 8;
    assert(AGBossRead(&s, 41, p, sizeof p, 1000, &h) == AGBossSnapshot);
    assert(s.actors[8].hp == 1500 && s.humans[0].burn == 3 && s.focus == 8);
    assert(AGBossRead(&s, 41, p, sizeof p, 1001, &h) == AGBossIgnored);
    be32(p + 13, 2);
    be32(p + 27, 1400);
    be16(p + 35, 812);
    be16(p + 45, 200);
    assert(AGBossRead(&s, 41, p, sizeof p, 1010, &h) == AGBossSnapshot);
    int x, y;
    AGBossPosition(&s.actors[8], 1110, &x, &y);
    assert(x == 762 && y == 255 && s.actors[8].damage == 100);
    p[48] = 4;
    be32(p + 13, 3);
    assert(AGBossRead(&s, 41, p, sizeof p, 1300, &h) == AGBossInvalid);
    assert(s.sequence == 2 && s.humans[0].burn == 3);
    header(p, 41, 2, 17);
    be16(p + 13, 10);
    be16(p + 15, 11);
    be16(p + 17, 1);
    assert(AGBossRead(&s, 41, p, 19, 1320, &h) == AGBossTerrain);
    const AGBossTile tile = {90, 9, 10};
    uint32_t pixels[9];
    for (int i = 0; i < 9; ++i) pixels[i] = 0xffaa5522;
    assert(AGBossModifyTile(&h, 41, &tile, 3, 3, pixels));
    assert(pixels[0] && pixels[8] && !pixels[1] && !pixels[4] && !pixels[7]);
    assert(!AGBossModifyTile(&h, 41, &tile, 3, 3, pixels));
}
static void mimic(void) {
    AGBossState s = {0};
    AGBossHole h;
    uint8_t p[38] = {0};
    header(p, 42, 1, 33);
    be32(p + 13, 1);
    p[17] = 8;
    p[18] = 9;
    p[19] = 255;
    p[20] = 1;
    be32(p + 22, 2900);
    be32(p + 26, 3000);
    be16(p + 30, 390);
    be16(p + 32, 290);
    assert(AGBossRead(&s, 42, p, sizeof p, 100, &h) == AGBossSnapshot);
    assert(s.actors[8].dark && s.actors[8].form == -1 && !s.actors[9].hp);
    assert(s.blindUntil == 1250 && s.actors[8].x == 390);
    be32(p + 13, 2);
    p[19] = 2;
    p[20] = 0;
    p[21] = 1;
    be16(p + 34, 590);
    assert(AGBossRead(&s, 42, p, sizeof p, 1300, &h) == AGBossSnapshot);
    assert(!s.actors[8].dark && s.actors[8].form == 2 && s.actors[9].hp == 2900 &&
        s.actors[9].x == 590 && s.actors[9].echo);
    header(p, 42, 3, 33);
    be16(p + 13, 10);
    be16(p + 15, 11);
    be16(p + 17, 2);
    be16(p + 19, 2);
    p[21] = 1;
    p[22] = 2;
    p[23] = 0;
    p[24] = 2;
    assert(AGBossRead(&s, 42, p, 25, 1410, &h) == AGBossTerrain);
    uint32_t pixels[] = {0xffffffff, 0xffffffff, 0xff00ffff, 0};
    AGBossTile t = {102, 9, 10};
    assert(!AGBossModifyTile(&h, 42, &t, 2, 2, pixels));
    t.id = 97;
    assert(AGBossModifyTile(&h, 42, &t, 2, 2, pixels));
    assert(!pixels[0] && pixels[1] == 0xff000000 && pixels[2] == 0xff00ffff && !pixels[3]);
    header(p, 42, 0, 33);
    assert(AGBossRead(&s, 42, p, 13, 1430, &h) == AGBossSnapshot && s.finished);
    header(p, 42, 3, 33);
    assert(AGBossRead(&s, 42, p, 25, 1450, &h) == AGBossIgnored);
}
static void maps(int argc, char **argv) {
    for (int i = 1; i < argc; ++i) {
        FILE *f = fopen(argv[i], "rb");
        assert(f);
        uint8_t raw[139];
        size_t n = fread(raw, 1, sizeof raw, f);
        fclose(f);
        int id = i == 1 ? 41 : 42;
        AGBossMap spec;
        assert(AGBossParseMap(id, raw, n, &spec));
        assert(spec.count == (id == 41 ? 20 : 10));
        assert(!AGBossParseMap(id, raw, n - 1, &spec));
    }
}
int main(int argc, char **argv) {
    dragon();
    mimic();
    maps(argc, argv);
    uint8_t roster[22] = {1, 255, 255, 255, 255, 0, 2, 'H', 'P'};
    roster[17] = 29;
    assert(!AGBossRosterAlias(roster, sizeof roster - 1));
    assert(AGBossRosterAlias(roster, sizeof roster) && roster[17] == 25);
    puts("PASS map definitions, boss snapshots, movement, HP, terrain and clone states");
}
