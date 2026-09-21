#!/usr/bin/env python3
"""Use the baked CC0 zombie model only on Nacht: Enchanted Lab.

Gameplay remains NZ:P-authoritative. Standing zombies use animated Lab mesh
variants whose visible head/arms follow the stock NZ:P dismemberment flags.
Crawlers intentionally keep the proven stock crawler path for now.
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
\tif (mapname == "ndu_enchanted") {
\t\tprecache_model ("models/xziel_lab/zombie_basic.mdl");
\t\tprecache_model ("models/xziel_lab/zombie_basic_nohead.mdl");
\t\tprecache_model ("models/xziel_lab/zombie_basic_nolarm.mdl");
\t\tprecache_model ("models/xziel_lab/zombie_basic_normarm.mdl");
\t\tprecache_model ("models/xziel_lab/zombie_basic_nohead_nolarm.mdl");
\t\tprecache_model ("models/xziel_lab/zombie_basic_nohead_normarm.mdl");
\t\tprecache_model ("models/xziel_lab/zombie_basic_noarms.mdl");
\t\tprecache_model ("models/xziel_lab/zombie_basic_nohead_noarms.mdl");
\t}
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


# XZIEL_LAB_VISUAL_DISMEMBERMENT: the body model is monolithic, while NZ:P's
# damage system tracks head/arms as separate invisible entities. On every
# relink, select a pre-baked body surface variant from those authoritative
# deadflags. This preserves headless bleed-out, arm loss, scoring and AI while
# making the visible mesh tell the truth.
relink_anchor = '''#endif // FTE

\t\tmakevectors (ent.angles);

\t\tfor(i = 0; i < 3; i++)
'''
relink_new = '''#endif // FTE

\t\t// XZIEL_LAB_VISUAL_DISMEMBERMENT
\t\tif (mapname == "ndu_enchanted" && ent.crawling != 1) {
\t\t\tlocal string lab_model;
\t\t\tif (!ent.head.deadflag) {
\t\t\t\tif (!ent.larm.deadflag && !ent.rarm.deadflag)
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic_nohead_noarms.mdl";
\t\t\t\telse if (!ent.larm.deadflag)
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic_nohead_nolarm.mdl";
\t\t\t\telse if (!ent.rarm.deadflag)
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic_nohead_normarm.mdl";
\t\t\t\telse
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic_nohead.mdl";
\t\t\t} else {
\t\t\t\tif (!ent.larm.deadflag && !ent.rarm.deadflag)
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic_noarms.mdl";
\t\t\t\telse if (!ent.larm.deadflag)
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic_nolarm.mdl";
\t\t\t\telse if (!ent.rarm.deadflag)
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic_normarm.mdl";
\t\t\t\telse
\t\t\t\t\tlab_model = "models/xziel_lab/zombie_basic.mdl";
\t\t\t}
\t\t\tif (ent.model != lab_model)
\t\t\t\tsetmodel(ent, lab_model);
\t\t\tsetmodel(ent.head, "");
\t\t\tsetmodel(ent.larm, "");
\t\t\tsetmodel(ent.rarm, "");
\t\t}

\t\tmakevectors (ent.angles);

\t\tfor(i = 0; i < 3; i++)
'''
if 'XZIEL_LAB_VISUAL_DISMEMBERMENT' not in s:
    if relink_anchor not in s:
        raise SystemExit("Lab visual-dismemberment relink anchor missing")
    s = s.replace(relink_anchor, relink_new, 1)

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
\t// XZIEL_LAB_SKIN_VARIANTS: the Lab family bakes four external horror skins,
\t// so intentionally preserve NZ:P's stock random skin index 0..3.
'''
if 'XZIEL_LAB_SKIN_VARIANTS' not in zs:
    if skin_anchor not in zs:
        raise SystemExit("Lab zombie spawn skin anchor missing")
    zs = zs.replace(skin_anchor, skin_new, 1)

hitbox_anchor = '''\tif (map_compatibility_mode == MAP_COMPAT_BETA) {
\t\tvector_scale_hack(self.head.bbmins, self.head.scale);
\t\tvector_scale_hack(self.head.bbmaxs, self.head.scale);
\t\tvector_scale_hack(self.head.view_ofs, self.head.scale);

\t\tvector_scale_hack(self.larm.bbmins, self.larm.scale);
\t\tvector_scale_hack(self.larm.bbmaxs, self.larm.scale);
\t\tvector_scale_hack(self.larm.view_ofs, self.larm.scale);

\t\tvector_scale_hack(self.rarm.bbmins, self.rarm.scale);
\t\tvector_scale_hack(self.rarm.bbmaxs, self.rarm.scale);
\t\tvector_scale_hack(self.rarm.view_ofs, self.rarm.scale);
\t}
'''
hitbox_new = hitbox_anchor + '''
\t// XZIEL_LAB_DAMAGE_ENVELOPE: the Lab presentation mesh is intentionally
\t// wider than NZ:P's segmented zombie. Expand only the damage proxies here;
\t// do NOT widen szombie.mins/maxs, because that movement hull must remain
\t// stock-sized for windows, doorways, pathing and zombie trains.
\tif (mapname == "ndu_enchanted") {
\t\tvector_scale_hack(self.head.bbmins, 1.85);
\t\tvector_scale_hack(self.head.bbmaxs, 1.85);

\t\tvector_scale_hack(self.larm.bbmins, 1.65);
\t\tvector_scale_hack(self.larm.bbmaxs, 1.65);
\t\tvector_scale_hack(self.rarm.bbmins, 1.65);
\t\tvector_scale_hack(self.rarm.bbmaxs, 1.65);

\t\t// The new rig carries its limbs a little farther from the torso than
\t\t// the legacy segmented mesh. Mildly expand offsets without moving the
\t\t// hitboxes so far out that center-mass shots develop holes.
\t\tvector_scale_hack(self.head.view_ofs, 1.08);
\t\tvector_scale_hack(self.larm.view_ofs, 1.12);
\t\tvector_scale_hack(self.rarm.view_ofs, 1.12);
\t}
'''
if 'XZIEL_LAB_DAMAGE_ENVELOPE' not in zs:
    if hitbox_anchor not in zs:
        raise SystemExit("Lab zombie damage-hitbox anchor missing")
    zs = zs.replace(hitbox_anchor, hitbox_new, 1)

zombie_core.write_text(zs, encoding="utf-8")

s = client.read_text(encoding="utf-8")
snap_anchor = '''    {"models/ai/zfull.mdl", [0, 0, 18], [0, 0, 35]},
'''
snap_new = '''    {"models/ai/zfull.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic_nohead.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic_nolarm.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic_normarm.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic_nohead_nolarm.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic_nohead_normarm.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic_noarms.mdl", [0, 0, 18], [0, 0, 35]},
    {"models/xziel_lab/zombie_basic_nohead_noarms.mdl", [0, 0, 18], [0, 0, 35]},
'''
if '"models/xziel_lab/zombie_basic.mdl", [0, 0, 18]' not in s:
    if snap_anchor not in s:
        raise SystemExit("zombie aim-snap anchor missing")
    s = s.replace(snap_anchor, snap_new, 1)

client.write_text(s, encoding="utf-8")
print("Bound Lab zombie family with aligned hitboxes, horror skins and visible dismemberment.")
