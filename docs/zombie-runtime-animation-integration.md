# Zombie animation runtime bridge

Xziel/NZ:P currently drives a classic Quake MDL body with explicit frame
indices from QuakeC. Skeletal FBX/GLB therefore cannot simply replace the
runtime model.

## Compatibility strategy

Every generated visual variant is baked to 211 body frames matching the
standing-zombie indices used by upstream zombie_core.qc:

- 0-12 idle
- 13-36 rise
- 37-52 walk A
- 53-66 walk B
- 67-82 walk C
- 83-90 jog
- 92-101 run
- 102-112 melee swipes
- 113-122 window hop
- 123-148 death ranges
- 149-152 fall
- 153-159 land
- 160-180 currently unused/reserved by the standing body
- 181-201 barricade/rip-board attacks
- 202-210 attack-through-window

Gameplay keeps its existing damage timing, hit boxes, navigation, barricade
logic and round logic. A future zombie animation variant is selected by
changing only its compatible body-model path.

## Vril alias limits

The SDL/Vril path currently defines 2048 alias vertices, 2048 triangles and
256 frames. The prototype baker targets below those limits and CI validates
the generated MDL with quake-mdl-info.

## Rollout

1. Prove glTF -> sampled OBJ frames -> MDL with the self-contained CC0
   Quaternius Zombie Apocalypse models.
2. Keep generated models opt-in until Android rendering is verified.
3. Add deterministic per-zombie model selection with stock fallback.
4. Retarget CMU human optical mocap onto the validated compatibility rig.
5. Enable the expanded pool only after the Android smoke test passes.

Crawler bodies use a separate frame contract and remain stock for now.
