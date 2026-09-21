#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
DEPS="$BUILD/deps"
PROJECT="$BUILD/android-project"
APP="$PROJECT/app"

rm -rf "$BUILD"
mkdir -p "$DEPS"

echo "==> Cloning native dependencies"
git clone --depth 1 --branch SDL2 https://github.com/libsdl-org/SDL.git "$DEPS/SDL"
git clone --depth 1 --branch SDL2 https://github.com/libsdl-org/SDL_mixer.git "$DEPS/SDL2_mixer"
git clone --depth 1 https://github.com/ptitSeb/gl4es.git "$DEPS/gl4es"
git clone --depth 1 https://github.com/nzp-team/vril-engine.git "$DEPS/vril"
git clone --depth 1 https://github.com/nzp-team/quakec.git "$DEPS/quakec"
git -C "$DEPS/quakec" fetch --depth 1 origin 04bd544172e16193162277a7c356c827e9653b06
git -C "$DEPS/quakec" checkout 04bd544172e16193162277a7c356c827e9653b06
git clone --depth 1 --branch feature/shadows-of-evil-completion https://github.com/1993velezpadilla-source/nzp-android.git "$DEPS/soe"
git -C "$DEPS/soe" fetch --depth 1 origin cd9ecccd956a935a2bf8bf9a7e95d020a960b7b1
git -C "$DEPS/soe" checkout cd9ecccd956a935a2bf8bf9a7e95d020a960b7b1

# Raise SDL's Android phone sensor polling target from 60 Hz to 120 Hz.
# The backend still clamps to the physical sensor's minimum delay, so devices
# that cannot sustain 120 Hz automatically run at their supported rate.
python3 - "$DEPS/SDL/src/sensor/android/SDL_androidsensor.c" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("delay_us = 1000000 / 60;", "delay_us = 1000000 / 120;")
path.write_text(text)
PY

echo "==> Patching Vril for Android GLES2 through GL4ES"
python3 "$ROOT/scripts/patch_vril_android.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_weaponhud.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v018.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_weaponhud_v020.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_combatfx.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_modern_movement.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_camera_feel.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_animation_feel.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v021.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v022.py" "$DEPS/vril"

echo "==> Patching and compiling Xziel mobile QuakeC"
python3 -m pip install --quiet colorama==0.4.6 fastcrc==0.3.0 pandas==2.1.4 cairosvg==2.8.2
python3 "$ROOT/scripts/patch_quakec_mobile.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_combatfx.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_modern_movement.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_mobile_v021.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_mobile_v022.py" "$DEPS/quakec"
echo "==> Applying tested Shadows of Evil gameplay overlay"
python3 "$DEPS/soe/scripts/apply_soe_quakec_overlay.py" "$DEPS/quakec"
chmod +x "$DEPS/quakec/bin/fteqcc-cli-lin" "$DEPS/quakec/tools/qc-compiler-gnu.sh"
(
    cd "$DEPS/quakec"
    bash tools/qc-compiler-gnu.sh
)

# Initialize GL4ES explicitly only after SDL has created the GLES2 context.
python3 - "$DEPS/gl4es/Android.mk" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace(
    "#LOCAL_CFLAGS += -DNO_INIT_CONSTRUCTOR",
    "LOCAL_CFLAGS += -DNO_INIT_CONSTRUCTOR",
)
path.write_text(text)
PY

echo "==> Creating SDL Android project"
cp -a "$DEPS/SDL/android-project" "$PROJECT"

rm -rf "$APP/jni/SDL" "$APP/jni/SDL2_mixer" "$APP/jni/gl4es" "$APP/jni/vril"
ln -s "$DEPS/SDL" "$APP/jni/SDL"
ln -s "$DEPS/SDL2_mixer" "$APP/jni/SDL2_mixer"
ln -s "$DEPS/gl4es" "$APP/jni/gl4es"
ln -s "$DEPS/vril" "$APP/jni/vril"

cp "$ROOT/android/jni/Android.mk" "$APP/jni/Android.mk"
cp "$ROOT/android/jni/Application.mk" "$APP/jni/Application.mk"
mkdir -p "$APP/jni/src"
cp "$ROOT/android/jni/src/Android.mk" "$APP/jni/src/Android.mk"

cp "$ROOT/android/app-build.gradle" "$APP/build.gradle"
cp "$ROOT/android/AndroidManifest.xml" "$APP/src/main/AndroidManifest.xml"
cp "$ROOT/android/strings.xml" "$APP/src/main/res/values/strings.xml"
cp "$ROOT/android/NZPActivity.java"    "$APP/src/main/java/org/libsdl/app/NZPActivity.java"

echo "==> Assembling official NZ:P game data for the APK"
ASSET_WORK="$BUILD/nzp-data"
DOWNLOADS="$BUILD/downloads"
mkdir -p "$ASSET_WORK" "$DOWNLOADS" "$APP/src/main/assets"

curl -fL --retry 6 --retry-delay 2 --retry-all-errors     https://github.com/nzp-team/assets/releases/download/newest/pc-nzp-assets.zip     -o "$DOWNLOADS/pc-nzp-assets.zip"

curl -fL --retry 6 --retry-delay 2 --retry-all-errors     https://github.com/nzp-team/quakec/releases/download/bleeding-edge/standard-nzp-qc.zip     -o "$DOWNLOADS/standard-nzp-qc.zip"

unzip -q "$DOWNLOADS/pc-nzp-assets.zip" -d "$ASSET_WORK"
mkdir -p "$ASSET_WORK/nzp"
unzip -q "$DOWNLOADS/standard-nzp-qc.zip" -d "$ASSET_WORK/nzp"

echo "==> Building additive Shadows of Evil map package"
git clone https://github.com/nzp-team/assets.git "$DEPS/soe-assets"
git -C "$DEPS/soe-assets" checkout c8135a66e00bb64577912fbf792f8fef7f47658e
git clone --recurse-submodules https://github.com/nzp-team/spawn-zone-tool.git "$DEPS/spawn-zone-tool"
git -C "$DEPS/spawn-zone-tool" checkout 3c6f9b87208026d7d639565deed64e541ffb18bf
python3 -m pip install --quiet -r "$DEPS/spawn-zone-tool/requirements.txt"
python3 "$DEPS/soe/scripts/generate_soe_full_city.py"
python3 "$DEPS/soe/scripts/apply_soe_asset_overlay.py" --assets-root "$DEPS/soe-assets"
(
    cd "$DEPS/soe-assets"
    bash tools/compile-wads.sh
    bash tools/compile-maps.sh -m soe/soe.map --zone-tool-path "$DEPS/spawn-zone-tool"
)
test -s "$DEPS/soe-assets/common/maps/soe.bsp"
test -s "$DEPS/soe-assets/common/maps/soe.nsz"
mkdir -p "$ASSET_WORK/nzp/maps"
cp "$DEPS/soe-assets/common/maps/soe.bsp" "$ASSET_WORK/nzp/maps/soe.bsp"
cp "$DEPS/soe-assets/common/maps/soe.nsz" "$ASSET_WORK/nzp/maps/soe.nsz"
echo "SoE map added without replacing stock v0.22 maps"

# Xziel mobile HUD art comes from a pinned CC0 icon pack and is rasterized at
# build time. This keeps the repository text-only while packaging professional
# touch-control art into the APK.
python3 "$ROOT/scripts/build_xziel_icons.py" "$ASSET_WORK/nzp/gfx/xziel"

# Replace the stock gameplay bytecode with our GPL QuakeC build. All other
# release-side data stays from the official NZ:P package.
cp "$DEPS/quakec/build/standard/progs.dat" "$ASSET_WORK/nzp/progs.dat"
if [[ -f "$DEPS/quakec/build/standard/progs.lno" ]]; then
    cp "$DEPS/quakec/build/standard/progs.lno" "$ASSET_WORK/nzp/progs.lno"
fi

(
    cd "$ASSET_WORK"
    zip -q -r "$APP/src/main/assets/nzp-data.zip" .
)

sha256sum "$APP/src/main/assets/nzp-data.zip" | awk '{print $1}'     > "$APP/src/main/assets/nzp-data.version"

mkdir -p "$APP/src/main/assets/licenses"
cp "$DEPS/vril/LICENSE" "$APP/src/main/assets/licenses/VRIL-GPL-2.0.txt"
cp "$DEPS/quakec/LICENSE" "$APP/src/main/assets/licenses/NZP-QUAKEC-GPL-2.0.txt"

curl -fL --retry 6 --retry-delay 2 --retry-all-errors     https://raw.githubusercontent.com/nzp-team/assets/main/LICENSE.md     -o "$APP/src/main/assets/licenses/NZP-ASSETS-CC-BY-SA-4.0.txt"

if [[ -f "$DEPS/gl4es/LICENSE" ]]; then
    cp "$DEPS/gl4es/LICENSE" "$APP/src/main/assets/licenses/GL4ES-LICENSE.txt"
elif [[ -f "$DEPS/gl4es/LICENSE.md" ]]; then
    cp "$DEPS/gl4es/LICENSE.md" "$APP/src/main/assets/licenses/GL4ES-LICENSE.txt"
fi

echo "==> Native source revisions"
echo "SDL:        $(git -C "$DEPS/SDL" rev-parse HEAD)"
echo "SDL_mixer:  $(git -C "$DEPS/SDL2_mixer" rev-parse HEAD)"
echo "GL4ES:      $(git -C "$DEPS/gl4es" rev-parse HEAD)"
echo "Vril:       $(git -C "$DEPS/vril" rev-parse HEAD)"
echo "QuakeC:     $(git -C "$DEPS/quakec" rev-parse HEAD)"
echo "Data SHA:   $(cat "$APP/src/main/assets/nzp-data.version")"

chmod +x "$PROJECT/gradlew"

echo "Prepared project: $PROJECT"
