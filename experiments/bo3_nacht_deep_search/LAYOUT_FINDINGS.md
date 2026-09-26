# BO3 Nacht layout recovery — current evidence

## Serialized map recovered

Source package:
- Workshop item: `2755515831`
- map: `Pavlov/Content/CustomMaps/UGC2755515831/Nacht_de_Untoten.umap`
- extracted map bytes: `14892083`
- Unreal serialization target: UE4.21
- UAssetGUI export: PASS
- JSON exports: `22540`
- JSON imports: `1366`
- NameMap entries: `11707`

## Static-mesh scene reconstruction

The UMAP contains:

- **10,794 StaticMesh instances**
- **494 unique meshes**
- max observed `AttachParent` depth: 2
- no serialized `bAbsoluteLocation`, `bAbsoluteRotation`, or `bAbsoluteScale` overrides

Breakdown:

| Group | Instances | Unique meshes |
|---|---:|---:|
| `MAP_FILES/zm_prototype_part*` | 120 | 120 |
| `p7_zm_nac_*` | 201 | 25 |
| `p7_zm_gen_proto_*` | 371 | 19 |
| other `CoD_nacht` assets | 10,099 | 328 |
| shared/gameplay | 3 | 2 |

The `p7_zm_gen_proto_*` component origins span approximately **33.20 m × 50.93 m × 8.26 m**. This is an origin-placement bound, not a mesh-vertex bounding box.

The `p7_zm_nac_*` component origins span approximately **112.39 m × 134.23 m × 13.09 m**, including exterior props such as antenna/vehicles/foliage.

## Critical map-geometry finding

The 120 `MAP_FILES/zm_prototype_part*` components sit almost at the map origin.

This is not evidence that the map has no layout. Their **mesh vertices carry baked map-space geometry**. Examples include BO3-style floor, concrete, wall, metal, wood, decal and Nacht chalk assets.

Therefore the next geometry step is:

`extract the 120 static meshes -> preserve vertex positions/material assignments -> combine them in map space`

Trying to infer the building only from component transforms would be wrong.

## Mindmirror cross-check

Mindmirror's public Zombies Chronicles Nacht pack contains **33 original Nacht environment models**.

The Pavlov BO3 port directly instantiates **25 of those 33** `p7_zm_nac_*` model names, with **no unexpected extra model name in that namespace**.

The eight pack models not instantiated directly are:

- `p7_zm_nac_barrel_explosive_red`
- `p7_zm_nac_barrel_explosive_red_dmg_02`
- `p7_zm_nac_wall_custom_tear_in_chunk_01`
- `p7_zm_nac_wall_custom_tear_in_chunk_02`
- `p7_zm_nac_wall_custom_tear_in_chunk_03`
- `p7_zm_nac_wall_custom_tear_in_chunk_04`
- `p7_zm_nac_wall_custom_tear_in_chunk_05`
- `p7_zm_nac_wall_custom_tear_in_chunk_06`

These are alternate damage/destruction states rather than a contradictory asset family.

## Reproducibility

Use:

`tools/nacht/derive_pavlov_bo3_nacht_layout.py`

against an UAssetGUI JSON export of `Nacht_de_Untoten.umap`.

It resolves Unreal import/export object references and composes component transforms using the UE4 `FRotator::Quaternion()` convention.
