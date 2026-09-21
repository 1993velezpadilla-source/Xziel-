# Xziel asset priority shortlist

Last reviewed: 2026-09-20

This is the actionable front of the larger commercial-safe catalog. It intentionally prioritizes legal clarity, animation/rig usefulness and Android suitability over sheer asset count.

## Tier A — prototype first

1. **OpenGameArt Male City Zombie (CC0)**  
   Rigged/textured with walk, run, three attacks, hit, scream, idle and death. Use as the first realistic/open humanoid zombie integration test.

2. **Quaternius Zombie Apocalypse Kit (CC0)**  
   60-model ecosystem with animated characters, enemies, dogs, props and vehicles. Use as the broad baseline pack and body-variety source.

3. **Quaternius Universal Animation Library 2 + KayKit Character Animations (CC0)**  
   Use as the retarget library for zombie locomotion, attacks, reactions, player movement and fallback state coverage.

4. **Studio New Punch split-body zombies — license verification required before use**  
   These are the best current leads for ready-made head/arm/leg dismemberment geometry. Acquire only after confirming the current Unity Asset Store license; do not mirror raw files publicly.

5. **FireWarden Lowpoly Pistol (CC0)**  
   Fictional design, 1,350 triangles, separate slide/trigger/hammer/barrel/loaded+empty magazines. Use as the weapon-animation reference implementation.

6. **Drillimpact PSX First Person Arms + OpenGameArt rigged FPS arms (CC0)**  
   Build the canonical Xziel first-person arm skeleton and retarget pipeline from these legal bases; replace art style as needed.

7. **Quaternius Downtown City MegaKit + Kenney city/factory/survival kits + Poly Haven/ambientCG (CC0)**  
   Use together to build abandoned urban test maps without proprietary map geometry.

8. **Binbun Muzzle Flash / Electric / Hit FX + OpenGameArt gore + TomAzod Water Splash (CC0)**  
   Build the reusable VFX graph: muzzle, impact, blood, sparks, electricity, puddle/rain splash and environmental FX.

9. **OpenGameArt Zombies Sound Pack + Free Firearm Sound Library + general CC0 impact/metal/water libraries**  
   Build layered original weapon/zombie/environment audio rather than cloning retail-game sound files.

10. **Gobkit Free Animal Pack + Quaternius dogs (CC0)**  
    Establish the non-humanoid rig/state pipeline for infected dogs, bats and future special enemies.

## Tier B — commercial with attribution

- Tony Flanagan animated zombie series — verify each exact listing and preserve CC BY attribution where applicable.
- Aiden Studios rigged/animated zombie on Sketchfab — CC Attribution; ~19.5k tris, useful as a modern mobile LOD0 reference.
- Other CC BY assets can be accepted when attribution is tracked automatically in the manifest/credits pipeline.

## Tier C — acquire/verify before production

- Hotstrike Stylized Dark Fantasy Zombie on Fab.
- Fab Zombies Modular Four Pack / Dismemberable Zombie Pack / gore systems.
- RetroStyle German Shepherd.
- Shadow Crawler.
- Any "free" marketplace item whose page does not expose a concrete reuse license.

## AI-generated source quarantine

3DAssets.dev currently offers a very useful CC0 Survival Forest Outpost pack with animated gun components, vehicles and props, but the source marks the pack AI-generated. Keep it in a QA lane until each selected asset passes:
- visual coherence review
- topology/UV/material review
- accidental resemblance/IP review
- mobile budget review
- manual in-game inspection

## Never graduate automatically

Do not move these into the commercial-safe lane without rights clearance:
- Call of Duty/other retail-game rips
- NC / NonCommercial assets
- "free download" files with no reuse license
- fan models copied from protected characters/weapons/brands
- raw marketplace packages whose EULA permits only embedded-project distribution

## First dismemberment prototype

Recommended legal prototype path:
1. Male City Zombie or Quaternius zombie as base.
2. Segment neck, shoulders, elbows, hips and knees in Blender.
3. Add stump cap meshes and blood emitter sockets.
4. Retain one canonical humanoid skeleton.
5. Map per-limb hit capsules and detach thresholds.
6. Leg loss -> crawler capability state.
7. Arm loss -> attack capability reduction.
8. Head loss -> lethal by default, archetype override optional.
9. Pool gibs, decals, blood particles and detached rigid bodies.
10. Stress test on Android before increasing gore concurrency.

This gives Xziel the gameplay behavior the user wants without depending on proprietary ripped meshes.
