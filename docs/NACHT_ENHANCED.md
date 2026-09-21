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
