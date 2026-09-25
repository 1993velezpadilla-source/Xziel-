#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_GENERAL=["topiq_nr","musiq","clipiqa+","maniqa"]
FACE_METRIC="topiq_nr-face"


def _named(items:list[str]):
    out=[]
    for raw in items:
        if "=" not in raw:
            raise ValueError(f"expected NAME=PATH, got {raw!r}")
        name,path=raw.split("=",1)
        p=Path(path)
        if not p.is_file():
            raise FileNotFoundError(p)
        out.append((name.strip(),p))
    return out


def _scalar(value):
    try:
        return float(value.detach().float().reshape(-1)[0].cpu().item())
    except Exception:
        return float(value)


def _range(metric):
    raw=getattr(metric,"score_range",None)
    if raw is None:
        return None
    try:
        return [float(raw[0]),float(raw[1])]
    except Exception:
        return None


def run(named,face_name:str):
    import torch
    import pyiqa
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    report={"schema":1,"device":str(device),"ready":True,"metrics":{},"warnings":[],"method":"pyiqa-multi-eye-v1"}
    for metric_name in DEFAULT_GENERAL:
        try:
            metric=pyiqa.create_metric(metric_name,device=device)
            values={name:round(_scalar(metric(str(path))),7) for name,path in named}
            report["metrics"][metric_name]={
                "higher_better":bool(getattr(metric,"higher_better",True)),
                "score_range":_range(metric),
                "values":values,
            }
            del metric
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:
            report["ready"]=False
            report["warnings"].append(f"{metric_name}:{type(exc).__name__}:{exc}")

    face_path=next((path for name,path in named if name==face_name),None)
    if face_path is None:
        report["ready"]=False
        report["warnings"].append(f"missing_face_view:{face_name}")
    else:
        try:
            metric=pyiqa.create_metric(FACE_METRIC,device=device)
            report["metrics"][FACE_METRIC]={
                "higher_better":bool(getattr(metric,"higher_better",True)),
                "score_range":_range(metric),
                "values":{face_name:round(_scalar(metric(str(face_path))),7)},
            }
        except Exception as exc:
            report["ready"]=False
            report["warnings"].append(f"{FACE_METRIC}:{type(exc).__name__}:{exc}")
    return report


def main()->int:
    p=argparse.ArgumentParser(description="HAYUYA Judge v5 independent IQA ensemble.")
    p.add_argument("--image",action="append",default=[],required=True,help="NAME=PATH")
    p.add_argument("--face-name",default="face")
    p.add_argument("--json",type=Path,required=True)
    a=p.parse_args()
    try:
        payload=run(_named(a.image),a.face_name)
        code=0 if payload["ready"] else 2
    except Exception as exc:
        payload={"schema":1,"ready":False,"metrics":{},"warnings":[f"{type(exc).__name__}:{exc}"],"method":"pyiqa-multi-eye-v1"}
        code=2
    a.json.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    return code


if __name__=="__main__":
    raise SystemExit(main())
