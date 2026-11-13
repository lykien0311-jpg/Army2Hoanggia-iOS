#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/QA/AGWheel.framework
cc -std=c11 -Wall -Wextra test_inventory282.c -o build/inventory-test
build/inventory-test
sdk="$(xcrun --sdk iphoneos --show-sdk-path)"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$sdk" -miphoneos-version-min=12.0 \
 -dynamiclib -fobjc-arc -fblocks -fvisibility=hidden -O1 -Wall -Wextra \
 -Wno-unused-parameter -Wno-deprecated-declarations -Wno-unused-function \
 -framework UIKit -framework Foundation -framework QuartzCore -framework CoreGraphics -framework WebKit \
 -Wl,-headerpad,4000 -Wl,-install_name,@rpath/AGWheel.framework/AGWheel \
 AGWheel.m Spectator.m SpectatorNative.c Lobby.m GameViewport.m GridLayout.c Inventory.c Turn33.c UfoAuto.c Notes77.m NotesProtocol.c WheelProtocol.c RoomNames.c RoomBridge.c Movement.c Blind.c BlindState.c Aura.c AuraSprites.m AuraState.c BattleWait.c Corpse.c Stats.c ShipTraceDisabled.c BossMaps.c BossNative.m NativeGuard.S \
 -o build/QA/AGWheel.framework/AGWheel
codesign --force --sign - --timestamp=none build/QA/AGWheel.framework/AGWheel
codesign --verify --strict --verbose=2 build/QA/AGWheel.framework/AGWheel
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json
files={'AGWheel.framework/AGWheel':Path('build/QA/AGWheel.framework/AGWheel')}
for name in ('lobby.js','lobby.html','pixel-ui.js'):
 files['AGWheel.framework/viewer/'+name]=Path('viewer')/name
with ZipFile('build/framework-282.zip','w',ZIP_DEFLATED)as z:
 manifest={}
 for name,p in files.items():
  b=p.read_bytes();z.writestr(name,b);manifest[name]=hashlib.sha256(b).hexdigest()
 z.writestr('framework-sha256.json',json.dumps(manifest))
PY
