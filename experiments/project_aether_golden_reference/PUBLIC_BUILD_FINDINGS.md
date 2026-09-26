# Project Aether public-build findings

## Verified public build

Official itch.io page:
https://verrial.itch.io/projectaether

Downloaded successfully in GitHub Actions from the official public page.

Payload:
- file: `game-13537492.zip`
- bytes: `4558801631`
- SHA-256: `03f410c85ac2fe160a4750f1a56ab925cec98c571c943e34dce522ffed6cfb2c`

Cooked Unreal package files:
- `ProjectAether/Content/Paks/ProjectAether-Windows.ucas` — 4,499,125,184 bytes
- `ProjectAether/Content/Paks/ProjectAether-Windows.utoc` — 12,087,753 bytes
- `ProjectAether/Content/Paks/ProjectAether-Windows.pak` — 17,825,185 bytes
- `ProjectAether/Content/Paks/global.ucas` — 2,510,848 bytes
- `ProjectAether/Content/Paks/global.utoc` — 662 bytes

IoStore was listed with retoc 0.1.5 and converted/indexed with retoc + repak.

## Nacht confirmed inside cooked build

Primary map:
- `ProjectAether/Content/Map_/Levels/zombie_cod5_prototype/zombie_prototype.umap`

World-partition/sublevel cells:
- `.../Cells/Cell_0.umap`
- `.../Cells/Cell_1.umap`
- `.../Cells/Cell_2.umap`
- `.../Cells/Cell_3.umap`
- `.../Cells/Cell_4.umap`
- `.../Cells/Cell_5.umap`
- `.../Cells/Cell_6.umap`

Each cell also has cooked/export and baked-data companions where present.

Nacht geometry directory:
- `ProjectAether/Content/Map_/MapGeometry/zombie_cod5_prototype/`

Confirmed geometry assets include:
- `NachtManualMergeGeo.uasset`
- `NachtManualMergedGeo.uasset`
- `NachtManualMergedGeo1.uasset`
- `NachtMergedGeo1.uasset`
- many numbered `NachtMergedGeo*.uasset` assets extending beyond 100
- associated `.uexp` cooked export payloads
- large numbers of WaW-era named environment/material assets under the same map directory

Examples seen in the package index:
- `berlin_floors_rock_tile2_*`
- `eb_art_ceiling_plaster02_*`
- `okinawa_wall_concrete_grimy_*`
- `peleliu_terrain_*`
- foliage/decal/environment assets

## Meaning for XZIEL

The public Project Aether build is not merely a launcher or executable shell. It contains a cooked UE5 implementation of Nacht with:
- an actual map package,
- partition/sublevel cells,
- baked data,
- Nacht-specific merged geometry,
- environment assets/material references.

This is enough to begin a real cooked-asset reconstruction/export audit for XZIEL without waiting for the editable Discord source.

## Important distinction

This public build is cooked content, not the editable Unreal source project. It is suitable for internal technical analysis and reproducible GOLDEN-reference testing.

Do not commit the downloaded third-party payload itself into this repository unless redistribution permission is explicitly verified. Keep the official fetch + checksum + extraction/index tooling reproducible instead.
