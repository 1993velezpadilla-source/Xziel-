#!/usr/bin/env bash
set -euo pipefail

GEOMETRY_INPUT="${HAYUYA_GEOMETRY_INPUT:-assets/characters/llorona/v2/hayuya/individual/llorona_front.png}"
DETAIL_DIR="${HAYUYA_DETAIL_DIR:-assets/characters/llorona/v2/hayuya/details}"
PROFILE="${HAYUYA_PROFILE:-monster}"
GPU_VRAM="${HAYUYA_GPU_VRAM:-24}"
BACKENDS="${HAYUYA_BACKENDS:-triposg,trellis2,trellis,instantmesh,triposr}"
OUTPUT_ROOT="${HAYUYA_OUTPUT_ROOT:-out/gpu-e2e/jobs}"
MODEL_ROOT="${HAYUYA_MODEL_ROOT:-.hayuya/models}"

echo "=== HAYUYA GPU E2E ==="
echo "geometry=${GEOMETRY_INPUT}"
echo "details=${DETAIL_DIR}"
echo "profile=${PROFILE}"
echo "gpu_vram=${GPU_VRAM}"
echo "backends=${BACKENDS}"

nvidia-smi
python3 --version

python3 -m venv .hayuya/control
.hayuya/control/bin/python -m pip install --upgrade pip
.hayuya/control/bin/python -m pip install   numpy pillow trimesh scipy fast-simplification

.hayuya/control/bin/python tools/hayuya3d/bootstrap.py --all

mkdir -p out/gpu-e2e
.hayuya/control/bin/python tools/hayuya3d/gpu_doctor.py   --model-root "${MODEL_ROOT}"   --backends "${BACKENDS}"   --include-support   --output out/gpu-e2e/gpu_doctor.json   --strict

ARGS=(
  --input "${GEOMETRY_INPUT}"
  --profile "${PROFILE}"
  --gpu-vram "${GPU_VRAM}"
  --backends "${BACKENDS}"
  --model-root "${MODEL_ROOT}"
  --output-root "${OUTPUT_ROOT}"
  --execute
  --viewforge required
  --appearance-judge required
  --geometry-refine required
  --gameprep required
)

if [[ -n "${DETAIL_DIR}" ]]; then
  ARGS+=(--input-dir "${DETAIL_DIR}")
fi

if [[ "${HAYUYA_REQUIRE_ALL:-0}" == "1" || "${HAYUYA_REQUIRE_ALL:-false}" == "true" ]]; then
  ARGS+=(--require-all)
fi

.hayuya/control/bin/python tools/hayuya3d/hayuya.py "${ARGS[@]}"

.hayuya/control/bin/python tools/hayuya3d/gpu_verify.py   --root "${OUTPUT_ROOT}"   --output out/gpu-e2e/GPU_E2E_PASS.json

echo "HAYUYA_GPU_E2E_PASS"
