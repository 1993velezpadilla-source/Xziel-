# Stained Shade Encounter — Church Ritual Special

Status: gameplay/audio design candidate

## Identity

Stained Shade owns the long church prayer. La Llorona no longer uses the Padre Nuestro/Ave Maria/Gloria sequence.

The prayer is the Stained Shade's manifestation clock. The current V5 target lasts **81.944 seconds** and the encounter follows actual audio EOF instead of a separate visible timer.

## Why this is separate from La Llorona

La Llorona is a social/risk gamble built around her children: she searches, cries "mis hijos", can discover a dead child, and can reward or punish interaction.

Stained Shade is a church ritual built around **confession, stained-glass omens, penance and judgment**. It does not use the child system and it does not drop Fragmento de Misericordia.

## Manifestation

Earliest round: 7.

After the church is unlocked:
- 4% roll near the start of an eligible round;
- 3% mid-round roll;
- 3 full rounds of cooldown after a manifestation;
- preferred positions: altar side, nave shadow, confessional, stained-window bay, bell-tower entry;
- never spawn directly in the player's current view.

She appears intact, begins the complete prayer, and remains for the audio duration unless interaction or damage changes the state.

Ignoring her is safe: at the final Amen she breaks into dim glass motes and disappears.

## The interaction — CONFESS

Within 2.2 m, the player can hold Use for 0.65 s once during the prayer.

There is no percentage display and no explanation of the result.

Her stained-glass pieces and halo carry one subtle dominant omen color. The color changes probabilities but never guarantees an outcome:

### Cyan omen
- 70% Blessing
- 20% Penance
- 10% Judgment

### Amber omen
- 30% Blessing
- 50% Penance
- 20% Judgment

### Magenta omen
- 15% Blessing
- 30% Penance
- 55% Judgment

This lets experienced players learn that the glass matters without turning the encounter into a solved yes/no interaction.

## Blessing

She completes a short response animation, grants one reward, then dissipates.

Starting pool:
- 38% Glass Ward
- 24% Max Ammo
- 18% Carpenter
- 12% Insta-Kill
- 6% Nuke
- 2% map-approved Wonder Weapon

### Glass Ward

A unique Stained Shade reward.

The next otherwise-lethal hit is negated and leaves the player at 1 HP. The ward expires after three rounds and only one may be held per player.

## Penance

The player becomes marked until the prayer reaches the final Amen.

While marked:
- nearby normal zombies gain +10% movement speed;
- the marked player takes +8% damage;
- Stained Shade cannot be interacted with a second time.

If the player is still alive when the prayer ends, Stained Shade grants a stronger reward and dissipates.

Penance success pool:
- 34% Max Ammo
- 24% Insta-Kill
- 18% Carpenter
- 12% Nuke
- 8% Glass Ward
- 4% Wonder Weapon

If the player goes down before the end, the Shade simply vanishes and grants nothing. It does not need another boss transition.

## Judgment / boss

Judgment can happen from the CONFESS roll or immediately if the player attacks the neutral Shade.

The prayer cuts off abruptly.

Boss health:
`max(2200, current_zombie_health * 6.5) * player_scale`

Player scale:
- 1P: 1.00
- 2P: 1.50
- 3P: 1.95
- 4P: 2.35

### Attacks

**Shard Volley**
- 28 damage per hit;
- at most two hits from one cast;
- 4.8 s cooldown;
- stained pieces brighten for 0.55 s before release.

**Halo Burst**
- 48 damage;
- 5.5 m radius;
- 7.5 s cooldown;
- 0.85 s halo telegraph.

**Stained Beam**
- 42 damage on contact;
- 1.4 s sweep;
- 8.5 s cooldown;
- pillars/walls block it.

## Damage-state integration from the build sheet

The supplied Stained Shade design already contains useful gameplay states, so they become the boss degradation language instead of ordinary gore:

- full HP: Intact Shade;
- <=75%: one arm shatters away;
- <=50%: lower half fades and she begins drifting;
- <=25%: headless/torso-drift final phase;
- death: Broken Glass Dissipate.

Actual limb-specific damage can choose left/right variants where available; HP thresholds are the fallback so the visual degradation always happens.

## Boss kill reward

One guaranteed reward:
- 30% Max Ammo
- 24% Carpenter
- 20% Insta-Kill
- 12% Nuke
- 9% Glass Ward
- 5% Wonder Weapon

No Fragmento de Misericordia here. That remains La Llorona's child-story reward.

## Audio

Baseline source: previous V4 prayer.

Current Stained Shade candidate:
`stained_shade_prayer_v5_enchanted_horror`

V5 adds more film-horror enchantment without adding a new white-noise bed:
- two voice-derived whisper shadows;
- reverse pre-echo;
- longer dark chapel reflections;
- low spectral shadow;
- faint pitched stained-glass resonances;
- exact 81.944 s runtime.

V4 stays preserved as rollback.
