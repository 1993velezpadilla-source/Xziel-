# Enhanced Asset Roadmap

This branch prepares a non-destructive visual upgrade path for the native Android NZ:P port.

## Goal

Keep the current gameplay/touch work intact while preparing higher-quality content that can be swapped in after touchscreen gameplay is locked.

## Rules

1. Do not replace working classic content in-place.
2. New content lands under `content/enhanced/`.
3. Every third-party asset must have a recorded source URL and explicit commercial-use license.
4. Reject assets marked personal-use, non-commercial, editorial-only, ripped, extracted, or with unknown provenance.
5. Keep gameplay logic separate from presentation so Classic and Enhanced can coexist.
6. Mobile budget first: prefer game-ready meshes, compact textures, and deterministic animation sets.

## First vertical slice

Target one complete visual test before scaling up:

- Primary zombie: **Zombie Soldier by Peter_D** — mobile-oriented, rigged, normal/roughness maps, Mixamo-compatible, CC BY.
- Fallback zombie: **Male City Zombie by Rikindle3D** — rigged, textured, multiple walk/attack/death/idle/run animations, CC0.
- Dog prototype: **Quaternius Zombie Apocalypse Kit** — CC0, includes two dogs and multiple animated characters/enemies.
- Environment materials: **Poly Haven** — CC0 textures/models/HDRIs.
- Blood/decal prototype: **Kenney Splat Pack** — CC0.
- Zombie vocals: **Zomby SFX Pack by saturn91** — CC0.
- Horror ambience: **Ambient Horror by techiew** — CC0.

## Integration order

1. Finish current touchscreen gameplay validation.
2. Import one zombie into an isolated test map.
3. Verify model scale, collision bounds, animation frame mapping, hit reactions, death and mobile performance.
4. Add one dog and validate special-round behavior.
5. Upgrade one existing map room with higher-resolution legal materials and decals.
6. Upgrade one first-person weapon.
7. Only after the vertical slice is stable, expand to the rest of the game.

## Renderer / format strategy

FTEQW supports a broad set of model/image formats and includes IQM and glTF tooling/plugins upstream. For the Android shipping path, do not assume every desktop plugin is available. Convert source assets into the format already proven by the Android build unless a newer format is explicitly validated on-device.

Recommended source workflow:

`FBX / glTF / Blend -> Blender cleanup -> mobile LOD / texture pass -> validated FTE/NZ:P runtime format`

## Visual direction

The target is not generic bright low-poly zombies. The target is classic dark round-based zombie horror:

- military/civilian undead silhouettes;
- damaged clothing and readable faces;
- bright supernatural eyes only where stylistically useful;
- dirty concrete, rusted steel, timber and industrial props;
- strong darkness/contrast with readable gameplay silhouettes;
- restrained fog, sparks, embers and emergency lighting;
- no copied COD logos, ripped models, extracted sounds or proprietary textures.

## Source candidates

- Zombie Soldier: https://sketchfab.com/3d-models/zombie-soldier-176e930e63d144cc8f615b8dd3a8c74f
- Male City Zombie: https://opengameart.org/node/111870
- Quaternius Zombie Apocalypse Kit: https://quaternius.com/packs/zombieapocalypsekit.html
- Poly Haven: https://polyhaven.com/
- Kenney Splat Pack: https://kenney-assets.itch.io/splat-pack
- Zomby SFX Pack: https://opengameart.org/content/zomby-sfx-pack
- Ambient Horror: https://opengameart.org/content/ambient-horror

## Definition of done for the first visual test

- Runs in the native Android APK.
- No regression to touch controls.
- No missing-texture/model warnings.
- Stable animation at gameplay framerate.
- Zombie remains readable in dark scenes.
- Performance is acceptable with a representative horde.
- Asset provenance is recorded in `content/enhanced/asset_manifest.json`.
