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
zombie_core = root / "source/server/ai/zombie_core.qc"

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

# The real zombie spawn path lives in zombie_core.qc. RelinkZombies() is not
# enough on Vril/standard QuakeC because its visual model switching is inside
# an FTE-only branch. Bind the Lab model at the actual allocation/spawn point.
zs = zombie_core.read_text(encoding="utf-8")

limb_anchor = '''#ifndef FTE

\tupdateLimb (szombie, 0, szombie.head);
\tupdateLimb (szombie, 1, szombie.larm);
\tupdateLimb (szombie, 2, szombie.rarm);

#endif // FTE
'''
limb_new = limb_anchor + '''
\t// XZIEL_LAB_SPAWN_MODEL: keep the stock limb entities alive for hitboxes
\t// and dismemberment bookkeeping, but do not render their legacy meshes
\t// over the complete Lab character.
\tif (mapname == "ndu_enchanted") {
\t\tsetmodel(szombie.head, "");
\t\tsetmodel(szombie.rarm, "");
\t\tsetmodel(szombie.larm, "");
\t}
'''
if 'XZIEL_LAB_SPAWN_MODEL' not in zs:
    if limb_anchor not in zs:
        raise SystemExit("Lab zombie limb-link spawn anchor missing")
    zs = zs.replace(limb_anchor, limb_new, 1)

body_anchor = '''\tszombie.movetype = MOVETYPE_WALK;
\tsetmodel(szombie, "models/ai/zb%.mdl");
\tszombie.hop_step = 0;
'''
body_new = '''\tszombie.movetype = MOVETYPE_WALK;
\tif (mapname == "ndu_enchanted")
\t\tsetmodel(szombie, "models/xziel_lab/zombie_basic.mdl");
\telse
\t\tsetmodel(szombie, "models/ai/zb%.mdl");
\tszombie.hop_step = 0;
'''
if 'if (mapname == "ndu_enchanted")\n\t\tsetmodel(szombie, "models/xziel_lab/zombie_basic.mdl");' not in zs:
    if body_anchor not in zs:
        raise SystemExit("Lab zombie body spawn anchor missing")
    zs = zs.replace(body_anchor, body_new, 1)

skin_anchor = '''\tszombie.head.skin = szombie.larm.skin = szombie.rarm.skin = szombie.skin;
'''
skin_new = skin_anchor + '''
\t// The baked Lab MDL currently exposes one atlas/skin. Do not inherit the
\t// stock random 0..3 zombie skin index.
\tif (mapname == "ndu_enchanted")
\t\tszombie.head.skin = szombie.larm.skin = szombie.rarm.skin = szombie.skin = 0;
'''
if 'stock random 0..3 zombie skin index' not in zs:
    if skin_anchor not in zs:
        raise SystemExit("Lab zombie spawn skin anchor missing")
    zs = zs.replace(skin_anchor, skin_new, 1)

zombie_core.write_text(zs, encoding="utf-8")

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
