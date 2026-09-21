# Nacht der Untoten — Enhanced Mode

Enhanced Mode is an opt-in presentation layer for the stock `ndu` map. Classic remains the compatibility baseline.

## Hard invariants
- Keep the stock BSP layout, playable bounds, doors, windows, wallbuys, spawn topology, round rules and economy.
- No replacement of stock maps in the APK.
- Android-first budgets; every enhanced feature must have a cheap fallback.
- Commercial-safe/free assets live separately from extracted/reference material.

## Runtime switch
`xziel_nacht_enhanced 0|1`, exposed only when `current_selected_bsp == "ndu"`.

## Enhancement passes
1. Environment materials: concrete, damaged plaster, metal, wood barricades, rubble.
2. Props: sandbags, crates, debris, lamps, cables, barrels; preserve collision/navigation.
3. Atmosphere: dust motes, localized smoke, embers/sparks, exterior fog, lightning flashes.
4. Lighting: stronger practical-light contrast and selective dynamic lights; never make interactables unreadable.
5. Zombies: rigged animated replacement set with stock hitbox/gameplay contract and LOD/mobile fallback.
6. First-person presentation: improved hands/weapon materials where licensing and Vril model path permit.
7. Audio: layered wind, distant thunder, structure creaks, debris, zombie ambience using redistribution-safe sources.
8. Destruction feedback: better impact particles/decals and barricade feedback without changing scoring.
9. Performance: distance culling, particle caps, dynamic-light caps, texture/model budgets and Classic fallback.

## Initial mobile budgets
- 60 FPS target on modern Android handhelds; graceful 30/45 fallback.
- Dynamic lights: <= 8 important transient lights in view.
- Ambient emitters: <= 24 active, distance-gated.
- Particles: bounded per effect; no unbounded per-frame spawning.
- Enhanced prop collision: default SOLID_NOT unless gameplay explicitly requires collision.
- Zombie replacement must preserve server bbox, damage regions and state machine.

## Asset intake
Every imported asset must record source URL, author, license, original format, converted format, modifications and redistribution/commercial status in a manifest before entering a distributable APK.


## Runtime zombie replacement

Enhanced now has a **real alternate zombie model path**, not only motion
smoothing. The first shipping compatibility model is the BSD-licensed
LibreQuake zombie pinned at commit `4d2da523331f00211c97c90dc5af8672a2967618`.

Vril swaps the normal Nacht zombie body at draw time while stock NZ:P remains
authoritative for AI, HP, damage, collision, navigation, scoring, limb state,
windows and round logic. NZ:P animation frame IDs are mapped onto the
alternate model's stand/walk/run/attack/down ranges.

This first model is deliberately a low-cost Quake MDL v6 compatibility
milestone: 373 vertices, 436 triangles and 250 frames. It proves the complete
Android model path. Crawlers retain the stock segmented model until a
purpose-built crawl/death conversion is ready. The same isolated runtime slot
can later receive a higher-detail CC0/CC-BY zombie without rewriting gameplay.
