#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
node test_spectator.js
mkdir -p build
cc -std=c11 -Wall -Wextra -Werror AuraState.c testdata/AuraStateTest.c -o build/aura-state-test
build/aura-state-test
cc -std=c11 -Wall -Wextra -Werror BossMaps.c testdata/BossMapsTest.c -o build/boss-maps-test
build/boss-maps-test
bash build.sh
sim_sdk="$(xcrun --sdk iphonesimulator --show-sdk-path)"
preview=build/SpectatorPreview.app
mkdir -p "$preview/viewer"
cp -R viewer/. "$preview/viewer/"
cp testdata/watch-pvp.json "$preview/"
cp build/WheelPreview.app/Info.plist "$preview/Info.plist"
/usr/libexec/PlistBuddy -c 'Set CFBundleIdentifier vn.army2hoanggia.spectatorpreview' "$preview/Info.plist"
/usr/libexec/PlistBuddy -c 'Set CFBundleExecutable SpectatorPreview' "$preview/Info.plist"
xcrun --sdk iphonesimulator clang -arch "$(uname -m)" -isysroot "$sim_sdk" -mios-simulator-version-min=16.0 \
  -DAG_WHEEL_PREVIEW=1 -fobjc-arc -fblocks -Wno-deprecated-declarations -framework UIKit -framework Foundation -framework CoreGraphics -framework WebKit \
  testdata/SpectatorPreview.m Spectator.m SpectatorNative.c Lobby.m GameViewport.m -o "$preview/SpectatorPreview"
codesign --force --sign - --timestamp=none "$preview"
device="$(cat build/simulator-id)"
xcrun simctl install "$device" "$preview"
xcrun simctl launch "$device" vn.army2hoanggia.spectatorpreview
result="$(xcrun simctl get_app_container "$device" vn.army2hoanggia.spectatorpreview data)/Documents/viewer-result.txt"
for attempt in {1..45}; do [[ -s "$result" ]] && break; sleep 1; done
cat "$result"
grep -q '^PASS ' "$result"
cp "$result" build/viewer-result.txt
framework=build/QA/AGWheel.framework
mkdir -p "$framework/viewer"
cp build/AGWheel.dylib "$framework/AGWheel"
cp -R viewer/. "$framework/viewer/"
python3 - <<'PY'
import plistlib
from pathlib import Path
plist=dict(CFBundleDevelopmentRegion='en',CFBundleExecutable='AGWheel',
           CFBundleIdentifier='vn.army2hoanggia.game.agwheel',CFBundleInfoDictionaryVersion='6.0',
           CFBundleName='AGWheel',CFBundlePackageType='FMWK',CFBundleShortVersionString='1.0',
           CFBundleSupportedPlatforms=['iPhoneOS'],CFBundleVersion='1',MinimumOSVersion='12.0')
Path('build/QA/AGWheel.framework/Info.plist').write_bytes(plistlib.dumps(plist,fmt=plistlib.FMT_BINARY))
PY
xcrun install_name_tool -id '@rpath/AGWheel.framework/AGWheel' "$framework/AGWheel"
xcrun lipo "$framework/AGWheel" -verify_arch arm64
test "$(xcrun otool -D "$framework/AGWheel" | tail -1)" = '@rpath/AGWheel.framework/AGWheel'
codesign --force --sign - --timestamp=none "$framework"
codesign --verify --strict --verbose=2 "$framework"
(cd build/QA && /usr/bin/zip -qr ../AGWheel-framework.zip AGWheel.framework)
shasum -a 256 build/AGWheel-framework.zip


