# NZ:P Quest Primitive Semantics — Source Audit

Pinned source: `nzp-team/quakec@dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163`  
Updated: 2026-09-20

Purpose: record the **actual runtime semantics** behind NZ:P quest/interact primitives, not only their mapper-facing FGD labels. This is the reference for designing Xziel's generic QuestGraph/state-machine layer.

## 1. trigger_interact — one activation per arming

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/triggers.qc

Observed behavior:

- accepts only a live `player`
- rejects downed players
- rejects interaction while the player is buying
- requires `PlayerIsLooking(player, trigger)`
- optional point cost uses the global game-mode cost multiplier
- optional useprint and sound feedback
- sets both `enemy` and global `activator` to the interacting player
- fires the target graph through `SUB_UseTargets()`
- **disarms itself after a successful use** by replacing `touch` with `SUB_Null`
- another entity must call its `.use` to re-arm it
- spawnflag 1 (`START INACTIVE`) causes it to begin disarmed

### Xziel pattern

This is not merely "press use." It is a reusable:

`ARMED -> PLAYER_LOOKS + USE [+ COST] -> FIRE GRAPH -> DISARMED -> EXTERNAL REARM`

That maps cleanly to `QuestInteractNode` with explicit retrigger policy.

## 2. SUB_UseTargets — the central event bus

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/sub_functions.qc

Observed behavior:

- supports `target` through `target8`
- sends `message` feedback to all player clients
- `killtarget` fake-removes every entity with the matching `targetname`
- supports delayed firing by creating a temporary `DelayedUse`
- supports a round-based delay by polling until the target round is reached
- when firing each destination, propagates `other.triggerstate` into `global_triggerstate`
- destination `.use` functions therefore receive ON/OFF-style relay state indirectly
- special spawn entities may be promoted from inactive variants during target firing

### Important source/docs discrepancy

For this pinned QuakeC snapshot, the code checks `delay` **before** `round_delay` and returns after creating the delayed event. Therefore if both are non-zero, ordinary time delay wins in this source snapshot.

The public mapping documentation has described `round_delay` as taking precedence over `delay`. Treat this as a **docs/source mismatch** and test before copying behavior. For Xziel, define precedence explicitly rather than inheriting ambiguity.

## 3. game_counter — reversible and optionally reusable counter

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/map_entities.qc
- tests: https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/tests/test_game_counter.qc

Observed behavior:

- normal/ON activation increments `frags`
- OFF trigger state decrements `frags`
- target graph fires on exact equality: `frags == health`
- spawnflag 1 removes the counter after firing
- spawnflag 2 resets it after firing
- reset restores the **initial** `frags`, which is cached in `cost`

### Xziel pattern

Use a generic counter with:
- increment/decrement actions
- exact/at-least comparison mode
- one-shot/reset/persistent completion policy
- explicit initial value

This supports collectibles, generators, symbols, switches, soul boxes, vote/sync counts and reversible puzzle state.

## 4. game_random — numbered random dispatch

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/map_entities.qc
- tests: https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/tests/test_game_random.qc

Observed behavior:

- requires `health` as maximum answer N
- requires `name` as target-name prefix
- chooses uniform integer 1..N
- constructs `<name>_<result>`
- temporarily assigns that as its target and calls `SUB_UseTargets()`

### Xziel pattern

`QuestRandomBranch(seed, choices[])` should store the chosen branch in shared match state so reconnects/save restore cannot reroll it unintentionally.

## 5. power_switch — built-in multi-switch AND gate

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/power_switch.qc

Observed behavior:

- each switch is one-shot
- each switch may fire its own targets immediately
- every switch increments global `activated_power_switches`
- global power becomes ON only when `activated_power_switches == num_power_switches`
- after the final required switch:
  - global `isPowerOn` becomes true
  - compatible power-gated doors are opened/removed
  - Pack-a-Punch machines are enabled
  - perk-light effects are enabled
  - zombie zones are recomputed

### Xziel pattern

This is a native example of:

`N independent objectives -> shared AND barrier -> global world-state transition`

Generalize it rather than hardcoding electricity. The same primitive can represent generators, ritual altars, fuse boxes, seals or pressure stations.

## 6. trigger_atroundend — exact round event

Sources:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/rounds.qc
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/triggers.qc

Observed behavior:

- round-end logic scans every `trigger_atroundend`
- fires only when `trigger.health == rounds`
- comparison is **exact equality**, not `>=`

### Pitfall

If an entity intended for round 20 is enabled only after round 20 has already ended, this implementation does not provide an automatic catch-up.

Xziel should support both:
- `OnExactRoundEnd(N)`
- `OnOrAfterRoundEnd(N)`

and make the choice data-driven.

## 7. teleporter — multiplayer group portal state machine

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/teleporter.qc

Observed behavior:

- stores up to four player entities
- uses an activation radius
- supports a power requirement
- supports entrance <-> pad linking state
- supports point cost
- supports cooldown state
- fires target graphs during portal actions
- teleports all players found inside the radius
- spatially offsets players at destination
- mode 2 supports timed return using `tpTimer`
- fixed cooldown path is 5 seconds in this snapshot
- resets weapon/reload timing and applies short movement penalty after transfer

### Xziel pattern

Model portals with explicit:
- `UNPOWERED`
- `UNLINKED`
- `READY`
- `ACTIVATING`
- `REMOTE`
- `RETURN_PENDING`
- `COOLDOWN`

and treat group membership as an explicit participant set rather than relying on incidental radius iteration.

Community reports prove that capability does not guarantee bug-free multi-player behavior, so multiplayer portal tests belong in the quest regression suite.

## 8. func_ending — one-shot global finale

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/func.qc

Observed behavior:

- optional point cost
- only a player can activate
- one-shot via `activated`
- after successful purchase it loops over **all players**
- each player is placed in end-game state and `EndGameSetup()` runs

### Xziel pattern

An ending purchase is a **shared match transition**, never merely a local player interaction.

## 9. teddy_spawn / teddy_react — shootable collectible trigger

Sources:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/map_entities.qc
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/triggers.qc
- weapon/damage integration:
  - https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/weapons/weapon_core.qc
  - https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/damage.qc

Observed behavior:

- teddy is a damageable bbox
- weapon/damage flow can invoke `teddy_react`
- normal mode fires its target graph
- alternate spawnflag mode finds/removes an entity through custom `teddyremovetarget`
- optional feedback sound
- teddy then fake-removes itself

### Xziel pattern

The familiar "shoot N hidden objects" Easter egg is simply:

`ShootableQuestItem -> Event -> Counter -> Completion Relay -> Reward`

The collectible model should be arbitrary; the engine primitive should not be teddy-specific.

## 10. secret-song path

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/map_entities.qc

Observed behavior:

- `item_radio` is a shootable secret object and can fire targets
- `game_songplay` is the active song-play entity
- `trigger_song` is legacy/dummy behavior and removes itself in this snapshot

### Xziel pattern

Keep collectible/secret completion separate from audio playback. A reward action may request music, but quest state must not depend on the audio object surviving.

## 11. trigger_awardpoints — one-use contextual reward volume

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/triggers.qc

Observed behavior:

- one-use via internal `health` flag
- player-only
- supports stand/crouch/prone requirements
- optional Double Points multiplication
- optional sound

This is useful precedent for hidden movement/stance discoveries, but Xziel should expose conditions generically rather than one bit flag per stance.

## 12. trigger_activator — specialized spawn activation

Source:
- https://github.com/nzp-team/quakec/blob/dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163/source/server/entities/triggers.qc

Despite the generic name, this implementation is specialized around activating inactive zombie spawn entities across target groups and then reassigning zombie spawn IDs.

Do **not** model it as a generic quest relay.

The source also contains suspicious/redundant `tempcount =+ 1` statements before the proper increments. This is another reason Xziel should reproduce semantics deliberately rather than mechanically porting old code.

## Proposed normalized Xziel primitives

From the source audit, the minimum reusable vocabulary should include:

- `Interact(condition, cost, feedback, retriggerPolicy)`
- `EventRelay(targets[], delaySeconds?, delayRounds?, state?)`
- `RemoveTargets(selector)`
- `Counter(initial, goal, comparison, resetPolicy)`
- `RandomBranch(seed, choices[])`
- `AllOf(children[])`
- `AnyOf(children[])`
- `RoundGate(round, exactOrAfter)`
- `Collectible(triggerMode, itemId)`
- `WorldStateFlag(key, value)`
- `GroupPortal(linkState, participantPolicy, returnPolicy, cooldown)`
- `ZoneActivation(zoneSet)`
- `Reward(actions[])`
- `GlobalEnding(requirements, cost?)`

These should serialize as quest data and use shared/player state explicitly. Map-specific names such as teddy, generator, key card, altar or ritual should be content data layered on top.

## Regression tests Xziel should inherit from this research

- interact fires once, then cannot fire until re-armed
- insufficient-cost interact makes no state change
- counter increments and decrements through relay state
- remove-on-complete vs reset-on-complete counters
- delayed relay preserves original activator
- target fan-out executes every target deterministically
- killtarget removes all matches
- exact-round event does not accidentally retrigger
- randomized branch persists across save/reconnect
- N-switch gate changes global state only after final unique switch
- 1/2/3/4-player portal occupancy
- player disconnect during group portal
- timed portal return with dead/downed participant
- global ending completes for all connected players
- collectible cannot be counted twice
- quest completion remains correct with audiovisual reward disabled

