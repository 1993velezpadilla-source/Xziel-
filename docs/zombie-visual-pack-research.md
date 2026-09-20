# Xziel zombie visual-pack research (2026-09-20)

This file records redistribution-safe candidates for future Xziel zombie visual
profiles. The goal is to improve model/animation quality without depending on
assets extracted from commercial Call of Duty releases.

## Safe candidates

### Quaternius — Zombie Apocalypse Kit
- Source: https://quaternius.com/packs/zombieapocalypsekit.html
- License: CC0.
- Source formats: FBX, OBJ, Blend, glTF.
- Pack scope: 60 models, including four enemies and two dogs.
- Candidate Xziel profile: **APOCALYPSE**.
- Best use: visual variety / alternate enemy bodies.

### Quaternius — Animated Zombie Pack
- Source: https://quaternius.com/packs/animatedzombie.html
- License: CC0.
- Source formats: FBX, OBJ, Blend.
- Two animated zombie models with a larger animation set.
- Candidate Xziel profile: **UNDEAD**.
- Best use: a focused zombie-only conversion test before importing a larger kit.

### Quaternius — Universal Animation Library 2
- Source: https://quaternius.com/packs/universalanimationlibrary2.html
- License: CC0.
- Source formats: FBX, GLB, Blend.
- 130+ humanoid animations; includes zombie locomotion and supports retargeting.
- Best use: retarget higher-quality locomotion / attacks / reactions onto a
  redistribution-safe zombie rig.

## Engine conversion path

The Android SDL Vril renderer currently consumes Quake alias-model animation
for these actors. Quake MDL animation is vertex-frame based, while the source
packs above are skeletal. Therefore a safe import pipeline must:

1. import the CC0 skeletal source in Blender;
2. retarget/select locomotion, attack, hit, crawl and death clips;
3. bake the armature deformation to fixed mesh frames;
4. keep vertex count/order identical across all baked frames;
5. downsample/atlas textures for mobile;
6. export the frame sequence to Quake MDL;
7. map the resulting frame ranges to NZ:P's existing zombie gameplay states;
8. validate collision, limb/head hit logic, barriers, crawlers, deaths and
   Android performance before exposing the profile in Settings.

Useful open tooling:
- https://github.com/khreathor/mdl-for-blender
- https://github.com/cmdrf/quake-export

The latter supports automated Quake MDL creation from OBJ frame sequences,
which makes it a good fit once Blender has baked the skeletal animation.

## Profile policy

Keep **CLASSIC** as the untouched NZ:P presentation and **MODERN** as Xziel's
current smoothing/presentation layer. New visible profile names should only be
added after their models and complete animation/state mappings are actually
packaged and validated.

Do not ship profiles called Black Ops / World at War / Modern Warfare using
models or animations extracted from those retail games. References to those
games are useful for motion direction and timing research, but Xziel's
redistributable asset packs should use assets we have permission to distribute.
