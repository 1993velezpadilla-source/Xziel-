#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path


def safe_copy(src: Path, dst: Path):
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
    return True


def main() -> int:
    p=argparse.ArgumentParser(description="Build a self-contained HAYUYA character package from a saved editor recipe.")
    p.add_argument("--recipe",required=True,type=Path)
    p.add_argument("--model",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--repo-root",type=Path,default=Path("."))
    args=p.parse_args()

    recipe=json.loads(args.recipe.read_text(encoding="utf-8"))
    job_id=str(recipe["job_id"])
    root=args.out/job_id
    if root.exists():
        shutil.rmtree(root)
    (root/"character").mkdir(parents=True)
    (root/"audio").mkdir(parents=True)
    (root/"docs").mkdir(parents=True)

    safe_copy(args.model,root/"character"/"model.glb")

    model_dir=args.repo_root/"hayuya"/"models"/job_id
    safe_copy(model_dir/"manifest.json",root/"character"/"manifest.json")
    safe_copy(model_dir/"rig_gate.json",root/"character"/"rig_gate.json")
    safe_copy(model_dir/"quality_gate.json",root/"character"/"quality_gate.json")

    # Keep the exact editor recipe beside the exported character.
    (root/"hayuya_recipe.json").write_text(json.dumps(recipe,indent=2)+"\n",encoding="utf-8")

    # Runtime-friendly profile: selected IDs are stable; labels are presentation.
    profile={
        "schema":1,
        "job_id":job_id,
        "skeleton_type":recipe.get("skeleton_type","hayuya_humanoid_v1"),
        "animations":recipe.get("selected",{}).get("animations",[]),
        "real_mocap":recipe.get("selected",{}).get("real_mocap",[]),
        "audio":recipe.get("selected",{}).get("audio",[]),
        "addons":recipe.get("selected",{}).get("addons",[]),
    }
    (root/"character_profile.json").write_text(json.dumps(profile,indent=2)+"\n",encoding="utf-8")

    copied_audio=[]
    unresolved_audio=[]
    for item in profile["audio"]:
        for raw in item.get("files") or []:
            src=args.repo_root/raw
            dst=root/"audio"/Path(raw).name
            if safe_copy(src,dst):
                copied_audio.append(str(dst.relative_to(root)))
            else:
                unresolved_audio.append(raw)
        directory=item.get("directory")
        if directory:
            src=args.repo_root/directory
            dst=root/"audio"/Path(directory).name
            if safe_copy(src,dst):
                copied_audio.append(str(dst.relative_to(root)))
            else:
                unresolved_audio.append(directory)

    # Copy project audio provenance/policy when available.
    safe_copy(args.repo_root/"docs"/"audio"/"XZIEL_HORROR_AUDIO_SOURCES.md",root/"docs"/"XZIEL_HORROR_AUDIO_SOURCES.md")
    safe_copy(args.repo_root/"hayuya"/"standards"/"hayuya_humanoid_v1.json",root/"docs"/"hayuya_humanoid_v1.json")
    safe_copy(args.repo_root/"hayuya"/"standards"/"hayuya_preview_pack_v1.json",root/"docs"/"hayuya_preview_pack_v1.json")

    unresolved_mocap=[
        x for x in profile["real_mocap"]
        if x.get("availability") not in (None,"local")
    ]
    build={
        "schema":1,
        "job_id":job_id,
        "model":str(args.model),
        "copied_audio":copied_audio,
        "unresolved_audio":unresolved_audio,
        "unresolved_external_mocap":unresolved_mocap,
        "game_ready":not unresolved_audio and not unresolved_mocap,
        "notes":[
            "External mocap is never silently bundled without an ingested/licensed local source.",
            "Gameplay state mapping remains explicit in character_profile.json."
        ]
    }
    (root/"BUILD.json").write_text(json.dumps(build,indent=2)+"\n",encoding="utf-8")

    zip_path=args.out/f"{job_id}-hayuya-package.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                z.write(path,path.relative_to(args.out))

    print("HAYUYA_PACKAGE_PASS")
    print(json.dumps({
        "job_id":job_id,
        "zip":str(zip_path),
        "zip_bytes":zip_path.stat().st_size,
        "game_ready":build["game_ready"],
        "unresolved_external_mocap":len(unresolved_mocap),
        "audio_items":len(copied_audio)
    },indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
