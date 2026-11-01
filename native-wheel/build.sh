#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
python3 test_ufo_auto.py
python3 test_protocol.py
python3 test_rooms.py
python3 test_movement.py
sdk="$(xcrun --sdk iphoneos --show-sdk-path)"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$sdk" -miphoneos-version-min=12.0 \
  -dynamiclib -fobjc-arc -fblocks -fvisibility=hidden -O1 -Wall -Wextra \
  -Wno-unused-parameter -Wno-deprecated-declarations -Wno-unused-function \
  -framework UIKit -framework Foundation -framework QuartzCore -framework CoreGraphics \
  -Wl,-headerpad,4000 -Wl,-install_name,@executable_path/Frameworks/AGWheel.dylib \
  AGWheel.m GameViewport.m GridLayout.c Turn33.c UfoAuto.c Notes77.m NotesProtocol.c WheelProtocol.c RoomNames.c RoomBridge.c Movement.c NativeGuard.S \
  -o build/AGWheel.dylib
codesign --force --sign - --timestamp=none build/AGWheel.dylib
codesign --verify --strict --verbose=2 build/AGWheel.dylib 2>build/code-signing.txt
codesign --display --verbose=4 build/AGWheel.dylib 2>>build/code-signing.txt
mkdir -p build/resign-check
cp build/AGWheel.dylib build/resign-check/AGWheel.dylib
codesign --force --sign - --timestamp=none build/resign-check/AGWheel.dylib
codesign --verify --strict --verbose=2 build/resign-check/AGWheel.dylib 2>>build/code-signing.txt
xcrun nm -gU build/AGWheel.dylib > build/exports.txt
xcrun otool -l build/AGWheel.dylib > build/load-commands.txt
shasum -a 256 build/AGWheel.dylib > build/SHA256.txt
python3 - <<'PY'
import hashlib,json,pathlib,subprocess
p=pathlib.Path('build/AGWheel.dylib');exports=pathlib.Path('build/exports.txt').read_text()
for name in ('AGWheelOpen','AGWheelTick','AGWheelReceive','AGRoomReceive','AGRoomRebuild','AGMoveAllow','AGNotesReceive','AGNotesInput','AGNotesSettings','AGNotesInbox','AGGridAdjust','AGWheelSuppressFooter','AGTurnReceive','AGTurnManual','AGTurnPulse','AGTurnChange','AGTurnAwait','AGTurnStatusUpdate','AGViewportKeypad'):
    assert '_'+name in exports,name
assert 'AGWheelPreview' not in exports,'Simulator fixtures in device dylib'
assert '_AGReleaseIdentity' in exports and b'2.4.1-HG78-IPA\0' in p.read_bytes()
info={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
      'release_version':'2.4.1','login_marker':'2.4.1-HG78-IPA',
      'xcode':subprocess.check_output(['xcodebuild','-version'],text=True).strip(),
      'compiler':subprocess.check_output(['xcrun','--sdk','iphoneos','clang','--version'],text=True).splitlines()[0],
      'sdk':subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-version'],text=True).strip(),
      'dylib_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
      'apple_codesign_strict_verified':True,'apple_resign_strict_verified':True,
      'physical_device_tested':False}
pathlib.Path('build/build-info.json').write_text(json.dumps(info,indent=2)+'\n')
PY

# The Simulator app loads a signed embedded library built from the same sources.
# Fixtures and their exports are excluded from the iPhone device dylib.
sim_sdk="$(xcrun --sdk iphonesimulator --show-sdk-path)"
sim_arch="$(uname -m)"
mkdir -p build/WheelPreview.app/Frameworks
cp captcha-preview-fixtures.json build/WheelPreview.app/
xcrun --sdk iphonesimulator clang -arch "$sim_arch" -isysroot "$sim_sdk" \
  -mios-simulator-version-min=16.0 -DAG_WHEEL_PREVIEW=1 -dynamiclib \
  -fobjc-arc -fblocks -fvisibility=hidden -O1 -Wno-deprecated-declarations \
  -framework UIKit -framework Foundation -framework QuartzCore -framework CoreGraphics \
  -Wl,-headerpad,4000 -Wl,-install_name,@rpath/libAGWheelPreview.dylib \
  AGWheel.m GameViewport.m GridLayout.c Turn33.c UfoAuto.c Notes77.m NotesProtocol.c WheelProtocol.c RoomNames.c RoomBridge.c Movement.c \
  -o build/WheelPreview.app/Frameworks/libAGWheelPreview.dylib
xcrun --sdk iphonesimulator clang -arch "$sim_arch" -isysroot "$sim_sdk" \
  -mios-simulator-version-min=16.0 -fobjc-arc -fblocks -O1 -framework UIKit \
  -Lbuild/WheelPreview.app/Frameworks -lAGWheelPreview -Wl,-rpath,@executable_path/Frameworks \
  Preview.m -o build/WheelPreview.app/WheelPreview
python3 - <<'PY'
import plistlib
p={'CFBundleIdentifier':'vn.army2hoanggia.wheelpreview','CFBundleExecutable':'WheelPreview','CFBundleName':'WheelPreview','CFBundleVersion':'2','CFBundleShortVersionString':'2.0','CFBundlePackageType':'APPL','MinimumOSVersion':'16.0','LSRequiresIPhoneOS':True,'UILaunchScreen':{},'UIDeviceFamily':[1,2],'UISupportedInterfaceOrientations':['UIInterfaceOrientationPortrait','UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']}
with open('build/WheelPreview.app/Info.plist','wb') as f:plistlib.dump(p,f)
PY
codesign --force --sign - --timestamp=none build/WheelPreview.app/Frameworks/libAGWheelPreview.dylib
codesign --force --sign - --timestamp=none build/WheelPreview.app
codesign --verify --deep --strict --verbose=2 build/WheelPreview.app 2>>build/code-signing.txt
python3 - <<'PY'
import json,subprocess,pathlib
d=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','available','-j']))
candidates=[x for key,items in d['devices'].items() if 'iOS' in key for x in items if 'iPhone' in x['name']]
if not candidates:raise SystemExit('No iPhone simulator available')
device=candidates[0]['udid'];pathlib.Path('build/simulator-id').write_text(device)
subprocess.run(['xcrun','simctl','boot',device],check=False)
subprocess.run(['xcrun','simctl','bootstatus',device,'-b'],check=True)
subprocess.run(['xcrun','simctl','install',device,'build/WheelPreview.app'],check=True)
subprocess.run(['xcrun','simctl','launch',device,'vn.army2hoanggia.wheelpreview'],check=True)
PY
preview_data="$(xcrun simctl get_app_container "$(cat build/simulator-id)" vn.army2hoanggia.wheelpreview data)"
for attempt in {1..30}; do
  if [ -s "$preview_data/Documents/captcha-ui-check.json" ]; then break; fi
  sleep 1
done
python3 - "$preview_data" <<'PY_UI'
import json,pathlib,sys
error=pathlib.Path(sys.argv[1])/'Documents/ui-error.json'
if error.exists():raise SystemExit(error.read_text())
PY_UI
cp "$preview_data/Documents/ui-check.json" build/ui-check.json
cp "$preview_data"/Documents/wheel-layout-*.png build/
cp "$preview_data"/Documents/captcha-*.png build/
cp "$preview_data"/Documents/captcha-ui-check.json build/
python3 -c 'import json; assert json.load(open("build/captcha-ui-check.json"))["passed"]'
python3 -c 'import json; assert json.load(open("build/ui-check.json"))["passed"]'
xcrun simctl io "$(cat build/simulator-id)" screenshot build/wheel-preview.png
for mode in input waiting single; do
  xcrun simctl terminate "$(cat build/simulator-id)" vn.army2hoanggia.wheelpreview
  argument="--$mode"
  if [ "$mode" = input ]; then argument="--show-input"; fi
  xcrun simctl launch "$(cat build/simulator-id)" vn.army2hoanggia.wheelpreview "$argument"
  sleep 5
  xcrun simctl io "$(cat build/simulator-id)" screenshot "build/wheel-$mode-preview.png"
done


