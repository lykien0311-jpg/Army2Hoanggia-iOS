# In-progress UI79 and clan member repair

Active request: responsive wheel/keypad, blank bet input, captcha keypad, wide inventory/equipment/special shops, UFO auto/map identity, and Menu → Thành viên opens no list (31023(1).mp4).

Latest UI test build succeeded: GitHub Actions 41072601217, artifact 12985316889, head 923b57a8d51a9bc745576d2519a14e6441a2d367, PR merge build fe7760161e69f5e30c95bd836aba755c472bcd75. Apple dylib SHA ee915aa852a065b374b645ce11666e1c45ff0cddd93b6aa25b2c26b66d7ffd76. Not a final delivered IPA. Six wheel viewport tests and six captcha modes passed; preview captcha images needed cache invalidation (now fixed in source).

Confirmed clan defect: packet118 member rank is server writeShort, native parser used readByte at six guarded sites. Corrected readShort. test_clan_members.py executes real six ARM64 parser blocks with mocked IO/allocation. 36 fixtures (empty, 1,10 members; pages0,12,25,30) pass. Original parser fails all6. Server source inspected was Notes77 ClanManager; latest Notes78 only login changes per prior verified packaging. No live VPS access.

Inventory: 546 static instruction hooks, Apple compiled AGGridAdjust, game-thread AGInventoryTick. Prior local test_grid_device.py (not committed; lost on user-message workspace reset) executed 78 layout/native paint cases (6 variants ×3screens×4sizes plus native c6/U5 paint) successfully. Need reconstruct and persist this test, add d6 paint/touch/navigation/scroll tests. Focus scroll metric now separated from scroll limit; pending fresh Apple build. Shop layout needs review of resize row counts. Captcha image cache fixture reset fixed.

IMPORTANT workspace resets to old snapshot on new user messages. GitHub branch is authoritative; fetch modified files before editing. Uncommitted investigation/artifacts can vanish.

UFO root finding: server Auto31 handles lobby auto-start, sends mode and 21-byte aim packets with command -115. Native IPA has NO Turn33 equivalent. This explains auto-start without firing. Server sends turn ticket trailer in cmd24 (magic1429485652 + int turn + long ticket); mode magic0x55464F00 (4 bytes); aim int turn,byte owner,long ticket,ushort angle,byte force,byte release,short originX,short originY. JAR game/Turn33 implements receive/changed/pulse/manualShot. Need port to native and verify actual shot dispatch/turn and arena guards; NOT IMPLEMENTED yet. All manual captcha retained.
Sources available by extracting game/Turn33.class and game/Room32.class from current server/client/Army2D-Kien.jar, CFR. Server Auto31 is army2/fight/Auto31.class.
Room32 boss map mapping:30/31→12,32→13,33→14,34→15,35→16,36→17,37→22,38→23,39→24,40→15.
Server Room nType map: boss offsets0→30,1→31,2→32,3→33,4→34,5/6→35,7→36,8→37,9→38,10→39,11/12 linked,13→40. Exp28.room changes money only. Native room preview still may map wrong: screenshot room9 area6 header36 Khu vực cấm with Trex. Do not claim this repaired. Existing static reference room titles can mask actualserver labels.

Native reverse: probe.py uses work/validation/inspect-ipa/Army2Hoanggia original. game/R5 room class2086cb0, game/T battle2088950; methods in metadata. R5.l55884c huge; n55df18 noauto. Original native noauto strings except frameworks. T.y0(III)V5697164 etc. Need trace server -115 dispatch and actual shot rather than rename.
Last source of user-facing IPA is Library libfile_a6445654335c8191a7bddd6059dc71dd (Army2Hoanggia-2.4.1-Notes78-GitHub.ipa SHAfc465ce2855da8d4430acaaf6fccdd67b9b4491058bfd196d5928c361a3492ba).
Current server ZIP libfile_879361786094819195704ee920afa6f7 SHA40440fbcc30fe1032474b8cc7227e3066ffd0fe63d669f7eed603f54a72bc200.
Packaging supports upload/Army2Hoanggia(2).ipa checksum b5fd4e77c62bb6751f53142711588ba0646dfe73e519bf2d504d4f9010ecc7cd as baseline. Exact GitHub Apple dylib only. No Linux-built dylib. Keep2.4.1-HG78-IPA login gate; bump build243 on final. Package before native tests (it rewrites validation fixtures).
No new final IPA has been delivered for UI79/clan. Do not report finished all scope until UFO and grid interaction verified.
