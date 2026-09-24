#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class RegionalMetric:
    region: str
    metric: str
    strategy: str
    seam_risk: str
    rig_risk: str
    destructive: bool


@dataclass
class RegionalDonor:
    region: str
    metric: str
    base_backend: str
    donor_backend: str
    base_score: float | None
    donor_score: float | None
    improvement: float | None
    strategy: str
    seam_risk: str
    rig_risk: str
    destructive: bool
    requires_rejudge: bool = True


@dataclass
class FinalistSummary:
    backend: str
    path: str
    global_score: float
    valid: bool
    production_score: float | None
    visual_score: float | None
    appearance_score: float | None
    face_score: float | None
    face_min_score: float | None
    head_density_score: float | None
    head_texel_density_score: float | None
    head_texture_detail_score: float | None
    material_score: float | None
    texture_resolution_score: float | None
    accessory_components: int | None = None


@dataclass
class CompositeChampionPlan:
    version: int
    mode: str
    base_backend: str
    base_path: str
    finalist_backends: list[str]
    finalists: list[FinalistSummary]
    donors: list[RegionalDonor]
    composite_required: bool
    executable_now: list[str]
    deferred_transfers: list[str]
    promotion_contract: list[str]
    notes: list[str]
    method: str = "hayuya-composite-champion-planner-v1"


REGIONAL_METRICS: tuple[RegionalMetric, ...] = (
    RegionalMetric(
        "face_identity",
        "appearance_face_detail_min_score",
        "surface_wrap_plus_identity_texture_projection",
        "high",
        "high",
        True,
    ),
    RegionalMetric(
        "face_geometry",
        "head_density_score",
        "local_surface_wrap",
        "high",
        "high",
        True,
    ),
    RegionalMetric(
        "face_texel_budget",
        "head_texel_density_score",
        "uv_local_reallocation_or_texture_projection",
        "medium",
        "medium",
        True,
    ),
    RegionalMetric(
        "face_surface_detail",
        "head_texture_detail_score",
        "local_texture_detail_projection",
        "medium",
        "low",
        False,
    ),
    RegionalMetric(
        "global_shape",
        "visual_score",
        "retain_base_geometry",
        "low",
        "low",
        False,
    ),
    RegionalMetric(
        "global_appearance",
        "appearance_score",
        "material_and_texture_reference",
        "medium",
        "low",
        False,
    ),
    RegionalMetric(
        "material_response",
        "material_score",
        "material_projection_then_rebake",
        "medium",
        "low",
        False,
    ),
    RegionalMetric(
        "texture_resolution",
        "texture_resolution_score",
        "texture_challenger_reference",
        "low",
        "low",
        False,
    ),
)


def _finite(value: Any) -> float | None:
    try:
        value=float(value)
    except (TypeError,ValueError):
        return None
    return value if math.isfinite(value) else None


def _get(item: Any, name: str, default: Any=None) -> Any:
    if isinstance(item,dict):
        return item.get(name,default)
    return getattr(item,name,default)


def _summary(item: Any) -> FinalistSummary:
    return FinalistSummary(
        backend=str(_get(item,"backend","unknown")),
        path=str(_get(item,"path","")),
        global_score=float(_get(item,"score",0.0) or 0.0),
        valid=bool(_get(item,"valid",False)),
        production_score=_finite(_get(item,"production_score")),
        visual_score=_finite(_get(item,"visual_score")),
        appearance_score=_finite(_get(item,"appearance_score")),
        face_score=_finite(_get(item,"appearance_face_detail_score")),
        face_min_score=_finite(_get(item,"appearance_face_detail_min_score")),
        head_density_score=_finite(_get(item,"head_density_score")),
        head_texel_density_score=_finite(_get(item,"head_texel_density_score")),
        head_texture_detail_score=_finite(_get(item,"head_texture_detail_score")),
        material_score=_finite(_get(item,"material_score")),
        texture_resolution_score=_finite(_get(item,"texture_resolution_score")),
    )


def _metric_value(summary: FinalistSummary, metric: str) -> float | None:
    aliases={
        "appearance_face_detail_min_score":"face_min_score",
    }
    return _finite(getattr(summary,aliases.get(metric,metric),None))


def _best_donor(
    finalists: list[FinalistSummary],
    spec: RegionalMetric,
) -> FinalistSummary | None:
    eligible=[
        (value,item)
        for item in finalists
        if (value:=_metric_value(item,spec.metric)) is not None
    ]
    if not eligible:
        return None
    return max(eligible,key=lambda pair:(pair[0],pair[1].global_score))[1]


def _improvement(base: float | None, donor: float | None) -> float | None:
    if donor is None:
        return None
    if base is None:
        return donor
    return donor-base


def _part_map_accessory_count(path: str, mode: str) -> int | None:
    if not path or mode not in {"character","prop","architecture"}:
        return None
    try:
        from part_map import build_part_map
        result=build_part_map(Path(path),mode=mode)
        return len(result.accessory_component_ids)
    except Exception:
        return None


def build_composite_plan(
    ranked: Iterable[Any],
    *,
    mode: str,
    max_finalists: int=5,
    minimum_regional_gain: float=0.5,
    inspect_parts: bool=True,
) -> CompositeChampionPlan:
    valid=[item for item in ranked if bool(_get(item,"valid",False))]
    if not valid:
        raise ValueError("composite planning requires at least one valid finalist")

    finalists=[_summary(item) for item in valid[:max(1,int(max_finalists))]]
    base=finalists[0]

    if inspect_parts:
        for item in finalists:
            item.accessory_components=_part_map_accessory_count(item.path,mode)

    donors: list[RegionalDonor]=[]
    for spec in REGIONAL_METRICS:
        donor=_best_donor(finalists,spec)
        if donor is None:
            continue
        base_value=_metric_value(base,spec.metric)
        donor_value=_metric_value(donor,spec.metric)
        gain=_improvement(base_value,donor_value)

        # Always record the region winner. A donor only requests a composite when
        # it differs from the base and provides meaningful or previously missing evidence.
        donors.append(RegionalDonor(
            region=spec.region,
            metric=spec.metric,
            base_backend=base.backend,
            donor_backend=donor.backend,
            base_score=base_value,
            donor_score=donor_value,
            improvement=round(gain,3) if gain is not None else None,
            strategy=spec.strategy,
            seam_risk=spec.seam_risk,
            rig_risk=spec.rig_risk,
            destructive=spec.destructive,
        ))

    # Detached accessories are the first geometry class that can eventually be
    # auto-swapped safely. Planning still requires later alignment/dedup proof.
    accessory_winner=None
    accessory_count=-1
    for item in finalists:
        count=item.accessory_components
        if count is not None and count>accessory_count:
            accessory_count=count
            accessory_winner=item
    if accessory_winner is not None and accessory_count>0:
        donors.append(RegionalDonor(
            region="detached_accessories",
            metric="accessory_component_count",
            base_backend=base.backend,
            donor_backend=accessory_winner.backend,
            base_score=float(base.accessory_components or 0),
            donor_score=float(accessory_count),
            improvement=float(accessory_count-(base.accessory_components or 0)),
            strategy="aligned_component_swap_then_mesh_doctor",
            seam_risk="low",
            rig_risk="medium" if mode=="character" else "low",
            destructive=False,
        ))

    meaningful=[
        d for d in donors
        if d.donor_backend!=base.backend
        and (
            d.base_score is None
            or d.improvement is None
            or d.improvement>=minimum_regional_gain
        )
    ]
    executable_now=sorted({
        d.region for d in meaningful
        if d.strategy in {
            "local_texture_detail_projection",
            "material_projection_then_rebake",
            "texture_challenger_reference",
        }
    })
    deferred=sorted({
        d.region for d in meaningful
        if d.region not in executable_now
    })

    return CompositeChampionPlan(
        version=1,
        mode=mode,
        base_backend=base.backend,
        base_path=base.path,
        finalist_backends=[x.backend for x in finalists],
        finalists=finalists,
        donors=donors,
        composite_required=bool(meaningful),
        executable_now=executable_now,
        deferred_transfers=deferred,
        promotion_contract=[
            "composite must re-enter the complete real-source Judge arena",
            "global score must not regress against the base champion",
            "weakest face-reference score must not regress when face evidence exists",
            "FaceMesh, FaceTex and FaceDetail evidence must remain complete for characters",
            "geometry/topology must pass Mesh Doctor after any geometry transfer",
            "normal and occlusion must be rebaked after topology or UV changes",
            "rig/skin/animation must remain valid for skinned characters",
            "source-vs-turntable QA must pass after fusion",
            "no original finalist is overwritten; composite is always a challenger",
        ],
        notes=[
            "The base finalist supplies the canonical coordinate system and continuity.",
            "Regional donors are evidence sources, not unconditional copy/paste instructions.",
            "High-risk body/face geometry transfers stay deferred until wrap/seam/skin-weight proof exists.",
            "Texture/material transfers can be attempted earlier because they preserve base topology.",
            "Every fusion is atomic: rejection restores the untouched base champion.",
        ],
    )


def write_composite_plan(plan: CompositeChampionPlan, path: Path) -> Path:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(asdict(plan),indent=2)+"\n",encoding="utf-8")
    return path


def main() -> int:
    import argparse

    parser=argparse.ArgumentParser(
        description="HAYUYA Composite Champion regional donor planner."
    )
    parser.add_argument("ranking_json",type=Path)
    parser.add_argument("--mode",choices=["prop","character","architecture"],required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--max-finalists",type=int,default=5)
    parser.add_argument("--no-part-inspection",action="store_true")
    args=parser.parse_args()

    ranking=json.loads(args.ranking_json.read_text(encoding="utf-8"))
    plan=build_composite_plan(
        ranking,
        mode=args.mode,
        max_finalists=args.max_finalists,
        inspect_parts=not args.no_part_inspection,
    )
    write_composite_plan(plan,args.output)
    print(json.dumps(asdict(plan),indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
