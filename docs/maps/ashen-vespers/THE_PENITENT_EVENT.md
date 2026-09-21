# THE PENITENT — Nun Proximity Horror Event

Status: **approved for prototype**
Map: **ASHEN VESPERS**
Internal ID: `event_penitent_nun`

## Core fantasy

A unique nun zombie is sometimes discovered crouched/kneeling low in a corner with her body facing the wall, almost like a punished child. She is not participating in the normal round. She is whispering the complete **Padrenuestro / Our Father** to herself.

There is no quest marker, icon, announcer, minimap ping or obvious tutorial. The player discovers her because of **3D positional audio** and body language.

The desired player reaction is:

> “What the hell is that? Should I touch her? Should I shoot her? What happens if I let her finish?”

The encounter must create dread through uncertainty, not through an unavoidable cheap kill.

## 1. Scheduling

The Penitent is a match event, not a normal enemy spawn.

### First eligibility
- never before round 5
- recommended first-roll window: rounds 6–11
- 35% eligibility roll at the start of an eligible round
- if not selected, roll again next eligible round
- guaranteed by round 12 unless the main quest/boss state blocks it

### Recurrence
Default launch behavior:
- **one full Penitent event per match**
- after completion, very rare non-interactive visual echoes may occur later
- no second full reward-bearing encounter in the same match

This preserves uncertainty between matches and stops farming.

### Conflict rules
Do not start while:
- Bishop encounter active
- mandatory main-quest arena state active
- player team is in last-man revive crisis
- another scripted special round owns the room
- candidate room is currently outside active streamed/collision cells

If blocked, defer rather than discard.

## 2. Spawn anchors

Author 10–14 dedicated Blender empties tagged `penitent_anchor`.

Good candidate zones:
- Z05 North Chapel rear corner
- Z06 South Chapel rear corner
- Z07 Vestry office corner
- Z08 Boiler/service alcove
- Z09 Tower stair landing
- Z10 Ringing Chamber wall
- Z11 Clock Chamber recess
- Z13 Courtyard sheltered corner

Avoid:
- Z00 initial spawn
- exposed center of Nave
- boss arena center
- box/perk interaction overlap
- any corner where player cannot retreat

### Anchor requirements
Every anchor stores:
- zone ID
- facing transform toward actual wall
- crouch/kneel floor height
- minimum player distance when selected
- line-of-sight exclusion cone
- retreat/nav clearance
- audio occlusion group

Selection rules:
1. zone must be currently reachable
2. no player inside 10 m at placement time
3. preferably outside every player's current direct view
4. never use the same anchor on consecutive matches when a deterministic history seed is available
5. choose once; do not teleport her merely because players took too long to find her

## 3. Pose and presentation

Default pose:
- knees tucked/crouched low
- torso leaning toward wall
- head slightly bowed
- hands clasped or scraping lightly at wall/floor
- subtle idle breathing/tremor
- no eye glow visible from behind

She does **not** immediately acknowledge the player.

Small unsettling details:
- fingers move out of rhythm with prayer
- shoulder twitch on selected words
- cloth/habit movement has a delayed secondary motion
- one frame-safe head micro-turn can occur when the player first enters close range, but she returns toward wall
- her shadow may not perfectly match her idle pose during the event

Do not overanimate her. Stillness is part of the fear.

## 4. Proximity / spatial audio

This is an NPC world emitter, not literal player voice chat.

### Audio ranges
- 18 m: barely audible breath/prayer through occlusion
- 10 m: intelligible whisper begins
- 6 m: clear directional whisper
- 3.5 m: intimate close-mic layer + breathing
- <2 m: subtle binaural/behind-ear layer may be added, but keep the true source spatially anchored

Walls/doors attenuate the voice. The player should be able to follow the sound around a corner.

### Placeholder recording

Safe temporary source:
- **NyxLurvig — “Padrenuestro (Our Father prayer in Spanish)”**
- Freesound sound ID: **499653**
- duration: **23.365 s**
- format: FLAC, 44.1 kHz, 16-bit stereo
- license: **CC0**
- URL: https://freesound.org/people/NyxLurvig/sounds/499653/

This recording is a temporary source only. Replace it with Christian's custom performance WAV when available.

### Temporary processing chain
Do not destroy intelligibility:
- convert to mono center source
- slight high-pass around 90–120 Hz
- gentle presence reduction around 2–4 kHz
- pitch down only ~1–2 semitones OR preserve pitch and use formant shift; avoid cartoon demon effect
- slow micro-modulation <1%
- subtle short room early reflections
- longer church tail only on a parallel send
- low reversed-breath swell at selected phrase boundaries
- random 80–180 ms dry/room timing drift on selected words
- volume automation should preserve whispered dynamics

At close range, add a separate breath layer rather than crushing the prayer with distortion.

### Additional placeholder SFX
A useful treatment reference is the Freesound recording:
- klankbeeld — `3 man whisper praying dutch.wav`
- Freesound sound ID: **223804**
- CC BY 4.0

Use as an acoustic/timing reference or temporary layered texture only if attribution requirements are accepted. Spanish CC0 source above is preferred for the actual prayer content.

## 5. Interaction rules

While `PRAYING`, the player has four meaningful choices:

### A. Respect the prayer — do nothing
Stay nearby or leave her alone until the prayer reaches its end.

At the final “Amén”:
1. she stops moving
2. 1.2–2.0 s silence
3. one nearby light goes out
4. player hears one breath behind them
5. when they look back, she is gone

Reward appears where she was.

This is the safest outcome, but the player is not told that.

### B. Interact
Interaction prompt is intentionally vague:
- `LISTEN`
or
- `REACH OUT`

Do not say “Start quest”.

On interaction:
- prayer stops instantly, even mid-word
- she remains motionless for 1.5 s
- neck/head begins an unnatural but physically plausible partial turn
- lights in current cell dip
- she whispers a short original line after Christian records VO; placeholder can be breath only
- she transitions into **JUDGEMENT** variant selected by match seed

### C. Shoot / melee her
Immediate high-risk response:
- hit registers, but the first hit cannot instantly erase the event
- prayer hard-stops
- 200–350 ms absolute silence
- violent scream
- she impacts wall or snaps upright
- event enters **WRATH HUNT**

No invulnerability after transformation; once combat begins she becomes a proper authoritative enemy.

### D. Approach too close
Crossing the 1.35 m personal-space threshold does not always trigger.

Seeded reaction:
- 65%: nothing except louder breathing
- 25%: she slowly turns her head but continues praying
- 10%: immediate JUDGEMENT

This prevents players from learning one perfectly safe distance rule.

## 6. Seeded outcome families

Choose the encounter family once when the Penitent spawns. Do not reroll based on player behavior.

### MERCY — 30%
If left undisturbed:
- reward: **Black Rosary Fragment**
- plus one team utility roll: ammo top-up / 750–1250 points / temporary discount
- fragment can participate in the optional Bellwether upgrade side quest

If interacted with:
- she gently reaches toward player
- disappears after a scare beat
- same fragment, reduced utility reward

If shot:
- converts to Wrath combat form; fragment drops only if defeated

### JUDGEMENT — 45%
If left undisturbed:
- she finishes prayer, vanishes
- reward drops
- 5–12 seconds later one harmless false scare triggers elsewhere: footsteps, door knock, silhouette, or bell movement

If interacted with:
- slow turn -> sudden lunge/teleport
- room enters a 25–35 s micro-lockdown
- kill a bounded group plus the Penitent
- successful clear gives an enhanced reward

If shot:
- immediate Wrath Hunt

### DECEPTION — 25%
Designed specifically so veteran players still hesitate.

If left undisturbed:
- normal reward appears after she vanishes
- after player picks it up, she reappears at a different nearby anchor for **one single scare attack**
- this attack can hurt but must not one-shot a full-health player
- she then becomes killable or escapes according to difficulty

If interacted with:
- she falls limp
- after a delay, attacks from a different direction

If shot:
- standard Wrath Hunt

Important fairness rule:
**uncertainty may cost health/position, never arbitrary unavoidable death.**

## 7. WRATH HUNT

The Penitent becomes a unique temporary elite.

Properties:
- very high sprint acceleration
- erratic stops and re-paths
- can use selected nun vault/crawl routes
- short wall-cling/perch presentation only where authored
- never teleports during the actual damaging attack frame
- teleport/reposition only while fully outside player LOS
- emits directional cloth/breath cues before attacking
- cannot spawn infinitely

Duration:
- 30–45 s target
- ends by killing her or surviving a bounded hunt phase depending on variant

Reward for defeating Wrath:
- Black Rosary Fragment
- guaranteed ammo utility
- bonus 1000–1500 team points
- small chance of one extra reward, never a full permanent power spike that makes provoking her mandatory

## 8. Black Rosary Fragment

Purpose:
- makes the scary event rewarding
- optional component for the Bellwether -> FINAL TOLL upgrade
- never required for basic power, survival, base Bellwether build or main boss completion

If the player skips the Penitent event, the main quest remains completable.

The upgrade route can use:
- Black Rosary Fragment
- one Bishop/elite material
- one Midnight-State interaction

## 9. Multiplayer behavior

- event exists once for the whole match
- prayer is a replicated positional emitter
- each player receives distance/occlusion mix locally
- first valid interact owns the interaction transaction
- all players can shoot after transformation
- reward is team-scoped unless item system explicitly supports shared quest inventory
- a disconnected triggering player cannot orphan event state

For co-op terror:
- the nun may be visible to one player before another due to room geometry
- do **not** deliberately desync her authoritative location between clients
- audio can be locally occluded, location cannot

## 10. State machine

```text
DORMANT
  -> SCHEDULED
  -> PLACED_HIDDEN
  -> PRAYING
      -> COMPLETED_UNDISTURBED
      -> PLAYER_INTERACTED
      -> PLAYER_ATTACKED
      -> PERSONAL_SPACE_REACTION

PLAYER_INTERACTED
  -> MERCY_EXIT
  -> JUDGEMENT_LOCKDOWN
  -> DECEPTION_EXIT

PLAYER_ATTACKED
  -> WRATH_TRANSFORM
  -> WRATH_HUNT

PERSONAL_SPACE_REACTION
  -> PRAYING
  -> JUDGEMENT_LOCKDOWN

COMPLETED_UNDISTURBED
  -> REWARD
  -> OPTIONAL_DECEPTION_STING
  -> COMPLETE

WRATH_HUNT
  -> DEFEATED_REWARD
  -> COMPLETE
```

All transitions are server-authoritative and idempotent.

## 11. Horror rules

Do:
- use silence before the scream
- make prayer directionally discoverable
- allow long tension before payoff
- use tiny animation details
- let the player choose whether to interfere
- preserve uncertainty across runs

Do not:
- put a “special zombie nearby” HUD warning
- play loud horror music the instant she spawns
- teleport her in full view
- one-shot the player because they pressed interact
- repeat the exact same scare every game
- make the reward so strong that optimal play always requires provoking her

## 12. Placeholder asset policy

The Spanish CC0 prayer can ship in an internal prototype if downloaded and stored with a small source manifest. Before public release, prefer Christian's custom recorded WAV so the performance belongs to the game.

For any non-CC0 temporary scream/breath assets:
- record the source URL
- license
- creator
- modification notes
- replace before release when necessary

No audio ripped from commercial horror games or Call of Duty.

## 13. Blender markers to add

```text
PENITENT_Z05_A
PENITENT_Z05_B
PENITENT_Z06_A
PENITENT_Z07_A
PENITENT_Z07_B
PENITENT_Z08_A
PENITENT_Z09_A
PENITENT_Z10_A
PENITENT_Z11_A
PENITENT_Z13_A
```

Each marker should carry:
- `xziel_kind = "penitent_anchor"`
- `zone_id`
- `wall_forward`
- `min_spawn_player_distance = 10.0`
- `personal_space_radius = 1.35`
- `clear_retreat_radius >= 2.5`

Exact transforms are authored after the semantic room pass against the real scan.

## 14. Validation

1. Penitent never blocks round completion while praying.
2. She cannot spawn inside visible player frustum when a hidden valid anchor exists.
3. Every anchor has valid floor/capsule clearance.
4. Prayer emitter attenuates/occludes correctly through doors and floors.
5. Shooting her transitions once; duplicate hits cannot double-start Wrath.
6. Interaction and gunshot in same network tick resolves deterministically.
7. Leaving her alone always reaches completion.
8. Reward cannot duplicate.
9. No seeded outcome can one-shot a full-health player without a telegraphed combat attack.
10. Boss/main quest defers event cleanly.
11. Disconnect during event cannot soft-lock.
12. Reset destroys emitter, reward and Penitent entity.
13. Event works with gore disabled.
14. Mobile build keeps prayer/breath audio voices inside active-voice budget.
15. Repeated matches do not always select the same anchor/outcome.
