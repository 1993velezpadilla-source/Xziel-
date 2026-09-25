#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict,dataclass
from pathlib import Path


ALIGNER_ID="minchul/cvlface_DFA_mobilenet"
IDENTITY_ID="minchul/cvlface_adaface_vit_base_kprpe_webface4m"


@dataclass
class FaceEvidence:
    path:str
    detector_score:float|None
    aligned_path:str|None
    bbox:list[float]|None
    ready:bool


@dataclass
class FaceIdentityReport:
    schema:int
    aligner_model:str
    identity_model:str
    device:str
    source:FaceEvidence
    candidate:FaceEvidence
    cosine_similarity:float|None
    ready:bool
    warnings:list[str]
    method:str="cvlface-dfa-adaface-kprpe-v1"


def _download_repo(repo_id:str,root:Path,token:str|None):
    from huggingface_hub import hf_hub_download
    root.mkdir(parents=True,exist_ok=True)
    list_path=hf_hub_download(repo_id,"files.txt",token=token,local_dir=root)
    files=[
        line.strip()
        for line in Path(list_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for name in files+["config.json","wrapper.py","model.safetensors"]:
        try:
            hf_hub_download(repo_id,name,token=token,local_dir=root)
        except Exception:
            if name in {"model.safetensors"}:
                raise
    return root


def _load_model(repo_id:str,root:Path,token:str|None):
    from transformers import AutoModel
    _download_repo(repo_id,root,token)
    cwd=os.getcwd()
    try:
        os.chdir(root)
        sys.path.insert(0,str(root))
        model=AutoModel.from_pretrained(str(root),trust_remote_code=True,token=token)
    finally:
        os.chdir(cwd)
        if sys.path and sys.path[0]==str(root):
            sys.path.pop(0)
    return model


def _to_tensor(path:Path):
    from PIL import Image
    from torchvision.transforms import Compose,Normalize,ToTensor
    img=Image.open(path).convert("RGB")
    trans=Compose([ToTensor(),Normalize(mean=[0.5]*3,std=[0.5]*3)])
    return trans(img).unsqueeze(0)


def _float(value):
    import torch
    if value is None:
        return None
    if torch.is_tensor(value):
        if value.numel()==0:
            return None
        return float(value.detach().float().reshape(-1)[0].cpu().item())
    try:
        return float(value)
    except Exception:
        return None


def _bbox(value):
    import torch
    if value is None:
        return None
    if torch.is_tensor(value):
        vals=value.detach().float().cpu().reshape(-1).tolist()
    elif isinstance(value,(list,tuple)):
        vals=list(value)
    else:
        return None
    return [round(float(x),6) for x in vals[:4]] if len(vals)>=4 else None


def _save_aligned(tensor,path:Path):
    import torch
    from PIL import Image
    x=tensor.detach().float().cpu()[0].clamp(-1,1)
    arr=((x*0.5+0.5)*255.0).byte().permute(1,2,0).numpy()
    path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(arr).save(path)


def _extract_embedding(value):
    import torch
    if torch.is_tensor(value):
        if value.ndim>=2:
            return value.reshape(value.shape[0],-1)
    if isinstance(value,(list,tuple)):
        for item in value:
            try:
                out=_extract_embedding(item)
                if out is not None:
                    return out
            except Exception:
                pass
    if isinstance(value,dict):
        for item in value.values():
            try:
                out=_extract_embedding(item)
                if out is not None:
                    return out
            except Exception:
                pass
    return None


def _face(path:Path,aligner,identity,device:str,out_path:Path):
    import torch
    x=_to_tensor(path).to(device)
    with torch.inference_mode():
        aligned,orig_ldmks,aligned_ldmks,score,thetas,bbox=aligner(x)
    det=_float(score)
    if aligned is None or not torch.is_tensor(aligned) or aligned.numel()==0:
        return FaceEvidence(str(path),det,None,_bbox(bbox),False),None
    _save_aligned(aligned,out_path)
    aligned=aligned.to(device)
    keypoints=aligned_ldmks.to(device) if hasattr(aligned_ldmks,"to") else aligned_ldmks
    with torch.inference_mode():
        raw=identity(aligned,keypoints)
    emb=_extract_embedding(raw)
    if emb is None:
        raise RuntimeError("AdaFace returned no embedding tensor")
    emb=torch.nn.functional.normalize(emb.float(),dim=-1)
    return FaceEvidence(str(path),det,str(out_path),_bbox(bbox),True),emb


def run(source:Path,candidate:Path,cache:Path,aligned_dir:Path)->FaceIdentityReport:
    import torch
    device="cuda" if torch.cuda.is_available() else "cpu"
    token=os.environ.get("HF_TOKEN") or None
    aligner=_load_model(ALIGNER_ID,cache/"aligner",token).to(device).eval()
    identity=_load_model(IDENTITY_ID,cache/"identity",token).to(device).eval()

    src_ev,src_emb=_face(source,aligner,identity,device,aligned_dir/"source.png")
    can_ev,can_emb=_face(candidate,aligner,identity,device,aligned_dir/"candidate.png")
    similarity=None
    if src_emb is not None and can_emb is not None:
        similarity=float((src_emb@can_emb.T).reshape(-1)[0].detach().cpu().item())
    ready=src_ev.ready and can_ev.ready and similarity is not None
    return FaceIdentityReport(
        schema=1,aligner_model=ALIGNER_ID,identity_model=IDENTITY_ID,device=device,
        source=src_ev,candidate=can_ev,
        cosine_similarity=round(similarity,7) if similarity is not None else None,
        ready=bool(ready),warnings=[]
    )


def main()->int:
    p=argparse.ArgumentParser(description="HAYUYA Judge v5 face-preservation eye using CVLFace AdaFace.")
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--cache",type=Path,default=Path(".cache/hayuya/cvlface"))
    p.add_argument("--aligned-dir",type=Path,required=True)
    p.add_argument("--json",type=Path,required=True)
    a=p.parse_args()
    try:
        if not a.source.is_file() or not a.candidate.is_file():
            raise FileNotFoundError(f"{a.source} / {a.candidate}")
        report=run(a.source,a.candidate,a.cache,a.aligned_dir)
        payload=asdict(report)
        code=0 if report.ready else 2
    except Exception as exc:
        payload={
            "schema":1,"aligner_model":ALIGNER_ID,"identity_model":IDENTITY_ID,
            "ready":False,"cosine_similarity":None,
            "warnings":[f"{type(exc).__name__}:{exc}"],
            "method":"cvlface-dfa-adaface-kprpe-v1",
        }
        code=2
    a.json.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    return code


if __name__=="__main__":
    raise SystemExit(main())
