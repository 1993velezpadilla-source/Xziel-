#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--turntable-dir",type=Path,required=True)
    p.add_argument("--face-dir",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--detail",type=Path,action="append",default=[])
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()

    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from judge_v4 import _labelled_sheet,_stack_boards

    turns=sorted(a.turntable_dir.glob("*.png"))
    faces=sorted(a.face_dir.glob("*.png"))
    if len(turns)!=24:
        raise RuntimeError(f"expected 24 Blender turns, got {len(turns)}")
    if len(faces)<7:
        raise RuntimeError(f"expected face closeups, got {len(faces)}")
    refs=[a.source,*[x for x in a.detail if x.is_file()]]
    a.out.mkdir(parents=True,exist_ok=True)

    source_sheet=_labelled_sheet(
        [(f"SOURCE {i+1}",x) for i,x in enumerate(refs[:8])],
        a.out/"source_sheet.jpg",
        title="SOURCE REFERENCES",
        columns=4,cell=320,
    )
    turn_sheet=_labelled_sheet(
        [(f"TURN {i*15:03d}",x) for i,x in enumerate(turns)],
        a.out/"turntable_sheet.jpg",
        title="KNOWN-BAD MONJA — BLENDER 24 VIEWS",
        columns=6,cell=280,
    )
    face_sheet=_labelled_sheet(
        [(f"FACE {x.stem}",x) for x in faces],
        a.out/"face_sheet.jpg",
        title="KNOWN-BAD MONJA — BLENDER FACE CLOSEUPS",
        columns=3,cell=420,
    )
    board=_stack_boards(
        [("SOURCE REFERENCES",source_sheet),("BLENDER TURNTABLE",turn_sheet),("BLENDER FACE CLOSEUPS",face_sheet)],
        a.out/"board.jpg",
    )
    payload={
        "schema":2,
        "renderer":"blender-eevee-24view-material-faithful-v1",
        "source":str(a.source),
        "turns":[str(x) for x in turns],
        "faces":[str(x) for x in faces],
        "board":str(board),
    }
    (a.out/"evidence.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
