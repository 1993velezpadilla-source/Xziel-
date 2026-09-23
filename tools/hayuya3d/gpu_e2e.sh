#!/usr/bin/env bash
set -euo pipefail

GEOMETRY_INPUT="${HAYUYA_GEOMETRY_INPUT:-assets/characters/llorona/v2/hayuya/individual/llorona_front.png}"
DETAIL_DIR="${HAYUYA_DETAIL_DIR:-assets/characters/llorona/v2/hayuya/details}"
PROFILE="${HAYUYA_PROFILE:-monster}"
GPU_VRAM="${HAYUYA_GPU_VRAM:-24}"
BACKENDS="${HAYUYA_BACKENDS:-triposg,trellis2,trellis,instantmesh,triposr}"
OUTPUT_ROOT="${HAYUYA_OUTPUT_ROOT:-out/gpu-e2e/jobs}"
MODEL_ROOT="${HAYUYA_MODEL_ROOT:-.hayuya/models}"
JOB_ID="${HAYUYA_JOB_ID:-proof}"
EVIDENCE_ROOT="${HAYUYA_EVIDENCE_ROOT:-out/gpu-e2e/${JOB_ID}}"

echo "=== HAYUYA GPU E2E ==="
echo "geometry=${GEOMETRY_INPUT}"
echo "details=${DETAIL_DIR}"
echo "profile=${PROFILE}"
echo "gpu_vram=${GPU_VRAM}"
echo "backends=${BACKENDS}"
echo "job_id=${JOB_ID}"
echo "evidence_root=${EVIDENCE_ROOT}"

nvidia-smi
python3 --version

python3 -m venv .hayuya/control
.hayuya/control/bin/python -m pip install --upgrade pip
.hayuya/control/bin/python -m pip install   numpy pillow trimesh scipy fast-simplification

.hayuya/control/bin/python tools/hayuya3d/bootstrap.py --all

mkdir -p "${EVIDENCE_ROOT}"

ENV_EXPORTS=".hayuya/envs/hayuya_env.sh"
if [[ "${HAYUYA_SETUP_BACKEND_ENVS:-1}" != "0" ]]; then
  .hayuya/control/bin/python tools/hayuya3d/backend_envs.py \
    --model-root "${MODEL_ROOT}" \
    --env-root .hayuya/envs \
    --backends "${BACKENDS}" \
    --include-support \
    --exports "${ENV_EXPORTS}" \
    --json "${EVIDENCE_ROOT}/backend_env_plan.json" \
    --execute
fi

if [[ ! -f "${ENV_EXPORTS}" ]]; then
  echo "Missing backend environment exports: ${ENV_EXPORTS}" >&2
  echo "Either allow HAYUYA_SETUP_BACKEND_ENVS=1 or provide the exports file." >&2
  exit 2
fi

# shellcheck disable=SC1090
source "${ENV_EXPORTS}"

.hayuya/control/bin/python tools/hayuya3d/gpu_doctor.py \
  --model-root "${MODEL_ROOT}" \
  --backends "${BACKENDS}" \
  --include-support \
  --output "${EVIDENCE_ROOT}/gpu_doctor.json" \
  --strict

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
  --mesh-doctor required
  --gameprep required
)

if [[ -n "${DETAIL_DIR}" ]]; then
  ARGS+=(--input-dir "${DETAIL_DIR}")
fi

if [[ "${HAYUYA_REQUIRE_ALL:-0}" == "1" || "${HAYUYA_REQUIRE_ALL:-false}" == "true" ]]; then
  ARGS+=(--require-all)
fi

.hayuya/control/bin/python tools/hayuya3d/hayuya.py "${ARGS[@]}"

.hayuya/control/bin/python tools/hayuya3d/gpu_verify.py \
  --root "${OUTPUT_ROOT}" \
  --output "${EVIDENCE_ROOT}/GPU_E2E_PASS.json"

echo "HAYUYA_GPU_E2E_PASS"
