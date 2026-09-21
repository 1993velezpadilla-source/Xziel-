#!/usr/bin/env python3
"""Use the baked CC0 zombie model only on Nacht: Enchanted Lab.

Gameplay remains NZ:P-authoritative. Intact standing zombies use the Lab model;
crawlers and severed-limb states intentionally fall back to stock segmented
models until dedicated Lab crawler/limb assets are baked.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_lab_zombies.py <quakec-root>")

root = Path(sys.argv[1])
main = root / "source/server/main.qc"
client = root / "source/client/zombie.qc"

s = main.read_text(encoding="utf-8")

precache_anchor = '\tprecache_model ("models/ai/zfull.mdl");\n'
precache = '''\tprecache_model ("models/ai/zfull.mdl");
\tif (mapname == "ndu_enchanted")
\t\tprecache_model ("models/xziel_lab/zombie_basic.mdl");
'''
if 'precache_model ("models/xziel_lab/zombie_basic.mdl")' not in s:
    if precache_anchor not in s:
        raise SystemExit("zombie precache anchor missing")
    s = s.replace(precache_anchor, precache, 1)

old = '''\t\tif (ent.larm.deadflag && ent.rarm.deadflag && ent.head.deadflag) {
\t\t\tsetmodel(ent.larm, "");
\t\t\tsetmodel(ent.rarm, "");
\t\t\tsetmodel(ent.head, "");

\t\t\tif (ent.crawling == 1)
\t\t\t\tsetmodel(ent, "models/ai/zcfull.mdl");
\t\t\telse
\t\t\t\tsetmodel(ent, "models/ai/zfull.mdl");
'''
new = '''\t\tif (ent.larm.deadflag && ent.rarm.deadflag && ent.head.deadflag) {
\t\t\tsetmodel(ent.larm, "");
\t\t\tsetmodel(ent.rarm, "");
\t\t\tsetmodel(ent.head, "");

\t\t\tif (ent.crawling == 1) {
\t\t\t\t// Phase 1 keeps NZ:P's crawler contract/model. A dedicated
\t\t\t\t// Lab crawler will replace this in the next asset pass.
\t\t\t\tsetmodel(ent, "models/ai/zcfull.mdl");
\t\t\t} else if (mapname == "ndu_enchanted") {
\t\t\t\t// Real CC0 animated Lab model. Its 0..210 frame layout mirrors
\t\t\t\t// NZ:P, so all existing AI/damage timings remain authoritative.
\t\t\t\tsetmodel(ent, "models/xziel_lab/zombie_basic.mdl");
\t\t\t} else {
\t\t\t\tsetmodel(ent, "models/ai/zfull.mdl");
\t\t\t}
'''
if 'setmodel(ent, "models/xziel_lab/zombie_basic.mdl")' not in s:
    if old not in s:
        raise SystemExit("RelinkZombies intact-model anchor missing")
    s = s.replace(old, new, 1)

main.write_text(s, encoding="utf-8")

s = client.read_text(encoding="utf-8")
snap_anchor = '''    {"models/ai/zfull.mdl", [0, 0, 18], [0, 0, 35]},
'''
snap_new = '''    {"models/ai/zfull.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic.mdl", [0, 0, 18], [0, 0, 35]},
'''
if '"models/xziel_lab/zombie_basic.mdl", [0, 0, 18]' not in s:
    if snap_anchor not in s:
        raise SystemExit("zombie aim-snap anchor missing")
    s = s.replace(snap_anchor, snap_new, 1)

client.write_text(s, encoding="utf-8")
print("Bound the real animated CC0 zombie model to intact Lab zombies only.")
