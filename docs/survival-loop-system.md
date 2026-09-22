# Reusable round-survival economy and power systems

This module is the shared gameplay layer for Sanctum and future maps. It deliberately separates game feel from map art so later maps can reuse the same tested runtime while supplying different machines, placements, names, models, audio, VFX and balance.

## Design goals

- Preserve the classic round-survival tension loop: weak opening, meaningful purchases, risk/reward exploration, short relief windows and strong late-run recovery options.
- Support perk-style permanent-for-the-run upgrades, randomized weapon vendors, fixed wall weapons, multi-tier weapon upgrading, preselected consumables, timed power-up drops and map-authored interactions.
- Keep the system deterministic and allocation-free during play. Content is fixed-capacity and authored before the match.
- Expose presentation events rather than hard-code art or sound. Android/Vulkan can attach original high-quality animations, emissive effects, jingles, announcer cues, haptics and particles without contaminating the gameplay core.
- Make optional depth optional. A player can survive by learning movement, weapons and economy; quests and advanced consumables can add mastery without turning basic setup into chores.

## Commercial/IP rule

We can study the pacing and interaction grammar that made famous round-based zombie modes memorable, but shipping content must use original names, models, textures, animations, sounds, music, logos, voice lines and wonder-weapon designs. The reusable runtime therefore uses generic engine concepts rather than branded machine names.

## Implemented foundation

- SurvivalRules for per-map balance.
- Perk catalog with reusable modifier outputs.
- Random weapon pool with round gates, weights and wonder-weapon flags.
- Wall weapon transactions.
- Multi-tier weapon upgrade transactions.
- Consumable deck, three-slot held inventory and machine draw escalation.
- Consumable effects: power-up grant, random/all perks, free random weapon, free upgrade, zombie-ignoring veil and horde freeze.
- Power-up drop lifecycle with deterministic RNG, drop chance, pity counter, cooldown, world lifetime and collection.
- Power-up effects: ammo refill signal, one-hit window, score multiplier, wave clear signal, repair-all signal, discount, heavy weapon window, random perk and full-heal signal.
- InteractionSystem registration for authored machines.
- GameplayEventQueue hooks for audio/VFX/UI presentation.
- Fixed-size storage only; no gameplay-time heap allocation.

## Presentation contract

The renderer/audio layer should make every pickup or purchase feel physical and authored:
- readable silhouette at gameplay distance;
- unique idle animation and emissive language per machine family;
- short anticipation animation before the reward is revealed;
- 3D positional machine hum, mechanical movement and reward sting;
- rarity/power communicated by material response, particles and sound, not only HUD text;
- map-matched PBR materials. Wooden barricade planks should derive their base material family from the same environment texture set or a calibrated companion material so they never look pasted into the scene.

## Next integration slice

1. Author Sanctum station placement from the actual church geometry and navigation data.
2. Connect perk modifiers to PlayerVitals, weapon reload/fire timing, sprint and revive systems.
3. Connect power-up signals to horde clearing, all-window repair, ammo refill and health restore.
4. Add original machine meshes/animation/audio/VFX for Sanctum.
5. Add a map-authored wonder-weapon recipe and one mystery-pool wonder weapon.
6. Add save-independent progression/collection only after the in-match loop is stable.
