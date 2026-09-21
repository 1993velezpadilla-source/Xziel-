# Call of Duty Zombies Quest Design Research

Updated: 2026-09-20

Purpose: preserve a research corpus for **Xziel / ZOMBIESSSSSSS PORTABLE** so future original zombie maps can be designed from proven quest structures instead of guessing.

This is **design research, not an asset-ripping plan**. We study progression, pacing, clue language, item economy, fail states, co-op roles, boss structure, side activities, and reward loops. We do not need Call of Duty code, textures, models, audio, story text, or proprietary puzzle assets to learn from these systems.

## Files

- `cod-zombies-main-quest-compendium.md` — game-by-game/map-by-map quest catalog and normalized completion routes.
- `classic-exact-walkthroughs.md` — dependency-accurate Treyarch quest structures from Black Ops through Black Ops 4, including historical player-count and RNG constraints.
- `non-treyarch-exact-walkthroughs.md` — exact Exo Zombies, Infinite Warfare Zombies and WWII quest structures.
- `cold-war-vanguard-mwz-exact.md` — exact Cold War/Vanguard progression plus MWZ's multi-deployment Acts, Dark Aether relics, portals and persistence model.
- `bo6-bo7-launch-exact.md` — exact Liberty Falls, Terminus, Citadelle des Morts, The Tomb and Ashes of the Damned dependency chains.
- `modern-exact-walkthroughs.md` — exact later BO6/BO7 quest orders, randomized-input rules, retries and boss logic.
- `bo7-cursed-relic-catalog.md` — all 30 BO7 Cursed Relics by map/tier/effect/trial type, including the still-unsolved Wrestler's Belt and reusable modifier-system architecture.
- `modern-side-easter-eggs.md` — exact modern BO6/BO7 optional content: minigames, companions, temporary transformations, traversal trials, wearables, high-round challenges, Survival and Rogue Run.
- `map-side-content-index.md` — map-by-map index of optional systems, hidden rewards, minigames and replay mechanics.
- `side-quest-mechanic-library.md` — reusable side-quest and minigame primitives extracted from successful maps.
- `super-ee-meta-progression.md` — cross-map completion, persistent rewards, Director's Cut/Pact-style lessons and an original Xziel Super Quest model.
- `community-quest-feedback.md` — recurring player praise/frustrations converted into design guardrails.
- `quest-design-patterns.md` — reusable design rules extracted from successful Zombies maps.
- `sources.md` — primary/current references and full-walkthrough indexes.
- `nzp-reference/` — exhaustive pinned NZ:P engine/map interaction corpus plus verified community quest mechanics and source availability.

## What counts as a quest map

Three classes are tracked:

1. **Full Main Quest** — a structured chain that ends in a narrative payoff, boss, extraction, or map-state change.
2. **Objective Story** — progression is explicit/objective-driven but still useful as quest-design research.
3. **Side-quest / survival research** — no true main quest, but the map contains useful hidden systems, mini-games, buildables, songs, unlocks, or secret rewards.

## Research fields to preserve for every map

- Setup gate: power / Pack-a-Punch / map traversal.
- Discovery language: audio, symbols, environmental clues, NPC dialogue, UI objectives.
- Required items and their source: fixed, random, crafted, boss drop, challenge reward.
- Parallel vs linear steps.
- Solo/co-op differences and player-count locks.
- Randomized-per-match puzzle inputs.
- Fail conditions and retry behavior.
- Round/time gates.
- Resource pressure: points, ammo, armor, perks, weapon rarity.
- Wonder Weapon role: optional, utility, damage, or hard quest key.
- Mini-game / ritual / escort / defense / memory / code / traversal steps.
- Boss phases and telegraphing.
- Main-quest reward and side-quest rewards.
- Persistent progression: Super EE, modes, operators, calling cards, permanent bonuses.
- What can be adapted into an **original Xziel mechanic** without copying protected content.

## Core rhythm seen repeatedly

**Explore → unlock map systems → discover clue → acquire/construct tool → prove mastery with a challenge → transform/upgrade tool → use it on a new class of puzzle → survive a ritual/defense → commit to a point of no return → boss/finale → persistent reward**

The details change wildly, but this rhythm repeats from Black Ops 1 through Black Ops 7.

## Rules for Xziel quest design

- A player should always understand *what changed* after a successful interaction, even when they do not yet know *why*.
- Cryptic is good; invisible is bad.
- Major quest items need distinct silhouettes, sounds, VFX, and pickup feedback.
- Randomized codes should be readable from the current match, never require blind brute force.
- Solo must get an equivalent mechanic when co-op synchronization is normally required.
- Avoid forcing players to destroy a good run because one obscure interaction was missed many rounds earlier.
- Hard fail states belong mainly at deliberate boss/ritual commits, not during long setup.
- Side quests should overlap naturally with normal survival routes.
- Every map should have at least one “I found this myself” secret and one deeper community-solver layer.
- The boss should test mechanics introduced earlier in the map.
- Persistent rewards make completion matter beyond a cutscene.
- Build quest steps as data/state machines so the engine can support radically different maps.

## Current coverage

The compendium covers:

- World at War foundations and side secrets
- Black Ops
- Black Ops II
- Advanced Warfare — Exo Zombies
- Black Ops III
- Infinite Warfare — Zombies
- WWII — Nazi Zombies
- Black Ops 4
- Black Ops Cold War
- Vanguard
- Modern Warfare III — MWZ
- Black Ops 6
- Black Ops 7 through Season 06 (2026-09-20)
- NZ:P official source-map interaction graphs and mapper/QuakeC quest primitives
- verified NZ:P community-map Easter eggs, secrets, round gates, teleporter chains, collectible counters and known broken quest paths

## Engine target

Quest content should eventually be authored through a generic graph/state-machine layer, not one-off hardcoded scripts.

Suggested runtime concepts:

- `QuestGraph`
- `QuestNode`
- `QuestCondition`
- `QuestAction`
- `QuestItem`
- `QuestSharedState`
- `QuestPlayerState`
- `QuestRandomSeed`
- `QuestCheckpoint`
- `QuestFailurePolicy`
- `QuestReward`
- `QuestTelemetryEvent`

Node types should include:

- interact
- collect
- build
- escort
- defend
- survive
- kill-target
- kill-in-zone
- match-symbol
- sequence-input
- memory
- audio-order
- light-order
- physics/object placement
- traversal/parkour
- timed carry
- multi-player sync
- charge-with-souls
- use-specific-weapon
- transform-item
- boss-phase
- branch-choice
- persistent unlock

The goal is to give Xziel the same **quest-design vocabulary** that made successful Zombies maps memorable while keeping our own maps, story, assets, and mechanics original.
