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
