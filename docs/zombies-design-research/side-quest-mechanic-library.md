# Side Quest & Minigame Mechanic Library

Updated: 2026-09-20

Purpose: turn optional Call of Duty Zombies secrets into reusable **mechanic families** for original Xziel maps. These are design abstractions, not copied content.

## 1. Hidden reward room / teleport event

Proven examples:
- Die Maschine: hidden-orb sequence after Pack-a-Punch leads to a dancing-zombie reward event.
- Mauer der Toten: six bunny parts lead to Mister Peeks' nightclub, combat waves and a reward choice.

Reusable Xziel pattern:
1. Scatter 4–8 themed objects.
2. Each pickup has strong audio/visual confirmation.
3. Completing the set opens an optional pocket arena.
4. Arena lasts 2–4 short waves or one minigame.
5. Player chooses one of several rewards.
6. Event can optionally refresh after N rounds with reduced rewards.

Why it works: scavenging gets an immediate payoff and collectibles become gameplay rather than checklist filler.

## 2. Delivery / errand minigame

Forsaken's Pizza Delivery is the key example: enter a hidden shop, take orders to several locations, receive escalating rewards and potentially a rare weapon.

Xziel adaptation:
- carry food, medicine, batteries, ammunition or ritual packages;
- route crosses active combat spaces;
- optional timer controls bonus tier;
- carried object can affect movement or weapon handling;
- each stop rewards immediately;
- finishing the set awards a jackpot.

## 3. Bartender / service minigame

Citadelle des Morts hides bottles, asks the player to identify/serve correct drinks, and rewards a free perk.

Xziel variants:
- apothecary;
- occult bar;
- field medic;
- cursed kitchen;
- ammunition workshop.

Wrong answers should cause a funny or temporary penalty rather than silently destroy the run.

## 4. Hidden animal / collectible hunt

Examples:
- Kowakujō toy mice.
- Citadelle Rat King.
- teddy bear, skull, bottle and headphone song hunts throughout Zombies.

Xziel rule:
Spawn a subset such as 5 of 8 locations each match; use a subtle proximity cue; optionally expose the final one through a perception perk. Required Main Quests should not depend on microscopic pixel hunting.

## 5. Parkour / movement trial

Kowakujō uses a timed lava-platform course for a free Ray Gun reward. Modern maps increasingly use grapple, wall movement and movement puzzles.

Xziel is especially suited for this because our movement set can include:
- sprint;
- slide;
- dolphin dive;
- mantle;
- wall jump;
- grapple.

Pattern:
1. Activate the course.
2. Checkpoints add time.
3. Failure resets only the course.
4. Medal tiers improve rewards.
5. Co-op records individual success instead of forcing every player to finish.

## 6. Performance / rhythm minigame

Rex Infernus includes an optional cassette-driven dance minigame with performance-scaled rewards.

Xziel pattern:
- activate music source;
- controlled arena;
- rhythm/directional/timing inputs;
- score grade controls loot;
- co-op vote to begin;
- mastery cosmetic or calling-card-style reward.

Touchscreens are naturally suited to rhythm/timing interactions.

## 7. Treasure hunt with curse/reward tradeoff

Terminus' Cursed Talisman chains a treasure map, island search, special-enemy fights, coin recovery and a final survival condition. The reward improves economy but introduces a downside when hit.

Xziel lesson:
Side rewards can **alter** a run rather than merely make it stronger.

Example original relic:
Blood Coin
- +25% essence from kills;
- lose 8% stored essence when hit;
- optional cleansing shrine trades away most of the bonus.

## 8. Time-trial unlock tree

Gorod Krovi rewards increasingly strong melee weapons for beating round/time marks.

Xziel pattern:
- Round 5 target → bronze reward.
- Round 10 → silver.
- Round 15 → gold.
- Round 20 → relic version.

This adds speedrun gameplay inside normal survival. Challenge time must use authoritative simulation time rather than device wall clock.

## 9. Enemy-mastery unlocks

Gorod Krovi's Mangler/Valkyrie helmet requirements and WWII's secret-character challenges reward learning enemy behavior.

Xziel feats:
- destroy armor before kill;
- disarm special attack;
- kill during charge;
- dodge attack N times;
- kill with the enemy's own hazard.

Rewards:
- enemy mask;
- resistance;
- finisher;
- cosmetic armor;
- codex entry.

## 10. Companion favors

Mauer's Klaus is not merely a quest key. He fights, revives, breaks objects, opens routes and performs special interactions.

Every Xziel companion should ideally have:
- combat behavior;
- one world/traversal ability;
- one rescue ability;
- one quest interaction;
- optional upgrade route.

Candidates:
- drone;
- cursed dog;
- mechanical raven;
- survivor NPC;
- summoned spirit.

## 11. Build + upgrade + mastery

Examples include Mob's Golden Spork, BO3 elemental weapons, Dead of the Night's Stake Knife / Savage Impaler, and Frozen Dawn's Raven's Claw → Raven's Eye.

Use three depths:
1. Acquire — useful immediately.
2. Upgrade — new behavior.
3. Mastery — optional hidden modifier.

Original example:
Cursed revolver → ricochet rounds → headshots mark targets → mastery makes marked deaths summon attacking ravens.

## 12. Hidden songs as exploration grammar

The classic pattern is three themed objects, any order, subtle confirmation, one-song activation.

Xziel can reuse the same infrastructure for:
- secret soundtrack;
- ambient horror tracks;
- developer commentary;
- lore episodes;
- jukebox unlocks.

## 13. Hidden power-up targets

Maps repeatedly hide one-use Max Ammo, Nuke, Double Points, Full Power, Fire Sale and perk rewards.

Good target types:
- obscure sightline;
- destructible prop;
- prone/crouch angle;
- ricochet;
- grenade throw;
- sniper target;
- movement route.

Important: hidden emergency resources are especially useful because knowledgeable players can save them for ritual/boss preparation.

## 14. Randomized evidence puzzle

Kowakujō's murder investigation is an especially useful modern example: the player gathers evidence, identifies the correct suspect/tool/place combination and converts that deduction into a final input.

Xziel data model:
- PuzzleSeed
- EvidenceSet
- CandidateSet
- Constraint list
- Solution

Every generated match must be unit-tested to guarantee exactly one valid solution.

## 15. Player-choice reward event

Examples include Mauer's reward selection, branching finales and optional cursed objects.

Choices can include:
- weapon;
- perk;
- salvage;
- temporary buff;
- cursed permanent buff.

A choice produces more replay value than one fixed chest.

## 16. Secret challenge characters / cosmetics

WWII Zombies built a huge long-tail system from hidden challenges: high rounds, low-spend runs, headshot restrictions, no-down completion, Main Quest completion, Treasure Zombie parts, solo boss feats and weapon-specific tasks. Many requirements persisted across different sessions.

Xziel should adapt this into a hidden dossier for:
- skins;
- masks;
- emblems;
- announcers;
- finishers;
- safehouse statues.

Do not hide gameplay-critical power behind rare RNG.

## 17. Treasure enemy

WWII uses rare Treasure Zombies that flee/drop currency and collectible fragments.

Xziel improvement:
- non-hostile escape-focused special;
- clear global audio cue;
- breadcrumb drops;
- short but fair despawn timer;
- pity timer;
- no duplicate collectible pieces until the set is complete.

## 18. Super-secret minigame inside a side quest

Infinite Warfare's skull-style puzzles mix symbols, colors, chess logic, paper reconstruction, directional inputs and an arcade-like finale.

The key design lesson is genre change: Zombies can briefly become a logic, arcade or skill game.

Reusable minigames:
- match-3;
- chess/placement logic;
- circuit routing;
- lockpick;
- rhythm;
- memory;
- shooting gallery;
- card logic;
- claw machine;
- RC vehicle.

## 19. Repeatable reward chamber

Some optional events can refresh after a round cooldown.

Suggested reward decay:
- first clear: guaranteed perk + high-tier item;
- second clear: ammo/salvage/temporary buff;
- later clears: score or small resource drops.

This keeps secrets useful without breaking the economy.

## 20. Cursed Mode / relic difficulty modifiers

Black Ops 7 expands voluntary difficulty through Relics: players equip modifier tiers, survive milestone rounds and earn rewards.

Xziel relic ideas:
- faster zombies;
- no armor;
- limited HUD;
- more elites;
- reduced ammo;
- darkness/fog;
- no wall buys;
- friendly fire;
- shared team health;
- cursed special rounds.

Prefer cosmetics, prestige and optional modifiers as rewards rather than mandatory power.

## 21. Recommended side-content budget per original Xziel map

For a medium/large map:

- 1 Main Quest
- 1 Wonder Weapon build
- 1 Wonder Weapon upgrade
- 1 major optional side quest
- 1 traversal/minigame challenge
- 1 free-perk quest
- 1 free-weapon quest
- 1 cursed risk/reward relic
- 1 collectible set
- 1 hidden song
- 6–10 hidden power-up targets
- 3–5 enemy mastery challenges
- 1 map-specific cosmetic unlock
- 1 Super Quest token/relic
- 3–6 lore/intel objects

That is enough density for discovery without making every wall interactive.

## 22. Side-quest runtime primitives

Suggested components:

- CollectibleSetComponent
- TimedChallengeComponent
- DeliveryRouteComponent
- RewardChoiceComponent
- HiddenTargetComponent
- MinigamePortalComponent
- CompanionCommandComponent
- EvidencePuzzleComponent
- ChallengeTrackerComponent
- CursedModifierComponent
- TreasureEnemyComponent
- CooldownEventComponent
- TraversalCourseComponent
- PerformanceScoreComponent

Every component must support:
- solo;
- co-op;
- late join;
- reconnect;
- save/load;
- deterministic random seeds;
- server authority;
- duplicate-event protection.

## 23. Keep this rule

The best optional Easter eggs do at least one of three things:

1. **Teach the map.**
2. **Change the run.**
3. **Give the player a story to tell.**

If a secret does none of those, it is probably clutter.

## 24. Challenge-board reward ladder

Origins' Rituals of the Ancients board is a useful early example: normal play feeds visible challenges, and completion pays out escalating utility such as Double Tap, Pack-a-Punched weapon rewards, Max Ammo and the One Inch Punch.

Xziel pattern:
- show 3–4 challenges at match start;
- use different categories: movement, accuracy, economy, special enemy;
- claim rewards physically at a board/shrine;
- each completed tier visually transforms the board;
- final tier may unlock one additional perk slot rather than a flat damage bonus.

## 25. Perk-slot expansion as side progression

Origins combines Golden Shovel progression, Zombie Blood and hidden dig spots to award Empty Perk Bottles, letting experienced players exceed the normal perk cap.

Xziel lesson:
A side quest can expand a **system limit** rather than give an item.

Possible rewards:
- +1 perk slot;
- +1 equipment reserve;
- +1 relic slot for current match;
- additional armor repair capacity;
- companion upgrade slot.

Cap these rewards so a completed side quest feels strong but does not erase resource decisions.

## 26. World-state modifier as reward

Shangri-La's Focusing Stone and Moon's completed Grand Scheme can leave players with all perks for the rest of the match. The important design idea is that finishing a major quest can visibly change the continued-survival state.

Xziel option:
After a Main Quest, offer:
- end match and play ending;
- or continue in "Aftermath Survival."

Aftermath can alter:
- sky/weather;
- enemy composition;
- perk cap;
- music;
- ambient dialogue;
- special round;
- boss roaming behavior.

That turns completion into the start of a second survival phase.

## 27. Utility-disruption elite

Mob of the Dead's Brutus can disable perk machines, Mystery Box, workbenches and traps until dealt with.

Xziel pattern:
Create an elite that attacks **player infrastructure**, not just player HP.

Targets:
- perk machine;
- ammo crate;
- trap switch;
- generator;
- crafting bench;
- fast-travel anchor.

Counterplay:
- clear audio cue when a utility is targeted;
- visible sabotage animation;
- repair cost or short repair minigame;
- weak point that rewards learning the enemy.

This creates strategic urgency without simply increasing enemy health.

## 28. Masks / wearable run modifiers

Revelations uses earned masks/hats tied to enemy interactions; Gorod Krovi uses helmets/wings for resistances and travel benefits; Rex Infernus extends the idea with a wearable mask whose passive can affect nearby enemies.

Xziel should support a single in-match wearable slot:
- mask;
- helmet;
- charm;
- cursed crown;
- goggles;
- amulet.

Wearables can modify one narrow behavior:
- fire resistance;
- explosive resistance;
- faster trap recharge;
- special-enemy damage resistance;
- movement bonus;
- occasional defensive proc.

Avoid stacking many passive wearables at once.

## 29. Free-perk ritual with narrative flavor

IX's Viking funeral gives a free perk after the player reconstructs a burial with themed objects. It is a strong example of a side reward that feels like a story instead of a vending-machine rebate.

Xziel pattern:
- discover a dead NPC / shrine / memorial;
- gather 2–4 contextually meaningful items;
- place them in understandable locations;
- trigger a short environmental payoff;
- award a perk or temporary blessing.

This is ideal for horror storytelling because the side quest can explain who lived/died in the space.

## 30. "First Easter Egg" lesson — low reward can still matter

Der Riese's Fly Trap in World at War is historically important because the reward itself was small: hidden toys, dialogue, achievement. What made it memorable was discovery.

Xziel should preserve some secrets with **no combat advantage at all**:
- ghost apparition;
- developer room;
- alternate radio;
- scary hallucination;
- hidden credits;
- map-history scene;
- joke interaction.

Not every secret needs currency or a gun. Mystery itself is part of the reward.
