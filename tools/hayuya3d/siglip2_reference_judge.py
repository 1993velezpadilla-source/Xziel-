#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CandidateSimilarity:
    name: str
    path: str
    cosine_similarity: float


@dataclass
class SigLIP2Report:
    schema: int
    model: str
    source: str
    device: str
    ready: bool
    candidates: list[CandidateSimilarity]
    warnings: list[str]
    method: str = "siglip2-image-embedding-fidelity-v1"


def _parse_named(items:list[str])->list[tuple[str,Path]]:
    out=[]
    for raw in items:
        if "=" not in raw:
            raise ValueError(f"expected NAME=PATH, got {raw!r}")
        name,path=raw.split("=",1)
        p=Path(path)
        if not name.strip() or not p.is_file():
            raise FileNotFoundError(f"missing candidate {name}={p}")
        out.append((name.strip(),p))
    return out


def _pooled(value):
    import torch
    if torch.is_tensor(value):
        return value
    for attr in ("pooler_output","image_embeds","last_hidden_state"):
        raw=getattr(value,attr,None)
        if raw is None:
            continue
        if attr=="last_hidden_state":
            return raw.mean(dim=1)
        return raw
    if isinstance(value,(tuple,list)) and value:
        return _pooled(value[0])
    raise TypeError(f"cannot extract pooled embedding from {type(value).__name__}")


def score(source:Path,candidates:list[tuple[str,Path]],model_id:str)->SigLIP2Report:
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from transformers import AutoModel, AutoProcessor

    device="cuda" if torch.cuda.is_available() else "cpu"
    model=AutoModel.from_pretrained(model_id,dtype="auto").to(device).eval()
    processor=AutoProcessor.from_pretrained(model_id)
    images=[Image.open(source).convert("RGB")]+[
        Image.open(path).convert("RGB") for _,path in candidates
    ]
    inputs=processor(images=images,return_tensors="pt")
    inputs={k:(v.to(device) if hasattr(v,"to") else v) for k,v in inputs.items()}
    with torch.inference_mode():
        features=_pooled(model.get_image_features(**inputs)).float()
    features=F.normalize(features,dim=-1)
    src=features[0:1]
    sims=(features[1:]@src.T).squeeze(-1).detach().cpu().tolist()
    if not isinstance(sims,list):
        sims=[float(sims)]
    rows=[
        CandidateSimilarity(name=name,path=str(path),cosine_similarity=round(float(sim),7))
        for (name,path),sim in zip(candidates,sims)
    ]
    return SigLIP2Report(
        schema=1,model=model_id,source=str(source),device=device,
        ready=len(rows)==len(candidates) and bool(rows),
        candidates=rows,warnings=[]
    )


def main()->int:
    p=argparse.ArgumentParser(description="HAYUYA Judge v5 SigLIP2 source-fidelity eye.")
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--candidate",action="append",default=[],required=True,help="NAME=PATH")
    p.add_argument("--model",default="google/siglip2-base-patch16-224")
    p.add_argument("--json",type=Path,required=True)
    a=p.parse_args()
    try:
        if not a.source.is_file():
            raise FileNotFoundError(a.source)
        report=score(a.source,_parse_named(a.candidate),a.model)
        payload=asdict(report)
        code=0 if report.ready else 2
    except Exception as exc:
        payload={
            "schema":1,"model":a.model,"source":str(a.source),
            "ready":False,"candidates":[],
            "warnings":[f"{type(exc).__name__}:{exc}"],
            "method":"siglip2-image-embedding-fidelity-v1",
        }
        code=2
    a.json.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    return code


if __name__=="__main__":
    raise SystemExit(main())
