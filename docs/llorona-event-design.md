# La Llorona Encounter — Xziel Church Map

Status: gameplay/audio implementation specification

## Core idea

La Llorona is a rare supernatural encounter, not part of the ordinary zombie population. Two persistent child entities, Hijo A and Hijo B, can be hidden inside normal waves. The player should initially be unsure that a special event exists.

## Encounter states

1. DORMANT — no visible Llorona. Children may be eligible to spawn.
2. PENITENT — La Llorona appears around the church crouched or kneeling, facing away. She whispers the Padre Nuestro and is non-hostile.
3. WAILING — separate neutral apparition. She cries and calls "mis hijos" from a distant point and disappears if approached.
4. SEARCHING — after a child dies, later appearances can path toward that child's death marker.
5. DISCOVERY — she sees a child death marker within 6 m. Prayer/wailing stops, she freezes, then the rage cue plays.
6. RAGE — boss health bar appears and she becomes fully hostile.
7. BANISHED — defeated or resolved by the mercy Easter egg.

## The two children

### Visual design

They are fictional undead/apparition children, not generic small zombies.

- Roughly 75–80% of an adult zombie's height.
- Old church/colonial clothing; wet dirty fabric, pale skin, clouded eyes.
- No exaggerated gore required.
- Hijo A: darker clothing and a subtle red thread/bracelet.
- Hijo B: pale night garment and a small wooden rosary/medallion.
- Slightly irregular gait, while preserving the normal zombie navigation envelope.
- Very quiet wet/cloth footsteps underneath ordinary zombie foley.

### Hidden-wave behavior

- Earliest eligibility: round 6.
- Each child can spawn only once per match unless the event is reset.
- Per eligible round: 9% chance to inject one child into an ordinary zombie spawn slot.
- Never inject both children in the same round.
- No special HUD, outline, name, or music.
- Combat behavior stays close to a normal zombie so the kill can happen accidentally.

When killed, create a cheap persistent child_death_marker at the death position. The visual corpse may be simplified or cleaned later, but gameplay keeps the marker.

## Random Llorona appearances

After the church zone is unlocked:

- PENITENT: 6% check at the beginning of an eligible round.
- WAILING: 5% check 30–90 seconds into an active round.
- Cooldown after a manifestation: 2 complete rounds.
- Never spawn directly inside the player's current view.
- Preferred points: altar side rooms, confessional corridor, cemetery edge, bell-tower approach, rear church corner.
- Minimum initial player distance: 12 m.
- PENITENT disappears if the player remains within 2.5 m for 2 seconds, attacks her, or breaks safety bounds.

Before RAGE she has no visible health bar.

## Discovery logic

If a child has died:

- SEARCHING manifestations choose the closest child_death_marker with 60% probability.
- She walks toward it instead of teleporting directly onto it.
- Trigger DISCOVERY only at <= 6 m, with line of sight, and marker age >= 2 s.

Sequence:
1. Stop prayer or wail.
2. Freeze locomotion for 0.65 s.
3. Turn head/upper torso toward the corpse.
4. Play llorona_rage_trigger.
5. After 1.25 s, snap full body toward the nearest living player.
6. Reveal boss HUD and enter RAGE.

If both children are dead, later voice work should use a stronger plural cue and increase Phase 2 pressure.

## Boss balance starting point

Scale from the current normal zombie health:

llorona_max_health = max(2500, current_zombie_health * 8) * player_scale

Player scale:
- 1 player: 1.00
- 2 players: 1.55
- 3 players: 2.00
- 4 players: 2.45

### Attacks

Claw / grab swipe:
- 45 damage.
- 1.15 s minimum repeat.
- Small forward step; no teleport hit.

Rage lunge:
- 70 damage direct hit.
- 7 m maximum launch distance.
- 5.5 s cooldown.
- Loud inhale telegraph.

Wail pulse:
- 20 damage maximum at close range, falling to 0 by 12 m.
- 0.65 s aim/vision distortion and directional audio shock.
- 9 s cooldown.
- Blocked by substantial world geometry.

Phase 2 below 40% HP:
- movement +12%;
- lunge cooldown 4.3 s;
- wail can briefly make nearby normal zombies sprint;
- no additional raw melee damage.

## Boss HUD

Title: LA LLORONA

- Health bar appears only after DISCOVERY.
- Desaturated white/gray treatment with an unstable pulse.
- Brief flicker before Wail Pulse.
- No numeric HP in the default HUD.

## Audio pipeline

Workflow: .github/workflows/elevenlabs-llorona.yml

Generator: tools/audio/generate_llorona_elevenlabs.py

Variants:
- llorona_prayer — full Padre Nuestro, whispered/crying but phrased continuously.
- llorona_mis_hijos — grieving "mis hijos" behavior using an original designed voice.
- llorona_rage_trigger — transition into RAGE after discovering a child death marker.

Each export includes raw MP3, dry 48 kHz / 24-bit WAV, processed 48 kHz / 24-bit WAV, and 48 kHz Opus OGG.

The voice is designed from a descriptive prompt. Do not clone or redistribute a specific viral recording or an unidentified performer's voice.

## Mercy Easter egg

Once a child has been seen or killed, three church objects can appear:
1. broken rosary beads;
2. a child's shoe;
3. a torn baptism record/page.

Returning all three to a memorial point near the altar before La Llorona discovers a corpse triggers RECONCILIATION instead of RAGE.

Result:
- both child spirits appear briefly;
- La Llorona stops crying;
- all three vanish;
- players receive a modest one-time reward such as an ammo refill or map-specific utility.

No on-screen quest checklist. Environmental clues should carry the discovery.


## Corpse discovery hint

The mercy route gets one subtle assist so players understand that the corpse matters without turning the event into a checklist.

Trigger conditions:
- first time each player deliberately looks at a dead child;
- player is within 4.5 m;
- unobstructed line of sight;
- crosshair/look direction remains on the corpse for at least 0.35 s;
- only while RECONCILIATION is still possible;
- shown once per player per match.

Display time: 4.25 s.

Spanish:
> Antes que la madre lo halle, reúne sus tres reliquias en el altar.

English:
> Before the mother finds him, gather his three relics at the altar.

Presentation:
- one short centered/bottom-center line;
- aged serif / old-church inscription treatment when the custom HUD skin is available;
- warm faded parchment-white rather than bright quest yellow;
- quick fade in and out;
- no icon, waypoint, objective counter, item names, or quest log entry;
- gameplay continues normally while it is visible.

Language comes from the phone/OS language. Android passes `Locale.getDefault().getLanguage()` into the runtime cvar `xziel_language`. Unsupported languages fall back to English. The localization table lives at `config/llorona_localization.json`.


## Prayer-timed manifestation window

La Llorona's neutral/penitent manifestation is now hard-bound to the prayer audio itself.

Authoritative duration: **82.0 seconds**.

The prayer is the event clock. The player does not get a separate timer UI.

### If no child has spawned or died yet

La Llorona may still manifest in PENITENT form before either child has appeared in the match.

For the entire 82-second prayer:
- the player may approach, observe, ignore her, or receive one of the randomized neutral interaction behaviors;
- any optional interaction prompt exists only while the prayer is still playing;
- there is no quest marker, countdown, objective text, or explanation that reveals the child mechanic;
- only one neutral behavior roll is selected for that manifestation.

At the final Amen:
- all neutral interaction closes immediately;
- La Llorona finishes the final pose/animation;
- she fades/despawns;
- nothing is punished merely because the player ignored her;
- the encounter can roll again on a later eligible manifestation according to normal cooldown/random rules.

### Random neutral behaviors

One behavior is chosen per manifestation:

- **prayer_only — 35%**: she never acknowledges the player and simply completes the prayer.
- **proximity_reaction — 25%**: close approach causes a subtle body/shoulder reaction but no direct interaction.
- **optional_use_interaction — 25%**: within 2.4 m a minimal Use prompt may appear; it can resolve only once and never reveals the Easter egg solution.
- **silent_head_turn — 15%**: at a random point during the prayer she slowly turns her head toward the nearby player, then resumes/holds the penitential pose.

The behavior roll is intentionally hidden so players cannot assume every apparition works the same way.

### If she finds a dead child during the prayer

A child discovery overrides the 82-second timer immediately.

The exact moment line-of-sight discovery conditions succeed:
1. stop the prayer audio mid-word/mid-sentence rather than fading it politely;
2. cancel any neutral interaction prompt;
3. freeze La Llorona for the DISCOVERY beat;
4. redirect her attention to the child corpse;
5. play the rage-trigger voice cue;
6. enter RAGE and reveal the boss HUD.

Once DISCOVERY happens, the prayer timer is discarded. She does **not** disappear at the original 82-second endpoint.

### Audio asset

Current selected prayer treatment:
- source performance: user-selected Spanish prayer recording;
- game timing target: 82.0 seconds;
- dark/enchantment treatment: church reverb, reverse/pre-echo, restrained ghost doubles, low drone and atmospheric air;
- package target: `llorona_prayer_enchanted_v2.ogg`;
- master target: 48 kHz stereo / 24-bit WAV.

The spoken content includes Padre Nuestro, Ave Maria, Gloria and the closing Fatima prayer. The player experiences the entire sequence as one uninterrupted manifestation unless a dead-child discovery interrupts it.


## Hidden fate gamble

Every neutral manifestation now rolls one hidden fate at spawn time. The player never sees the roll.

Possible hidden fates:
- **OFFERING — 48%**
- **HOSTILE_TEST — 52%**

The player choice is only whether to interact before the prayer ends.

### Seen tracking

Ignoring La Llorona matters only if she actually registers the player during that manifestation.

A player becomes SEEN when all of these are true:
- within 18 m;
- unobstructed line of sight;
- inside an 85-degree view cone;
- visibility is continuous for at least 0.30 s.

Once SEEN is set, it remains true until that manifestation ends.

If the player is never SEEN, doing nothing is always safe.

### Interaction matrix

If the player interacts during the prayer window:

- hidden fate = OFFERING:
  - she grants one randomized boon;
  - no child clue is revealed;
  - no explanation is shown;
  - she departs without Rage.

- hidden fate = HOSTILE_TEST:
  - the interaction immediately fails;
  - neutral audio/interaction is cancelled;
  - she enters RAGE.

If the player does not interact before the last Amen:

- player never SEEN:
  - she departs neutrally regardless of hidden fate.

- player SEEN + hidden fate = OFFERING:
  - she interprets the refusal as rejection/ingratitude;
  - at prayer end she enters RAGE.

- player SEEN + hidden fate = HOSTILE_TEST:
  - ignoring her was unknowingly the correct choice;
  - she departs neutrally.

This creates the intended uncertainty: interaction can save the player or trigger the boss, and ignoring her can also save the player or trigger the boss.

### Boon pool

When OFFERING + successful interaction occurs, grant exactly one weighted random boon:

- 30% — **Ammo Blessing**: refill the current weapon and part of reserve ammo.
- 22% — **Temporary Damage**: +20% weapon damage for 45 s.
- 20% — **Spirit Armor**: absorbs the next two ordinary zombie hits; expires after 75 s.
- 16% — **Haste**: +10% movement and reload speed for 40 s.
- 12% — **Mercy Points**: small points grant.

The boon is identified only after it has been granted. No preview lets the player know whether interaction is worth the risk.

### Dead-child priority

Dead-child discovery always has higher priority than the hidden fate system.

If La Llorona discovers a dead child at any point:
- prayer stops immediately;
- any pending boon is cancelled;
- any neutral interaction is cancelled;
- DISCOVERY -> RAGE occurs regardless of OFFERING/HOSTILE_TEST.

A dead child does not automatically force Rage merely because it exists somewhere in the map. She still has to find it.

## Audio candidate policy

The previous enchanted prayer is frozen and must remain available as a rollback reference:

- **V2 / llorona_prayer_enchanted_v2** — LOCKED BASELINE

The new darker experiment is:

- **V3 / llorona_prayer_enchanted_v3_darker** — CURRENT TEST CANDIDATE

V3 keeps the lead voice readable and adds only supporting horror layers:
- extra breath/whisper aura keyed to the spoken voice;
- quiet low spectral shadow behind the lead;
- longer ancient-chapel reflections;
- selected reverse-like pre-echo swells;
- subliminal low-frequency presence;
- intermittent non-verbal breath texture in long pauses.

Do not overwrite V2 when iterating on V3 or later versions.


## Rage kill rewards

La Llorona's kill reward depends on **why** she entered RAGE. This prevents all Rage encounters from feeling identical and preserves the hidden-fate gamble.

### Rejected OFFERING -> Corrupted Offering

This is the premium reward path.

Condition:
- hidden fate was OFFERING;
- La Llorona saw the player;
- the player ignored her until the prayer ended;
- she entered RAGE because she interpreted the rejection as ingratitude;
- the player defeats her.

On death she always drops exactly one **Corrupted Offering** result.

Weighted table:
- 32% — Max Ammo.
- 24% — Carpenter / repair all repairable barriers.
- 18% — Insta-Kill.
- 12% — Nuke.
- 8% — one map-approved Wonder Weapon.
- 6% — Fragmento de Misericordia, the relic substitute.

The table is intentionally weighted by practical match value. Common results are immediately useful round stabilizers; the rare results can materially change the run.

### Smart anti-waste handling

A Corrupted Offering should not become a useless joke roll.

- If Carpenter rolls while all repairable barriers are already effectively full, reroll once into another eligible reward.
- If the selected Wonder Weapon duplicates the exact Wonder Weapon already held by the receiving player, choose another map-approved Wonder Weapon; if none is eligible, fall back to Nuke.
- If Fragmento de Misericordia rolls after the mercy ritual is already complete, convert it into the Wonder Weapon roll.
- Never spawn two Fragmentos de Misericordia in the same match.

### Fragmento de Misericordia

This is not a fourth normal relic and it is not a permanent wildcard inventory slot.

It is a one-use substitute token that can replace **exactly one** missing mercy-ritual relic:
- broken rosary beads;
- child's shoe;
- torn baptism record/page.

Rules:
- consumed when committed at the altar;
- can substitute only one missing slot;
- cannot replace a child corpse/death marker;
- cannot satisfy two missing relics;
- cannot duplicate a relic slot already completed;
- only one can exist/activate per match.

This means a very lucky La Llorona kill can rescue a damaged Easter-egg attempt without trivializing the full ritual.

### HOSTILE_TEST Rage -> Wrath Compensation

If the player interacted and the hidden fate was HOSTILE_TEST, killing her grants a smaller guaranteed combat reward:

- 55% — Max Ammo.
- 30% — Carpenter.
- 15% — Insta-Kill.

No Wonder Weapon or relic substitute on this path.

### Dead-child discovery Rage -> Mourning Cache

If she entered RAGE because she physically discovered a dead child, defeating her grants:

- 50% — Max Ammo.
- 25% — Insta-Kill.
- 15% — Nuke.
- 10% — Fragmento de Misericordia.

This path has a higher relic-substitute chance than rejected OFFERING because it is directly connected to the child storyline, but it does not grant the full premium Wonder Weapon roll by default.

### Player-facing presentation

Do not show percentages or reward tables in-game.

Players should learn over repeated runs that:
- defeating an enraged La Llorona always matters;
- different causes of Rage appear to produce different loot quality;
- rejecting a peaceful OFFERING and surviving the resulting boss fight can produce unusually valuable drops.

The reward object should visually read as supernatural rather than as a normal zombie drop until it resolves into the final reward.


## Fragmento de Misericordia — diminishing drop curve

Fragmento de Misericordia is no longer a one-time-only reward.

Global chance across every eligible La Llorona kill-reward pool:
- before any Fragmento has been granted: **6%**;
- after the first Fragmento: **3%**;
- after the second Fragmento: **1.5%** for the remainder of the match.

The chance only decays after a Fragmento is actually granted.

A player can hold up to two Fragmentos at once. Across the whole match, at most two authentic relic slots may be substituted, guaranteeing that at least one authentic ritual relic is still required.

If another Fragmento roll occurs after the two-slot substitution cap has already been consumed, convert the result into a high-value fallback:
- 55% Nuke;
- 45% eligible Wonder Weapon.

### Child-event probability

Child injection now uses **6% per eligible round**, preserving the hidden-event rarity.

Each individual child still appears at most once per match.

The Fragmento's initial 6% roll and the child 6% roll remain independent. If both systems are eligible in the same round, the natural probability of both 6% rolls succeeding is **0.36%**. No artificial 6% double-event override is used; the simultaneous occurrence stays genuinely exceptional.

### HOSTILE_TEST rewards upgraded

Interacting with La Llorona when her hidden fate is HOSTILE_TEST can still produce premium loot if the player survives and defeats her.

Reward algorithm:
1. first roll the current dynamic Fragmento chance (6% / 3% / 1.5%);
2. if it fails, normalize the non-Fragmento scores and roll exactly one reward;
3. there is never an empty boss-kill result.

HOSTILE_TEST non-Fragmento score weights:
- Max Ammo — 40;
- Carpenter — 27;
- Insta-Kill — 16;
- Nuke — 9;
- Wonder Weapon — 2.

This keeps premium outcomes possible after a trap interaction, but rarer than on the rejected-OFFERING path.

### Rejected OFFERING reward scores

After the dynamic Fragmento roll fails:
- Max Ammo — 32;
- Carpenter — 24;
- Insta-Kill — 18;
- Nuke — 12;
- Wonder Weapon — 8.

### Dead-child discovery reward scores

After the dynamic Fragmento roll fails:
- Max Ammo — 44;
- Insta-Kill — 25;
- Nuke — 15;
- Wonder Weapon — 10.

The same 6/3/1.5 Fragmento curve applies here.

## V4 horror audio candidate

V2 remains the locked rollback baseline.

V3 remains preserved as the previous candidate.

Current candidate:
- **llorona_prayer_enchanted_v4_horror**
- duration: **81.944 s**
- 48 kHz stereo master;
- game OGG derived from the same master.

V4 specifically addresses the audible static/white-noise buildup heard in V3:
- V3 is denoised before new effects are created;
- no generated white-noise layer is added;
- whisper textures are derived from the actual prayer voice;
- one higher spectral whisper and one lower breath-shadow move behind the lead;
- reverse echo creates horror-film pre-verb before phrases;
- the chapel tail is darker and longer;
- a very low, quiet spectral shadow adds supernatural mass without masking consonants;
- final output remains trimmed to exactly 81.944 s so manifestation timing does not drift.

Reproduction script:
`tools/audio/process_llorona_v4_horror.sh`


## Identity split — prayer moved to Stained Shade

The long Padre Nuestro / Ave Maria / Gloria ritual no longer belongs to La Llorona.

New ownership:
- **Stained Shade** owns the full church prayer and its 81.944 s ritual window.
- **La Llorona** owns the "mis hijos / donde estan mis hijos" searching lament.

La Llorona's manifestation lifetime now follows the actual EOF of `llorona_mis_hijos_search_loop`.

During the search loop:
- she wanders between hidden search points;
- if no child has spawned or died, she still behaves like she is searching;
- OFFERING/HOSTILE_TEST interaction remains available while the lament is active;
- if the player never triggers Rage, she disappears when the audio ends;
- if she discovers a dead child, the lament cuts immediately and DISCOVERY -> RAGE takes priority.

The search audio uses repeated variations rather than one identical hard loop so she can sound nearer, farther, left/right, and more desperate across one manifestation.
