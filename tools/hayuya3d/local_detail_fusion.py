#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import math
from dataclasses import asdict,dataclass
from pathlib import Path


@dataclass
class LocalDetailFusionResult:
    base_mesh:str
    donor_mesh:str
    output_glb:str
    region:str
    ready:bool
    basecolor_image_index:int|None
    changed_pixels:int
    unchanged_pixels:int
    changed_fraction:float
    donor_alignment_p95_ratio:float|None
    skin_payload_preserved:bool
    geometry_preserved:bool
    skipped_uv_seam_faces:int
    error:str|None=None
    method:str="hayuya-local-basecolor-fusion-v1"


def _deps():
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree
    return np,trimesh,cKDTree


def _smoothstep(x):
    np,_,_=_deps()
    x=np.clip(x,0.0,1.0)
    return x*x*(3.0-2.0*x)


def _single_mesh(path:Path):
    np,trimesh,_=_deps()
    scene=trimesh.load(path,force="scene",process=False)
    meshes=[]
    for node_name in scene.graph.nodes_geometry:
        transform,geom_name=scene.graph[node_name]
        geom=scene.geometry[geom_name]
        if not hasattr(geom,"faces") or not len(geom.faces):
            continue
        mesh=geom.copy()
        mesh.apply_transform(transform)
        meshes.append(mesh)
    if len(meshes)!=1:
        raise ValueError(
            "local detail fusion v1 requires exactly one triangle mesh "
            f"(got {len(meshes)})"
        )
    mesh=meshes[0]
    uv=getattr(getattr(mesh,"visual",None),"uv",None)
    if uv is None or len(uv)!=len(mesh.vertices):
        raise ValueError("base mesh has no per-vertex UVs")
    return mesh


def _basecolor_image(path:Path):
    from texture_gate import embedded_images
    matches=[
        (index,mime,data)
        for index,mime,data,roles in embedded_images(path)
        if "baseColor" in set(roles or [])
    ]
    if len(matches)!=1:
        raise ValueError(
            "local detail fusion v1 requires exactly one embedded baseColor "
            f"image (got {len(matches)})"
        )
    return matches[0]


def _wrap_uv(values):
    np,_,_=_deps()
    raw=np.asarray(values,dtype=np.float64)
    wrapped=np.mod(raw,1.0)
    integer_upper=(
        (np.abs(wrapped)<=1e-10)
        &(raw>0.0)
    )
    wrapped[integer_upper]=1.0
    return wrapped


def _region_weights(vertices,region:str,up_axis:int):
    np,_,_=_deps()
    values=np.asarray(vertices,dtype=np.float64)[:,up_axis]
    lo=float(np.min(values))
    hi=float(np.max(values))
    extent=max(hi-lo,1e-9)
    h=(values-lo)/extent
    region=str(region or "").lower()
    if region=="head":
        return _smoothstep((h-0.66)/0.18)
    if region=="middle":
        lower=_smoothstep((h-0.18)/0.18)
        upper=_smoothstep((0.84-h)/0.18)
        return lower*upper
    if region=="lower":
        return _smoothstep((0.46-h)/0.20)
    raise ValueError(
        f"local detail region {region!r} is not executable in v1"
    )


def _deterministic_donor_cloud(
    donor:Path,
    *,
    samples:int,
):
    np,_,_=_deps()
    from material_bridge import build_source_color_cloud
    state=np.random.get_state()
    try:
        np.random.seed(424242)
        return build_source_color_cloud(
            donor,total_samples=max(2000,int(samples))
        )
    finally:
        np.random.set_state(state)


def _align_cloud(points,base_vertices):
    np,_,cKDTree=_deps()
    points=np.asarray(points,dtype=np.float64)
    base=np.asarray(base_vertices,dtype=np.float64)
    p_lo=np.min(points,axis=0)
    p_hi=np.max(points,axis=0)
    b_lo=np.min(base,axis=0)
    b_hi=np.max(base,axis=0)
    p_center=(p_lo+p_hi)*0.5
    b_center=(b_lo+b_hi)*0.5
    p_diag=max(float(np.linalg.norm(p_hi-p_lo)),1e-9)
    b_diag=max(float(np.linalg.norm(b_hi-b_lo)),1e-9)
    scale=b_diag/p_diag
    aligned=(points-p_center)*scale+b_center
    tree=cKDTree(aligned)
    distances,_=tree.query(base,k=1,workers=-1)
    p95=float(np.percentile(distances/b_diag,95.0))
    return aligned,b_diag,p95


def _barycentric_grid(tri_xy,min_x,max_x,min_y,max_y):
    np,_,_=_deps()
    xs=np.arange(min_x,max_x+1,dtype=np.float64)+0.5
    ys=np.arange(min_y,max_y+1,dtype=np.float64)+0.5
    xx,yy=np.meshgrid(xs,ys)
    p=np.stack([xx,yy],axis=-1)
    a,b,c=tri_xy
    v0=b-a
    v1=c-a
    v2=p-a
    den=v0[0]*v1[1]-v1[0]*v0[1]
    if abs(float(den))<=1e-12:
        return None,None
    u=(v2[...,0]*v1[1]-v1[0]*v2[...,1])/den
    v=(v0[0]*v2[...,1]-v2[...,0]*v0[1])/den
    w=1.0-u-v
    inside=(u>=-1e-6)&(v>=-1e-6)&(w>=-1e-6)
    bary=np.stack([w,u,v],axis=-1)
    return bary,inside


def fuse_local_basecolor(
    base_mesh:Path,
    donor_mesh:Path,
    output_glb:Path,
    *,
    region:str,
    up_axis:str|int="y",
    donor_samples:int=60_000,
    max_alignment_p95_ratio:float=0.18,
)->LocalDetailFusionResult:
    np,_,cKDTree=_deps()
    try:
        axis_map={"x":0,"y":1,"z":2}
        if isinstance(up_axis,str):
            if up_axis.lower() not in axis_map:
                raise ValueError(f"invalid up_axis: {up_axis}")
            axis=axis_map[up_axis.lower()]
        else:
            axis=int(up_axis)
            if axis not in (0,1,2):
                raise ValueError(f"invalid up_axis index: {axis}")

        base=_single_mesh(base_mesh)
        image_index,mime,image_bytes=_basecolor_image(base_mesh)
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as image:
            source_had_alpha="A" in image.getbands()
            rgba=image.convert("RGBA")
            pixels=np.asarray(rgba,dtype=np.uint8).copy()

        vertices=np.asarray(base.vertices,dtype=np.float64)
        faces=np.asarray(base.faces,dtype=np.int64)
        uv=np.asarray(base.visual.uv,dtype=np.float64)
        weights=_region_weights(vertices,region,axis)

        donor_points,donor_colors=_deterministic_donor_cloud(
            donor_mesh,samples=donor_samples
        )
        aligned,diag,alignment_p95=_align_cloud(
            donor_points,vertices
        )
        if alignment_p95>max_alignment_p95_ratio:
            raise RuntimeError(
                "donor alignment too weak for local fusion: "
                f"p95={alignment_p95:.6f}>"
                f"{max_alignment_p95_ratio:.6f}"
            )
        tree=cKDTree(np.asarray(aligned,dtype=np.float64))
        _,nearest=tree.query(vertices,k=1,workers=-1)
        vertex_colors=np.clip(
            np.asarray(donor_colors,dtype=np.float64)[nearest],
            0,255,
        )

        h,w=pixels.shape[:2]
        changed_mask=np.zeros((h,w),dtype=bool)
        skipped_seams=0
        for face in faces:
            tri_w=weights[face]
            if float(np.max(tri_w))<=1e-4:
                continue
            tri_uv=_wrap_uv(uv[face])
            # Avoid painting across wrapped UV seams in v1. Those boundary
            # triangles stay base-exact until seam-aware unwrap support lands.
            if (
                float(np.ptp(tri_uv[:,0]))>0.5
                or float(np.ptp(tri_uv[:,1]))>0.5
            ):
                skipped_seams+=1
                continue

            tri_xy=np.empty((3,2),dtype=np.float64)
            tri_xy[:,0]=tri_uv[:,0]*(w-1)
            tri_xy[:,1]=(1.0-tri_uv[:,1])*(h-1)
            min_x=max(0,int(math.floor(float(np.min(tri_xy[:,0])))))
            max_x=min(w-1,int(math.ceil(float(np.max(tri_xy[:,0])))))
            min_y=max(0,int(math.floor(float(np.min(tri_xy[:,1])))))
            max_y=min(h-1,int(math.ceil(float(np.max(tri_xy[:,1])))))
            if max_x<min_x or max_y<min_y:
                continue

            bary,inside=_barycentric_grid(
                tri_xy,min_x,max_x,min_y,max_y
            )
            if bary is None or not np.any(inside):
                continue
            local_alpha=np.sum(
                bary*tri_w.reshape((1,1,3)),axis=-1
            )
            donor_rgb=np.sum(
                bary[...,None]
                *vertex_colors[face].reshape((1,1,3,3)),
                axis=-2,
            )
            alpha=np.clip(local_alpha,0.0,1.0)
            active=inside&(alpha>1e-4)
            if not np.any(active):
                continue

            ys,xs=np.nonzero(active)
            gy=ys+min_y
            gx=xs+min_x
            a=alpha[active][:,None]
            base_rgb=pixels[gy,gx,:3].astype(np.float64)
            new_rgb=(
                base_rgb*(1.0-a)
                +donor_rgb[active]*a
            )
            pixels[gy,gx,:3]=np.clip(
                np.rint(new_rgb),0,255
            ).astype(np.uint8)
            changed_mask[gy,gx]=True

        changed=int(np.count_nonzero(changed_mask))
        total=int(h*w)
        unchanged=total-changed
        if changed<=0:
            raise RuntimeError(
                "local fusion changed no texture pixels"
            )
        if unchanged<=0:
            raise RuntimeError(
                "local fusion unexpectedly replaced the entire atlas"
            )

        out_image=Image.fromarray(
            pixels,
            mode="RGBA",
        )
        buf=io.BytesIO()
        if source_had_alpha:
            out_image.save(buf,format="PNG",optimize=True)
        else:
            out_image.convert("RGB").save(
                buf,format="PNG",optimize=True
            )

        from glb_images import replace_embedded_images
        replace_embedded_images(
            base_mesh,
            output_glb,
            {image_index:("image/png",buf.getvalue())},
        )

        from gltf_position_patch import skin_payload_signature
        skin_preserved=(
            skin_payload_signature(base_mesh)
            ==skin_payload_signature(output_glb)
        )

        from qa import inspect_mesh
        base_qa=inspect_mesh(
            base_mesh,
            backend="local_fusion_base",
            mode="character",
            target_faces=max(1,len(faces)),
        )
        out_qa=inspect_mesh(
            output_glb,
            backend="local_fusion_output",
            mode="character",
            target_faces=max(1,len(faces)),
        )
        geometry_preserved=bool(
            base_qa.vertices==out_qa.vertices
            and base_qa.faces==out_qa.faces
            and base_qa.components==out_qa.components
            and list(base_qa.bbox or [])==list(out_qa.bbox or [])
        )
        if not geometry_preserved:
            raise RuntimeError(
                "local texture fusion changed geometry"
            )
        if not skin_preserved:
            raise RuntimeError(
                "local texture fusion changed JOINTS/WEIGHTS payload"
            )

        return LocalDetailFusionResult(
            base_mesh=str(base_mesh),
            donor_mesh=str(donor_mesh),
            output_glb=str(output_glb),
            region=str(region),
            ready=True,
            basecolor_image_index=image_index,
            changed_pixels=changed,
            unchanged_pixels=unchanged,
            changed_fraction=round(changed/total,6),
            donor_alignment_p95_ratio=round(alignment_p95,6),
            skin_payload_preserved=True,
            geometry_preserved=True,
            skipped_uv_seam_faces=skipped_seams,
        )
    except Exception as exc:
        return LocalDetailFusionResult(
            base_mesh=str(base_mesh),
            donor_mesh=str(donor_mesh),
            output_glb=str(output_glb),
            region=str(region),
            ready=False,
            basecolor_image_index=None,
            changed_pixels=0,
            unchanged_pixels=0,
            changed_fraction=0.0,
            donor_alignment_p95_ratio=None,
            skin_payload_preserved=False,
            geometry_preserved=False,
            skipped_uv_seam_faces=0,
            error=f"{type(exc).__name__}:{exc}",
        )


def main()->int:
    import argparse
    parser=argparse.ArgumentParser(
        description="HAYUYA semantic local baseColor fusion challenger."
    )
    parser.add_argument("--base",type=Path,required=True)
    parser.add_argument("--donor",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument(
        "--region",
        choices=["head","middle","lower"],
        required=True,
    )
    parser.add_argument("--up-axis",choices=["x","y","z"],default="y")
    parser.add_argument("--json",type=Path)
    args=parser.parse_args()
    result=fuse_local_basecolor(
        args.base,args.donor,args.output,
        region=args.region,
        up_axis=args.up_axis,
    )
    payload=json.dumps(asdict(result),indent=2)
    print(payload)
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(payload+"\n",encoding="utf-8")
    return 0 if result.ready else 2


if __name__=="__main__":
    raise SystemExit(main())
