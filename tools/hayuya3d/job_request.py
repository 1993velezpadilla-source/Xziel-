#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROFILES = {"preview", "mobile", "game", "monster", "ultra"}
MODES = {"auto", "prop", "character", "architecture"}
TIERS = {"auto", "compatibility", "balanced", "high", "flagship"}
JOB_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ALLOWED_EXTERNAL_REPOS = {
    "1993velezpadilla-source/legacy-cache-staging-03",
}


def load_request(path: Path, repo_root: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("unsupported job request schema")

    required = ["job_id", "owner", "title", "geometry_input", "profile", "mode", "portable_target"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))

    job_id = str(data["job_id"])
    if not JOB_RE.fullmatch(job_id):
        raise ValueError("job_id may only contain letters, digits, dot, underscore and dash")

    if data["profile"] not in PROFILES:
        raise ValueError(f"invalid profile: {data['profile']}")
    if data["mode"] not in MODES:
        raise ValueError(f"invalid mode: {data['mode']}")
    if data["portable_target"] not in TIERS:
        raise ValueError(f"invalid portable_target: {data['portable_target']}")

    source_repo = str(data.get("source_repo", "") or "").strip()
    source_ref = str(data.get("source_ref", "main") or "main").strip()
    if source_repo:
        if source_repo not in ALLOWED_EXTERNAL_REPOS:
            raise ValueError(f"external source_repo not allowed: {source_repo}")
        if not JOB_RE.fullmatch(source_ref.replace("/", "-")):
            raise ValueError("invalid external source_ref")
        data["source_repo"] = source_repo
        data["source_ref"] = source_ref
    else:
        geometry = (repo_root / str(data["geometry_input"])).resolve()
        try:
            geometry.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise ValueError("geometry_input escapes repository") from exc
        if not geometry.is_file():
            raise FileNotFoundError(f"geometry_input missing: {data['geometry_input']}")

        for key in ("reference_dir", "detail_dir"):
            value = str(data.get(key, "") or "").strip()
            if not value:
                data[key] = ""
                continue
            target = (repo_root / value).resolve()
            try:
                target.relative_to(repo_root.resolve())
            except ValueError as exc:
                raise ValueError(f"{key} escapes repository") from exc
            if not target.is_dir():
                raise FileNotFoundError(f"{key} missing: {value}")
        data["source_repo"] = ""
        data["source_ref"] = ""

    data["gpu_vram"] = int(data.get("gpu_vram", 24))
    data["backends"] = str(
        data.get("backends")
        or "triposg,trellis2,trellis,instantmesh,triposr"
    )
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data = load_request(args.request, repo_root)
    print(json.dumps(data, indent=2))

    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as f:
            for key in (
                "job_id", "owner", "title", "geometry_input", "reference_dir",
                "detail_dir", "profile", "mode", "portable_target", "gpu_vram", "backends",
                "source_repo", "source_ref"
            ):
                value = str(data.get(key, ""))
                if "\n" in value or "\r" in value:
                    raise ValueError(f"multiline workflow output not allowed: {key}")
                f.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
