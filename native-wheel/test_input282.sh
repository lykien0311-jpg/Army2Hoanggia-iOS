#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
app=build/MarketInputPreview.app
mkdir -p "$app"
sdk="$(xcrun --sdk iphonesimulator --show-sdk-path)"
xcrun --sdk iphonesimulator clang -arch "$(uname -m)" -isysroot "$sdk" -mios-simulator-version-min=16.0 -DAG_WHEEL_PREVIEW=1 -fobjc-arc -fblocks -Wno-deprecated-declarations -framework UIKit -framework Foundation -framework WebKit -framework CoreGraphics testdata/MarketInputPreview.m GameViewport.m -o "$app/MarketInputPreview"
python3 - <<'PY'
from pathlib import Path
import plistlib
p=dict(CFBundleIdentifier='vn.army2hoanggia.marketinputpreview',CFBundleExecutable='MarketInputPreview',CFBundleName='MarketInputPreview',CFBundleVersion='282',CFBundleShortVersionString='2.4.1',CFBundlePackageType='APPL',MinimumOSVersion='16.0',LSRequiresIPhoneOS=True,UILaunchScreen={},UIDeviceFamily=[1,2])
Path('build/MarketInputPreview.app/Info.plist').write_bytes(plistlib.dumps(p))
PY
codesign --force --sign - --timestamp=none "$app"
device="$(xcrun simctl list devices available -j | python3 -c 'import json,sys;d=json.load(sys.stdin);print(next(x["udid"] for k,a in d["devices"].items() if "iOS" in k for x in a if "iPhone" in x["name"]))')"
xcrun simctl boot "$device" || true
xcrun simctl bootstatus "$device" -b
xcrun simctl install "$device" "$app"
xcrun simctl launch "$device" vn.army2hoanggia.marketinputpreview
result="$(xcrun simctl get_app_container "$device" vn.army2hoanggia.marketinputpreview data)/Documents"
for attempt in {1..45}; do [[ -s "$result/input-282-check.json" ]] && break; sleep 1; done
cp "$result/input-282-check.json" build/
cp "$result/input-282-native.png" build/
cat build/input-282-check.json
python3 -c 'import json; assert json.load(open("build/input-282-check.json"))["passed"]'
