# Sanctum Character Adaptation Pipeline

Status: active production handoff.

## Goal

Do not build the Sanctum cast from primitive cubes/cones. Use real free/licensed base meshes and transform them into the ten authored characters from the build sheets.

Primitive generated proxies under `assets/sanctum/characters/proxies` are now SCALE/ID FALLBACK ONLY.

Production starting points live under:
- `assets/sanctum/free_models`
- `assets/sanctum/character_bases`
- mapping authority: `assets/sanctum/characters/base_assignment.json`

## Character targets

### Choir Wretch
Start from Monk + Thin Zombie.
Keep:
- human anatomy/rig proportions;
- robe mass from monk;
- undead thin silhouette from thin zombie.
Replace/add:
- choir robe layers;
- jaw damage modularity;
- faded red choir panels;
- crosses/rope belt;
- corpse face/hands.

### Bell Ringer
Start from Monk + Male 3D.
Add:
- bell prop;
- rope/twine;
- blue-gray/ivory layered robe;
- modular limb damage.

### Censer Brute
Start from Giant Mutant + Monk.
Add:
- oversized layered hood/robe;
- heavy rope;
- chain + censer;
- exaggerated hands.
Do not simply scale a normal zombie.

### Reliquary Horror
Start from Giant Mutant + Monster.
Build custom:
- shrine/back reliquary assembly;
- crosses;
- candles;
- hanging censers;
- chains;
- boss damage break stages.

### Grave Sexton
Start from Male City Zombie + Male 3D.
Add:
- heavy caretaker coat/apron;
- shovel;
- keyring;
- grave hook;
- muddy cemetery materials.

### Penitent Deacon
Start from Monk + Male 3D.
Add:
- burgundy stole/hood;
- relic lantern;
- rope belt;
- chain/cross details.

### Stained Shade
Start from Old Lady + Female Character.
Replace materials:
- translucent ghost cloth;
- stained-glass emissive shard layers;
- spectral lower fade.
Keep separate opaque/translucent materials for mobile optimization.

### Lost Child
Start from Lowpoly Kid.
Replace:
- clothing with distressed dress;
- hair with wet hair cards;
- skin/materials;
- doll;
- rosary.
Keep child-scale skeleton.

### Waterbound Child
Start from Lowpoly Kid.
Replace:
- wet dress;
- wet hair;
- water sheen;
- bare feet;
- mist/drip VFX.

### La Llorona
Start from Old Lady + Female Character + Female Body.
Create hero mesh:
- believable adult female anatomy;
- layered waterlogged dress/lace;
- long wet black hair;
- black tears;
- rosary/cross;
- mist lower hem.
Do not ship the base model unchanged.

## Output standard

Each target must eventually contain:
- `<target>_HQ.glb`
- `<target>_mobile.glb`
- `<target>_source.obj` or equivalent retained where license permits;
- PBR textures;
- rig/skeleton metadata;
- animations or retarget map;
- damage/socket manifest;
- license/provenance manifest;
- preview PNG.

## Mobile tiers

HQ is the master.

Mobile variants are derived after silhouette/material correctness:
- preserve face/hands/hero silhouette;
- reduce hidden robe layers first;
- atlas small accessories;
- use bounded alpha cards;
- simplify cloth interior geometry;
- preserve animation pivots and damage sockets.

## Acceptance rule

A downloaded base is not considered a Sanctum character merely because it imports.

It passes only when:
1. silhouette clearly matches the build sheet;
2. clothing/props match the character identity;
3. face/hands read as horror rather than generic game asset;
4. scale matches canonical roster;
5. materials fit the church palette;
6. mobile version preserves identity;
7. license/provenance is retained;
8. it no longer resembles the original free asset at first glance.

## Current automation

`.github/workflows/sanctum-recover-blend-models.yml`
- downloads the missing Blender-source free models;
- runs Blender headless;
- exports OBJ + GLB;
- stages bases for all ten targets;
- generates review contact sheets;
- validates and commits usable outputs.

The non-Blender modeling agent consumes the resulting OBJ/GLB and does not need Blender installed.
