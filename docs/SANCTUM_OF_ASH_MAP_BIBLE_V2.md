# SANCTUM OF ASH — Map Bible v2
Status: AUTHORITATIVE DESIGN SPEC for the native Xziel map
Branch: `feature/sanctum-native-xziel-v1`
Supersedes: the older blockout-era Map Bible v1 where this document conflicts with it.

## 0. Non-negotiable authority

SANCTUM OF ASH ships as a native Xziel/Vulkan map.

- `sanctum.xzsm` / native authored assets are visual authority.
- `sanctum.xmap` is gameplay spatial authority.
- Blender is the authoring source for zones, pivots, interaction anchors, character anchors, portals and export metadata.
- Quake BSP, QuakeC, Vril, GL4ES and NZ:P are compatibility/reference evidence only.
- Never move new Sanctum gameplay back onto the old Quake map to make a test easier.
- Never reduce the church back to one global floor height. The real multi-level layout is part of the map.

Current native proof at the time of this spec:
- 216 walkable floor sections.
- 7 progression doors.
- 28 fitted zombie windows/barricades.
- 28 zombie spawn candidates/anchors.
- authored player spawn and arena bounds.
- native Vulkan/Xziel church rendering.
- real multi-level courtyard/nave/boiler/tower/roof traversal.

The master source church remains preserved and non-destructive. Gameplay collision, nav, interaction and animation use authored simplified data.

---

## 1. Core fantasy

A storm has trapped the player at a ruined church complex known as **SANCTUM OF ASH**. Decades earlier, the church became the site of a failed containment rite. The clergy believed seven bells could seal a supernatural breach beneath the sanctuary. At **03:17**, the rite failed. The final bell was never completed, the tower mechanism seized, the dead rose through the church and service spaces, and the figure responsible for maintaining the bells became fused with the machinery and debris of the tower.

The result is not a static haunted church. The whole building is the story:

- the courtyard shows the disaster from outside;
- the nave shows the failed ritual;
- the office and corridor contain records and personal evidence;
- the boiler level explains how the old building still powers the ritual machinery;
- the tower contains the bell sequence and the physical consequences of the failure;
- the clock chamber preserves 03:17;
- the roof/tower expose the player to the storm and distant supernatural presences;
- the ringing chamber becomes the Bell Warden confrontation space.

The player is never forced to understand all lore to enjoy survival. The basic loop must work by itself. Lore, Seven Bells and ambient apparitions reward curiosity.

---

## 2. Horror tone

Target feeling: old-school vulnerability, readable danger, long quiet tension and sudden environmental pressure.

We want:
- distant thunder before lightning;
- rain and wind stronger as the player climbs;
- old wood responding under footsteps;
- a bell heard through several rooms before the player understands it;
- low organ/clock/mechanical tones after power restoration;
- sparse passive La Llorona and Praying Nun presence;
- silhouettes and movement at long distance used rarely;
- rooms that sound different when doors open;
- the player hearing a threat before seeing it.

We do not want:
- constant jump scares;
- nonstop whisper spam;
- every prop moving;
- physics clutter flying around the room;
- every decoration becoming an interaction;
- a quest checklist covering the screen;
- horror sounds stealing priority from weapon/UI-critical audio.

Passive presence remains restrained:
- La Llorona: sparse distant crying/presence, routed through the AcousticGraph.
- Praying Nun: sparse prayer/whisper presence, room-aware and occluded.
- Neither is required for normal survival progression.
- Rare visual manifestations may be added later, but their normal state is audio/atmosphere, not a collision-bearing NPC.

---

## 3. Spatial progression

Primary route:

1. **Fallen Courtyard** — spawn / first survival read.
2. **Nave Entry** — first paid entry into the church.
3. **Main Nave** — central combat loop, altar sightline, random arsenal candidate.
4. **Office / Office Corridor** — tighter side route, records/relic space.
5. **Boiler Room** — power restoration and steam hazard.
6. **Nave Return / Tower Access** — the church changes after power.
7. **Tower Stairs** — compressed vertical pressure.
8. **Ringing Chamber** — bell mechanics, trap, later boss arena.
9. **Clock Chamber** — 03:17 mechanism.
10. **Roof Chamber** — storm exposure and mobility pressure.
11. **Tower Top / Turret** — visual payoff, shortcut/final atmosphere.

The nave is the map's main training loop. Tower progression is deliberately tighter but must never become a one-door permanent camp.

The exterior must eventually reconnect to the interior through an additional safe/earned route so the player can create a larger late-round loop.

---

## 4. Progression doors

Current progression door set and initial economy:

| ID | Route | Initial cost |
|---|---|---:|
| D01 | Courtyard -> Nave | 750 |
| D02 | Nave -> Office/Corridor | 1000 |
| D03 | Corridor -> Boiler | 1000 |
| D04 | Nave -> Tower Stairs | 1250 |
| D05 | Tower Stairs -> Ringing Chamber | 1250 |
| D06 | Ringing Chamber -> Clock Chamber | 1500 |
| D07 | Clock Chamber -> Roof Chamber | 1500 |

Costs are tuning values, not geometry authority.

Every progression door must be a real animated door in Blender, not a disappearing blocker.

Runtime already provides:
- `Closed -> Opening -> Open`;
- 0.90 s default opening duration;
- collision release at 0.62 progress.

Blender must provide:
- door frame;
- leaf;
- true hinge pivot;
- closed transform;
- intended open transform;
- swing clearance;
- blocker;
- interaction anchor;
- acoustic portal ID;
- audio emitter position.

Presentation should normally rotate approximately 90–95 degrees with easing when the physical doorway permits it. Geometry wins over a fixed angle.

No door may:
- rotate around its center;
- clip deeply through masonry;
- open through the player;
- leave invisible collision behind;
- open physically while its AcousticGraph portal remains closed.

---

## 5. Zombie window / barricade law

This section is mandatory because window ambiguity is one of the easiest ways to create impossible spawns and cross-room bugs.

Each gameplay zombie window is **one portal with two authored sides**.

Naming:
- `WIN_<ZONE>_<NN>`
- `WIN_<...>_SIDE_A`
- `WIN_<...>_SIDE_B`
- `WIN_<...>_APPROACH`
- `WIN_<...>_LANDING`
- `WIN_<...>_BLOCKER`

Meaning:
- **SIDE_A** = zombie approach / exterior-or-backstage side.
- **SIDE_B** = defended/player side.
- authored normal points A -> B.

Each window owns:
- exactly one gameplay barricade state;
- exactly one primary blocker;
- one plank mesh-set/material binding;
- one deterministic visual seed;
- one approach anchor;
- one landing anchor;
- an owning source zone and destination zone;
- optional spawn ownership.

### Spawn rules

A normal spawn window:
- may spawn zombies only on SIDE_A;
- must place the spawn outside direct player space;
- must provide a navigable path from spawn -> approach -> aperture -> landing;
- must not create a second hidden spawn on SIDE_B;
- must not share a blocker ID with a different opening.

A window between two playable rooms:
- is a two-way portal only if explicitly authored that way;
- is **not automatically a zombie spawn**;
- must declare which side, if any, owns zombie spawning;
- must use the same window state from either view so the map never has two contradictory barricades in one physical hole.

Player rebuild interaction is normally on SIDE_B.
Zombie tearing normally originates on SIDE_A.
Debris direction depends on the actor/side causing the break.

All 28 current fitted windows must be audited under this contract before final placement is accepted.

---

## 6. Power state

Power is restored in the **Boiler Room** after acquiring two fuse components.

Before power:
- most ritual machines are dormant;
- tower mechanical sound is reduced;
- clock is inert;
- selected lights remain dead;
- powered traps unavailable.

After power:
- lighting wakes from lower level toward nave/tower;
- old electrical/mechanical hum enters the soundscape;
- the organ gives one restrained unresolved response;
- clock machinery begins;
- powered traps and stations can activate;
- the AcousticGraph may expose new mechanical emitters;
- quest state can proceed.

Do not turn power-on into a giant particle event. It should feel physical and architectural.

---

## 7. Survival interaction set

Only the controlled interaction core is animated/interactive by default.

### Always allowed interaction families
- progression doors;
- zombie windows/barricades;
- power controls/fuses;
- wall weapon buys;
- perk/reliquary stations;
- random arsenal station;
- weapon upgrade station;
- Votive/consumable station;
- physical power-up pickups;
- approved traps;
- Seven Bells quest props;
- explicitly approved shortcuts.

### Normally static
- pews;
- rubble piles;
- statues;
- most candles;
- chairs/desks;
- decorative books;
- loose church clutter;
- generic wall props.

Static props may have ambient shader/VFX motion (flame, dust, water, cloth secondary motion) only when bounded and non-gameplay-authoritative.

This keeps the map stable. We are not making every object a physics toy.

---

## 8. Original survival machines in Sanctum

### Reliquary Draught
Perk station integrated into church architecture.
Needs:
- wall/floor mounting;
- idle hum;
- subtle stained-glass/liquid movement;
- short purchase animation;
- powered state;
- interaction arc that does not block combat routes.

### Confessional Arsenal
Random weapon station.
Visual language:
- confessional/reliquary mechanism;
- brief anticipation;
- physical revealed weapon;
- authored relocation anchors in multiple zones.

Candidate locations:
- Nave;
- Office;
- Lower service/Boiler route;
- Ringing Chamber;
- Exterior/Courtyard.

### Wall Imprints
Fixed weapon buys embedded into believable wall/wood/metal surfaces.
Never float in front of the scan.

### Foundry of Absolution / Altar Forge
Upgrade station located near the altar.
Physically visible early but locked until Seven Bells completion.
The altar therefore acts as a long-term visual objective.

### Votive Engine
Run-consumable station.
Small footprint; not a giant arcade machine.
Should feel like a strange church mechanism with a clear use point.

---

## 9. Seven Bells — canonical quest

The quest explains the architecture rather than forcing unrelated chores.

### Stage 1 — Three relics
- **Torn Hymn** — Office.
- **Iron Vestry Key** — Boiler / lower service.
- **Blackened Censer** — Nave/altar.

Each relic gets a fixed authored socket and a visible empty/collected state.

### Stage 2 — Restore power
Acquire two fuse components from separated routes and activate Boiler power.

### Stage 3 — Wake the bells
Ringing Chamber.
The player receives a short randomized sequence and reproduces it.
Every bell must have:
- real pivot/rope/striker animation;
- visual cue paired with audio;
- collision-safe interaction point.

### Stage 4 — Stop the clock
Clock Chamber.
Set the mechanism to **03:17**.
Clock hands/mechanism are real Blender-authored pivots, not a UI-only puzzle.

### Stage 5 — Charge the Ash Sigil
Return to Nave.
Kills inside the marked ritual area charge the sigil.
VFX must stay readable without covering enemies.

### Stage 6 — Bell Warden
Spawn/activate in the Ringing Chamber/tower route.
The arena must gain at least two enemy approach paths once the permanent shortcut is involved.

Bell Warden is an original tower creature fused with bell metal, rope, wood and masonry. It is not just a larger priest zombie.

### Stage 7 — Reward
- unlock Altar Forge;
- open permanent tower shortcut;
- change atmosphere;
- optionally enable a harder endless-state modifier.

The basic survival game must remain playable without completing Seven Bells.

---

## 10. Character / enemy placement philosophy

Normal zombie ecology should use multiple silhouettes:
- parish civilian undead;
- maintenance/boiler workers;
- choir husks;
- ash-covered crawlers;
- rope-bound tower dead;
- bell-deafened runners;
- occasional clergy;
- occasional nun variants.

Do not make the roster “all priests/nuns.”

### Character anchor classes

Blender creates stable role anchors. Exact licensed meshes can be swapped later without rewriting gameplay.

- `CHAR_UNDEAD_CIVILIAN_*`
- `CHAR_UNDEAD_MAINTENANCE_*`
- `CHAR_UNDEAD_CHOIR_*`
- `CHAR_UNDEAD_CLERGY_*`
- `CHAR_UNDEAD_NUN_*`
- `CHAR_PASSIVE_NUN_*`
- `CHAR_LLORONA_PRESENCE_*`
- `CHAR_BELL_WARDEN`
- `CHAR_HIGH_CLERGY_SLOT_*` for any pope/high-clergy-style model that is actually present after asset audit.

Important: the repository currently does not expose confirmed pope/priest/cardinal asset filenames. Do not invent a filename or make the story depend on one. The Blender scene owns stable **roles/anchors**, and the asset audit binds actual meshes later.

### Placement reasons

- Civilians: courtyard/nave/office routes because they explain the congregation/collapse.
- Maintenance undead: boiler/service spaces because they belong there visually.
- Choir husks: nave/tower-adjacent areas.
- Clergy variants: nave/altar/office, used sparingly.
- Nun variants: side aisles/office/tower transitions, sparingly.
- Passive Praying Nun: non-blocking atmospheric anchors in side-room/acoustic routes, never in a place where she can physically trap the player.
- La Llorona: exterior/roof/tower acoustic paths; rare visual silhouette anchors may face open sky/courtyard sightlines.
- Bell Warden: Ringing Chamber/tower route only.

No character model may be placed only because “it looks cool.” It needs a zone reason, spawn reason, quest reason or atmosphere reason.

---

## 11. La Llorona and Praying Nun

These are presence systems first.

### La Llorona
Purpose:
- create distant dread;
- connect courtyard/storm/roof acoustically;
- reward players who pay attention to direction and distance.

Normal behavior:
- positional cry/presence;
- long-range attenuation;
- door/portal occlusion;
- low-pass through closed architecture;
- zone reverb;
- sparse cadence.

Visual apparition, if enabled:
- non-solid;
- no player collision;
- no nav obstacle;
- only appears at authored LOS-safe anchors;
- disappears before becoming a pathing dependency.

### Praying Nun
Purpose:
- make interior silence uncomfortable;
- imply the church is occupied by something other than normal zombies.

Normal behavior:
- prayer/whisper;
- spatial room anchor;
- sparse;
- never spammed.

A physical undead nun variant is a separate enemy archetype and must not share the same semantic ID as the passive presence.

---

## 12. Audio material map

Blender/material metadata should identify at least:
- stone;
- old wood floor;
- wet stone;
- shallow puddle;
- metal stairs/mechanism;
- glass;
- rubble;
- cloth/carpet if used.

Needed sound families:
- realistic wood footsteps/creaks;
- wet footsteps/splashes;
- stone footsteps;
- old door hinge/latch/impact;
- plank stress/tear/snap/fall;
- glass fracture/fall;
- rubble/debris impacts;
- rain;
- water drips;
- wind;
- thunder;
- lightning transient;
- bells;
- clock/mechanism;
- boiler;
- distant organ;
- zombie window attacks;
- machine hums/reward stings;
- La Llorona/Nun presence.

Every shipped third-party audio file must retain license/provenance suitable for redistribution/commercial release.

---

## 13. Weather / VFX

Exterior, roof and tower should sell the storm.

Allowed:
- bounded rain emitters;
- lightning event with synchronized light/audio;
- puddle material and small splash VFX;
- drips from damaged architecture;
- dust/ash motes indoors;
- restrained candle flames/smoke;
- short debris bursts on plank/glass break.

Avoid:
- global expensive rain inside every room;
- unbounded GPU particles;
- physics debris that can accumulate forever;
- bloom strong enough to hide enemies;
- lightning frequency that becomes irritating.

The master asset remains high quality. Device tiers reduce runtime cost through culling/LOD/particle/audio budgets, not by destroying the master.

---

## 14. Traps

### Nave chandelier
Physical authored anchor + fall path.
Must not cover the entire room.

### Boiler steam burst
Narrow route hazard.
Needs volume, warning state and safe post-trigger navigation.

### Bell shockwave
Ringing Chamber.
Power dependent.
Physical bell response + radial presentation.
Also participates in Seven Bells.

Traps must not share quest interaction IDs even if they use the same physical hero object.

---

## 15. Spawn policy

Spawn geometry is not just a point.

Each zombie spawn needs:
- spawn anchor;
- facing;
- owning zone;
- route to player space;
- off-camera/occluded intent;
- valid nav approach;
- optional window ownership;
- minimum clearance.

Never:
- spawn inside solid collision;
- spawn visibly in front of the player;
- spawn behind a sealed door with no route;
- use a window spawn whose defended side belongs to an unrelated room;
- put the spawn exactly in the aperture.

Current 28 spawn candidates are starting anchors, not permission to skip inspection.

---

## 16. Blender collection plan

Required top-level authored collections:

- `SOURCE_CHURCH_FULL` — untouched source.
- `SANCTUM_STATIC_ENV`
- `SANCTUM_DRESSING`
- `SANCTUM_COLLISION`
- `SANCTUM_FLOORS`
- `SANCTUM_NAV`
- `SANCTUM_DOORS`
- `SANCTUM_WINDOWS`
- `SANCTUM_INTERACTIVES`
- `SANCTUM_QUEST`
- `SANCTUM_CHARACTER_ANCHORS`
- `SANCTUM_AUDIO`
- `SANCTUM_VFX`
- `SANCTUM_DEBUG`

Do not move original source objects destructively just to satisfy runtime needs. Add authored overlays/proxies and export metadata.

---

## 17. Object metadata minimum

Every gameplay-authored object should expose:
- `soa_id`
- `zone_id`
- `kind`
- `export=true/false`
- `floor_id` when relevant
- `interaction_radius` when relevant
- `audio_portal_id` when relevant
- `spawn_side` for spawn windows
- `collision_policy`
- `notes`

Doors add:
- hinge axis;
- closed/open transforms;
- blocker ID.

Windows add:
- side A/B anchors;
- normal;
- approach/landing;
- barricade visual IDs.

Character anchors add:
- role;
- ambient/enemy/boss;
- LOS policy;
- collision policy;
- facing.

---

## 18. Anti-bug laws

1. One physical opening = one canonical gameplay ID.
2. One door/window state is shared by render, collision, nav and audio.
3. No duplicate hand-entered coordinates when Blender can export them.
4. No gameplay object derives height from raw photogrammetry bbox minimum.
5. No spawn is accepted without an authored route/landing.
6. No dynamic prop may become permanent unbounded physics debris.
7. No decorative animation may move collision unless the gameplay system owns it.
8. No quest step depends on a model file whose provenance/availability is not confirmed.
9. No map edit may reintroduce Quake/BSP as shipping authority.
10. Every portal/door/window has a testable side/orientation.
11. Every intended playable edge gets collision/fall protection.
12. Map changes that alter counts/IDs require an export report explaining the delta.

---

## 19. Visual map schematic

Not to scale; this is interaction topology.

```text
                           [ TOWER TOP / TURRET ]
                                   |
                            [ ROOF CHAMBER ]
                                   |
                              D07 1500
                                   |
                           [ CLOCK CHAMBER ]
                         [03:17 mechanism]
                                   |
                              D06 1500
                                   |
                         [ RINGING CHAMBER ]
                       [bells] [shockwave]
                     [BELL WARDEN FINALE]
                                   |
                              D05 1250
                                   |
                           [ TOWER STAIRS ]
                                   |
                              D04 1250
                                   |
  [OFFICE] ---- [OFFICE CORRIDOR] ---- [ MAIN NAVE / ALTAR ]
  [Hymn]              |                 [Ash Sigil]
     |               D03                [Altar Forge]
     |              1000                [Reliquary]
    D02               |                 [training loop]
   1000          [ BOILER ROOM ]               |
                  [Power/Fuses]                 |
                  [Steam trap]                  |
                                               D01 750
                                                 |
                                        [ FALLEN COURTYARD ]
                                           [PLAYER SPAWN]
                                      [storm / rain / Llorona]
```

Windows/barricades sit on the exterior and zone boundaries around this topology; they are not additional progression edges unless explicitly authored as portals.

---

## 20. Implementation issues

- #41 — Blender scene as authored spatial authority.
- #42 — 28 windows as sided portals.
- #43 — 7 real hinge doors + acoustic portals.
- #44 — story/character anchors/model-role audit.
- #45 — survival machines/wall buys/pickups.
- #46 — environmental audio/weather.
- #47 — Seven Bells + Bell Warden staging.
- #48 — automated map sanity checks.

Execution order:
1. #41
2. #42 and #43
3. #48
4. #45 and #46
5. #47
6. #44 asset bindings can run in parallel once the real model inventory is known, but role anchors belong in #41.

---

## 21. Definition of “map ready for art polish”

Before high-detail dressing expands further:
- all 7 doors physically match their authored apertures;
- all 28 windows have correct sides/routes;
- player cannot fall through intended playable edges;
- all interactives sit on real floor planes;
- no zombie spawn is inside the playable room by accident;
- all core quest anchors have combat clearance;
- AcousticGraph portals correspond to physical doors/openings;
- character-role anchors exist;
- authored ID report passes CI.

After that, Blender can safely push detail, hero props, animation and atmosphere without constantly invalidating gameplay.

---

## 22. Quality bar

The target is “premium mobile horror survival,” not “old Quake map with a prettier shell.”

That means:
- high-quality master geometry/materials;
- controlled native animation;
- authored collisions;
- spatial audio;
- believable doors/windows;
- readable dark lighting;
- stable mobile frame pacing;
- no obvious proxy cubes in shipping presentation;
- no pasted-on machine art;
- no broken two-sided window logic;
- no gameplay authority split between old and new map systems.

Every future Sanctum change should be checked against this document and the Blender authoring contract.
