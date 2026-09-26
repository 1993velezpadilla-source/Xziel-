# XZIEL map runtime contract — Nacht reference v1

This branch turns the verified BO3 Nacht metadata audit into reusable native-engine
runtime primitives without shipping the third-party Pavlov/Call of Duty asset
payload.

## Source of truth

The validated reference package lives on
`experiment/bo3-nacht-standalone-audit` under:

`experiments/bo3_nacht_reference/xziel_reference_package/`

Validation evidence:

- 10,791 scene instances
- 492 unique meshes
- 12 barricades
- 21 zombie spawns
- 9 purchase slots
- 3 authored functional WallBuy anchors
- 6 geometry-derived purchase slots
- purchase calibration RMSE: 3.642585764715487 cm
- 0 unresolved purchase slots

The native runtime profile in `engine/src/nacht_reference.cpp` intentionally
contains only compact gameplay metadata needed by the engine.

## Coordinate conversion

The persisted package uses:

- X = horizontal X
- Y = horizontal Y
- Z = up

The native XZIEL gameplay core currently uses:

- X = horizontal X
- Y = up
- Z = horizontal Z

Therefore:

`engine = { package.x, package.z, package.y }`

Do not change this mapping independently in individual systems.

## Generic runtime pieces

`PurchaseSystem`

- fixed-memory catalog, max 16 purchase points
- proximity query
- affordability check
- deterministic point deduction
- supports wall weapons, weapon cabinets and equipment
- no allocation in interaction calls

`HordeDirector`

- max active zombie capacity raised to 24
- spawn catalog capacity raised to 32
- spawn points can be replaced at runtime without reallocating

`NachtRuntime`

- starts with 500 points
- starts with Start Zone active
- Start Zone = 10 zombie spawns
- unlocking Box Zone = 15 total active spawn points
- unlocking Upstairs = 21 total active spawn points
- owns the nine Nacht purchase definitions
- purchase results return the item ID that the inventory/weapon layer must grant

## Nine purchase slots

- RK5 — 500
- Sheiva — 500
- KRM-262 — 750
- Kuda — 1250
- Pharo — 700
- KN-44 — 1400
- Argus — 1100
- Locus cabinet — 5000
- Fragmentation Grenades — 250

## Current boundary

The gameplay contract is live and tested, but the full BO3/Pavlov geometry is
not yet mounted into the native Android world renderer. For that reason the
Nacht runtime is not enabled by default in the small native sandbox.

The next integration step is to bind:

1. map geometry/collision to the native renderer/world,
2. the Android Interact input to `NachtRuntime::queryPurchase/tryPurchase`,
3. purchase item IDs to the weapon/inventory catalog,
4. buyable doors to `NachtRuntime::unlockZone`,
5. the 12 barricades to zombie navigation/repair behavior.

This same contract is intended to be reused by HAYUYA and future XZIEL maps:
maps provide data; the engine provides purchases, zones, spawning and
interaction behavior.
