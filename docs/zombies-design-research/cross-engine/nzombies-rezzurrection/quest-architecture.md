# Cross-engine quest reference: nZombies Rezzurrection

Pinned upstream: `nZombies-Time/nZombies-Rezzurrection@ee145e14f457e26f7d5314a9f67eb821d69e3e2a`  
License file: `gamemode/LICENSE.txt` — GNU GPL v3.

This corpus is intentionally separate from the NZ:P corpus. It exists because nZombies Rezzurrection is an open-source Zombies-style engine whose repository explicitly advertises **official configs with Full Easter Eggs**, and its source exposes reusable quest architecture directly.

We preserve **structural research** (state machines, item-carry semantics, counters, soul collection, buildables, fail/retry behavior, endings), not proprietary Call of Duty art/audio/models.

## Core major-quest state machine

Source: `gamemode/gamemodes/nzombies/gamemode/easter_eggs/sv_major_ee.lua`

Runtime state:
- `Steps[]`
- `CurrentStep`

Operations:
- `AddStep(func, optionalIndex)`
- `SetCurrentStep(step)`
- `CompleteStep(step, ...)`
- `Reset()`
- `Cleanup()`

Important semantic:
`CompleteStep(N)` only advances when `CurrentStep == N`. It executes the registered callback for that step and then increments the global major-step pointer.

This is a clean precedent for Xziel's:
`QuestGraph.currentNode -> complete -> transition -> activate next phase`.

## Case study: Imprisoned

Source: `gamemode/lua/nzmapscripts/nz_zs_obj_station;Imprisoned.lua`

### Supporting systems

Item categories:
- `shield1`
- `shield2`
- `shield3`
- `fuses`
- `chargedfuses`

The three shield part categories:
- choose one of several random spawn positions on reset
- are non-shared player carry items
- do not drop when the carrier is downed
- feed a `buildable_table`
- completed table grants a Zombie Shield on use

Fuse categories demonstrate state transformation:
`Fuse -> insert in generator -> collect souls -> ChargedFuse`.

Fuses:
- can be carried
- can drop from a downed/player state
- can respawn/reset if lost
- are tracked against a shared table so the exact logical fuse survives transformations

Generators use `nz_script_soulcatcher`:
- target amount = 20
- range = 500
- only collect when electricity is active
- completion marks the attached fuse charged
- completion opens linked progression doors
- the third completed generator enables the PAP-side spawn/progression group

### Major step 1 — timed multi-station challenge

Completion calls show Step 1 is completed only after **three challenge stations** succeed.

One observed station:
- begins a 60-second run
- periodically changes a required interaction/light state
- after each flip the player has a short response window (~3 s)
- missing the response fails that station attempt and requires retry
- completing all three stations advances the major quest

Normalized:
`Parallel/serial ChallengeStations(3) -> all complete -> CompleteStep(1)`

This is direct precedent for retryable timed minigames that do **not** destroy the match.

### Major step 2 — electrified-shield dual target

Two special damage targets are created.

Each:
- responds to damage
- checks the attacker's active weapon
- requires the Zombie Shield
- electrifies the shield/records the interaction

After the two required activations, `CompleteStep(2)`.

Normalized:
`Acquire/Build UtilityWeapon -> Electrify/qualify weapon -> hit 2 quest targets -> Step2`.

### Major step 3 — Pack-a-Punch weapon requirement

Three forcefield/generator objects each:
- only count while `CurrentStep == 3`
- check the attacking weapon for the PAP modifier
- are one-shot via `HasBeenPaPShot`
- increment shared `doneforcefields`

When all 3 have been hit with a Pack-a-Punched weapon:
`CompleteStep(3)`.

Normalized:
`UseSpecificWeaponState(PAP) on 3 unique targets -> Counter(3) -> next phase`.

### Major step 4 — destruction phase / infinite-round commit

Step 3's transition:
- removes the energy shield
- changes control-panel visual state
- attaches an on-remove callback to a quest button

Removing that button triggers Step 4.

Step 4:
- records the round reached
- puts round logic into an infinity/finale state
- waits for a second core-destruction object to be removed
- then completes Step 5

Normalized:
`WorldBarrierOff -> destroy activation target -> commit finale -> survival/finale state -> destroy core -> ending`.

### Major step 5 — ending + persistent gameplay reward

Ending sequence:
- queues cinematic camera views
- displays completion text
- temporarily slows time
- freezes round spawning
- plays finale music
- freezes/retargets players during the presentation
- nukes remaining enemies
- resumes the game
- grants permanent perks to all players

This is a valuable alternative to "ending always terminates the match": the quest can produce a **cinematic global completion state and then return players to survival with permanent rewards**.

## Case study: Breakout

Source: `gamemode/lua/nzmapscripts/nz_ttt_kosovos;Breakout.lua`

Item categories:
- `gascan`
- `ee_key`
- `ee_battery`
- `ee_chargedbattery`

### Key -> lock -> step transition

A lock advertises a required item `ee_key`.
On use:
- verifies player carries key
- consumes key
- removes cabinet/lock world objects
- completes Step 1

Normalized:
`CarryItem(Key) + Use(Lock) -> Consume(Key) -> RemoveBarrier -> CompleteStep(1)`.

### Battery gating

The normal battery:
- is pickable only at/after quest Step 1
- is a droppable carry item
- pickup itself can advance Step 2 in the current script

A later ghost/placement node:
- accepts the uncharged battery
- creates a soul catcher
- requires 10 valid soul events in range 200
- only accepts kills with electric damage
- transforms the result into `ee_chargedbattery`

Normalized:
`Battery -> place -> ChargeWithSouls(10, damageType=shock) -> ChargedBattery`.

This is strong precedent for **typed soul-charge conditions**, not merely "kill N zombies nearby."

## Xziel primitives strengthened by this cross-engine source

The combined NZ:P + nZombies evidence now supports first-class primitives for:

- explicit ordered major-step state
- item categories with per-player/shared ownership
- random spawn locations
- pickup conditions based on quest phase
- consume-on-use item gates
- drop-on-downed policy
- reset/recovery when a quest item is lost
- buildable tables with multiple part categories
- item transformation (uncharged -> charged)
- soul collection with count, radius and damage/weapon condition
- timed minigames with retry, not hard match fail
- exact unique-target counters
- weapon-state requirements (e.g. upgraded/PAP)
- phase-dependent damage handlers
- world barrier removal
- finale commit / infinite-round mode
- cinematic queues
- global player freeze/unfreeze
- post-quest persistent rewards

## Design lesson

NZ:P demonstrates how far a mapper can go with generic target graphs. nZombies Rezzurrection demonstrates the next layer: **explicit typed quest objects and ordered major steps**.

Xziel should combine the strengths:
- data-driven graph fan-out from NZ:P
- explicit quest-state/item/recovery semantics from nZombies
- deterministic multiplayer shared state
- serialization/checkpoint support
- platform-safe presentation separated from quest truth


