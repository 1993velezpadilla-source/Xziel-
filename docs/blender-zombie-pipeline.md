# Blender Zombie Pipeline

This branch turns GitHub Actions into the Blender workstation for the zombie project. The phone/chat workflow stays lightweight: code and art-generation recipes live in GitHub, Actions runs Blender headless, and the resulting GLB/BLEND/PNG files are returned as workflow artifacts.

## Phase 1

1. Clone the current MakeHuman repository.
2. Read the MakeHuman core human base mesh.
3. Run Blender without a GUI.
4. Normalize the body to game scale.
5. Apply deterministic corpse asymmetry.
6. Build procedural decomposed-skin, cloth, blood, bone and eye materials.
7. Add torn clothing shells and wound geometry.
8. Export:
   - `zombie_lod0.glb`
   - `zombie_lod1.glb`
   - `zombie_lod2.glb`
   - `zombie_lod0.blend`
   - `zombie_preview.png`
   - `zombie_manifest.json`
9. Upload the whole output directory as a GitHub Actions artifact.

The model is intentionally generated from a real humanoid topology instead of primitive boxes/cylinders. Phase 1 is the visual pipeline proof and does not yet replace the in-game zombie.

## Source/licensing

The source body is the MakeHuman core base mesh. MakeHuman core graphical assets are CC0. The generated visual asset therefore has a clean starting point for game use. Third-party MakeHuman community assets are **not** automatically accepted by this pipeline because their licenses can differ.

## Phase 2

Move the generator to Blender 4.2+ + MPFB2 and automate:
- humanoid skeleton generation;
- skin weights;
- game-engine rig conversion;
- retargeting of walk/run/attack/hit/death animations;
- head/limb separation anchors for dismemberment;
- headless/deheaded locomotion variants;
- socket/attachment points;
- FBX/GLB export validation.

## Phase 3

Generate a small zombie family from one recipe:
- normal male;
- normal female;
- thin/decomposed;
- heavy;
- burned;
- partial-face destruction.

All variants will share compatible gameplay dimensions and animation contracts while changing proportions, face damage, clothing and material seed.

## Game integration gates

A generated zombie is not promoted into the Android map until it passes:
- collider/hitbox alignment;
- headshot registration;
- correct forward-facing root orientation;
- walk/run animation root motion policy;
- no backwards-facing locomotion;
- dismemberment socket validation;
- mobile triangle/material/texture budgets;
- LOD switch test;
- Nacht spawn-path smoke test.
