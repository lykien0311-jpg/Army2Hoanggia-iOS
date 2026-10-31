# iOS 2.4.1 build 243 completed locally

Input SHA fc465ce2855da8d4430acaaf6fccdd67b9b4491058bfd196d5928c361a3492ba, supplied Army2Hoanggia-2.4.1(1).ipa. Final package and validation hashes: validation-ui79.json.

Apple Xcode 16.4 build: GitHub Actions 41147494762, branch 0fe1c6bbf24d4d7044805fb26fe4032862443834, tested PR merge eec95a6d32b84f153f5de1c7284323bc43c606ba. Exact device dylib SHA b3bff49771313c52b49566f97ebaa8add94111358d3e6a8cfa8dbca076c089db. Apple strict codesign and re-sign verification passed. No Linux-built dylib.

Included: wheel/V9 responsive game viewport with keypad retained, blank amount entry and keyboard-aware controls; captcha game viewport/key forwarding and redundant bottom buttons removed; wide adaptive inventory and both shops (up to seven columns), updated tap/nav/drag/scroll metrics and resize row counts; packet118 clan member readShort fix; ticketed UFO Turn33 receive/tick/manual fire cancellation using original native shot entry; Room32 boss preview lookup instead of map minus 18.

UFO: server -115 mode/21-byte aim and cmd24 17-byte turn announcement observed without consuming the native stream. Guards include active scene identity, same connection, local player and current owner, turn/ticket, exact origin, force/angle ranges, pending/manual/duplicate, movement/flight, native dialogs, manual captcha and foreground. Server computes the aim; the client invokes the native shot routine. No captcha automation.

Validation: 36 clan fixtures; 156 actual Apple ARM64 UFO cases; 624 native/Apple grid layout, keyboard, pointer and drag cases; 444 Apple Notes bridge assertions; 12 native OK transitions; 25 native login/version cases; six Simulator viewports and six manual captcha modes. Existing wheel, room and movement tests also passed. test_grid_device.py, test_turn_device.py and test_boss_preview.py preserve new checks. Arm64 tests mock UIKit/OS/Java/network primitives; they do not constitute an iPhone/VPS integration test.

No VPS change, physical iPhone test or new signing certificate. Re-sign the IPA using the user's certificate. Login marker remains 2.4.1-HG78-IPA; bundle build243. Native resources: 522 of 525 archive entries unchanged. Supplied APK Army2HoangGia(2).apk retained as reference only; not modified.
