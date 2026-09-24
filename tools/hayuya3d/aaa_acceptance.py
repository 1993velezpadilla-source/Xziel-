#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import asdict,dataclass
from pathlib import Path
from typing import Any


@dataclass
class AAAGate:
    id: str
    category: str
    ready: bool
    required: bool
    evidence: str
    blocker: str | None=None


@dataclass
class AAAReadinessReport:
    version: int
    ready: bool
    passed_required: int
    total_required: int
    blockers: list[str]
    advisories: list[str]
    gates: list[AAAGate]
    method: str="hayuya-internal-aaa-acceptance-contract-v1"


def _finite(value:Any)->bool:
    try:
        return math.isfinite(float(value))
    except (TypeError,ValueError):
        return False


def _gate(
    gates:list[AAAGate],
    gate_id:str,
    category:str,
    ready:bool,
    evidence:str,
    *,
    required:bool=True,
    blocker:str|None=None,
)->None:
    gates.append(AAAGate(
        id=gate_id,
        category=category,
        ready=bool(ready),
        required=required,
        evidence=evidence,
        blocker=(blocker if required and not ready else None),
    ))


def evaluate_aaa_acceptance(
    manifest:dict,
    qa_report:dict,
)->AAAReadinessReport:
    """Evaluate HAYUYA's strict internal high-end acceptance contract.

    "AAA" here is an internal engineering bar, not an external certification.
    The contract is evidence-completeness-first: missing proof fails closed.
    Numeric aesthetic floors are intentionally not invented until calibrated on
    a larger real-asset corpus.
    """
    gates:list[AAAGate]=[]
    advisories:list[str]=[]

    mode=str(qa_report.get("mode") or manifest.get("mode") or "prop")
    profile=str(qa_report.get("profile") or manifest.get("profile") or "")
    high_end=profile in {"monster","ultra"}

    _gate(
        gates,"pipeline.success","pipeline",
        manifest.get("status")=="success",
        f"status={manifest.get('status')}",
        blocker="pipeline did not complete successfully",
    )

    geometry=qa_report.get("geometry") or {}
    structure=qa_report.get("structure") or {}
    geometry_integrity=bool(
        geometry.get("ready")
        and structure.get("valid")
        and structure.get("finite_vertices")
        and int(structure.get("duplicate_faces") or 0)==0
        and int(structure.get("degenerate_faces") or 0)==0
        and int(structure.get("nonmanifold_edges") or 0)==0
        and structure.get("winding_consistent")
    )
    _gate(
        gates,"geometry.integrity","geometry",geometry_integrity,
        "QA geometry + Mesh Doctor structural audit",
        blocker="geometry has unresolved structural defects",
    )

    source=qa_report.get("source_coverage") or {}
    source_ready=bool(
        int(source.get("judged") or 0)>=int(source.get("expected") or 0)
    )
    _gate(
        gates,"source.coverage","fidelity",source_ready,
        f"judged={source.get('judged')} expected={source.get('expected')}",
        blocker="not every real geometry source has Judge evidence",
    )

    turn=qa_report.get("turntable_qa")
    turn_ready=bool(
        int(source.get("expected") or 0)==0
        or (isinstance(turn,dict) and turn.get("ready"))
    )
    _gate(
        gates,"source.turntable","fidelity",turn_ready,
        "source-vs-turntable validation",
        blocker="final asset lacks passing multi-view source-vs-turntable proof",
    )

    material=qa_report.get("material") or {}
    channels=set(material.get("channels") or [])
    material_ready=bool(
        material.get("ready")
        and material.get("texture_resolution_ready")
        and material.get("rebake_ready")
    )
    _gate(
        gates,"material.readiness","materials",material_ready,
        f"channels={sorted(channels)} texture={material.get('base_color_min_edge')} target={material.get('target_texture_size')}",
        blocker="material/texture/rebake contract is incomplete",
    )

    if high_end:
        pbr_core={"baseColor","roughness","normal"}
        pbr_ready=pbr_core.issubset(channels)
        _gate(
            gates,"material.pbr_core","materials",pbr_ready,
            f"required={sorted(pbr_core)} actual={sorted(channels)}",
            blocker="high-end asset is missing core PBR evidence",
        )
        target=int(material.get("target_texture_size") or 0)
        min_edge=int(material.get("base_color_min_edge") or 0)
        _gate(
            gates,"texture.hero_resolution","materials",
            bool(target>0 and min_edge>=target),
            f"weakest_baseColor={min_edge}px target={target}px",
            blocker="Hero Master visible texture target is not met",
        )

    face=qa_report.get("face_evidence") or {}
    if mode=="character":
        face_chain=bool(face.get("quality_evidence_ready"))
        _gate(
            gates,"character.face_chain","character",face_chain,
            "identity/FaceMesh/FaceTex/FaceDetail evidence chain",
            blocker="character face-quality evidence chain is incomplete",
        )
        if face.get("required"):
            _gate(
                gates,"character.face_refs","character",
                bool(face.get("ready")),
                f"evaluated={face.get('evaluated')} expected={face.get('expected')} worst={face.get('min_score')}",
                blocker="explicit face references are not completely evaluated",
            )
        for key in (
            "head_density_score",
            "head_texel_density_score",
            "head_texture_detail_score",
        ):
            _gate(
                gates,f"character.{key}","character",
                _finite(geometry.get(key)),
                f"{key}={geometry.get(key)}",
                blocker=f"missing {key} evidence",
            )

        rig=qa_report.get("rig") or {}
        _gate(
            gates,"character.rig","character",bool(rig.get("rig_ready")),
            f"skins={rig.get('skins')} joints={rig.get('joint_count')}",
            blocker="character has no validated skin/rig",
        )
        skin_weights=qa_report.get("skin_weights") or {}
        _gate(
            gates,"character.skin_weights","character",
            bool(skin_weights.get("applicable") and skin_weights.get("ready")),
            (
                f"applicable={skin_weights.get('applicable')} "
                f"weighted={skin_weights.get('weighted_vertices')} "
                f"zero={skin_weights.get('zero_weight_vertices')} "
                f"non_normalized={skin_weights.get('non_normalized_vertices')} "
                f"invalid_joints={skin_weights.get('invalid_joint_references')}"
            ),
            blocker="character skin weights are missing, malformed, non-normalized, or reference invalid joints",
        )
        _gate(
            gates,"character.animation","character",
            bool(rig.get("animation_ready")),
            f"animations={rig.get('animations')}",
            blocker="character has no validated animation clips",
        )

    gameprep=manifest.get("gameprep") or qa_report.get("gameprep")
    lods=(gameprep or {}).get("lods") or []
    _gate(
        gates,"runtime.gameprep","runtime",
        bool(gameprep and lods),
        f"lod_count={len(lods)}",
        blocker="GamePrep runtime package is missing",
    )

    pack=manifest.get("portable_pack") or {}
    tiers=pack.get("tiers") or []
    complete_lods=pack.get("complete_lod_chain")
    _gate(
        gates,"runtime.portable_pack","runtime",
        bool(pack and tiers and complete_lods),
        f"tiers={len(tiers)} complete_lod_chain={complete_lods}",
        blocker="portable runtime tiers are incomplete",
        required=profile in {"mobile","game","monster","ultra"},
    )

    composite=manifest.get("composite_champion") or {}
    execution=manifest.get("composite_execution") or {}
    composite_required=bool(composite.get("composite_required"))
    deferred=list(composite.get("deferred_transfers") or [])
    if composite_required:
        composite_complete=bool(
            execution.get("ready")
            and not deferred
            and str(manifest.get("champion",{}).get("backend","")).startswith("composite_")
        )
        _gate(
            gates,"composite.optimized","composite",composite_complete,
            f"execution_ready={execution.get('ready')} deferred={deferred} champion={manifest.get('champion',{}).get('backend')}",
            blocker="better regional donor evidence exists but Composite Champion fusion is not fully resolved",
        )
    else:
        _gate(
            gates,"composite.optimized","composite",True,
            "base finalist already owns strongest measured regional evidence",
        )

    qa_ready=bool(qa_report.get("production_ready"))
    _gate(
        gates,"qa.production_ready","qa",qa_ready,
        f"production_ready={qa_ready}",
        blocker="QA Package does not consider the asset production-ready",
    )

    warnings=[str(x) for x in (qa_report.get("warnings") or []) if str(x).strip()]
    if warnings:
        advisories.extend(warnings[:20])

    required=[g for g in gates if g.required]
    blockers=[g.blocker for g in required if not g.ready and g.blocker]
    passed=sum(1 for g in required if g.ready)
    return AAAReadinessReport(
        version=1,
        ready=not blockers,
        passed_required=passed,
        total_required=len(required),
        blockers=blockers,
        advisories=advisories,
        gates=gates,
    )


def write_aaa_report(report:AAAReadinessReport,path:Path)->Path:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(asdict(report),indent=2)+"\n",encoding="utf-8")
    return path


def main()->int:
    import argparse
    parser=argparse.ArgumentParser(description="HAYUYA internal AAA acceptance contract.")
    parser.add_argument("manifest",type=Path)
    parser.add_argument("qa_report",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    report=evaluate_aaa_acceptance(
        json.loads(args.manifest.read_text(encoding="utf-8")),
        json.loads(args.qa_report.read_text(encoding="utf-8")),
    )
    write_aaa_report(report,args.output)
    print(json.dumps(asdict(report),indent=2))
    return 0 if report.ready else 2


if __name__=="__main__":
    raise SystemExit(main())
