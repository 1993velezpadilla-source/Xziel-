#!/usr/bin/env python3
"""Xziel v0.26: deterministic four-player co-op spawn layout.

NZ:P normally randomizes the first four character spawn entities. For online
co-op we keep the map-authored four spawn positions but bind player slots
1..4 to spawn classes 1..4. This prevents clients from stacking on the same
spawn and keeps the starting group in the map's intended spawn area.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_multiplayer_v026.py <quakec-root>")

root = Path(sys.argv[1])
path = root / "source" / "server" / "player" / "player_core.qc"
text = path.read_text(encoding="utf-8")

anchor = """#endif // FTE

	// Assign a location
	while(!found_viable_spawn) {
"""
insert = """#endif // FTE

	// Online/co-op: make the first four player slots deterministic. The map's
	// authored spawn1..spawn4 positions are already designed as a nearby start
	// group, so each network player gets a stable, distinct location.
	if (coop && self.playernum >= 1 && self.playernum <= 4) {
		switch(self.playernum) {
			case 1: spawn_point = find(world, classname, SPAWN_1_CLASS); break;
			case 2: spawn_point = find(world, classname, SPAWN_2_CLASS); break;
			case 3: spawn_point = find(world, classname, SPAWN_3_CLASS); break;
			case 4: spawn_point = find(world, classname, SPAWN_4_CLASS); break;
		}

		if (spawn_point != world) {
			float occupied = false;
			entity nearby = findradius(spawn_point.origin, 32);
			while (nearby != world) {
				if (nearby.classname == "player" && nearby != self)
					occupied = true;
				nearby = nearby.chain;
			}
			if (!occupied)
				found_viable_spawn = true;
		}
	}

	// Assign a location
	while(!found_viable_spawn) {
"""
if "Online/co-op: make the first four player slots deterministic" not in text:
    if anchor not in text:
        raise SystemExit("Could not find Player_PickSpawnPoint location anchor")
    text = text.replace(anchor, insert, 1)

path.write_text(text, encoding="utf-8")
print("Applied Xziel v0.26 deterministic four-player co-op spawns.")
