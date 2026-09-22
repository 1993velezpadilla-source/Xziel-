# SANCTUM OF ASH — Blender Authoring Contract
Status: AUTHORITATIVE TECHNICAL HANDOFF for Blender/map work
Companion: `docs/SANCTUM_OF_ASH_MAP_BIBLE_V2.md`

This file exists so a person or automation editing the Blender map does not have to reverse-engineer gameplay intent.

## 1. Principle

Blender owns authored spatial facts. Xziel owns runtime state.

Blender decides:
- where a door/window/machine/quest object is;
- its pivot/orientation;
- which zone it belongs to;
- which side is which;
- visual mesh/socket locations;
- collision/nav proxy geometry;
- audio/VFX anchors.

Xziel decides:
- whether a door is purchased/open;
- barricade plank state;
- scores/economy;
- zombie state;
- quest state;
- machine state;
- power state;
- audio voice scheduling.

Do not put runtime state machines into Blender. Do not hard-code duplicated Blender coordinates into C++ when the exporter can emit them.

---

## 2. Coordinate and floor discipline

- Native map uses the current Xziel Y-up/meter-space export contract.
- Preserve the established native conversion path.
- Every authored interaction must be snapped to a validated dominant playable floor plane or explicit support socket.
- Never use raw photogrammetry `bbox.min.z` as “the floor.”
- Multi-level zones remain separate.

Required floor tags:
- courtyard;
- main_church / nave;
- office;
- office_corridor;
- boiler;
- tower_stairs;
- ringing_chamber;
- clock_chamber;
- roof_chamber;
- tower_top/turret.

---

## 3. Stable IDs

Every exported authored object receives a unique `soa_id`.

Examples:
- `SOA_D01_COURTYARD_NAVE`
- `SOA_WIN_NAVE_03`
- `SOA_PERK_SECOND_WIND`
- `SOA_QUEST_CLOCK_0317`
- `SOA_CHAR_BELL_WARDEN`
- `SOA_AUDIO_LLORONA_ROOF_01`

IDs survive mesh swaps. Never use Blender auto-generated object suffixes as gameplay IDs.

---

## 4. Doors

Hierarchy:
```
SOA_Dxx_ROOT
  FRAME
  LEAF
    HANDLE optional
  PIVOT_HINGE empty
  BLOCKER
  INTERACT
  AUDIO
  DEBUG_SWING
```

Required custom properties on ROOT:
- `soa_id`
- `kind="door"`
- `zone_a`
- `zone_b`
- `cost`
- `open_duration=0.90`
- `collision_release_progress=0.62`
- `audio_portal_id`
- `open_angle_degrees`
- `hinge_axis`
- `starts_open=false`

LEAF origin/pivot must match the hinge.
The engine presentation drives animation from `openProgress`.

Validation:
- closed leaf fills intended route;
- open leaf clears intended route;
- blocker matches closed doorway;
- interaction point is reachable;
- no major masonry clipping;
- swing volume does not cross a permanent combat choke unless intentional.

---

## 5. Zombie windows

Hierarchy:
```
SOA_WIN_<ZONE>_<NN>_ROOT
  APERTURE_DEBUG
  SIDE_A
  SIDE_B
  APPROACH
  LANDING
  BLOCKER
  PLANK_SOCKET_0...
  AUDIO
  DEBRIS_ORIGIN
```

ROOT properties:
- `soa_id`
- `kind="zombie_window"`
- `zone_a`
- `zone_b`
- `normal_a_to_b`
- `spawn_side="A"|"B"|"none"`
- `two_way_portal=true|false`
- `maximum_planks`
- `plank_material_id`
- `debris_material_id`
- `plank_mesh_set_id`
- `visual_seed`

Rules:
- SIDE_A and SIDE_B must be physically separated on opposite sides of the aperture.
- APPROACH sits on the zombie side.
- LANDING sits on the defended destination side.
- BLOCKER belongs to this opening only.
- One ROOT = one ZombieWindowSystem ID.
- Do not create a second “inside window” state for the same aperture.

If the opening connects two playable rooms:
- set `two_way_portal=true`;
- set spawn side only if deliberately desired;
- otherwise `spawn_side="none"`.

---

## 6. Zombie spawns

Hierarchy:
```
SOA_ZSP_<ZONE>_<NN>
  SPAWN
  LOOK
  ROUTE_0
  ROUTE_1 ...
```

Properties:
- `soa_id`
- `kind="zombie_spawn"`
- `zone_id`
- `window_id` optional
- `min_round`
- `weight`
- `requires_occlusion=true`
- `enabled=true`

A window spawn must be outside its opening, never inside the player room.

Route validation must prove:
spawn -> approach -> aperture/door/breach -> landing -> nav.

---

## 7. Interactives

Each machine/quest object uses:
```
ROOT
  HERO_MESH
  INTERACT
  PLAYER_STAND optional
  AUDIO
  VFX
  COLLISION
  ANIM_* children/pivots
```

The player interaction point must:
- be reachable by touch/mouse aim;
- not require standing inside collision;
- not face directly into a common zombie spawn;
- preserve a mobile-friendly approach width.

Machines must have an authored footprint. No floating cubes.

---

## 8. Character anchors

Anchors are empties, not gameplay meshes.

Properties:
- `soa_id`
- `kind="character_anchor"`
- `role`
- `zone_id`
- `behavior="enemy"|"ambient"|"boss"`
- `collision="none"|"actor"`
- `los_policy`
- `audio_profile`
- `model_asset_id` optional only after audit.

Roles:
- civilian undead;
- maintenance undead;
- choir;
- clergy;
- nun enemy;
- passive praying nun;
- La Llorona presence;
- Bell Warden;
- high-clergy/pope-style slot only if an exact licensed asset is verified.

Never make quest logic depend on a particular model filename.

---

## 9. Passive apparition anchors

Passive Nun/Llorona anchors:
- collision none;
- nav none;
- no solid blocker;
- must not occupy the center of a required escape lane;
- should have LOS-safe entrance/exit framing;
- audio anchor may remain even when visual apparition is disabled.

---

## 10. Seven Bells objects

### Relics
Each relic has:
- socket;
- pickup position;
- empty state;
- collected state.

### Bells
Each bell has:
- bell body pivot;
- striker/clapper pivot if used;
- rope/handle interaction;
- audio emitter;
- VFX response;
- accessible visual cue.

### Clock
Clock hands and any key mechanism use explicit pivots.
03:17 state must be representable physically.

### Ash Sigil
- physical/decal anchor;
- volume defining kill-charge region;
- VFX center;
- audio center;
- no collision unless specifically required.

### Bell Warden
- boss start anchor;
- arena bounds;
- intro camera-safe/LOS-safe placement;
- navigation escape;
- at least two enemy approach routes in final state.

---

## 11. Audio portals

Doors and major architectural openings receive `audio_portal_id`.

A physical door's portal openness follows the same gameplay door state.
Never author separate “audio door state.”

Zones map to the native Sanctum AcousticGraph:
- exterior/courtyard;
- main church;
- office;
- corridor;
- boiler;
- tower stairs;
- ringing chamber;
- clock chamber;
- roof chamber;
- tower top.

---

## 12. Footstep and surface metadata

Walkable surfaces should resolve to a surface family:
- stone;
- wet_stone;
- old_wood;
- puddle;
- metal;
- rubble;
- cloth/carpet optional.

Do not put footstep selection on decorative meshes that the player cannot walk on.

---

## 13. Weather/VFX authoring

Use volume/anchor objects, not millions of placed particles.

Examples:
- `SOA_VFX_RAIN_COURTYARD`
- `SOA_VFX_RAIN_ROOF`
- `SOA_VFX_DRIP_NAVE_01`
- `SOA_VFX_PUDDLE_COURTYARD_02`
- `SOA_LIGHTNING_KEY_TOWER`

Export:
- bounds;
- density/profile ID;
- device-tier importance;
- audio link if relevant.

---

## 14. Collision policy

Use simple authored collision.

Allowed:
- boxes;
- capsules;
- convex simplified hulls;
- limited special shapes when necessary.

Avoid:
- raw photogrammetry triangle collision;
- tiny debris as gameplay collision;
- collision on visual-only nails/candles;
- moving decorative collision.

Dynamic collision only belongs to approved gameplay systems:
- doors;
- barricades/windows;
- approved traps/shortcuts.

---

## 15. Animation policy

Animate only objects with a clear reason.

Approved categories:
- doors;
- barricade planks;
- bell/rope/clock quest objects;
- machines;
- traps;
- power switch/fuse interactions;
- selected environmental loops such as candles/cloth/drips;
- boss/characters.

Decorative scene objects remain static unless explicitly promoted.

All gameplay animations need:
- deterministic start/end;
- bounded duration;
- transform owned by one system;
- no unbounded rigid-body dependency;
- reset behavior for level restart.

---

## 16. Export validation

Exporter/CI must reject:
- duplicate `soa_id`;
- door missing hinge/pivot;
- window missing side anchors;
- spawn window with spawn on defended side;
- window with duplicate blocker;
- invalid zone reference;
- interactive floating away from floor/support;
- spawn inside collision;
- landing inside collision;
- door open transform still blocks nav;
- quest anchor in inaccessible zone;
- audio portal without physical counterpart;
- playable floor edge with known fall-through gap.

Warnings:
- large visual mesh touching several zones;
- apparatus too close to nav centerline;
- passive apparition in direct spawn LOS;
- hero object with missing provenance.

---

## 17. Debug render pack

Each Blender CI run should output:
1. top map with zone labels;
2. isometric map;
3. door overlay with IDs and swing arcs;
4. window overlay with SIDE_A/SIDE_B arrows;
5. spawn-route overlay;
6. quest/interactives overlay;
7. character/audio anchor overlay;
8. floor/collision overlay.

These renders are for phone review before an Android build.

---

## 18. Handoff checklist for any Blender editor

Before editing:
- read Map Bible v2;
- preserve source collection;
- work in authored collections;
- keep stable IDs;
- do not reintroduce Quake/BSP authority.

Before committing:
- regenerate scene manifest;
- regenerate native map;
- run sided-window validation;
- run door pivot/open-clearance validation;
- run spawn route validation;
- run floor/fall-edge validation;
- inspect top/isometric overlays;
- document intentional count/ID changes.

If a visual change would require breaking one of these contracts, change the contract explicitly in the Map Bible first rather than silently working around it.
