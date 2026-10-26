#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
python3 test_protocol.py
sdk="$(xcrun --sdk iphoneos --show-sdk-path)"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$sdk" -miphoneos-version-min=12.0 \
  -dynamiclib -fobjc-arc -fblocks -fvisibility=hidden -O1 -Wall -Wextra \
  -Wno-unused-parameter -Wno-deprecated-declarations -Wno-unused-function \
  -framework UIKit -framework Foundation -framework QuartzCore \
  -Wl,-install_name,@executable_path/Frameworks/AGWheel.dylib \
  AGWheel.m WheelProtocol.c NativeGuard.S -o build/AGWheel.dylib
codesign --force --sign - --timestamp=none build/AGWheel.dylib
codesign --verify --strict --verbose=2 build/AGWheel.dylib
xcrun nm -gU build/AGWheel.dylib > build/exports.txt
xcrun otool -l build/AGWheel.dylib > build/load-commands.txt
shasum -a 256 build/AGWheel.dylib > build/SHA256.txt

# Compile a separate simulator preview. No fixture code is in AGWheel.dylib.
sim_sdk="$(xcrun --sdk iphonesimulator --show-sdk-path)"
sim_arch="$(uname -m)"
mkdir -p build/WheelPreview.app
xcrun --sdk iphonesimulator clang -arch "$sim_arch" -isysroot "$sim_sdk" \
  -mios-simulator-version-min=16.0 -DAG_WHEEL_PREVIEW=1 -fobjc-arc -fblocks -O1 \
  -Wno-deprecated-declarations -framework UIKit -framework Foundation -framework QuartzCore \
  AGWheel.m WheelProtocol.c Preview.m -o build/WheelPreview.app/WheelPreview
python3 - <<'PY'
import plistlib
p={'CFBundleIdentifier':'vn.army2hoanggia.wheelpreview','CFBundleExecutable':'WheelPreview','CFBundleName':'WheelPreview','CFBundleVersion':'1','CFBundleShortVersionString':'1.0','CFBundlePackageType':'APPL','MinimumOSVersion':'16.0','LSRequiresIPhoneOS':True,'UILaunchScreen':{},'UIDeviceFamily':[1,2],'UISupportedInterfaceOrientations':['UIInterfaceOrientationPortrait','UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']}
with open('build/WheelPreview.app/Info.plist','wb') as f:plistlib.dump(p,f)
PY
codesign --force --sign - --timestamp=none build/WheelPreview.app
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
sleep 4
xcrun simctl io "$(cat build/simulator-id)" screenshot build/wheel-preview.png
