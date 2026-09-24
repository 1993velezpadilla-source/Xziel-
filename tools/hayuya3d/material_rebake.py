#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


HERE=Path(__file__).resolve().parent


@dataclass
class MaterialRebakeResult:
    source_mesh:str
    target_mesh:str
    output_glb:str
    requested_channels:list[str]
    resolved_channels:list[str]
    remaining_channels:list[str]
    attempted:bool
    method:str
    report:str|None=None
    error:str|None=None


def find_blender(explicit:str|Path|None=None)->Path|None:
    raw=explicit or os.environ.get("HAYUYA_BLENDER")
    if raw:
        path=Path(raw).expanduser()
        if path.is_file():
            return path.resolve()
        resolved=shutil.which(str(raw))
        if resolved:
            return Path(resolved).resolve()
    resolved=shutil.which("blender")
    return Path(resolved).resolve() if resolved else None


def build_normal_rebake_command(
    blender:Path,
    source_mesh:Path,
    target_mesh:Path,
    output_glb:Path,
    report:Path,
    *,
    size:int,
)->list[str]:
    return [
        str(blender),
        "--background",
        "--factory-startup",
        "--python",
        str((HERE/"blender_material_rebake.py").resolve()),
        "--",
        "--source",str(source_mesh.resolve()),
        "--target",str(target_mesh.resolve()),
        "--output",str(output_glb.resolve()),
        "--report",str(report.resolve()),
        "--size",str(int(size)),
    ]


def rebake_material_channels(
    source_mesh:Path,
    target_mesh:Path,
    output_glb:Path,
    *,
    required:list[str]|tuple[str,...]|set[str],
    max_texture_size:int,
    blender:str|Path|None=None,
)->MaterialRebakeResult:
    requested=sorted({str(x) for x in required if x})
    remaining=set(requested)
    resolved:set[str]=set()
    blender_path=find_blender(blender)

    output_glb.parent.mkdir(parents=True,exist_ok=True)
    report_path=output_glb.with_suffix(".rebake.json")

    if "normal" not in remaining or blender_path is None:
        if target_mesh.resolve()!=output_glb.resolve():
            shutil.copy2(target_mesh,output_glb)
        return MaterialRebakeResult(
            source_mesh=str(source_mesh),
            target_mesh=str(target_mesh),
            output_glb=str(output_glb),
            requested_channels=requested,
            resolved_channels=[],
            remaining_channels=sorted(remaining),
            attempted=False,
            method="blender_unavailable" if "normal" in remaining else "nothing_supported_requested",
        )

    attempted=True
    error=None
    try:
        cmd=build_normal_rebake_command(
            blender_path,
            source_mesh,
            target_mesh,
            output_glb,
            report_path,
            size=max(64,min(8192,int(max_texture_size))),
        )
        subprocess.run(cmd,check=True)

        if not output_glb.is_file() or output_glb.read_bytes()[:4]!=b"glTF":
            raise RuntimeError("normal_rebake_missing_or_invalid_glb")

        # Never clear the blocker merely because Blender returned zero.
        # Verify the exported runtime asset actually advertises a normal channel.
        from qa import inspect_mesh
        inspected=inspect_mesh(
            output_glb,
            backend="material_rebake_verify",
            mode="prop",
            target_faces=1,
        )
        if "normal" not in set(inspected.pbr_channels or []):
            raise RuntimeError(
                "normal_rebake_output_has_no_normal_channel:"
                + ",".join(inspected.pbr_channels or [])
            )

        resolved.add("normal")
        remaining.discard("normal")
        method="blender_cycles_selected_to_active_tangent_normal_v1"
    except Exception as exc:
        error=f"{type(exc).__name__}:{exc}"
        method="normal_rebake_failed"
        if target_mesh.resolve()!=output_glb.resolve():
            shutil.copy2(target_mesh,output_glb)

    return MaterialRebakeResult(
        source_mesh=str(source_mesh),
        target_mesh=str(target_mesh),
        output_glb=str(output_glb),
        requested_channels=requested,
        resolved_channels=sorted(resolved),
        remaining_channels=sorted(remaining),
        attempted=attempted,
        method=method,
        report=str(report_path) if report_path.is_file() else None,
        error=error,
    )


def main()->int:
    import argparse
    p=argparse.ArgumentParser(description="Rebake topology-dependent HAYUYA material channels.")
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--target",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--required",action="append",default=[])
    p.add_argument("--texture-size",type=int,default=2048)
    p.add_argument("--blender")
    p.add_argument("--json",type=Path)
    a=p.parse_args()
    result=rebake_material_channels(
        a.source,a.target,a.output,
        required=a.required,
        max_texture_size=a.texture_size,
        blender=a.blender,
    )
    payload=json.dumps(asdict(result),indent=2)
    print(payload)
    if a.json:
        a.json.parent.mkdir(parents=True,exist_ok=True)
        a.json.write_text(payload+"\n",encoding="utf-8")
    return 0 if not result.error else 2


if __name__=="__main__":
    raise SystemExit(main())
