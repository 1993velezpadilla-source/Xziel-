import json
import os
from pathlib import Path

import cv2
import numpy as np

TEXTURE_DIR = Path(os.environ.get(
    "XZIEL_TEXTURE_DIR",
    "church/out/xziel_native_static/textures/xziel/sanctum",
))
MODEL_PATH = Path(os.environ.get(
    "XZIEL_SR_MODEL",
    "church/out/FSRCNN_x2.pb",
))
REPORT_PATH = Path(os.environ.get(
    "XZIEL_TEXTURE_ENHANCE_REPORT",
    "church/out/xziel_native_static/sanctum_texture_enhance_report.json",
))

if not MODEL_PATH.is_file():
    raise SystemExit(f"missing super-resolution model: {MODEL_PATH}")

superres = cv2.dnn_superres.DnnSuperResImpl_create()
superres.readModel(str(MODEL_PATH))
superres.setModel("fsrcnn", 2)

records = []
enhanced = 0

for path in sorted(TEXTURE_DIR.glob("*.png")):
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise RuntimeError(f"failed to decode {path}")

    h, w = image.shape[:2]
    if min(w, h) < 256 or max(w, h) >= 1800:
        records.append({
            "file": path.name,
            "before": [w, h],
            "after": [w, h],
            "enhanced": False,
        })
        continue

    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        alpha = None
    elif image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]
    else:
        bgr = image[:, :, :3]
        alpha = None

    # The 2019 St Giles source ships 1K photogrammetry atlases. FSRCNN x2
    # reconstructs a 2K sampling grid cheaply enough for CI/mobile; a mild
    # LAB local-contrast and unsharp pass restores stone/wood micro-contrast
    # without turning scan noise into crunchy halos.
    up = superres.upsample(bgr)

    lab = cv2.cvtColor(up, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(
        clipLimit=1.22,
        tileGridSize=(12, 12),
    )
    l = clahe.apply(l)
    up = cv2.cvtColor(
        cv2.merge((l, a, b)),
        cv2.COLOR_LAB2BGR,
    )

    blur = cv2.GaussianBlur(
        up,
        (0, 0),
        0.78,
    )
    up = cv2.addWeighted(
        up,
        1.12,
        blur,
        -0.12,
        0.0,
    )

    if alpha is not None:
        alpha_up = cv2.resize(
            alpha,
            (up.shape[1], up.shape[0]),
            interpolation=cv2.INTER_LANCZOS4,
        )
        output = np.dstack((up, alpha_up))
    else:
        output = up

    if not cv2.imwrite(
        str(path),
        output,
        [cv2.IMWRITE_PNG_COMPRESSION, 3],
    ):
        raise RuntimeError(f"failed to write {path}")

    enhanced += 1
    records.append({
        "file": path.name,
        "before": [w, h],
        "after": [int(up.shape[1]), int(up.shape[0])],
        "enhanced": True,
    })

report = {
    "method": "FSRCNN_x2 + mild CLAHE + unsharp",
    "targetScale": 2,
    "enhancedCount": enhanced,
    "textures": records,
}

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

if enhanced < 10:
    raise RuntimeError(
        f"expected at least 10 church atlases to enhance, got {enhanced}"
    )

print("XZIEL_SANCTUM_TEXTURES_2K_READY", json.dumps({
    "enhanced": enhanced,
    "report": str(REPORT_PATH),
}))
