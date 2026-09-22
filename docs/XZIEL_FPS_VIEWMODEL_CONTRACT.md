# Xziel FPS Viewmodel Contract

This is the import contract for first-person firearms in the native Xziel/Vulkan path.

The immediate goal is simple: a clean, stable, high-quality firearm must render correctly before skeletal animation is required. Rigging is optional for the first checkpoint and must never be allowed to corrupt the static ready pose.

## Coordinate and scale contract

- Runtime space: meters.
- Up axis: +Y.
- Camera/viewmodel forward: +Z.
- Imported geometry must have finite transforms with applied scale.
- The complete static ready-pose envelope must be between 0.30 m and 1.50 m on its longest axis.
- Normal rifle target is approximately 0.75-1.05 m overall.
- No hidden helper mesh, armature control, reference plane or locator may dominate the exported bounds.

The native loader measures the actual XZSM vertex cloud. Declared source metadata alone is not accepted as proof.

## Geometry quality gate

Current native limits live in `engine/include/xziel/static_mesh.hpp`.

The gate rejects:

- empty or extremely fragmented models
- fewer than 96 vertices / indices
- more than 600,000 vertices
- more than 900,000 indices
- more than 128 render batches
- non-triangle index counts
- weapon envelopes outside 0.30-1.50 m
- a vertex cloud where most of the weapon collapses into one tiny region
- a long needle/line/triangle that happens to reach the expected rifle length
- models whose robust 3D thickness is implausibly close to zero

A rejected imported weapon does not crash the game. Xziel leaves the bad mesh unloaded and uses the bounded native rifle blockout while diagnostics identify the exact rejection reason.

## Required static checkpoint

Before animation work, the source must produce a correct static ready pose with:

- receiver/body visibly intact
- stock intact
- barrel/muzzle intact
- magazine in the correct location
- sights/rail intact when present
- no giant triangles or lines
- no collapsed pieces at the origin
- no unexplained scale jump
- no camera-crossing helper geometry

Do not spend time repairing a complicated skeleton just to pass this checkpoint. If the rig is the source of corruption, export a clean static mesh first.

## Recommended movable pieces

Keep these as separate named objects when the source supports it:

- `weapon_body`
- `magazine`
- `bolt`
- `charging_handle`
- `muzzle`
- `trigger`

These pieces allow Xziel to add bounded native fire/recoil, magazine reload and bolt motion without requiring a full skeletal runtime immediately.

## Animation staging

Animation should be added in this order:

1. static ready pose
2. fire/recoil
3. magazine detach/insert
4. bolt/charging-handle motion
5. full reload timing
6. optional hand/arm skeletal animation

At every stage, the static model remains a valid fallback.

## Materials

Source assets may remain full PBR during authoring. Preserve Base Color, normal, roughness, metallic and AO source textures.

XZSM v3 currently binds the Base Color texture plus vertex normals/colors in the native static-mesh renderer. Do not destructively throw away the other PBR maps: they are source material for the later native material ABI.

For mobile:

- prefer a small number of well-packed material sets
- avoid hundreds of tiny material slots
- 2K is a good normal target
- 4K is acceptable for a hero weapon when the source genuinely contains that detail
- do not upscale a blurry source and call it additional detail

## Failure telemetry

Accepted weapon:

`XZIEL_WEAPON_VIEWMODEL_SANITY_OK ...`

Rejected weapon:

`XZIEL_WEAPON_VIEWMODEL_REJECTED reason=<reason> ...`

Safe runtime fallback:

`XZIEL_WEAPON_VIEWMODEL_FALLBACK_BLOCKOUT`

The diagnostic includes envelope size, robust 90% extents, peak vertex concentration, batch count, vertex count and index count.

## Non-negotiable rule

A green build is not enough if the first-person model is visually broken.

The imported firearm must pass both the deterministic geometry gate and an in-game visual inspection before it replaces the native blockout as the accepted Sanctum weapon.
