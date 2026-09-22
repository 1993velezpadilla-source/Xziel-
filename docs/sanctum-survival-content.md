# Sanctum survival content direction

This document defines the first-map content layer that sits on top of Xziel's
reusable round-survival runtime. Mechanics may use familiar survival-game
interaction grammar, but all names, art, audio, animation, lore, models and
wonder weapons are original.

## Player-facing loop

1. Spawn vulnerable with a basic weapon and 500 points.
2. Earn points by fighting and repairing windows.
3. Decide between opening space, buying a dependable wall weapon, gambling on
   the random arsenal, or saving for a perk.
4. Build a run identity with a limited perk set instead of automatically buying
   every upgrade.
5. Recover from bad momentum through rare power-up drops and smart barricade
   play.
6. Reach the weapon-upgrade station and optional secrets without making the
   basic survival loop depend on a long quest.
7. Late rounds become execution and routing tests rather than pure stat checks.

The first ten minutes must contain meaningful choices even for a player who
knows nothing about easter eggs.

## Machine families

### Reliquary Draught
Perk station. A tall brass/iron church reliquary with a small stained-glass
reservoir. Idle state has a low mechanical hum, glass glow and subtle liquid
movement. Purchase rotates an internal seal, fills a small vessel and delivers
one short tactile animation. No soda branding or copied jingles.

Initial effect catalog:
- Martyr's Blood — increases maximum survivability.
- Quick Benediction — faster reload handling.
- Pilgrim's Step — movement/endurance improvement.
- Last Rite — faster revive/recovery utility.
- Choir of Lead — faster follow-up fire.
- Saint's Sight — stronger precision/headshot payoff.
- Threefold Vow — one additional weapon slot.
- Ashen Mantle — reduced self/explosive damage.

Names are provisional localization keys until final narrative review; numeric
effect IDs in the engine stay stable.

### Confessional Arsenal
Random weapon station. The reward is hidden inside a mechanically animated
confessional/reliquary assembly. Interaction starts a brief anticipation cycle,
cycles silhouettes/light/audio, then reveals a physical weapon pickup.

Rules:
- weighted weapon pool;
- round gates;
- explicit wonder-weapon rarity flag;
- deterministic seeded RNG for reproducible challenge/speedrun categories;
- no monetized rerolls in the survival match.

### Wall Imprints
Fixed weapon buys. The wall treatment should look authored into Sanctum:
engraved/chalk/metal silhouette plus a restrained emissive trace, price and
interaction prompt. Weapon model and ammo behavior remain shared engine data.

### Foundry of Absolution
Weapon-upgrade station. A compact bell-foundry/reliquary mechanism rather than a
copy of any existing upgrade machine. Three upgrade tiers are supported by the
runtime. Each tier must have an obvious physical/audio payoff and a gameplay
payoff; upgrades cannot be communicated by HUD color alone.

### Votive Engine
Run-consumable station. The player can bring a small pre-match deck and draw
from it during play. Held inventory is deliberately tiny so consumables are
emergency decisions, not permanent passive power.

Runtime effects already supported:
- grant a temporary power-up;
- random perk;
- all-perk exceptional reward;
- free random-weapon roll;
- free weapon-upgrade transaction;
- temporary veil that makes zombies ignore the player;
- short horde freeze.

## Power-up language

Power-ups are physical world pickups with an unmistakable silhouette, a moving
light/particle treatment, positional loop and collection sting. Every effect
also receives a plain accessibility label in UI.

Current runtime families:
- Ammunition — refill carried weapon ammo.
- Execution Rite — temporary extreme lethality.
- Double Tithe — temporary 2x score.
- Final Toll — clear currently active enemies with a bell-wave presentation.
- Restoration — rebuild every gameplay-authoritative window without awarding
  repair points.
- Open Coffers — temporary purchase discount.
- War Relic — temporary heavy/special weapon opportunity.
- Saint's Favor — random perk grant.
- Second Breath — restore health.

Shipping names remain editable; gameplay enum IDs are the stable contract.

## Barricade quality contract

A barricade is not a floating generic prop.

Each authored window owns:
- a plank PBR material binding;
- a debris PBR material binding;
- a plank mesh-set ID;
- a deterministic visual seed;
- gameplay-authoritative plank count.

For Sanctum, those bindings should come from the church's own wood family when
possible. If no suitable wood exists, create a calibrated companion material
with the same texel density, roughness/specular response, dirt/moisture range
and lighting response as the environment. Mesh variants should alter knots,
chips, warping, nail positions and orientation while preserving collision.

Zombie tear and player rebuild animation must visibly correspond to the actual
plank count. Removed planks become bounded debris, then clean themselves up
outside the critical combat path.

## First wonder weapon direction

Working codename: TOLLKEEPER.

Identity:
- built from a compact bell resonator, old electrical winding and church metal;
- primary shot releases a focused resonance bolt that damages and staggers a
  line of enemies;
- charged shot stores resonance and releases an expanding ring after a short
  readable wind-up;
- the room acoustics, nearby bells and reverb react to the charge/release;
- limited ammo prevents it from replacing normal gunplay;
- acquisition can be either a rare arsenal roll or an optional map-specific
  construction route.

This is a design target, not a commitment to a copied weapon archetype. Final
geometry, animation, sound and behavior must be created for Xziel.

## Replayability and community hooks

- deterministic run seed available to the simulation layer;
- separate categories can later use random seed, fixed seed, no-perk,
  no-random-arsenal and quest-completion rules;
- secret routes must save time or trade safety rather than only add lore;
- no mandatory objective checklist HUD;
- round, purchase and quest events are emitted through GameplayEventQueue so
  splits/stat tracking can be added without changing combat code.

## Mobile-quality presentation target

The first free map is the quality bar for every later map. On supported phones:
- stable frame pacing takes priority over adding unbounded particles;
- authored meshes/PBR materials for hero objects and machines;
- LOD/culling for repeated props;
- 3D positional audio with occlusion and room reverb;
- touch-safe prompts that do not cover the center of the screen;
- short, cancellable interaction animations;
- haptic accents for purchase/reward moments;
- readable silhouettes in dark scenes without excessive bloom;
- no asset may look visually disconnected from the room containing it.

## IP/source rule

Study successful round-survival pacing and interaction design, but do not ship
extracted proprietary models, textures, animations, sounds, music, logos,
voice lines, machine branding or wonder weapons. Third-party assets must have a
license suitable for redistribution/commercial release and provenance should be
kept with the asset pipeline.
