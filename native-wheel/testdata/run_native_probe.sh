#!/bin/bash
set -euo pipefail
base="$1"
staged="$2"
mkdir -p native-wheel/build
sed -i '' '/void AGWheelTick(void \*env, int variant) {/a\
    extern void AGBossNativeProbe(void *, int); AGBossNativeProbe(env,variant);\
' native-wheel/AGWheel.m
awk '/^sdk=/{started=1} started{print} /  -o build\/AGWheel.dylib/{exit}' native-wheel/build.sh |
    sed 's/^  AGWheel.m/  NativeBossProbe.m AGWheel.m/' > native-wheel/build/sim-compile.sh
(cd native-wheel && bash build/sim-compile.sh)
xcrun install_name_tool -id '@rpath/AGWheel.framework/AGWheel' native-wheel/build/AGWheel.dylib
PYTHONPATH=native-wheel python3 native-wheel/testdata/prepare_native_probe.py "$base" native-wheel/build/AGWheel.dylib "$staged"
app="$staged/Payload/Army2Hoanggia.app"
for binary in "$app/Army2Hoanggia" "$app/Frameworks/gdx.framework/gdx" "$app/Frameworks/ObjectAL.framework/ObjectAL" "$app/Frameworks/AGWheel.framework/AGWheel"; do
    xcrun vtool -set-build-version iossimulator 12.0 18.5 -replace -output "$binary.tmp" "$binary"
    mv "$binary.tmp" "$binary"
    chmod +x "$binary"
done
codesign --force --sign - "$app/Frameworks/gdx.framework"
codesign --force --sign - "$app/Frameworks/ObjectAL.framework"
codesign --force --sign - "$app/Frameworks/AGWheel.framework"
codesign --force --sign - "$app"
device="$(xcrun simctl list devices booted -j | python3 -c 'import json,sys; print(next((d["udid"] for ds in json.load(sys.stdin)["devices"].values() for d in ds if d["state"]=="Booted"), ""))')"
if [[ -z "$device" ]]; then
    device="$(xcrun simctl list devices available -j | python3 -c 'import json,sys; print(next(d["udid"] for os,ds in json.load(sys.stdin)["devices"].items() for d in ds if "iOS" in os and "iPhone" in d["name"]))')"
    xcrun simctl boot "$device"
    xcrun simctl bootstatus "$device" -b
fi
bundle=vn.army2hoanggia.game
xcrun simctl install "$device" "$app"
xcrun simctl launch "$device" "$bundle"
log="$(xcrun simctl get_app_container "$device" "$bundle" data)/Documents/map-native-probe.txt"
for iteration in {1..36}; do
    if [[ -s "$log" ]] && grep -Eq '^(PASS|FAIL)' "$log"; then
        cat "$log"
        grep -q '^PASS ' "$log"
        exit
    fi
    sleep 1
done
if [[ -s "$log" ]]; then cat "$log"; fi
xcrun simctl spawn "$device" log show --last 1m --predicate 'process == "Army2Hoanggia"' --style compact | tail -50
exit 1
