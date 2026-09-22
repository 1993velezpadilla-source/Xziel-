#!/usr/bin/env python3
"""Generate a game-ready La Llorona GLB from multi-view concept references via Meshy."""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://api.meshy.ai/openapi/v1"
CREATE_URL = f"{API_BASE}/multi-image-to-3d"
REF_DIR = Path(os.environ.get("LLORONA_REF_DIR", "assets/characters/llorona/reference"))
OUT_DIR = Path(os.environ.get("LLORONA_OUT_DIR", "out/llorona"))
ORDERED_REFS = ["front.jpg", "left.jpg", "back.jpg", "right.jpg"]
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELED"}


def fail(message: str, code: int = 1) -> None:
    print(f"::error::{message}")
    raise SystemExit(code)


def read_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    if not raw.startswith(b"\xff\xd8"):
        fail(f"Reference is not a JPEG: {path}")
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def api_json(method: str, url: str, api_key: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Xziel-Llorona-GitHub-Actions/1.0",
        },
    )
    try:
        with urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        fail(f"Meshy HTTP {exc.code}: {body[:1200]}")
    except URLError as exc:
        fail(f"Meshy network error: {exc}")
    return json.loads(body) if body else {}


def download(url: str, path: Path) -> None:
    req = Request(url, headers={"User-Agent": "Xziel-Llorona-GitHub-Actions/1.0"})
    try:
        with urlopen(req, timeout=180) as resp, path.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    except (HTTPError, URLError) as exc:
        fail(f"Download failed for {path.name}: {exc}")


def validate_glb(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 20:
        fail(f"GLB missing or too small: {path}")
    with path.open("rb") as f:
        if f.read(4) != b"glTF":
            fail(f"Invalid GLB magic: {path}")


def sanitized_task(task: dict) -> dict:
    clean = json.loads(json.dumps(task))
    if isinstance(clean.get("model_urls"), dict):
        clean["model_urls"] = {k: bool(v) for k, v in clean["model_urls"].items()}
    if isinstance(clean.get("thumbnail_urls"), dict):
        clean["thumbnail_urls"] = {k: bool(v) for k, v in clean["thumbnail_urls"].items()}
    if clean.get("thumbnail_url"):
        clean["thumbnail_url"] = True
    if clean.get("alpha_thumbnail_url"):
        clean["alpha_thumbnail_url"] = True
    if isinstance(clean.get("texture_urls"), list):
        clean["texture_urls"] = [{k: bool(v) for k, v in x.items()} for x in clean["texture_urls"]]
    return clean


def main() -> None:
    api_key = os.environ.get("MESHY_API_KEY", "").strip()
    if not api_key:
        fail("MESHY_API_KEY is missing. Add it as a GitHub Actions repository secret, then rerun this workflow.")

    missing = [str(REF_DIR / n) for n in ORDERED_REFS if not (REF_DIR / n).is_file()]
    if missing:
        fail("Missing La Llorona reference images: " + ", ".join(missing))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    refs = [read_data_uri(REF_DIR / n) for n in ORDERED_REFS]
    target_polycount = int(os.environ.get("LLORONA_TARGET_POLYCOUNT", "60000"))
    if not 100 <= target_polycount <= 300000:
        fail("LLORONA_TARGET_POLYCOUNT must be between 100 and 300000")
    texture_resolution = os.environ.get("LLORONA_TEXTURE_RESOLUTION", "4k")
    if texture_resolution not in {"2k", "4k", "8k"}:
        fail("LLORONA_TEXTURE_RESOLUTION must be 2k, 4k, or 8k")

    payload = {
        "image_urls": refs,
        "texture_image_urls": refs,
        "ai_model": "meshy-7.1",
        "geometry_resolution": "2k",
        "should_texture": True,
        "enable_pbr": True,
        "texture_resolution": texture_resolution,
        "should_remesh": True,
        "topology": "triangle",
        "target_polycount": target_polycount,
        "save_pre_remeshed_model": True,
        "pose_mode": "a-pose",
        "image_enhancement": True,
        "remove_lighting": True,
        "target_formats": ["glb"],
        "auto_size": True,
        "origin_at": "bottom",
        "multi_view_thumbnails": True,
    }

    print("Creating Meshy multi-image task for La Llorona...")
    print(
        f"model=meshy-7.1 geometry=2k texture={texture_resolution} "
        f"PBR=yes A-pose=yes mobile_target={target_polycount} faces"
    )
    created = api_json("POST", CREATE_URL, api_key, payload)
    task_id = created.get("result")
    if not task_id:
        fail(f"Meshy did not return a task id: {created}")
    print(f"Meshy task: {task_id}")
    (OUT_DIR / "task_id.txt").write_text(str(task_id) + "\n", encoding="utf-8")

    deadline = time.monotonic() + int(os.environ.get("MESHY_TIMEOUT_SECONDS", "2700"))
    last_progress = None
    task = {}
    while time.monotonic() < deadline:
        task = api_json("GET", f"{CREATE_URL}/{task_id}", api_key)
        status = str(task.get("status", "UNKNOWN"))
        progress = task.get("progress")
        state = (status, progress)
        if state != last_progress:
            print(f"status={status} progress={progress}")
            last_progress = state
        if status in TERMINAL:
            break
        time.sleep(15)
    else:
        fail(f"Timed out waiting for Meshy task {task_id}")

    (OUT_DIR / "meshy_task.json").write_text(
        json.dumps(sanitized_task(task), indent=2, sort_keys=True), encoding="utf-8"
    )
    if task.get("status") != "SUCCEEDED":
        err = task.get("task_error") or {}
        fail(f"Meshy task ended as {task.get('status')}: {err}")

    model_urls = task.get("model_urls") or {}
    mobile_url = model_urls.get("glb")
    master_url = model_urls.get("pre_remeshed_glb")
    if not mobile_url:
        fail("Meshy succeeded but returned no GLB URL")

    mobile = OUT_DIR / "llorona_mobile_60k.glb"
    download(mobile_url, mobile)
    validate_glb(mobile)
    print(f"Downloaded mobile GLB: {mobile} ({mobile.stat().st_size:,} bytes)")

    if master_url:
        master = OUT_DIR / "llorona_master_pre_remesh.glb"
        download(master_url, master)
        validate_glb(master)
        print(f"Downloaded master GLB: {master} ({master.stat().st_size:,} bytes)")
    else:
        print("::warning::Meshy did not return pre_remeshed_glb; mobile GLB is still valid.")

    thumbs = task.get("thumbnail_urls") or {}
    for name in ("front", "right", "back", "left"):
        url = thumbs.get(name)
        if url:
            download(url, OUT_DIR / f"preview_{name}.png")
    if task.get("thumbnail_url") and not (OUT_DIR / "preview_front.png").exists():
        download(task["thumbnail_url"], OUT_DIR / "preview_front.png")

    manifest = {
        "task_id": task_id,
        "status": task.get("status"),
        "ai_model": "meshy-7.1",
        "geometry_resolution": "2k",
        "texture_resolution": texture_resolution,
        "target_polycount": target_polycount,
        "pose_mode": "a-pose",
        "pbr": True,
        "source_views": ORDERED_REFS,
        "outputs": sorted(p.name for p in OUT_DIR.iterdir() if p.is_file()),
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("LA_LLORONA_MESHY_GLBS_READY")


if __name__ == "__main__":
    main()
