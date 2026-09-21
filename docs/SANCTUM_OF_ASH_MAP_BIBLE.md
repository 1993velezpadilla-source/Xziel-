# SANCTUM OF ASH — Zombies Map Bible v1

Development geometry: St Giles-without-Cripplegate scan by artfletch, licensed CC BY.  
Release direction: heavily fictionalize the landmark while preserving attribution to the scan source and keeping the gameplay layout original.

## Core fantasy

A ruined church complex has become the center of a supernatural outbreak. The building is not treated as a static arena: the nave, undercroft service spaces, tower, bell chamber, clock chamber and roof become a vertical progression map. The player starts outside with the church visibly looming above them and gradually climbs from the lower service areas to the tower finale.

Working release name: **SANCTUM OF ASH**.

## Geometry-derived zones

The source scan exposes distinct mesh/material groups that are useful for real gameplay zoning:

- Main church / nave and altar
- Exterior / courtyard
- Office
- Office corridor
- Boiler room / lower service area
- Tower stairs
- Ringing chamber
- Clock chamber
- Roof chamber
- Tower top / turret

These are discovered directly from the imported scan rather than invented as arbitrary rooms.

## Opening flow

**Round start — Fallen Courtyard**

The initial spawn is outside the building. The first rounds are intentionally readable and tight, with four exterior zombie approach candidates and one paid route into the nave. The tower is visible immediately so players understand that vertical progression is part of the map.

The opening weapon economy should provide a weak but dependable wall weapon plus one high-risk melee/shotgun option near a spawn approach.

## Main progression

1. Fallen Courtyard
2. Nave
3. Office / Corridor
4. Boiler Room — restore power
5. Nave shortcut / tower access
6. Tower Stairs
7. Ringing Chamber
8. Clock Chamber
9. Roof Chamber
10. Tower Top / finale

The map should always offer at least one loop once the nave is open. Avoid long one-way corridors with no bailout unless they are deliberate high-risk quest spaces.

## Door blockout

Initial pass costs:

- Courtyard → Nave: 750
- Nave → Office/Corridor: 1000
- Corridor → Boiler: 1000
- Nave → Tower stairs: 1250
- Tower stairs → Ringing chamber: 1250
- Ringing chamber → Clock chamber: 1500
- Clock chamber → Roof chamber: 1500

These are balancing placeholders and should be tuned after actual survival tests.

## Power

Power is restored in the **Boiler Room**.

The player must obtain two fuse components from two different combat routes before the switch becomes usable. Power enables:

- perk stations
- bell shockwave trap
- boiler steam trap
- tower lift/shortcut if later added
- quest clock mechanism
- altar upgrade-machine quest state

Power should cause a strong audiovisual state change: lights awaken in sequence from the boiler level up through the nave and tower, the organ emits a low unresolved chord, and the tower clock starts ticking.

## Mystery / randomized weapon system

Working prop name: **Mystery Reliquary**.

The first candidate location is the nave. Additional relocation points should be authored in the office, lower service level, ringing chamber and exterior graveyard/courtyard.

When relocated, it should leave an unmistakable audiovisual trail so mobile players can find it without memorizing every location.

## Upgrade machine

Working prop: **Altar Forge**.

It is physically present near the altar but unavailable initially. It unlocks at the end of the Seven Bells quest. This makes the altar a visible long-term objective from early rounds.

## Original perk placeholders

These are project-specific names for the blockout:

- Second Wind — lower / early route
- Iron Veins — office
- Rapid Hands — ringing chamber
- Deadeye — clock chamber
- Sprint Surge — roof chamber

Final perk count and balance should be determined after combat-route testing.

## Traps

**Falling Chandelier — Nave**  
A ceiling hazard that crushes/staggers a lane. It creates a temporary safe opening but should never cover the whole room.

**Boiler Steam Burst — Lower level**  
Power-dependent. High damage in a narrow service route, forcing the player to time movement through the room.

**Bell Shockwave — Ringing Chamber**  
Power-dependent. Ringing the bell generates a radial knockback/damage pulse with a long cooldown. It also participates in the main quest.

## Main quest — Seven Bells

The quest is designed so normal survival naturally teaches the spaces needed for later steps.

### 1. Recover the three relics

- Torn Hymn — office
- Iron Vestry Key — boiler / lower service space
- Blackened Censer — altar / nave

### 2. Restore power

Find two fuse components in separate zones and activate the boiler system.

### 3. Wake the bells

At the ringing chamber, the player hears a short randomized bell sequence. Repeat the sequence using the bells. The sequence should be readable through both audio and visual cues for accessibility/mobile play.

### 4. Stop the clock

In the clock chamber, set the mechanism to **03:17**. The correct time is foreshadowed by environmental clues rather than a random brute-force puzzle.

### 5. Charge the Ash Sigil

Return to the nave. Kills within a marked ritual area charge the sigil. Different enemy archetypes can contribute different charge amounts.

### 6. Bell Warden

The completed sigil summons the **Bell Warden** in the ringing chamber/tower route.

The Bell Warden is not simply a zombie priest. Design direction: an original large creature deformed by bell metal, rope, wood and masonry fragments. Its attacks should use sound/shockwaves and environmental movement.

### 7. Reward

Defeating the Bell Warden:

- unlocks the Altar Forge
- opens a permanent tower shortcut
- changes the map atmosphere
- unlocks an optional endless-round modifier / harder state

## Enemy ecology

Normal undead should include multiple silhouettes so the map does not become “only zombie nuns/priests.”

Suggested families:

- parish civilian undead
- maintenance / boiler workers
- choir husks
- ash-covered crawlers
- rope-bound tower dead
- bell-deafened runners
- occasional nun and clergy variants as part of the setting, not the entire roster

Special enemy concept: **Censer Wraith** — fast, smoke-obscured enemy that temporarily interferes with visibility rather than simply having more health.

Boss: **Bell Warden**.

## Spawn philosophy

The automated blockout creates spawn candidates from real mesh-zone bounds for:

- exterior
- main church
- office
- office corridor
- boiler
- tower stairs
- ringing chamber

These are candidates only. Final spawn points must be moved to actual windows, doors, wall breaches and off-camera approach corridors after collision/navigation inspection.

No spawn should pop visibly into existence in the player's direct view.

## Navigation rules

- Keep a complete training loop in the nave.
- Exterior should connect back into the nave through at least two late-game routes.
- Tower progression is intentionally tighter and more dangerous.
- Do not let the tower become a permanent one-door camp spot.
- Ringing chamber must have at least two enemy approach paths once its shortcut is unlocked.
- Narrow service areas should have clear visual escape language.
- Maintain mobile-friendly collision margins around pews and scan irregularities.

## Mobile rendering / collision strategy

The source scan is ~2.82M triangles. The automated LOD0 pass currently targets ~650k triangles.

Next optimization stages:

- preserve the untouched source inside the master Blender file
- split gameplay zones for occlusion/culling
- author simple collision proxies instead of using photogrammetry mesh collision
- create lower LODs per zone rather than one global destructive decimation
- reduce texture memory selectively; do not destroy hero surfaces/stained glass
- use room/portal visibility so tower and underground geometry are not drawn from the nave
- remove photogrammetry floaters and inaccessible junk
- bake or simplify lighting for the current Android target while preserving high-quality source assets for the newer engine

## Fictionalization for public release

St Giles is the production foundation, not the final identity.

Before release:

- alter tower crown silhouette
- replace distinctive modern/signage details
- create a larger ruined courtyard / cemetery
- add an original undercroft/crypt extension
- partially collapse one nave side
- add original stained glass and altar art
- reroute at least one major corridor
- add original tower machinery and bell architecture
- use the fictional name SANCTUM OF ASH

This lets the map preserve the physical believability of a real building while becoming our own Zombies location.

## Current automated deliverables

The Blender pipeline now produces:

- full editable master .blend
- mobile LOD GLB
- source metadata and attribution
- geometry report
- exterior/top/entry inspection renders
- gameplay-zone blockout .blend
- gameplay plan JSON
- top/isometric/tower quest renders

The next pass is collision + actual window/door placement against the scan, followed by export into the game runtime.
