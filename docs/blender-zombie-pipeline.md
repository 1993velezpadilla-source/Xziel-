# Blender Zombie Pipeline

This branch turns GitHub Actions into the Blender workstation for ZOMBIESSSSSSS PORTABLE. The phone/chat workflow stays lightweight: generation code lives in GitHub, Actions runs Blender headlessly, and review/export files return as workflow artifacts.

## Phase 1 — proof of execution

Phase 1 proved the autonomous path with Blender 4.0 + the raw MakeHuman base OBJ. It successfully generated GLB/BLEND/PNG outputs, but the raw base includes helper geometry that produced unacceptable visual artifacts when treated as a finished game body. That route is retained only as a historical smoke test and is **not** approved for game integration.

## Phase 2 — MPFB rigged character pipeline

The active path now uses:

- Blender 4.5.14 LTS from the official Blender Linux build.
- MPFB2 2.0.17 source installed as a Blender extension.
- MakeHuman System Assets CC0 pack.
- MPFB's `game_engine` skeleton and weights.
- MPFB's official helper-removal/export copy workflow.

The generator creates an adult humanoid through MPFB, applies a real MakeHuman skin, attaches system eyes/teeth/work clothing/shoes where available, then adds procedural corpse treatment:

- desaturated decomposed skin while preserving source skin detail;
- bruising/necrosis and integrated blood material regions;
- grime overlays on clothing;
- cloudy corpse-eye treatment;
- dirty/yellowed teeth;
- cold key + red rim review lighting.

### Phase 2 outputs

- `zombie_mpfb_lod0.glb`
- `zombie_mpfb_lod0.fbx`
- `zombie_mpfb.blend`
- `zombie_mpfb_preview.png`
- `zombie_mpfb_manifest.json`

LOD1/LOD2 are intentionally deferred until we validate a reduction method that preserves the MPFB skin weights instead of pretending a static decimation is game-ready.

## Source/licensing

The active Phase 2 character uses the MakeHuman System Assets pack, which is published as CC0. MPFB itself is a GPL Blender extension used as a build tool; its code is not copied into the game asset output. Third-party community assets are not automatically accepted because their licenses can differ.

## Next engineering stage

After the Phase 2 visual/rig output is accepted:

- validate bone orientation and scale in the game importer;
- add walk/run/attack/hit/death animation retargeting;
- create head and limb separation anchors for dismemberment;
- create headless/deheaded locomotion variants;
- add gameplay sockets and hitbox metadata;
- build weight-preserving LOD1/LOD2;
- validate mobile triangle/material/texture budgets;
- run Nacht spawn/path/headshot smoke tests.

## Game integration gates

A generated zombie is not promoted into the Android map until it passes:

- collider/hitbox alignment;
- headshot registration;
- correct forward-facing root orientation;
- animation root-motion policy;
- no backwards-facing locomotion;
- dismemberment socket validation;
- mobile performance budget;
- LOD switch test;
- map spawn-path smoke test.
