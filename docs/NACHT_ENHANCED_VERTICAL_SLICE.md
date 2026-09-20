# Nacht der Untoten — Enhanced Vertical Slice

## Purpose

Nacht is the first full Enhanced/Shattered visual benchmark for the native Android port.

**Gameplay must not change.** The existing map layout, collision, zombie routes, doors, costs, weapon behavior, Mystery Box logic, Ray Gun damage, round progression, and touch controls remain authoritative.

Classic remains untouched. Enhanced is an alternate presentation layer.

## Verified source baseline

Upstream editable map source:
`nzp-team/assets/source/maps/ndu/ndu.map`

Current map inventory from the real source:

- 432 entities
- 24 `spawn_zombie`
- 21 `explosive_barrel`
- 16 `path_corner`
- 14 `light`
- 10 `light_spot`
- 1 `light_environment`
- 12 `item_barricade`
- 9 `buy_weapon`
- 8 `weapon_wall`
- 8 `place_fire`
- 1 fixed `mystery_box`
- 133 `func_wall`
- 123 `place_model`
- 28 `misc_model`

The Mystery Box is at origin `1080 2368 56`.

### Highest-impact map textures

1. `NDUWALL` — 986 faces
2. `CONS5NNY3` — 185
3. `DEBRIS_HNF3P` — 148
4. `GROUND_HB3` — 48
5. `3TILES_GREY_64` — 37
6. `DOORWAY_MET` — 33
7. `W_WOOD_BROWN_RE` — 31
8. `M_METAL_DARKBLU` — 30
9. `W_S_WOODEN_B64` — 23
10. `BOX_SIDE_O` — 18
11. `{RAILLING_NDU` — 17
12. `{BOARD_FE` — 12
13. `{BARBED_WIRE_V` — 8

These are the first surfaces to target. Utility surfaces such as NULL/CLIP/TRIGGER/SKIP are not visual-upgrade targets.

## Renderer reality: Vril Android path

The current Android APK uses **Vril Engine through GL4ES**, not the full FTEQW renderer.

Verified Vril SDL/OpenGL capabilities we can use immediately:

- dynamic lightmaps: `r_dynamic`
- surface-reactive dynamic lighting when `gl_flashblend 0`
- projected alias-model shadows: `r_shadows`
- fog / sky fog
- smooth model shading
- mipmapped linear/trilinear filtering
- configurable texture maximum size / picmip
- decals and QMB particle system
- explosion / trail / spark / blood / flame / muzzle particle controls
- model interpolation
- lightstyles / flicker
- existing static BSP lightmaps

Not currently present in Vril:

- FTE-style realtime world shadow maps
- FTE `.rtlights`
- FTE bloom / HDR cvars
- FTE normal/specular material pipeline

Therefore Max v1 must use the features Vril actually has. Do not silently depend on FTE-only cvars.

### PBR asset conversion rule

Poly Haven and similar PBR sources are still useful. For Vril v1:

`PBR source -> base color + AO/detail bake -> mobile diffuse texture -> Vril lightmap/dynamic-light response`

Keep normal/roughness source files archived in provenance metadata so they can be used later if a shader renderer is added.

## Content modes

### Classic
Exactly current NZ:P assets and rendering behavior. No Enhanced overlay. This is the low-end fallback and visual preservation mode.

### Enhanced Low
- Enhanced zombie/body models at lowest validated LOD
- 512 px world texture target
- filtered textures, no retro nearest filtering
- new 2D VFX at reduced particle density
- no model shadows
- cheap flash-blended dynamic lights
- minimal ground clutter

### Enhanced Medium
- 1K hero/world textures where useful
- medium zombie LOD
- surface-reactive dynamic lights
- no projected model shadows by default
- moderate smoke/fire/sparks/debris
- moderate clutter

### Enhanced High
- 1K world textures; selective 2K hero assets only after memory test
- high zombie LOD
- surface-reactive dynamic lighting
- projected model shadows
- high particle density
- higher decal persistence / visual detail
- more map clutter

### Enhanced Max
- highest validated LODs
- 2K hero texture experiments only where visible benefit exists
- surface-reactive dynamic lights for fire, Mystery Box, Ray projectile/impact, explosions
- projected model shadows
- maximum validated particles / decals / clutter
- best filtering
- no fake promise of FTE realtime shadow maps until/if that renderer feature is actually ported

## Zombie pass

First candidate:
**Studio New Punch FREE Shirtless Zombie**

Why:
- Humanoid rig
- body-parts/dismemberment variant
- three LOD levels
- facial blendshapes
- glowing-eye-ready presentation
- suitable for testing arm/head/leg loss without authoring a new mesh

Target pipeline:

1. retarget one existing or Rokoko/Mixamo zombie animation set;
2. map current NZ:P gameplay states to idle/walk/run/attack/hit/death/crawl;
3. map current limb flags to detachable body parts;
4. retain all current zombie HP/damage/round scaling;
5. validate horde performance before adding more variants.

After the first zombie works, expand the visual pool from ready-made legal models. Stats remain tied to enemy class/round, never the skin.

## Mystery Box pass

Keep current Mystery Box gameplay code.

Current QC already separates:
- box open frames 1–8
- close frames 9–12
- glow entity
- floating weapon
- spark effect
- light calls
- sound
- teddy / movement behavior

Enhanced targets:

- higher-detail box texture/model treatment
- smoother/interpolated opening presentation where the runtime permits
- brighter but controlled glow
- floating-weapon halo
- dust/sparks/energy particles
- dynamic light that reacts with surrounding bunker surfaces on Medium+
- richer opening/closing audio only if provenance is safe

Do not modify:
- price
- RNG
- weapon allow-list
- timing
- ownership logic
- teddy odds

## Ray Gun visual pass

Keep existing projectile gameplay and damage.

Verified current behavior:
- projectile class `projectile_raybeam`
- starting speed 2000
- accelerates
- splash radius 64
- direct/splash damage controlled separately from presentation
- green normal / red upgraded presentation path

Enhanced targets:

- cleaner projectile core
- energy trail
- translucent outer glow
- impact ring
- plasma splash
- sparks/smoke only where visually useful
- green/red dynamic light affecting nearby surfaces on Medium+
- Max may use a larger cosmetic light radius but **damage radius remains 64**

Candidate free effect sources are recorded in `asset_manifest.json`.

## Explosive barrels

Nacht contains **21** explosive-barrel entities using `models/props/Barrel_m.mdl`.

Primary replacement candidate:
Poly Haven `barrel_03` (CC0, roughly 1K triangles).

Enhanced explosion presentation:
- flash
- fireball flipbook
- sparks
- smoke
- optional short-lived debris
- surface-reactive dynamic light on Medium+
- scorch/decal if current decal system proves stable

The explosion's gameplay damage/trigger logic is unchanged.

## Fire and light

Nacht already has **8 `place_fire`** entities and a strong warm/cool light palette.

Use these existing authored positions as anchors instead of randomly adding lights.

On Medium+:
- flame VFX gets a nearby dynamic light;
- `gl_flashblend 0` allows dynamic light to affect nearby lightmapped surfaces;
- intensity/radius must be bounded for Android.

On High/Max:
- enable model shadows;
- increase particle detail;
- preserve darkness/readability rather than flooding the bunker with light.

## Environment pass

Use the real map instead of rebuilding its collision.

Priority replacements:
- bunker wall/concrete
- damaged floor
- wood boards
- dark/rusted metal
- door metal
- crates
- barrels
- rails/barbed wire
- debris

Ground detail is quality-scaled:
- Low: texture-only grit
- Medium: sparse trash/debris
- High: sparse 3D gravel/trash
- Max: slightly denser 3D debris and small stones, still bounded

Do not scatter hundreds of tiny meshes. Prefer baked/texture detail where silhouette does not matter.

## UI / points / text

Enhanced may replace the bitmap charset/font atlas while Classic keeps the stock charset.

Candidate:
Barlow Condensed (OFL-1.1).

Targets:
- clearer point values
- cleaner purchase prompts
- less pixelated menu/HUD text
- animated score gain/loss only as presentation; score math unchanged

## Performance gates

Every visual feature must be individually disableable by quality preset.

First device acceptance:
- no touch/input regression
- no gameplay timing change
- no collision/nav change
- no missing asset spam
- stable 60 FPS target where hardware permits
- no runaway dynamic-light rebuild cost during horde + fire + Ray Gun + barrel explosion
- stable memory after repeated rounds/restarts

## First on-device Enhanced milestone

Nacht must demonstrate all of the following in one build:

1. one modern dismemberable zombie;
2. crawler state;
3. upgraded dominant wall/floor textures;
4. one modern explosive barrel + explosion;
5. enhanced Mystery Box glow/open presentation;
6. enhanced Ray projectile + impact/splash;
7. responsive fire/projectile/explosion lighting;
8. Enhanced HUD/font sample;
9. Low / Medium / High / Max switchable presets;
10. Classic remains visually and behaviorally unchanged.
