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


## MAP_FILES geometry export — verified

The 120 `MAP_FILES/zm_prototype_part*` static meshes were exported successfully with CUE4Parse-Conversion as glTF/GLB.

Verified CI result:
- queued static meshes: **120**
- successful GLBs recovered: **120 / 120**
- total vertices: **106,095**
- total triangles: **122,926**
- mesh-space bounds minimum: `(-501.65, -725.17, -147.93)`
- mesh-space bounds maximum: `(2393.95, 2730.50, 565.14)`
- span: approximately **28.96 m × 34.56 m × 7.13 m** at UE centimeter units

This confirms that the `zm_prototype_part*` packages contain actual recoverable world geometry, not merely material names or empty placeholder assets.

The geometry exporter does not commit the recovered third-party mesh payloads. CI preserves only audit reports and generated diagnostic previews.

Reproducible workflow:
`.github/workflows/pavlov-bo3-nacht-mapfiles-gltf-audit.yml`


## Independent UE Viewer / UModel cross-check

The same Pavlov `CoD_nacht/MAP_FILES` directory was independently processed with UE Viewer / UModel using the explicit `-game=ue4.21` override.

Verified result:
- input `.uasset` files scanned: **328**
- UModel command successes: **328 / 328**
- failures: **0**
- exported world-mesh glTF files: **120**
- exported binary buffers: **120**
- exported textures: **136 TGA**
- exported material descriptors: **84 MAT**
- exported material/text metadata files: **84 TXT**
- exported payload size in the ephemeral runner: **257,107,300 bytes**

This independently confirms the same **120** world meshes found by CUE4Parse and also proves that the map package carries recoverable material/texture data rather than geometry alone.

Examples of recovered texture channels include:
- `i_t7_concrete_tiles_4x4_dirty_01_c.tga`
- `i_t7_dirt_rocky_01_n.tga`
- `i_t7_decal_grunge_oil_stain_wet_01_s.tga`
- `i_t7_zm_ctl_wood_plank_wide_01_c.tga`
- `i_t7_zm_ctl_wood_plank_wide_01_n.tga`
- `i_t7_zm_chalk_buy_locus_c.tga`

The third-party exported payload remains ephemeral and is not committed to this repository.


## Pavlov MAP_FILES material-channel audit

UE Viewer / UModel exported **84** material descriptors from the map-surface asset set.

Resolved channel coverage in the community port:
- Normal: **84 / 84**
- Diffuse: **80 / 84**
- SpecPower: **1 / 84**
- direct Specular field: **0 / 84**
- unique referenced textures: **132**

Observed texture-name suffixes among resolved/auxiliary references:
- `_c`: **83**
- `_n`: **64**
- `_s`: **1**

This does **not** prove that Treyarch's original T7 material system only used diffuse + normal. It describes how the Pavlov UE4 port's cooked materials resolve through UModel. Several materials also expose additional textures through UModel's `Other[]` list, so XZIEL should not discard auxiliary maps blindly.

Examples:
- `t7_asphalt_old_dark` -> Diffuse `i_t7_asphalt_old_dark_c`, Normal `i_t7_asphalt_old_dark_n`
- `t7_concrete_floor_broken_02` -> Diffuse `i_t7_concrete_floor_broken_02_c`, Normal `i_t7_concrete_floor_broken_02_n`
- `t7_decal_grunge_oil_stain_wet_01` resolves `i_t7_decal_grunge_oil_stain_wet_01_s` as its Diffuse input in this port

This is a critical warning for automated suffix-based mapping: channel semantics must come from the material descriptor when available, not filename suffix alone.
