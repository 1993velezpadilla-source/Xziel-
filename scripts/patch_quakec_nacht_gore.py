#!/usr/bin/env python3
"""Presentation-only gore polish for Nacht: Enchanted Lab.

NZ:P already contains dedicated full/crawler/head/arm models and authoritative
dismemberment/crawler gameplay. This patch does not replace that logic. It
makes the existing sever events read harder on the Enchanted practice map by
layering bounded blood/gib particles and a crawler-conversion burst.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_nacht_gore.py <quakec-root>")

root = Path(sys.argv[1])

weapon = root / "source/server/weapons/weapon_core.qc"
s = weapon.read_text(encoding="utf-8")

old = r'''void(vector where) spawn_gibs = {

#ifndef FTE

	particle(where, where*0.1, 225, 1);

#else

	FTE_RunParticleEffect(world, CSQC_PART_ZOMBIEGIB, where, 0, world);

#endif // FTE

}'''

new = r'''void(vector where) spawn_gibs = {

#ifndef FTE

	particle(where, where*0.1, 225, 1);

#else

	FTE_RunParticleEffect(world, CSQC_PART_ZOMBIEGIB, where, 0, world);

	// The Enchanted practice map uses the existing NZ:P dismemberment state
	// but gives each sever event a denser, still bounded, visual signature.
	if (mapname == "ndu_enchanted") {
		FTE_RunParticleEffect(world, CSQC_PART_BLOODIMPACT, where, 0, world);
		FTE_RunParticleEffect(world, CSQC_PART_BLOODIMPACT, where + '2 -2 3', 0, world);
		FTE_RunParticleEffect(world, CSQC_PART_BLOODIMPACT, where + '-3 2 1', 0, world);
	}

#endif // FTE

}'''
if old not in s:
    raise SystemExit("spawn_gibs anchor missing")
s = s.replace(old, new, 1)
weapon.write_text(s, encoding="utf-8")

crawler = root / "source/server/ai/crawler_core.qc"
s = crawler.read_text(encoding="utf-8")
needle = 'setmodel(who,"models/ai/zbc%.mdl");'
replacement = r'''setmodel(who,"models/ai/zbc%.mdl");

#ifdef FTE
	// Legs-to-crawler conversion already exists in stock NZ:P. Add one
	// low-cost burst so the state change is readable without inventing a
	// second crawler system or changing damage/health rules.
	if (mapname == "ndu_enchanted") {
		FTE_RunParticleEffect(world, CSQC_PART_ZOMBIEGIB, who.origin - '0 0 20', 0, world);
		FTE_RunParticleEffect(world, CSQC_PART_BLOODIMPACT, who.origin - '0 0 18', 0, world);
	}
#endif // FTE'''
if needle not in s:
    raise SystemExit("crawler conversion anchor missing")
s = s.replace(needle, replacement, 1)
crawler.write_text(s, encoding="utf-8")

print("Applied bounded Enchanted gore polish over stock crawler/dismemberment systems.")
