# Official Map Secret / Quest Micro-Case Studies

Pinned source: `nzp-team/assets@c8135a66e00bb64577912fbf792f8fef7f47658e`

These examples are reconstructed from source entity graphs, not from walkthrough prose.

## Hangar — 5-object song + 3-object hidden unlock

### Song

Five `teddy_spawn` entities all target `mus_egg`.

`game_counter targetname=mus_egg`:
- goal: 5
- one-shot on completion
- target: `mus_play`
- completion message: "You Have Found Us All!"

`game_songplay targetname=mus_play` then plays the map song.

Normalized pattern:

`5 ShootableSecrets -> Counter(5) -> Song`

### Three hidden perk-bottle interactions

Three hidden `place_model` perk bottles are named:
- `bot1`
- `bot2`
- `bot3`

Three `trigger_interact` nodes:
- each killtargets/removes its matched bottle model
- each fires `FlopDoor`

Three one-shot `game_counter` listeners share `targetname=FlopDoor` with goals 1, 2 and 3.

The goal-3 counter:
- killtargets `Floppa`

`Floppa` is a `func_wall`, so completing all three removes a blocker.

The goal-1 and goal-2 counters are used as explicit progress feedback through messages `1/3` and `2/3`; goal 3 reports `3/3`.

Normalized pattern:

`InteractHidden1/2/3 -> remove each collectible -> staged progress feedback -> Counter(3) -> remove world blocker`

This is an excellent source-backed example of a hidden collectible side quest unlocking access without needing a special inventory system.

## Nacht der Untoten (`ndu`) — environmental destruction song

Twenty-one `explosive_barrel` entities all target `song_counter`.

`game_counter targetname=song_counter`:
- goal = 21
- one-shot
- target = `song_target`

`game_songplay targetname=song_target` plays the secret song.

Normalized pattern:

`Destroy 21 environmental objects -> Counter(21) -> Song`

This proves secret counters do not need "collectible" objects. Any damageable entity capable of firing a target can feed the same quest primitive.

## NZP Warehouse — 3 teddies simultaneously unlock song and Pack-a-Punch access

Three `teddy_spawn` entities all target `song_counter`.

The counter:
- goal = 3
- target = `song_play`
- killtarget = `pap_door`

`pap_door` is a `func_wall`.

Therefore the **same completion event**:
1. starts the song
2. removes the Pack-a-Punch blocker

Normalized pattern:

`3 ShootableSecrets -> Counter(3) -> [PlaySong + Remove(PAPBlocker)]`

This is an important design pattern: one quest completion can fan out into both cosmetic and gameplay rewards.

## NZP Warehouse 2 — 3-teddy song plus direct secret interaction

### Song

Three `teddy_spawn` entities -> `song_counter` -> `game_songplay`.

Normalized:

`3 ShootableSecrets -> Counter(3) -> Song`

### Separate secret interaction

A `trigger_interact`:
- fires `comms_wait`
- killtargets `secret`

`secret` is a `func_wall`, so it is removed immediately.

`comms_wait` is a delayed relay:
- delay = 3 seconds
- target = `comms_mission_complete`

That target is an ambient radio/message sequence.

Normalized:

`SecretInteract -> RemoveBlocker + Delay(3s) -> MissionCompleteAudio`

Again, logical unlock and presentation feedback are separate actions.

## Bunker Defense — mixed secret types

### Simple teddy song

One `teddy_spawn` targets `Counter`.

`game_counter targetname=Counter`:
- goal = 1
- one-shot
- target = `Song`

`game_songplay targetname=Song` plays the track.

### Other teddy interactions

Other teddies in the same map use alternate mode/spawnflags and target labels such as `Jug` and `PaP`, demonstrating that teddy entities are not intrinsically "song collectibles"; their behavior depends on their target graph.

### Finale

The map also contains a `func_ending` priced at 25,000 points.

This combines conventional survival progression with secret triggers and a global purchasable finale.

## Reusable conclusions

1. **The event source is interchangeable.** Teddy, barrel, button, interaction volume, power switch and door can all feed the same counter/relay vocabulary.
2. **Counters can drive both progress feedback and final unlocks.** Hangar uses parallel threshold counters 1/2/3, while other maps use a single final threshold.
3. **One completion can produce multiple rewards.** Warehouse couples song playback and PAP access in one counter completion.
4. **World unlocks are often blocker removal.** `killtarget` against `func_wall` is a recurring "unlock secret area" technique.
5. **Feedback belongs on parallel branches.** Audio/messages do not have to be the state machine itself.
6. **Quest content should be object-agnostic.** Xziel should expose `DamageableEventSource`, `InteractEventSource`, `Counter`, `RemoveWorldBlocker`, and `Reward` rather than hardcoding "teddy EE".

