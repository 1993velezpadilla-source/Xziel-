# CALL OF DUTY ZOMBIES — MAP DNA ATLAS / XZIEL DESIGN REVERSE ENGINEERING

Updated: 2026-09-24  
Project: Xziel / ZOMBIESSSSSSS PORTABLE

## Scope

This is a clean-room design study of publicly observable Call of Duty Zombies map behavior. It does **not** contain copied geometry, proprietary map files, game scripts, source code, textures, audio, meshes, quest text, or extracted assets.

The machine-readable source is `docs/zombies-map-dna-atlas.v1.json`. The atlas currently covers 66 official experiences and references across Treyarch, Sledgehammer, Infinity Ward, and later Call of Duty Zombies releases. Each entry is classified so remakes, reimaginings, survival submaps, and objective/open-world modes do not get mixed with original round-based maps.

## The reusable map grammar

Across the corpus, the strongest maps are not defined by one exact layout. They repeatedly combine a small number of reusable spatial grammars:

1. **Single holdout** — tiny readable footprint, resource scarcity, almost no safe reset.
2. **Hub + spokes** — a central landmark with deliberate route choices into themed subregions.
3. **Looping compound** — one or more circulation loops that can be opened progressively.
4. **Vertical stack** — floors or terraces connected by stairs, lifts, ziplines, jump routes, drops, or teleport.
5. **Multi-hub** — several locally readable combat spaces connected by risky transitions.
6. **Vehicle-connected regions** — combat islands connected by a bus, boat, truck, teleporter, or similar macro-travel system.
7. **State-layered map** — the same or similar footprint changes through power, alternate realms, time states, decompression, ritual state, or Dark Aether shifts.

XZIEL should treat these as topology primitives, not as layouts to copy.

## Door economy and route pressure

Doors are not merely blockers. They are player-authored topology.

A useful door does at least one of these:

- opens a safety loop;
- exposes a resource;
- reveals a landmark;
- creates a faster return route;
- removes a choke while creating a new spawn angle;
- trades early economy for later mobility;
- changes team split/rejoin behavior.

The player should sometimes have a reason **not** to open a door immediately. If every door is an automatic purchase, the economy has no route strategy.

### Xziel rule

Every medium/large round-based map should have:

- at least one meaningful early fork;
- at least one loop the team can deliberately complete;
- at least one shortcut unlocked after commitment;
- at least one doorway whose purchase changes combat behavior, not just walking distance.

## Power is a map state transition

Classic maps frequently use power as the moment the location wakes up. Later maps replace one global switch with reactors, generators, rituals, or distributed objectives, but the design purpose is the same:

- move the player out of spawn;
- teach major regions;
- activate utilities;
- change lighting/audio;
- create new route value;
- establish the first major match milestone.

XZIEL should model power as a state graph. Lights, machines, ambient audio, traps, doors, interactives, and enemy behavior may subscribe to that state.

## Training spaces are a budget, not a mistake

A map needs enough open circulation for high-round survival, but unlimited safe loops flatten tension.

The corpus repeatedly balances training space with one or more interruptors:

- special enemies;
- environmental hazard;
- narrow connector;
- periodic objective;
- roaming boss;
- changing spawn direction;
- low-visibility event;
- temporary lockdown;
- long transit penalty.

### Xziel rule

For each major loop, record:

- width and minimum escape clearance;
- number of blind corners;
- number of zombie entry vectors;
- nearest bailout;
- whether a special enemy can invalidate the loop;
- whether the loop becomes safer or more dangerous after a door opens.

## Map readability

Large maps remain learnable when they use layered orientation:

- one global landmark;
- distinct regional silhouettes;
- room-purpose naming;
- unique light/audio palette per zone;
- consistent transit grammar;
- visible destinations before the player reaches them.

A church tower, lighthouse, rocket, theater stage, arena, castle keep, or central machine can act as a global compass.

### Xziel rule

Each map should define:

- **global landmark** — visible or inferable from multiple zones;
- **regional landmarks** — one per major zone;
- **transition language** — how the player recognizes doors, stairs, lifts, teleporters, ziplines, vehicles, portals;
- **return-route language** — what tells the player a shortcut now exists.

## Spawn architecture

Good zombie pressure is spatial.

Spawn design should distinguish:

- window/barricade entry;
- ground emergence;
- hidden offscreen entry;
- rooftop/vertical entry;
- flanking portal;
- special-enemy entry;
- boss/arena spawn.

The director should choose spawn groups from current player distribution, route ownership, sightlines, and desired pressure—not simply nearest distance.

### Xziel requirement

Never visibly pop a normal zombie into a clear player-facing area. A spawn group needs concealment, traversal time, or a believable emergence animation.

## Progression families

The atlas identifies recurring progression grammars:

- **doors only** — survival-first;
- **single power gate** — classic milestone;
- **distributed generators/reactors** — map-teaching progression;
- **ritual network** — repeat a learned action across districts;
- **transport unlock** — travel network doubles as progression;
- **quest gate** — parts/steps unlock utility or new space;
- **objective unlock** — discrete missions expand a hub;
- **state shift** — realm/time/pressure state changes route value.

These can be composed. The engine should not hardcode one "COD-style" progression path.

## Quest grammar

Major quests commonly reduce to reusable node types:

- collect N components;
- activate N regional anchors;
- perform ordered sequence;
- charge object with kills;
- escort/protect;
- survive lockdown;
- use weapon/state on target;
- align symbols/clocks/controls;
- transport item between zones;
- defeat elite/boss;
- permanently change map state.

XZIEL already has logic nodes that map naturally to this grammar. Original quests should be authored from these primitives rather than reproducing any existing quest.

## Special enemies as route modifiers

Special enemies are most useful when they make the player move differently.

Examples of abstract roles:

- **chaser** — invalidates static camping;
- **area denial** — contaminates floor or room;
- **economy attacker** — steals or disables a resource;
- **ranged pressure** — punishes long sightline comfort;
- **tank** — blocks narrow route;
- **teleporter/flanker** — breaks predictable kiting;
- **roaming boss** — forces continuous macro-awareness;
- **objective disruptor** — attacks an active system.

The director should choose roles based on current map topology and player behavior.

## Transport systems

Transport is useful when it solves a real scale problem.

Good transport has:

- predictable origin/destination;
- readable state;
- meaningful travel time;
- risk or opportunity cost;
- strategic reason to use it besides novelty.

Vehicles are appropriate for region-scale maps. Ziplines/lifts suit vertical maps. Teleporters suit nonphysical or ritual spaces. One-way slides/drops are useful for controlled commitment.

## Environmental hazard

Hazards become gameplay when they alter path choice:

- mud/snow/slow terrain;
- toxic gas;
- lava/fire;
- decompression;
- fog;
- artillery;
- freezing water;
- moving machinery;
- timed electric areas.

Decorative damage volumes are not enough. The player must be able to read, predict, route around, or exploit the hazard.

## Scale progression across eras

The design trend is not simply "maps became bigger."

The more useful pattern is:

- early maps concentrate tension in small footprints;
- middle-era maps add strong traversal and quest layers;
- later maps use regional identity, vehicles, alternate states, and optional side systems to make larger spaces manageable.

For Xziel, **complexity must scale with navigation support**. A bigger map requires more landmarks, shortcuts, local loops, and explicit route grammar.

## Cross-studio lessons

### Advanced Warfare Exo Zombies

Useful reference for:

- movement abilities changing route value;
- open entry instead of repairable windows;
- area-specific power;
- contamination/decontamination pressure;
- objective interruptions inside survival.

### Infinite Warfare Zombies

Useful reference for:

- aggressively themed districts;
- environmental traps tied to attractions;
- minigames/side economies;
- map-specific player power systems;
- strong visual identity per region.

### WWII Nazi Zombies

Useful reference for:

- horror-forward art direction;
- guided critical-path quest support;
- fog as dynamic pressure;
- surface-to-underground escalation;
- body-horror enemy readability.

These are comparative references, not templates.

## SANCTUM OF ASH application

Sanctum already contains the right raw ingredients: exterior arrival, nave, office/service route, boiler power, tower ascent, ringing chamber, clock chamber, roof, traps, quest anchors, multiple spawn zones, and a boss space.

The atlas suggests strengthening it with the following original design requirements:

1. Keep the **church tower as the global landmark**.
2. Preserve an **early fork**: service/boiler route versus tower-progress route.
3. Make boiler power a **full audiovisual state change**, not a boolean.
4. Ensure the nave becomes a **completed combat loop**, not a dead-end arena.
5. Add one **post-power shortcut** reconnecting upper tower progression to a lower safe return path.
6. Give every major zone at least **two zombie pressure vectors**; large zones should have three or more.
7. Make one special enemy role a **loop breaker**, not a pure health sponge.
8. Use tower ascent as a **vertical commitment** with periodic bailout points.
9. Keep the Bell Warden finale mechanically foreshadowed by bell shockwave / sound-pressure hazards earlier in the match.
10. Keep the Seven Bells quest original, but implement it through generic reusable logic nodes so later maps can share the engine technology without sharing content.

## Mobile translation

For portable hardware, map DNA matters more than brute-force fidelity.

Prefer:

- room/portal culling;
- region streaming;
- fixed authored spawn groups;
- precomputed zone bounds;
- deterministic door state;
- bounded quest graphs;
- sparse but meaningful dynamic lights;
- audio zones with occlusion;
- static geometry batching by spatial cell;
- local combat loops that fit in resident memory.

Do not reduce gameplay complexity merely to reduce render complexity. Stream and cull the map so the gameplay graph can remain rich.

## Validation philosophy

A generated Xziel map should be tested on four independent layers:

1. **Topology** — routes, loops, forks, shortcuts, irreversible drops.
2. **Economy/progression** — door prices, power timing, resource access.
3. **Pressure** — spawn vectors, special enemies, hazards, traversal interruptions.
4. **Readability/horror** — landmarks, lighting, audio, environmental storytelling.

A map is not finished because geometry renders. It is finished when all four layers survive repeated playtests.

## Sources

Primary current/historical references include Activision/Call of Duty official guides and blogs for Zombies Chronicles, Black Ops 4, Cold War, WWII, Black Ops 6, and Black Ops 7, plus community catalog cross-checks for older map inventories. Exact source URLs are stored in the JSON atlas so the data remains auditable.
