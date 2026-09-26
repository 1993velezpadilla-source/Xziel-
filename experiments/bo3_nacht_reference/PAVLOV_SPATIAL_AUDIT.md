# Pavlov BO3 Nacht spatial audit

Source under test:
- Steam Workshop item: `2755515831`
- Pavlov custom map package: `Nacht_de_Untoten.umap`
- Cooked engine version used for parsing: UE4.21
- UAssetGUI conversion: SUCCESS
- Spatial manifest workflow run: `36219847793`
- Workflow artifact SHA-256: `742b6f98a5c7cf2d679f439fbaf60d1fb2d8605e49e2dd7c94c09fa6d023948e`

Important provenance note:
This is a community Pavlov port whose published credits attribute map geometry/models to Call of Duty BO1/BO3. It is **not** Treyarch's editable Radiant source and must not be treated as an authoritative original BO3 `.map` file. It is useful as an independently inspectable spatial reference.

## Parsed map facts

`Nacht_de_Untoten.umap`
- cooked file size: 14,892,083 bytes
- Level export index: 175
- level actors: 11,023
- StaticMeshActor actors: 10,789
- static-mesh placements resolved: 10,794
- unique static meshes: 494
- placements under `CoD_nacht`: 10,791
- unique meshes under `CoD_nacht`: 492
- `MAP_FILES` placements: 120
- unique `MAP_FILES` meshes: 120
- gameplay actors selected: 71

## Gameplay inventory recovered from the map

Resolved actor classes include:
- 21 `ZombieSpawner`
- 15 `Zombie_hounds_Spawner`
- 12 `Barricade`
- 10 Pavlov player spawns
- 3 `WallBuy`
- 2 `BuyableDoor`
- 2 `BuyableDoor_Child`
- 1 `MysteryBoxLocation`
- 1 `PunchAPackMachine`
- 1 `ZombieGameLogic`
- 1 `WonderFizz`
- 1 `PerkMachine_QuickRevive`

Lighting/environment actors include 86 point lights, 12 spot lights, 2 directional lights, exponential-height fog, skylight, reflection capture, sky sphere, navmesh and visibility volumes.

## Example recovered placements

- Mystery box: `(-344.898, -1727.906, 0.0)`, yaw `-34.754`
- Quick Revive: `(-496.779, 1470.500, 2.540)`, yaw `-90.000`
- Pack-a-Punch: `(131.317, 558.055, 438.616)`, yaw `180`
- Buyable door: `(434.340, -1488.440, 124.460)`, yaw `-90`
- Buyable door: `(-472.440, 323.850, 504.284)`, yaw `90`

Barricades recovered:
- `(-548.138, -1230.949, 2.540)`
- `(-548.138, 491.754, 2.540)`
- `(-548.138, 1917.356, 2.540)`
- `(432.617, 2241.796, 2.540)`
- `(584.516, 644.378, 2.540)`
- `(1619.553, -1570.235, 2.539)`
- `(2665.904, -2280.712, 2.539)`
- `(1144.955, -2587.296, 2.539)`
- `(563.271, -621.877, 368.300)`
- `(716.534, -1478.619, 368.300)`
- `(596.583, -2883.087, 368.300)`
- `(2308.538, -2592.599, 368.300)`

## Reproducible extraction path

The branch contains:
- `.github/workflows/pavlov-bo3-nacht-uassetgui-audit.yml`
- `tools/maps/extract_pavlov_nacht_layout.py`

The workflow:
1. downloads the public Workshop item with SteamCMD;
2. unpacks `WindowsNoEditor.pak`;
3. locates `Nacht_de_Untoten.umap`;
4. converts the cooked map to UAssetAPI JSON with UAssetGUI;
5. resolves Level actors, StaticMeshComponents, mesh references and transforms;
6. emits `nacht-spatial-manifest.json`.

No third-party map payload is committed to this repository.
