# BO3 Nacht deep-search spatial findings

## Source chain

This audit uses Pavlov Workshop item `2755515831`, a community UE4.21 port whose credits attribute Call of Duty BO1/BO3 map geometry/models to Treyarch.

This is **not Treyarch source code** and must not be treated as an official Radiant `.map`. It is useful as a spatial/asset bridge while the original BO3 `zm_prototype` world source remains unavailable publicly.

## Verified payload

Workshop download:
- 2,670,719,720 bytes
- `WindowsNoEditor.pak`: 2,543,506,907 bytes
- `LinuxServer.pak`: 127,212,802 bytes

Windows PAK index:
- 3,871 package entries
- 3,870 `.uasset`
- 1 `.umap`

Map:
- `Pavlov/Content/CustomMaps/UGC2755515831/Nacht_de_Untoten.umap`
- cooked UE4.21 map size: 14,892,083 bytes

UAssetGUI 1.1.0 successfully exported the map to UAssetAPI JSON.

## Spatial extraction

The UAssetAPI map JSON contains:
- 22,540 exports
- 1,366 imports
- 11,023 level actors
- 10,794 static-mesh instances
- 494 unique static meshes
- 10,791 static-mesh instances under the `/CoD_nacht/` asset tree
- 492 unique static meshes under `/CoD_nacht/`

The map contains a large `MAP_FILES` family with `zm_prototype_part*` assets that encode building/world surfaces and decals. A first pass identifies 120 static-mesh references in this family.

## Level actor composition

Largest actor groups:
- 10,789 `StaticMeshActor`
- 86 `PointLight`
- 21 `ZombieSpawner`
- 19 `PlayerBlocker`
- 15 `Zombie_hounds_Spawner`
- 12 `SpotLight`
- 12 `Barricade`
- 10 Pavlov player spawns
- 9 emitters
- 3 `WallBuy`
- 2 buyable doors
- 2 child buyable-door actors
- 1 Mystery Box location
- 1 Quick Revive machine
- 1 WonderFizz
- 1 Pack-a-Punch machine
- 1 ZombieGameLogic
- 1 Pavlov_Codz_GameLogic
- sky/fog/reflection/navigation/visibility actors

## Example verified gameplay placements

Coordinates are UE units from the community port and are reference data, not yet XZIEL coordinates.

- Mystery Box location: approximately `(-344.90, -1727.91, 0)`
- Quick Revive: approximately `(-496.78, 1470.50, 2.54)`
- Buyable door: approximately `(434.34, -1488.44, 124.46)`
- Buyable door: approximately `(-472.44, 323.85, 504.28)`
- Wall buy: approximately `(-570.94, -2645.72, 499.07)`
- Wall buy: approximately `(2404.99, -2562.86, 136.03)`
- Wall buy: approximately `(-248.92, 1034.31, 141.15)`

Barricades, zombie spawns, hound spawns, player spawns and other gameplay placements are all recoverable from the same map JSON.

## Important geometry observation

Most ordinary environment placement is represented by thousands of `StaticMeshActor` root-component transforms. The port therefore preserves enough spatial metadata to reconstruct the scene graph rather than merely providing a bag of unplaced models.

Some `zm_prototype_part*` map-surface meshes have identity/no explicit transform, which is consistent with geometry baked in map/world coordinates. These require mesh-vertex inspection before applying coordinate transforms.

## Reproducible tool

`tools/maps/extract_pavlov_nacht_layout.py`

The tool resolves UAssetAPI package indices, filters actual PersistentLevel actors, resolves static-mesh references, records root/component transforms, and emits a spatial manifest without committing the third-party mesh/texture payloads.

## Next validation

1. Run the extractor in CI and preserve `nacht-spatial-manifest.json` as an artifact.
2. Independently parse the same `.umap` with CUE4Parse using the PAK's actual mount path.
3. Compare actor count, static-mesh count and transforms.
4. Extract the `MAP_FILES/zm_prototype_part*` static meshes and inspect vertex coordinate bounds.
5. Convert one world-geometry subset plus its materials into XZIEL and render an A/B reference frame.
