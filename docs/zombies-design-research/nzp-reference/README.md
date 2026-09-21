# NZ:P Quest / Interaction Reference Corpus

Updated: 2026-09-20

Purpose: preserve the reusable interaction and quest vocabulary already present in Nazi Zombies: Portable so **Xziel / ZOMBIESSSSSSS PORTABLE** can implement a generic quest/state-machine system from verified precedent instead of rediscovering every mechanism.

## Pinned upstream snapshots

- `nzp-team/assets@c8135a66e00bb64577912fbf792f8fef7f47658e`
- `nzp-team/quakec@dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163`

The pins are intentional. A future refresh can diff these hashes and regenerate the corpus without mixing versions.

## What is exhaustively captured

For the pinned official snapshots:

- **20/20** `.map` files under `assets/source/maps`
- **5,250** top-level map entities and all of their key/value properties
- **2,216** resolved `target/target2/target3/target4/killtarget -> targetname` edges
- **22** unresolved references preserved rather than silently discarded
- **2/2** mapper FGD files
- **90** mapper-facing entity classes with fields and spawnflags
- **78/78** server-side QuakeC `.qc` files
- every top-level function entry point found in those 78 files
- source coordinates for entity-class mentions and target/use/touch/round/player-count APIs

Brush geometry is deliberately omitted from the generated logic corpus. The original immutable map path/blob is retained for provenance.

## Layout

- `engine/fgd-entity-catalog.json` — complete mapper entity vocabulary.
- `engine/quakec-symbol-index-part-01.json` … `part-07.json` — complete server QuakeC symbol/source-coordinate index.
- `maps/official-map-logic-part-01.json` … `part-05.json` — complete geometry-free entity logic for all official source maps.
- `community-map-quest-catalog.md` — verified quest/Easter-egg/interactions described by community map releases.
- `community-map-release-inventory.md` — release-board inventory and extraction status.
- `upstream-snapshots.json` — immutable snapshot/count manifest.
- `LICENSE_NOTES.md` — provenance and reuse boundary.

## Interaction vocabulary already represented

The FGD catalog includes, among other things:

- direct use interactions: `trigger_interact`, `func_button`
- one-shot/repeat/event routing: `trigger_once`, `trigger_multiple`, `trigger_relay`, `trigger_activator`
- counters/requirements: `trigger_counter`, `game_counter`, `func_counter`, `func_oncount`
- round gates: `trigger_atroundend`
- randomized dispatch: `game_random`
- secret/reward flow: `trigger_secret`, `trigger_awardpoints`, `func_ending`
- world state: `power_switch`, doors, rotating/moving entities, sky changes
- teleporter systems: destination, entrance, pad and timed teleporter entities
- traps/electric logic: `trigger_electro`, `zapper_node`, `zapper_light`
- audiovisual feedback: songs, voices, ambient audio, screen flash
- zombie progression: spawn zones, zombie/dog spawns, horde points
- player-specific starts: `info_player_1_spawn` through `info_player_4_spawn`
- perks, wall weapons, barricades, radios and placeable models/fire

The QuakeC index points to the implementation/tests behind these primitives, while the map-logic files show how the primitives are actually chained.

## Multiplayer rule

NZ:P supports co-op up to four players and exposes player-specific spawn entities. That **does not mean a quest requires four players**. Community quest steps are marked four-player-required only when the release/source explicitly proves that requirement. No assumption is made from general co-op support.

## Completeness boundary

The official GitHub source snapshots above are exhaustively indexed.

Community releases are different: many are distributed through GitHub Discussions with external ZIP/PK3/Drive/MediaFire links, and only some include J.A.C.K/`.map` sources. The community catalog therefore distinguishes:

- **SOURCE_EXTRACTED** — source map/project logic obtained and indexed.
- **SOURCE_AVAILABLE** — author states/source link confirms editable source exists.
- **MECHANICS_VERIFIED** — release documentation/changelog establishes the interaction chain, but editable map source has not yet been archived here.
- **SURVIVAL_ONLY_OR_NO_QUEST_FOUND** — no substantial quest chain found in the release description/source evidence.
- **UNVERIFIED_EXTERNAL_ARCHIVE** — external package exists but source-level quest logic is not verified.

Never convert a release-board claim into a working-quest claim when comments/changelogs show the Easter egg is broken.

