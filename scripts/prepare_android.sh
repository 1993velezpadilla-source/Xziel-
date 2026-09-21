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
python3 "$ROOT/scripts/patch_vril_lab_alias_limits.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_weaponhud.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v018.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_weaponhud_v020.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_combatfx.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_modern_movement.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_camera_feel.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_animation_feel.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v021.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v022.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v023.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v024.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_mobile_v025.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_nacht_enhanced.py" "$DEPS/vril"
python3 "$ROOT/scripts/patch_vril_nacht_textures.py" "$DEPS/vril"

echo "==> Patching and compiling Xziel mobile QuakeC"
python3 -m pip install --quiet colorama==0.4.6 fastcrc==0.3.0 pandas==2.1.4 numpy==1.26.4 cairosvg==2.8.2 pillow==11.3.0
python3 "$ROOT/scripts/patch_quakec_mobile.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_combatfx.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_modern_movement.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_mobile_v021.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_mobile_v022.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_nacht_activation.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_nacht_lab_zombies.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_nacht_runtime.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_nacht_fx_v2.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_nacht_gore.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_waw_legacy_audio.py" "$DEPS/quakec"
python3 "$ROOT/scripts/patch_quakec_nacht_original_audio.py" "$DEPS/quakec"
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

echo "==> Building separate Nacht Enchanted practice BSP from source"
bash "$ROOT/scripts/build_nacht_enchanted_map.sh" "$ASSET_WORK"
python3 "$ROOT/scripts/build_nacht_enchanted_sky.py" "$ASSET_WORK/nzp"

# Xziel mobile HUD art comes from a pinned CC0 icon pack and is rasterized at
# build time. This keeps the repository text-only while packaging professional
# touch-control art into the APK.
python3 "$ROOT/scripts/build_xziel_icons.py" "$ASSET_WORK/nzp/gfx/xziel"
echo "==> Staging opt-in Nacht Enhanced CC0 texture pack"
bash "$ROOT/scripts/fetch_nacht_enhanced_textures.sh" "$ASSET_WORK"
python3 "$ROOT/scripts/build_nacht_enchanted_transparents.py" "$BUILD/nacht-enchanted-source/assets" "$ASSET_WORK/nzp"
python3 "$ROOT/scripts/build_nacht_enchanted_props.py" "$ASSET_WORK/nzp"

echo "==> Baking real CC0 animated zombie for Nacht Enchanted Lab"
QUAT_COMMIT="db3df04d1e4714298a09510b26fb6de6645138a2"
curl -fL --retry 6 --retry-delay 2 --retry-all-errors \
  "https://raw.githubusercontent.com/agentkaerf/FreeModels/$QUAT_COMMIT/Zombie%20Apocalypse%20Kit%20-%20March%202024/Characters/glTF/Zombie_Basic.gltf" \
  -o "$DOWNLOADS/quaternius-zombie-basic.gltf"
curl -fL --retry 6 --retry-delay 2 --retry-all-errors \
  "https://raw.githubusercontent.com/agentkaerf/FreeModels/$QUAT_COMMIT/Zombie%20Apocalypse%20Kit%20-%20March%202024/License.txt" \
  -o "$DOWNLOADS/quaternius-zombie-license.txt"
python3 "$ROOT/scripts/build_nacht_lab_zombie.py" \
  "$DOWNLOADS/quaternius-zombie-basic.gltf" \
  "$ASSET_WORK/nzp" \
  "$DEPS/vril/source/anorms.h"
mkdir -p "$ASSET_WORK/nzp/licenses"
{
  echo "Xziel Nacht Enchanted Lab - Quaternius Zombie"
  echo "Source mirror commit: $QUAT_COMMIT"
  echo "Original creator: Quaternius"
  echo "License: CC0 1.0"
  echo "Source asset: Zombie Apocalypse Kit / Zombie_Basic.gltf"
  echo
  cat "$DOWNLOADS/quaternius-zombie-license.txt"
} > "$ASSET_WORK/nzp/licenses/XZIEL-QUATERNIUS-ZOMBIE-CC0.txt"

python3 "$ROOT/scripts/build_nacht_enchanted_decals.py" "$ASSET_WORK/nzp"
python3 "$ROOT/scripts/build_nacht_enchanted_audio.py" "$ASSET_WORK/nzp"
bash "$ROOT/scripts/import_waw_reference_audio.sh" "$ASSET_WORK"

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
