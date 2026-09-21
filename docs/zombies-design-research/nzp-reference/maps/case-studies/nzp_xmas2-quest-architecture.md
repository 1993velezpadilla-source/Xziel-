# Case Study — `nzp_xmas2` Quest Architecture

Pinned source: `nzp-team/assets@c8135a66e00bb64577912fbf792f8fef7f47658e`  
Map: `source/maps/nzp_xmas2/nzp_xmas2.map`

The companion file `nzp_xmas2-quest-subgraphs.json` preserves the full extracted `q_*` / `sq_*` entity graph. This document explains the strongest reusable patterns without copying brush geometry.

## Why this map matters

Within the official NZ:P source snapshot, `nzp_xmas2` is the densest quest-like map examined:

- 25 `trigger_interact`
- 12 `game_counter`
- 11 `func_button`
- 7 `game_songplay`
- 4 `game_screenflash`
- 56 `trigger_multiple`

The naming also cleanly separates larger `q_*` chains from `sq_*` side-quest chains.

## Main progression cluster: gramophone -> bells -> drawer -> key -> boiler

### A. Match start establishes the gramophone loop

All four player spawn entities target `q_gramo_start`. This is significant: the map deliberately uses player-spawn events as quest/world-state initialization.

`q_gramo_start` begins normal gramophone ambience and a timed loop.

### B. Power changes the gramophone state

The `power_switch`:

- targets `q_gramo_dis_start`
- also targets normal power-light behavior
- killtargets `q_gramo_normal_kill`

The `q_gramo_dis_start` group:
- changes/toggles the gramophone presentation
- starts distorted gramophone ambience
- eventually enables `q_gramo_interact`

So power is not just a generic electricity flag here; it causes a quest-specific state transition.

### C. Gramophone interaction unlocks the bell stage

`q_gramo_interact` is a `trigger_interact` that starts inactive. Once armed, interacting fires the shared target `q_gramo_interact_seq`.

Multiple entities share that targetname, producing parallel effects:
- immediate jumpscare
- delayed voice line
- `q_bells_activate`

`q_bells_activate` waits **one round**, then fires `q_bells_kill_blocker`, which killtargets every `q_bell_blocker` wall.

Pattern:

`POWER -> ARM GRAMOPHONE -> INTERACT -> PARALLEL FEEDBACK -> ROUND DELAY -> REMOVE BELL BLOCKERS`

This is a clean example of a quest changing traversal/interaction availability one round later.

## Seven-bell staged progression

Seven separate `func_button` entities each:

- fire `q_bell_increment`
- also target their own bell-state entity (`q_bell_1` ... `q_bell_7`)

The clever part is `q_bell_increment`.

Seven separate `game_counter` entities share that same `targetname`, but use goals 1 through 7:

| Counter goal | Fires |
|---:|---|
| 1 | `q_bell_ring_1` |
| 2 | `q_bell_ring_2` |
| 3 | `q_bell_ring_3` |
| 4 | `q_bell_ring_4` |
| 5 | `q_bell_ring_5` |
| 6 | `q_bell_ring_6` |
| 7 | `q_bell_ring_7` + `q_bell_finished_wait` |

All seven counters are one-shot. Every bell press targets all surviving counters named `q_bell_increment`; the threshold-1 counter fires/removes on press 1, threshold-2 on press 2, and so on.

This implements a **progress-stage sequencer from ordinary counters** without a dedicated sequence entity.

### Completion fans out over time

When count 7 fires `q_bell_finished_wait`, multiple relays sharing that targetname schedule different consequences:

- ~2.9 s: quest sting/music
- ~3 s: screen flash
- ~5 s: voice feedback
- **90 s:** arm `q_drawer_interact`

Pattern:

`COUNTER COMPLETE -> MULTIPLE TIMED CONSEQUENCES -> DELAYED NEXT QUEST STEP`

## Drawer -> revealed key -> key pickup -> boiler door

After the 90-second bell completion delay:

1. `q_drawer_interact` is armed.
2. Player interacts with drawer.
3. Drawer opens and fires `q_drawer_key_delay`.
4. The shared delay target drives at least two timed actions:
   - ~0.25 s: reveal key model + music cue
   - ~1.5 s: arm `q_key_interact`
5. Player uses `q_key_interact`.
6. The key interaction:
   - arms `q_boiler_door_interact`
   - killtargets/removes `q_drawer_key`
7. Player can now interact with `q_boiler_door_interact`.
8. Boiler door opens.

Pattern:

`DELAYED ACCESS -> OPEN CONTAINER -> REVEAL ITEM -> ARM PICKUP -> PICKUP REMOVES ITEM -> ARM LOCKED INTERACTION -> OPEN PATH`

This is almost exactly the generic "find item / use item on lock" vocabulary needed for modern Zombies quests.

## Weapon construction chain

### A. Find the frame

A `trigger_interact` fires:
- `q_wep_frame`
- `q_wep_frame_collect`

`q_wep_frame_collect` waits **one round**, then:
- plays a frame-related voice cue
- fires `q_tokens_show`

### B. Reveal three quest tokens

`q_tokens_show` fans out to:
- scarf model + scarf interact
- glasses model + glasses interact
- toy model + toy interact

All three token interactions were initially inactive.

Each token pickup:
- toggles/removes its token presentation
- schedules a related voice cue
- **arms a corresponding fire-placement interaction**

Mapping:
- glasses -> `q_fire_g_interact`
- toy -> `q_fire_t_interact`
- scarf -> `q_fire_s_interact`

Pattern:

`FIND CORE PART -> ROUND DELAY -> REVEAL 3 ITEMS -> EACH ITEM UNLOCKS ITS MATCHED USE LOCATION`

### C. Place/use all three tokens

Each `q_fire_*_interact`:
- reveals/changes its corresponding token-at-fire model
- increments `q_fire_counter`

`q_fire_counter` requires exactly 3. On completion it:
- fires a screen flash
- schedules dialogue
- killtargets `q_body_blocker`
- resets on completion (spawnflag 2)

Pattern:

`3 MATCHED ITEM USES -> COUNTER(3) -> FEEDBACK + REMOVE BLOCKER`

### D. Body interaction unlocks weapon energy

A fire-damage-style `func_button` associated with the body:
- swaps frozen/thawed body state
- moves/removes snow
- fires `q_wep_energy_collect`

The energy interaction was initially inactive. When armed and collected, it:
- toggles the energy model
- reveals/opens cart-box state
- changes cart state
- arms `q_wep_cart_interact`
- killtargets the closed cart-box representation

### E. Cart -> assembly -> delayed weapon reward

`q_wep_cart_interact`:
- changes cart state
- fires cart collection
- arms `q_wep_assembly_interact`

`q_wep_assembly_interact`:
- reveals assembled weapon model
- reveals lightning/sprite effect
- screen flashes
- fires `q_wep_obtain_delay`

`q_wep_obtain_delay` waits **2.5 seconds**, then enables `q_wep_obtain`.

`q_wep_obtain` is a zero-cost `buy_weapon` reward. Its cleanup path removes assembly/reward presentation and also participates in a later round-delayed continuation.

Pattern:

`PARTS -> TRANSFORMATION -> ENERGY -> CONTAINER -> CART -> ASSEMBLY -> VFX -> DELAY -> FREE WEAPON REWARD`

This is a complete buildable/wonder-weapon style pipeline composed from generic entities.

## Post-weapon continuation -> spirit -> world transformation

The weapon cleanup group includes a relay with a **2-round delay** that:
- toggles `q_spirit`
- arms `q_spirit_interact`
- plays a reveal cue

When the spirit interaction is used it fans out to:
- `q_sky_change_wait`
- `q_sky_change_flash`
- `q_spirit`
- `q_spirit_final`

The sky-change relay then:
- changes sky state
- killtargets `snow_ents`

Parallel targets trigger:
- screen/audio feedback
- a final voice cue

Pattern:

`CLAIM REWARD -> WAIT 2 ROUNDS -> REVEAL NEW INTERACTION -> INTERACT -> GLOBAL ENVIRONMENT TRANSFORMATION`

This is a strong example of **a reward not being the end of the quest**, but instead unlocking a later world-state phase.

## Snowman side quest

Five separate `trigger_interact` entities represent:
- snow part 1
- coal
- carrot
- snow part 2
- snow part 3

Each:
- plays a chime
- increments `sq_snowman_counter`
- killtargets/removes its own visible part

`sq_snowman_counter` goal = **5**. Completion arms `sq_snowman_trigger`.

The final interaction:
- reveals/completes the full snowman
- plays a dedicated song
- fires `sq_snowman_dropper`

Three relays sharing `sq_snowman_dropper` stagger rewards at roughly:
- 2 s
- 3 s
- 4 s

Those targets are `spawn_pu` power-up drops.

Pattern:

`COLLECT 5 PARTS -> ARM BUILD INTERACTION -> BUILD -> MUSIC -> STAGGERED 3-REWARD DROP`

This is a textbook data-driven buildable side quest.

## Three-interact song side quest

Three ordinary `trigger_interact` entities all target `sq_song_counter`.

`sq_song_counter`:
- goal = 3
- reset-on-complete
- fires `sq_song_trigger`

`sq_song_trigger` is `game_songplay`.

Pattern:

`3 SECRETS -> RESETTABLE COUNTER -> SONG`

## Hidden free-power-up interactions

Three one-shot `func_button` secrets independently reveal/spawn:
- Insta-Kill
- bonus points
- Double Points

Each button targets both:
- a `spawn_pu`
- the corresponding hidden model

Pattern:

`HIDDEN SHOOT/USE TARGET -> VISIBLE FEEDBACK + POWER-UP SPAWN`

## Architectural lessons for Xziel

### 1. One targetname may intentionally have many listeners

The bell quest depends on **multiple counters sharing one targetname**. Xziel's event bus must support deterministic fan-out, not first-match dispatch.

### 2. "Locked" interactions are just dormant nodes

Many quest interactions are authored with `trigger_interact` start-inactive. Progress does not spawn special quest code; it simply arms the next interaction.

### 3. Delays exist at three different timescales

This map uses:
- seconds
- whole rounds
- long seconds-scale waits (90 s)

The QuestGraph needs first-class timers and round gates, not ad-hoc sleeps.

### 4. Visual state and logical state are separate

A pickup often:
- toggles/removes a model
- changes another visual
- increments quest state
- enables another interaction
- schedules voice/audio

These are parallel actions from one node. Do not encode quest progression inside animation/VFX objects.

### 5. Buildables are graph composition, not a special hardcoded feature

The snowman and weapon chains prove that collect/build/reward flows can be represented through:
- dormant interact nodes
- counters
- relays
- visual toggles
- killtarget/removal
- delayed actions
- reward entities

Xziel should preserve that composability while giving creators a safer high-level authoring layer.

## Xziel normalized graph sketches

### Snowman

```
CollectSnow1 --\
CollectSnow2 ---\
CollectSnow3 ----> Counter(5) -> Enable(BuildSnowman)
CollectCoal -----/
CollectCarrot --/

BuildSnowman
  -> Show(CompletedSnowman)
  -> PlayMusic
  -> Delay(2s) -> RewardDrop1
  -> Delay(3s) -> RewardDrop2
  -> Delay(4s) -> RewardDrop3
```

### Weapon

```
CollectFrame
 -> DelayRounds(1)
 -> Reveal(Scarf, Glasses, Toy)

CollectScarf   -> Enable(PlaceScarf)
CollectGlasses -> Enable(PlaceGlasses)
CollectToy     -> Enable(PlaceToy)

PlaceScarf   --\
PlaceGlasses ---> Counter(3)
PlaceToy     --/
 CounterComplete
   -> Flash
   -> Dialogue
   -> Remove(BodyBlocker)

BodyEvent
 -> Enable(CollectEnergy)

CollectEnergy
 -> Open(CartBox)
 -> Enable(CollectCart)

CollectCart
 -> Enable(AssembleWeapon)

AssembleWeapon
 -> Show(Weapon)
 -> VFX
 -> Delay(2.5s)
 -> Enable(ClaimWeapon)

ClaimWeapon
 -> RewardWeapon
 -> Cleanup
 -> DelayRounds(2)
 -> Reveal/Enable(Spirit)

SpiritInteract
 -> ChangeSky
 -> Remove(SnowWorldState)
 -> Flash/Music
 -> FinalVoice
```

### Bell / key / boiler

```
Power
 -> ChangeGramophoneState
 -> Enable(GramophoneInteract)

GramophoneInteract
 -> Feedback
 -> DelayRounds(1)
 -> Remove(BellBlockers)

BellPresses -> ParallelStageCounters(1..7)
Stage7
 -> Delayed feedback
 -> Delay(90s)
 -> Enable(Drawer)

Drawer
 -> Open
 -> Delay(.25s) -> Reveal(Key)
 -> Delay(1.5s) -> Enable(KeyPickup)

KeyPickup
 -> Remove(KeyModel)
 -> Enable(BoilerDoorInteract)

BoilerDoorInteract
 -> OpenBoilerDoor
```

