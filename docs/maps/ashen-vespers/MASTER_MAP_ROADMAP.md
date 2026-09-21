# ASHEN VESPERS — Master Zombies Map Roadmap

Status: **design locked enough for implementation scaffolding**
Working title: **ASHEN VESPERS**
Map source: St Giles Cripplegate by artfletch (Sketchfab UID `b92917ff83914adc8bc93959ba8b4399`)
Source license: **Creative Commons Attribution (CC BY)**. Preserve attribution in shipped credits/package metadata.

## 0. Why this map

The first free Xziel original map should feel immediately readable like classic round-based Zombies while having an identity that belongs to Xziel: a compact Gothic church, a dangerous vertical bell tower, an under-church service level, moving Mystery Box, wall weapons, power, perks, traps, dismemberment, special rounds, minibosses, a real main quest, side quests, a unique wonder weapon and an end-boss.

This document is map-specific. Core systems remain data-driven and server-authoritative.

## 1. Verified source geometry

The current GitHub Actions Blender ingest passed successfully.

- Source mesh objects: **43**
- Source triangles: **2,822,713**
- Current automated mobile LOD0: **649,977 triangles**
- Source bounds from Blender ingest: about **61.44 x 38.40 x 44.69 model units**
- Source GLB textures: **11**, up to **8192 px**
- The source model includes the church interior, exterior/cutaway, rooms below/around the church and tower interior.
- Material/object group names reveal useful real subspaces including:
  - main church
  - boiler/service room
  - office
  - office corridor
  - ringing chamber
  - clock chamber
  - roof chamber
  - tower stairs
  - tower top
  - turret/exterior

The 650k LOD is an ingest/inspection asset, **not the final mobile render budget**. The gameplay pass must split the church into cullable cells and generate LOD1/LOD2 plus simplified collision.

## 2. Originalization rule

The real church scan is a legal CC-BY source, but the shipped horror map should become a fictional Xziel location.

Keep the architectural skeleton and credit the source creator, but redress heavily:
- damaged/broken pew layouts
- blocked arches and rebuilt traversal
- fictional undercroft/reliquary additions
- ash, fire damage, boarded windows, rubble and destroyed masonry
- fictional heraldry and signage
- custom altar/upgrade station
- custom box, perk machines, trap hardware and quest props
- custom lighting and sky
- custom story/lore

Do **not** copy Treyarch map geometry, quest scripts, proprietary art, VO, UI, wonder-weapon models or branded machine art. Use classic Zombies pacing as a design reference only.

## 3. Map fantasy and pillars

**Fantasy:** an abandoned parish where the bell tower is acting like a resonant beacon for the dead. The player is trapped inside while a corrupted bishop keeps re-opening the boundary between the church and the undercroft.

Pillars:
1. **Readable survival loop** — a new player understands doors, wall guns and power without a guide.
2. **Two-route opening** — north and south paths create co-op choice and replay.
3. **Vertical tension** — tower floors are high-risk/high-reward.
4. **Loopable combat spaces** — no long chain of dead-end rooms.
5. **Quest depth without blocking survival** — power and upgrade station are simple; the full Easter egg is optional.
6. **Mobile-safe density** — scary and detailed without requiring the entire photogrammetry scan to render at once.

## 4. Playable zone graph

| ID | Zone | Gameplay purpose |
|---|---|---|
| Z00 | West Vestibule / Spawn | Round 1 start, revive perk, two cheap wall buys |
| Z01 | Nave | Main combat lane, organ trap, visual centerpiece |
| Z02 | North Aisle | Early route A, SMG wall buy, box candidate |
| Z03 | South Aisle | Early route B, shotgun wall buy, box candidate |
| Z04 | Chancel / High Altar | Mid-map convergence, upgrade station, boss arena |
| Z05 | North Chapel | Reload perk, quest sigil, box candidate |
| Z06 | South Chapel | Damage perk, quest sigil |
| Z07 | Vestry / Office | Build table, quest-item route, wall shotgun |
| Z08 | Underchurch Boiler / Service Level | Main power, health perk, steam trap, box candidate |
| Z09 | Tower Stairs | Vertical choke, late wall gun, counterweight trap |
| Z10 | Ringing Chamber | Stamina perk, soul-charge station, box candidate |
| Z11 | Clock Chamber | Main quest timing step, elite ambush zone |
| Z12 | Roof Chamber / Tower Top | Quest climax and optional extraction/end interaction |
| Z13 | Exterior Courtyard Loop | Outdoor breathing room, extra route, box/perk candidate |

### Route topology

Start opens into two affordable choices:

- Z00 -> Z02 -> Z05 -> Z04
- Z00 -> Z03 -> Z06 -> Z07 -> Z04

Then:
- Z07 -> Z08 (power route)
- Z00/Z01 -> Z09 -> Z10 -> Z11 -> Z12
- Z02 and Z03 can later connect to Z13 to create an exterior loop.

The player should never need to enter the tower to turn on basic power or use the upgrade station. Tower progression is optional/high-value until the main quest asks for it.

## 5. Door / debris economy

Prototype values:

| Gate | Cost | Notes |
|---|---:|---|
| Spawn -> North Aisle | 750 | route A |
| Spawn -> South Aisle | 750 | route B |
| North Aisle -> North Chapel | 1000 | |
| South Aisle -> South Chapel | 1000 | |
| South Chapel -> Vestry | 1000 | |
| North Chapel -> Chancel | 1250 | |
| Vestry -> Chancel | 750 | creates loop |
| Vestry -> Underchurch | 1250 | power route |
| Nave -> Tower Stairs | 1250 | optional early, dangerous |
| Tower Stairs -> Ringing Chamber | 1250 | power-gated consumer |
| Ringing -> Clock Chamber | 1500 | late route |
| Side aisle -> Exterior Courtyard | 1000 | one side first; second door opens from inside |

Target solo map-open cost: roughly 8,000–10,000 points depending on route.

## 6. Power and upgrade station

### Power
Use a small multi-step power setup, not an obscure quest:

1. Two **Brass Fuses** spawn from four authored anchor groups.
2. Team picks both up.
3. Install them into the switchboard in Z08 Boiler/Service.
4. Pull master switch.
5. Power circuit enables perks, tower machinery, traps and the upgrade station.

Fuse anchors are chosen once per match from a deterministic seed.

### Upgrade station
Working final-game name: **The Consecrator**.

Prototype can bind to the existing Pack-a-Punch backend. In the shipped original game, art/name/audio are Xziel-owned.

Location: Z04 Chancel, visually tied to the altar/reliquary. It becomes usable as soon as power is on. Do not require the full main quest.

## 7. Exact first-map weapon pool

Keep this map deliberately curated.

### Starting weapon
- M1911-style starter pistol (prototype may use existing `m1911` implementation)

### Wall buys
1. Kar98k — Z00 — 300
2. M1A1 Carbine — Z00/Z01 — 500
3. Thompson — Z02 North Aisle — 1200
4. Double-Barreled Shotgun — Z03 South Aisle — 1000
5. STG-44 — Z04 Chancel side wall — 1200
6. M1897 Trench Gun — Z07 Vestry/Office corridor — 1200
7. BAR — Z08 Boiler/Service — 1400
8. FG42 — Z09 Tower Stair landing — 1500

### Mystery-Box-only prototype guns
- PPSh-41
- MG42
- M1919 Browning
- .357 Magnum
- PTRS-41
- Panzerschreck

The box may also roll wall weapons. Do not include every weapon in the engine; this restricted pool gives the map its own identity.

### Map-exclusive wonder weapon
**BELLWETHER** — quest-build weapon, not a normal box drop.

Gameplay concept:
- primary: high-impact resonant projectile
- nearby zombies receive a short resonance link
- linked targets amplify the next damage pulse
- charged shot is required for one main-quest interaction
- upgraded name: **FINAL TOLL**

Build the mechanic with original assets. Do not reskin a proprietary Call of Duty wonder weapon.

## 8. Mystery Box director

Five anchors:
- B0 North Aisle
- B1 South Aisle
- B2 North Chapel
- B3 Boiler/Service level
- B4 Ringing Chamber
- optional sixth late anchor in Exterior Courtyard after that loop is opened

Rules:
- initial location chosen from B0/B1/B2
- no box in the spawn room
- relocation threshold chosen once per move: **5–8 completed spins**
- never relocate before 3 completed spins
- never choose the same anchor twice in a row
- occupied/reserved anchors cannot be selected
- one authoritative box result per spin
- result timeout closes the box
- box move event uses an original **Bell-Raven / ash swarm** presentation instead of copying a teddy-bear presentation
- destination is readable through a vertical ash/spectral-light cue plus a distant bell chime

Optional power-up: **Open Offering**
- enables all eligible box anchors for 30 seconds
- temporary reduced price
- expiry restores the single canonical box

## 9. Perks

Final-game names are provisional but functions are clear:

| Function | Working name | Location |
|---|---|---|
| solo/co-op revive aid | Second Breath | Z00 |
| extra health / survivability | Iron Blood | Z08 |
| faster reload / handling | Quick Hands | Z05 |
| higher fire output | Overpressure | Z06 |
| sprint/mobility | Fleetfoot | Z10 or Z13 |
| optional third weapon slot | Pilgrim's Burden | Z11, late |

Prototype can map these to existing perk backends while original models/UI/audio are built.

## 10. Trap placements

### T0 — Organ Resonance
- Zone: Z01 Nave
- Activation: organ console
- Cost: 1000
- Duration: 18 s
- Cooldown: 60 s
- Pulses down the nave at fixed intervals
- stuns/kills enemies based on round scaling
- columns provide readable safe pockets

### T1 — Boiler Purge
- Zone: Z08
- Cost: 1000
- Duration: 15 s
- Cooldown: 75 s
- pressurized steam/fire hazard
- no random power-up drops from trap kills

### T2 — Bell Counterweight
- Zone: Z09
- Cost: 1250
- Duration: 10 s
- Cooldown: 90 s
- mechanical counterweight sweeps/crushes the stair choke

### T3 — Chancel Arc
- Zone: Z04 side arches
- Cost: 1500
- Duration: 20 s
- Cooldown: 90 s
- powered arc barrier covering one lane, never both exits at once

Trap rule: **never make a one-exit room lethal to players with no alternate escape**.

## 11. Zombie spawn plan

Use zone-aware active spawn groups. Opening a door updates eligible spawn groups and nav connectivity.

### Start / western church
- 6 early entry vectors split across west, north and south exterior windows
- no spawn directly in player line-of-sight when avoidable

### North/South aisles
- exterior window entries
- one delayed interior breach each after the relevant route opens
- do not activate all aisle windows simultaneously in early rounds

### Chancel/chapels
- rear windows/side entrances
- one controlled floor-rise spawn for quest/boss moments only

### Underchurch
- 3 breach/door/vent entries
- one floor-rise spawn flagged as special

### Tower
- enemies enter from stairs, roof breach and scripted chamber entries
- do not make normal zombies magically appear on a sealed floor in clear view

### Active-enemy targets
Use a bounded mobile profile and scale by player count. Starting target:
- 1P: 24 active
- 2P: 28 active
- 3P: 32 active
- 4P: 36 active

Total round population is independent of active cap.

## 12. Enemy roster and round scheduling

### Normal enemies
**Parishioner Zombie**
- standard walker/runner progression
- full limb/head hit zones
- crawler transition on leg destruction
- selected variants can remain dangerous for a short headless timer after decapitation

### Fast enemy
**Penitent Nun**
- begins mixing into normal waves from round 4
- faster acceleration, lower durability
- round 4–9: max 2–3 simultaneously
- later rounds: threat-budget controlled

### Elite
**Ash Priest**
- first eligible round: 8
- initial max alive: 1
- after round 18: max alive 2
- support/ranged pressure; never become an endless summoner
- boss-add budget applies to anything it creates

### Boss
**The Hollow Bishop**
- first standalone boss round: **15**
- recurrence: rounds **25, 35, 45...**
- if a scripted main-quest boss encounter is active, scheduled Bishop round is deferred, not lost
- prewarm model, audio, particles and projectiles before encounter

### Special rounds
First special round: **round 6** for predictable onboarding.

After that, next special round occurs 5–6 rounds after the previous one.

Primary special:
**Choir Rush**
- Penitent Nuns only
- short, fast wave
- guaranteed full-ammo reward on completion
- no Bishop on same round

Later alternate special:
**Ash Procession**
- smaller mixed Priest + aggressive undead wave
- starts only after round 16
- uses threat budget so elites cannot stack uncontrollably

Scheduler priority:
1. mandatory quest encounter
2. Bishop boss round
3. special round
4. normal round

Deferred events get rescheduled; never silently discarded.

## 13. Main quest — THE LAST TOLL

Survival does not require this quest.

### Step 1 — Restore the grid
Collect two Brass Fuses, install in Z08, turn on power.

### Step 2 — Assemble the Resonance Key
Three randomized quest components:
- Silver Clapper
- Burned Register
- Brass Seal

Each component has 3 possible authored spawn anchors. Team state is authoritative.

Build at the Vestry workbench in Z07.

### Step 3 — Wake the organ
Insert Resonance Key into the organ mechanism in Z01.
The organ plays a randomized 4-note/chime pattern.

### Step 4 — Answer the windows
Activate four matching stained-glass/sigil interactions across Z04/Z05/Z06 in the correct order.
Wrong input resets only the current sequence, not the whole quest.

### Step 5 — Open the reliquary
A hidden compartment below/behind the Chancel unlocks and provides the Bellwether core.

### Step 6 — Charge three resonance stations
Stations:
- North Chapel
- South Chapel
- Ringing Chamber

Kills must occur inside the station radius. Each station has a bounded required count.
At least one station requires an Ash Priest kill, preventing all three from being completed on round 3.

### Step 7 — Build BELLWETHER
Return charged components to the Vestry bench and build the wonder weapon.

### Step 8 — Strike midnight
Use a charged Bellwether shot on the Clock/Bell mechanism in Z11.
Lighting/audio switch into the **Midnight State**.

### Step 9 — Bishop arena
Doors around Z04/Z01 lock into a controlled arena with safe revive space.

Boss phase idea:
1. Bishop shield is linked to three resonance nodes.
2. Kill round-owned enemies near each node to overload it.
3. Shield falls for a timed damage window.
4. Bishop releases floor shockwaves and directional projectiles.
5. Bellwether charged shot can stun during an exposed sigil window.
6. Repeat with faster timing, bounded adds and no infinite spawning.

### Step 10 — The Black Clapper
Boss death drops the Black Clapper.
Carry it to Z12 Tower Top and install it.

### Step 11 — Choice
Ring the bell:
- **End / Extract:** complete the story run.
- **Continue:** remain in endless survival and receive a permanent match reward (example: one free team ammo refill plus reduced Consecrator cost).

## 14. Side quests

Keep first-map side content focused:

1. **Broken Hymn** — find 3 hidden music objects -> unlock original music track.
2. **Candle Circle** — light a randomized candle pattern without taking damage -> one random free perk for the team.
3. **Monument Offering** — interact with three marked memorials in a seeded order -> points/ammo reward.
4. **Bellwether upgrade** — post-build optional challenge -> FINAL TOLL upgrade path.

Do not ship twenty tiny interactions. Four memorable side quests are enough for launch.

## 15. Dismemberment requirements

Map enemy models must support:
- head
- torso
- left/right upper and lower arms
- left/right upper and lower legs
- detachable head/limbs where mesh allows
- crawler state without changing enemy/round identity
- headless timer variant for selected undead
- gore-off mode with identical gameplay state
- pooled detached limbs/decals for Android

Bosses and elites define their own detachable/weak-point rules; do not assume normal zombie sever logic applies.

## 16. Horror dressing plan

Visual navigation must remain readable beneath the horror layer.

- Spawn: weak warm candle/utility light, mostly intact
- North route: cold moon/cyan glass spill
- South route: warmer fire/amber damage
- Chancel: high-contrast altar silhouette
- Underchurch: industrial amber/red, steam, pipes
- Tower: moonlight, moving shadows, bell silhouettes
- Midnight State: global desaturation + black/red resonance accents

Set dressing:
- broken pews used to shape loops, not random clutter
- rubble blocks non-playable cuts and scan holes
- hanging cloth and banners hide photogrammetry seams
- damaged stained glass supplies strong quest landmarks
- corpse/debris budget is capped
- use fog cards/volumes, not huge transparent particle counts
- dynamic lights limited by importance/distance

## 17. Audio plan

Core cues:
- round-start bell motif
- distant tower creaks
- pipe-organ stingers for quest state
- unique nun scream/cloth movement
- priest vocal/attack tell
- Bishop arrival bell + low choir hit
- box-location chime
- trap wind-up sounds before damage starts

Critical gameplay audio must be distinguishable from ambience.

## 18. Blender / map implementation passes

### Pass A — Source preservation
- keep untouched source in `SOURCE_CHURCH_FULL`
- keep attribution metadata
- never destructively overwrite archival scan

### Pass B — Gameplay segmentation
Split into authored culling cells:
- exterior
- nave/chancel
- north aisle/chapel
- south aisle/chapel
- vestry/office
- boiler/undercroft
- tower stairs
- ringing/clock
- roof/top

### Pass C — Geometry cleanup
- repair walkable floor holes
- delete hidden/duplicate scan fragments
- replace high-noise surfaces near player eye level
- author low-poly collision
- author door/debris blockers
- author nav links for stairs/drops
- validate player capsule clearance everywhere

### Pass D — Mobile LOD
Per cell:
- LOD0 gameplay quality
- LOD1 mid-distance
- LOD2 silhouette
- HLOD for exterior view
- texture atlases/material consolidation where practical
- occlusion/portal culling so basement/tower/interior do not all render together

The current 649,977-triangle GLB is only an intermediate source.

### Pass E — Semantic markers
Add Blender empties with stable IDs for:
- player spawns
- zones
- doors/debris
- zombie spawns
- dog/special spawns if later needed
- box anchors
- wall buys
- perks
- power/fuses
- traps
- quest items
- soul collectors
- boss arena
- build table
- upgrade station
- extraction/end interaction

### Pass F — Base survival
Implement and validate:
- rounds
- zoning
- doors
- wall buys
- Mystery Box
- power
- perks
- upgrade station
- revive
- drops
- game reset

### Pass G — Enemy layer
- Parishioner
- Nun
- Priest
- Bishop
- dismemberment/crawler/headless behavior
- special/boss scheduler
- threat budget

### Pass H — Quest/traps
- graph-driven quest nodes
- buildable Bellwether
- 4 traps
- main quest
- 4 side quests
- boss state machine

### Pass I — Final art/audio
- original horror dressing
- lighting
- particles
- decals
- original UI prompts
- audio
- VO/lore only after gameplay states are stable

### Pass J — Mobile performance / QA
- round 30 solo
- round 30 4P
- 1000-kill corpse/dismember stress
- all box anchors
- every door ordering
- quest with each random seed class
- disconnect/reconnect during quest item and boss
- map reset after quest completion
- no spawn stalls
- no backward-facing locomotion
- no invisible head hitbox after decapitation
- no frame hitch when Bishop first appears

## 19. Launch acceptance bar

Do not call this free launch map ready until:

- all routes have valid nav from every active spawn
- power can always be completed
- upgrade station can always be reached
- no random quest seed can soft-lock
- Mystery Box cannot select occupied/invalid anchors
- boss/special collision defers correctly
- crawler/headless state does not corrupt round population
- player cannot become trapped behind a trap/door
- touch interaction volumes are forgiving
- map can survive repeated reset/restart without stale state
- no copyrighted COD art/audio/model is packaged as an original Xziel asset
- attribution for St Giles source is shipped
- performance profile has bounded active enemies, corpses, lights and FX

## 20. Immediate next implementation task

The next Blender pass should stop using generic center-of-bounds gameplay markers and instead create **named semantic markers attached to the real room geometry** above. The generated report should include every marker and the zone it belongs to. Once those anchors exist, the map can be wired to the existing server-authoritative Zombies systems without hard-coding raw coordinates in gameplay code.


## 21. Signature horror event — THE PENITENT

Ashen Vespers has a once-per-match optional proximity-horror encounter built around a unique praying nun.

- internal ID: `event_penitent_nun`
- first eligibility: round 5+, expected discovery rounds 6–12
- one of multiple hidden authored corner anchors is chosen from currently reachable rooms
- she crouches/kneels facing the wall and whispers the full Padrenuestro through a 3D positional emitter
- no HUD marker or tutorial reveals the event
- leaving her undisturbed, interacting, approaching too closely, or attacking can produce different seeded response families
- outcomes are intentionally uncertain between matches but never arbitrarily one-shot a healthy player
- reward: optional **Black Rosary Fragment**, used by the FINAL TOLL side-upgrade path and not required for basic survival/main-quest completion
- shooting her can trigger a bounded **Wrath Hunt**
- use CC0 Spanish Padrenuestro placeholder during prototype, then replace with Christian's custom performance WAV

Full behavior/state machine:
`docs/maps/ashen-vespers/THE_PENITENT_EVENT.md`
