# SANCTUM OF ASH — NATIVE XZ HORROR REDESIGN v2

Updated: 2026-09-22
Runtime authority: Xziel native / Vulkan
Visual authority: sanctum.xzsm + authored native assets
Gameplay authority: .xmap
Legacy BSP/Quake/NZ:P: reference only — never runtime authority

## Non-negotiable baseline

Preserve the current validated native map instead of rebuilding from the old Quake version:

- 216 walkable/multilevel surfaces
- 7 gameplay-authoritative doors
- 28 windows/barricades
- 28 zombie spawn approaches
- courtyard, nave, office/corridor, boiler, tower stairs, ringing chamber, clock chamber, roof/tower top
- current real player spawn and arena bounds
- native Xziel/Vulkan rendering
- static-by-default environmental geometry
- controlled deterministic interactions only

No free-physics decoration pass. No animation-everything pass. Objects that do not improve gameplay, horror, readability, or storytelling remain static.

## Core redesign idea — THE CHURCH IS LISTENING

The new pass makes Sanctum feel less like a photogrammetry church used as an arena and more like a place that survived a catastrophe and is still behaving incorrectly.

The horror curve is vertical:

**outside isolation → human evidence → mechanical unease → ritual corruption → exposed supernatural tower**

The player should feel that climbing the church is moving closer to whatever woke it.

---

## FLOOR 0 — FALLEN COURTYARD

### Geometry / dressing

Keep the existing courtyard footprint and approach lanes. Dress it as a failed refuge perimeter:

- wrecked temporary barricades
- rain-dark stone
- abandoned bags and emergency supplies
- broken parish notice board
- snapped umbrella / clothing caught on ironwork
- a damaged vehicle or utility cart only if it does not obstruct the training loop
- grave/cemetery dressing pushed to non-combat margins
- one high upstairs window visible from spawn
- church tower kept as the dominant navigation silhouette

### Lighting

- cold storm sky
- moonlight only where it improves silhouette readability
- warm dirty light leaking from one or two church windows
- lightning projection through architecture
- wet-ground highlights
- no broad videogame fill light

### Audio

Base:
- rain bed
- exterior wind
- distant thunder
- rain gutters / stone runoff

Sparse one-shots:
- distant human scream
- metal sign/chain movement
- wood shifting
- far zombie call
- single unexplained bell before power
- extremely rare distant woman-like lament, original Xziel recording/source only

### Horror event

One upper window may show a silhouette for less than a second during a lightning flash. Maximum once per match. It is not a quest clue.

---

## FLOOR 1 — NAVE / THE FALSE SAFE ROOM

The nave remains the primary training loop and must remain mobile-readable.

### Geometry

Preserve clear circulation around pews. Add story dressing mostly outside the movement envelope:

- pews displaced into failed barricades
- torn hymn sheets
- blackened rosary
- old blood trail that continues toward the office route
- broken confession booth
- fallen censer
- damaged stained glass
- survivor tally marks
- an unfinished wall warning
- Altar Forge visible but dormant

### Lighting

The nave becomes the signature visual space:

- cold moon through damaged windows
- original stained-glass projected color on stone/floor
- candle islands around selected story props
- dark upper rafters
- lightning creates brief high-contrast silhouettes
- altar receives controlled visual emphasis without looking like a UI marker

### Audio

Base:
- rain on roof
- long church room tone
- subtle wind leakage
- occasional timber/pew settling

Localized:
- confession-area whisper/breath
- organ body resonance
- candle/fire detail where present
- window rattle during stronger wind

Rare:
- one isolated organ note
- muffled movement behind a wall
- very low choir-like breath texture with no recognizable melody

The nave must have long periods where none of the rare events play.

---

## FLOOR 1A — OFFICE / ARCHIVE CORRIDOR

This becomes the first strong human-history area.

### Dressing

- parish registry with names crossed out
- emergency incident notes
- old photographs
- maintenance clipboard
- clock
- archive boxes
- physical radio/tape recorder
- projector/slide equipment
- wall writing layered over legitimate church signage

### Lighting

- narrow warm desk-lamp pool
- cold corridor darkness outside it
- projector beam with sparse dust
- one stable navigation light
- one event-driven fixture, not constant flicker

### Audio

- clock
- paper movement
- ceiling/building movement
- radio static fragments
- short incomplete recorded testimony
- rare footsteps apparently above the ceiling

A recording can terminate because the original recorder hears something behind them. Do not explain what it was.

---

## FLOOR -1 — BOILER / SERVICE UNDERCROFT

This is where normal architecture begins to feel physically hostile.

### Gameplay

Power remains here. Keep escape language obvious. Do not clutter the narrow combat route.

### Dressing

- abandoned temporary shelter
- failed repair tools
- pressure gauge stuck high
- burned fuse panel
- emergency blankets/supplies
- old blood on valve/door
- pipes disappearing into inaccessible darkness

### Lighting

- furnace red/orange practical
- sparse emergency lamp
- steam intermittently cuts sightlines without hiding enemies unfairly
- power activation changes the whole room state

### Audio

- boiler low rumble
- pipe ticks
- pressure releases
- metal contraction
- steam
- water drip
- fuse/electrical detail
- extremely rare coughing/tapping behind inaccessible masonry

### Power activation sequence

Power is not a single switch sound.

1. switch clunk
2. electrical strain
3. boiler/fan machinery wakes
4. emergency light changes
5. audio propagation changes
6. nave lights wake in sequence
7. organ gives one unresolved low chord
8. tower clock begins ticking
9. selected machines/radios become active

---

## FLOOR 2 — TOWER STAIRS / THE PURSUIT SHAFT

This is a deliberate compression of the player's comfort.

### Geometry

Keep stairs and collision clean. No loose physics objects.

Dressing:
- dropped maintenance tools
- broken lantern
- scratched numbers
- rope burn/drag marks
- small blood traces leading upward
- wall damage revealing older masonry

### Lighting

- narrow pools of light
- severe vertical shadow
- lightning through tower openings
- controlled moving rope shadow

### Audio

- footsteps on stone/wood
- wind pressure
- rope tension
- building groan
- footsteps one level above the player with no confirmed source

The footsteps must be rare enough that players debate whether they heard them.

---

## FLOOR 3 — RINGING CHAMBER / THE BELLS

This is the first openly supernatural space.

### Geometry

Keep bell machinery readable and deterministic.

Interactive objects:
- authored bell mechanisms
- quest controls
- Bell Shockwave trap

Everything else stays static.

### Lighting

- bell silhouette against exterior opening
- dust beam
- dark floor perimeter
- brief lightning backlight
- subtle ritual-state lighting only after relevant quest progress

### Audio

- rope strain
- bell settling resonance
- wind
- timber structure
- distant tower groan
- bell shockwave transient
- rare vocal-like resonance tail embedded in the room decay

The bell audio needs multiple layers: attack, metal body, room tail, exterior tail, mechanical rope/wood, and supernatural layer only when appropriate.

---

## FLOOR 4 — CLOCK CHAMBER / 03:17

This room should feel precise and wrong.

### Dressing

- clock machinery
- repair notebook
- repeated 03:17 references hidden naturally
- damaged maintenance markings
- old grease and tool wear
- one clue partly obscured rather than highlighted

### Lighting

- moonlight slices through moving mechanism
- gear shadows begin after power
- tiny maintenance practicals
- no glowing quest arrows

### Audio

- close ticking
- gear engagement
- wood/metal stress
- distant bell transmission through structure
- ticking subtly stops during selected supernatural events

Silence after the clock stops is more important than adding another stinger.

---

## FLOOR 5 — ROOF / TOWER TOP / EXPOSURE

The top is not relief. It removes the protection of the building.

### Lighting

- dominant storm
- lightning reveals full architecture for fractions of a second
- distant landscape mostly black
- readable enemy silhouettes
- no excessive fog wall around the player

### Audio

- high wind
- heavy thunder
- rain exposure
- bell below
- distant fires/structural noise
- rare far-off siren or human distress

The player should hear how high they climbed.

---

# ROUTING REDESIGN

Preserve the seven existing authoritative doors and 28 barricade/window locations. Improve what they communicate rather than multiplying interactions.

Primary progression:

Fallen Courtyard
→ Nave
→ Office/Corridor
→ Boiler / Power
→ Nave reopened state
→ Tower Stairs
→ Ringing Chamber
→ Clock Chamber
→ Roof / Tower Top

Required loops:

- Nave remains a complete combat loop.
- After power, one lower-route shortcut reconnects to the nave.
- Exterior receives a late-game reconnection to prevent the opening courtyard becoming dead content.
- Ringing chamber must have two enemy approaches after its shortcut state.
- Tower must never become a permanent one-door camp.

# INTERACTION BUDGET

Allowed deterministic interactions:

- 7 doors
- 28 barricade/window systems
- power
- Mystery Reliquary
- Altar Forge
- perk/reliquary stations
- wall buys
- Seven Bells quest controls
- Bell Shockwave
- Boiler Steam Burst
- selected radios/projector/recorders
- pickups/relics

Environmental motion allowed only when authored and bounded:

- door hinge animation
- barricade plank state changes
- bell/rope mechanism
- clock gears
- projector reel
- subtle lamp swing
- controlled steam
- rain
- cloth/candle effects where cheap and deterministic

No arbitrary rigid-body clutter.

# AUDIO BANK PLAN

The repository currently contains 1,106 CC0/public-domain raw audio files in assets/audio/cc0_horror_library (115,843,104 bytes total). Treat this as source material, not a single random pool.

Curate into these runtime banks:

1. undead_idle_near
2. undead_idle_far
3. undead_attack
4. undead_pain
5. undead_death
6. undead_crawler
7. undead_breath_gurgle
8. human_distress_far
9. human_whisper
10. human_cry_lament
11. horror_stinger_soft
12. horror_stinger_hard
13. supernatural_drone
14. ritual_texture
15. church_roomtone
16. office_roomtone
17. boiler_roomtone
18. tower_roomtone
19. roof_exterior
20. rain_light
21. rain_heavy
22. thunder_near
23. thunder_far
24. wind_interior
25. wind_exterior
26. wood_creak
27. wood_break
28. barricade_plank
29. old_door
30. metal_stress
31. glass_break
32. stone_debris
33. footsteps_wood
34. footsteps_stone
35. footsteps_gravel
36. water_drip
37. pipe_boiler
38. steam_pressure
39. electrical
40. radio_static
41. projector_mechanical
42. clock_mechanical
43. bell_mechanical
44. bell_resonance
45. mystery_reliquary
46. altar_forge
47. quest_feedback
48. silence_control / event scheduler state

Important: source/action semantics must be curated. A zombie idle cannot be used for attack, an attack vocal cannot be tagged as death, and a plank break cannot substitute for a door hinge simply because it sounds scary.

# AMBIENT EVENT RULES

- no fixed scream timer
- no repeating same event back-to-back
- per-zone weighted pools
- global horror cooldown
- silence windows
- maximum plays per match for signature events
- occlusion based on room/door/material
- distance filtering
- interior/exterior transitions
- round intensity changes probability, not just volume
- ultra-rare events may not occur in every match
- no required quest clue depends solely on a random event

# PERFORMANCE TARGET

The horror pass must not undo the native mobile strategy:

- keep current native XZ geometry authority
- room/portal culling
- zone LOD
- sparse particles
- baked/static lighting wherever possible
- limited dynamic shadow casters
- event-driven lights rather than dozens of always-updating lights
- spatial audio voice budget with priority stealing
- far ambience can be virtualized
- never render/process inaccessible tower/undercroft detail unnecessarily

# FINAL FEEL

Sanctum of Ash should not feel like "a church with zombies."

It should feel like the player entered a real refuge after everyone else lost, restored machinery that should have stayed dead, and climbed toward a bell tower that has been waiting for someone to wake it.
