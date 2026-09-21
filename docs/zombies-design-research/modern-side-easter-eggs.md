# Modern Side Easter Eggs & Optional Systems — BO6 / BO7

Updated: 2026-09-20

Purpose: preserve the **documented and currently verified optional-content layer** from Black Ops 6 and Black Ops 7. This is separate from the Main Quest files because these maps often hide an entire second game of minigames, companions, collectibles, temporary transformations, traversal trials, free-perk quests, high-round bosses and run-changing rewards.

This is design research. Exact item pins may shift between patches or randomized spawns, so source links remain authoritative for implementation verification. Unknown, disputed and launch-window discoveries are marked as such rather than presented as fact.

---

# BLACK OPS 6

## Liberty Falls — documented optional systems

Current guide coverage: 6 major side Easter eggs plus hidden power-up targets.

### Secret song — three-headphone collectible grammar

- Three Mister Peeks headphones.
- Any-order collection.
- Strong confirmation cue.
- One-time musical reward.

Reusable lesson:
A three-object song chain remains useful because players understand the grammar immediately after seeing it on several maps.

### Free Deadshot skill shot

- A long-range shooting challenge.
- Precision matters; the player is rewarded for clean execution rather than a fetch chain.
- A miss can invalidate the current attempt.

Reusable lesson:
A single high-skill shot can create a memorable reward with almost no scripting overhead.

### Savings & Loan vault

1. Find three environmental notes/fragments.
2. Each exposes two digits.
3. Combine them into the current-match six-digit vault code.
4. Open the bank vault.
5. Use Loot Keys to open safe-deposit boxes for randomized rewards.

Reusable lesson:
**environmental code fragments + repeatable loot keys** create both a one-time discovery puzzle and an ongoing reward sink.

Xziel primitive:
- `CodeFragmentSet`
- `VaultAccess`
- `ConsumableLootKey`

### Aetherella temporary transformation

1. Build/obtain the Jet Gun.
2. Vacuum nine hidden Aetherella figures.
3. The final collectible transforms the player temporarily.
4. While transformed, the player is effectively a powerful alternate combat form with eye-laser attacks.

Strategic detail:
The final figure can be deliberately left uncollected until the player wants the temporary form for a difficult fight.

Reusable lesson:
A collectible hunt can culminate in a **temporary playable transformation**, and expert players can treat the last collectible as a stored resource.

### Liberty Lanes bowling minigame

1. Shoot the hidden shoe targets.
2. The map transports/changes state into the bowling event.
3. Charge/throw bowling balls down zombie-filled lanes.
4. Score determines reward quality.
5. A high threshold grants a mastery/Dark Ops-style recognition.

Reusable lesson:
The best minigames:
- use rules anyone understands immediately;
- convert zombies into game pieces;
- score performance rather than only success/failure;
- give reward tiers.

### Hidden one-use power-up targets

The map hides shootable versions of standard power-ups.

Reusable lesson:
Knowledgeable players can intentionally **bank an emergency resource in the environment** and trigger it only when needed.

---

## Terminus — documented optional systems

Current guide coverage: 5 major side Easter eggs plus several micro-secrets.

### Cursed Talisman treasure hunt

Normalized flow:

1. Obtain the traversal/melee prerequisite.
2. Reveal/read the treasure-map clue.
3. Travel to the marked island/location.
4. Recover the Watch.
5. Burn/defeat the three skeleton encounters across different islands.
6. Recover three Cursed Coins.
7. Travel to the final island.
8. Survive three complete rounds.
9. Claim the Cursed Talisman.

Reward behavior:
- increases Essence gain;
- being hit has a linked economic downside.

Reusable lesson:
A side quest reward can create a **new economic rule** instead of pure power.

### Mega Stuffy companion

1. Collect six stuffed-animal pieces.
2. Assemble them in Living Quarters.
3. The finished companion becomes a flying helper.
4. It attacks enemies.
5. It can assist/revive and provide support utility.

Reusable lesson:
Collectibles feel substantially better when the completed set becomes a **persistent in-match companion**.

### Boat Race

- Hidden start interaction.
- Tactical Raft/boat becomes the minigame vehicle.
- Pass through gates/course markers.
- Time/performance controls rewards.

Reusable lesson:
If a map already has a vehicle, optional content should exploit that vehicle rather than introducing an unrelated arcade screen.

### Cooking/fish interactions

Optional fish/cooking systems can provide temporary effects.

Reusable lesson:
Minor crafting can be a low-stakes discovery layer distinct from the Main Quest.

### Basketball precision reward

A small environment-based skill shot yields Essence/reward.

Reusable lesson:
Not every secret needs a ten-minute chain.

### Void Cannon meteor reward

A map interaction can redirect artillery/large machinery at a world target to produce high-tier loot.

Reusable lesson:
Large scenery systems feel more believable when players can repurpose them.

---

## Citadelle des Morts — documented optional systems

Current guide coverage: 6 major side Easter eggs.

### Bartender minigame

1. Find three hidden liquor bottles.
2. Bottle labels/appearance provide the order clues.
3. Start the Tavern service event.
4. Zombies become customers rather than ordinary combat targets.
5. Serve the correct drinks.
6. Receive a free perk reward.

Reusable lesson:
A side quest can temporarily replace the game's combat verb with a **service/recognition minigame** while keeping zombies in-theme.

### Rat King

1. Find a set of hidden rats.
2. Complete the collection.
3. Trigger the crown/king reward sequence.

Reusable lesson:
Animal/mascot hunts work best when the final reward visibly changes the environment or creates a unique prop, not just a UI counter.

### Raven optional reward branch

An optional Raven interaction branches from the Dark Incantation / elemental progression and can pay a bonus perk.

Reusable lesson:
Main Quest infrastructure can expose optional branches without forcing every player to do them.

### Bell Tower repair/firing sequence

1. Recover/repair the required cannon/bell-tower components.
2. Use the repaired mechanism.
3. Trigger a loot/reward event.

Reusable lesson:
**Repair → operate → payoff** is a strong side-quest grammar because the restored object remains visually meaningful.

### Hidden one-use power-ups

Several standard power-ups are hidden as shootable/environmental targets.

---

## The Tomb — documented optional systems

Current guide coverage: 8 major side Easter eggs.

### Golden Tier III Armor

1. Find/break the two hidden Nexus crates.
2. Recover two statue heads.
3. Install them at the Dig Site statues.
4. Complete the first Blood Sacrifice challenge.
5. Complete the second Blood Sacrifice challenge.
6. Challenges deliberately leave the player at extremely low health while preserving armor.
7. Completion unlocks the renewable Golden Armor system.

Reusable lesson:
A side quest can permanently alter the **armor economy for the rest of the run**.

### Free Ray Gun through archaeology/digging

1. Obtain the shovel.
2. Use the perception prerequisite to identify higher-value dig spots.
3. Dig over multiple rounds.
4. Recover three Ancient Gems.
5. Install them at the bull/statue interaction.
6. Defeat the spawned Doppelghasts.
7. Receive the Ray Gun.

Important pacing:
The system naturally spans rounds instead of asking players to dig infinitely in one round.

Reusable lesson:
RNG collection feels fairer when:
- a perception upgrade exposes opportunity;
- progress is rate-limited predictably;
- completion becomes guaranteed.

### Free Pack-a-Punch I + Cryo Freeze

A moving/electrified object chain in the Nexus can be hit in the correct quick sequence for a free weapon upgrade/ammo-mod reward.

Reusable lesson:
Movement/readiness skill can reward economic progression directly.

### Round-scaling Aether Tool

Freeze the required waterfalls / complete the environmental interaction.

Reward scales based on the current round.

Reusable lesson:
A secret found late should not pay an early-game-quality reward.

### Free Self-Revive + Light Mend

Break/shoot the required vase set.

Reusable lesson:
Simple destruction hunts are acceptable when the item silhouettes are legible and the reward is immediately useful.

### Friendly zombie soldiers

1. Equip Brain Rot.
2. Trigger the four marked skull interactions quickly enough.
3. Friendly soldiers/AI appear and assist.

Reusable lesson:
A short ammo-mod puzzle can create a temporary **faction inversion** rather than another loot chest.

---

## Shattered Veil — documented optional systems

Current guide coverage: 6 side Easter eggs including song, free weapon, free perk, companion, free Field Upgrade charge and extras.

### Free Wunderwaffe DG-2

Gate:
- at least one full Liminal ritual complete.

Normalized flow:
1. Follow the visible smoke/cloud chain.
2. Rotate/interact with the required objects in the correct direction/order.
3. Shoot the final cloud.
4. One player can claim the free Wunderwaffe DG-2.

Reusable lesson:
A powerful free weapon can be gated behind **partial Main Quest mastery** without being required for the Main Quest itself.

### 115 Bell

- Obtain/access the Bell.
- Ring it exactly/approximately the themed 115-count requirement.
- Receive a free perk reward.

Reusable lesson:
Absurd, playful count-based interactions are good as optional jokes when failure is harmless.

### Mister Peeks bodyguard

1. Collect six bodyguard pieces around the estate.
2. Assemble the figure.
3. It becomes a friendly Vermin companion.
4. It assists with damage/revives.
5. Feeding/donut progression can evolve it.

Reusable lesson:
A companion side quest is much deeper when the companion has its **own upgrade/evolution track**.

### Free Aether Shroud charge

A single-use Shroud canister is available in the Mainframe Chamber.

Reusable lesson:
Place optional quest-support resources near the step that uses them so players without the optimal loadout are not hard-blocked.

### S.A.M. trap

A target/trap chain unlocks an additional map trap.

Reusable lesson:
Side quests can permanently add **new map infrastructure**.

### Round-100 Z-Rex challenge

A high-round interaction allows an optional rematch/challenge boss.

Reusable lesson:
Boss assets can create long-tail mastery content after the ordinary Main Quest audience is done.

---

## Reckoning — documented optional systems

Current guide coverage: 8 side Easter eggs.

### S.A.M. Trial risk/reward layer

- S.A.M. Trials can be pushed toward Legendary reward quality.
- Strong completion can award a free perk.
- Failure can apply temporary Grief-style punishments such as Ammo Drain, Weapon Nerf or Weapon Carousel.

Reusable lesson:
Failure does not always have to mean "nothing happens." A failed challenge can create a **fun temporary negative modifier**.

### Pool-ball 1-1-5

Shoot/interact with the correct pool balls in the themed number sequence to receive a Self-Revive.

Reusable lesson:
Recognizable lore numbers can work as optional fan-service interactions without becoming mandatory quest logic.

### Aetherella companion

- Trigger the bathroom-stall/figure route.
- Charge the figurine with Gorgofex.
- Use the Sublevel system to activate the companion.

Reusable lesson:
A recurring mascot mechanic can be reinterpreted differently on each map: transformation on one, companion on another.

### Golden Trash Bin

1. Find/interact with all eight bins.
2. Individual bins may pay little or nothing.
3. The completed set creates the golden-bin jackpot.

Reusable lesson:
A low-value collectible set can hide its real payoff until full completion.

### Chicken Bucket Hat

1. Trigger the bucket interaction with explosive damage.
2. Collect the six chicken wings.
3. Equip the resulting wearable for the match.

Reusable lesson:
A humorous cosmetic can also function as an in-match wearable system.

### Android Assembly vending machine

- Melee once per round for a random payout.
- A stronger Melee Macchiato interaction gives a final jackpot.
- Cashing out permanently ends the once-per-round gambling loop.

Reusable lesson:
**repeatable small reward vs one-time cash-out** creates an elegant risk/reward choice.

### Optional high-round bosses

Round-100 boss interactions create prestige challenges beyond the story run.

---

# BLACK OPS 7

## Ashes of the Damned — documented optional systems

Current guide coverage: 7 major side Easter eggs.

### Soda fountain / Mixologist

Each drink is a separate recipe:
1. Find three themed ingredients.
2. Add only the correct three at Reba's Diner.
3. Brew the matching drink.
4. Receive the associated free perk.
5. Only one drink can be completed per match.
6. Completing all recipes therefore creates a **multi-match achievement track**.

Reusable lesson:
Side content can intentionally span multiple runs without making players repeat a Main Quest.

### Jump Pad network → free Ray Gun Mark II

1. Power/open the full map.
2. Ride all eight jump pads in a connected loop.
3. After the required round delay, read the blinking lobby code.
4. The code is a sequence of pad numbers.
5. Ride the pads in that order.
6. A reward rift opens with premium loot/free Ray Gun Mark II.

Reusable lesson:
Traversal networks can become a **route-order memory puzzle** after the player has naturally learned them.

### Bear Tracks → melee-only secret boss

1. Buy Death Perception.
2. Follow the glowing bear tracks hidden in the fog roads.
3. Interact with five.
4. Enter the secret bear encounter.
5. Kill the boss using melee only.
6. Earn permanent double points on melee kills for the rest of that game.

Reusable lesson:
**perception secret → restricted boss → permanent run modifier** is a complete side-quest arc in miniature.

### Chompy feeding

A world creature/object accepts weapons/equipment and can return salvage or rare rewards.

Reusable lesson:
A map mascot can become an economy sink/gambling system.

### Hidden power-ups

Shootable power-ups remain bankable emergency resources across the large open road network.

---

## Astra Malorum — documented optional systems

Current guide coverage: 6 major side Easter eggs.

### "Magic" headphone song

Three headphones across the observatory/Mars route.

### Pareidolia space-drift secret

1. View/stare at the giant Mars head for the original musical callback.
2. Explode/manipulate the floating asteroid near Wisp Tea.
3. Wall-jump onto the fragment.
4. Drift through space while the remix plays.
5. The first successful ride can also award Tessie's DG-2 turret.

Reusable lesson:
A traversal spectacle can simultaneously be:
- song Easter egg;
- movement toy;
- item reward;
- lore/reference.

### Five-skull memory minigame

1. Shoot/find five skulls until they enter their active state.
2. Place them on the desk.
3. Start the event.
4. Skulls float in a generated sequence.
5. Reproduce the sequence by shooting them in order.
6. Team receives a Random Perk.

Reusable lesson:
A classic Simon/memory game becomes more thematic when the **memory objects are collectibles the player found first**.

### Gramophone/disc combat challenges

1. Recover the music discs.
2. Take a disc to a gramophone.
3. Starting the track begins its combat challenge.
4. Success pays a Mystery Perk.
5. Failure still pays salvage.

Reusable lesson:
Failure consolation rewards make players willing to experiment without trivializing the success reward.

---

## Paradox Junction — documented optional systems

Current guide coverage: 8 major side Easter eggs.

### Mannequin acid-melt free perk

1. Obtain/fill the vial in the correct timeline.
2. Melt mannequins around the other timeline.
3. The vial has limited uses and must be refilled.
4. Finish all required mannequins.
5. Return to the future state.
6. Receive the Random Perk reward.

Reusable lesson:
The map's timeline mechanic should affect side quests too, not only the Main Quest.

### Friendly-zombie bunker opening

1. Build/obtain the relevant weapon/tool.
2. Guide the mannequin interaction across the timeline states.
3. Use Brain Rot / conversion tools on zombies.
4. Converted zombies perform the required knocks/interactions.
5. Open the bunker.
6. Claim a mixed reward bundle: weapon, perk, Essence.

Reusable lesson:
A status-effect mechanic can turn enemies into **temporary puzzle actors**.

### Mini golf

- One attempt per match.
- Sink the putt first try for a premium/triple reward.
- Miss and receive a small consolation reward.

Reusable lesson:
A one-attempt skill secret creates tension without being punishing because the reward is optional and failure still acknowledges the attempt.

### Hidden power-up meta chain

Several hidden targets are split between Past and Future.

Collecting the initial set unlocks additional rewards such as Fire Sale/Random Perk.

Reusable lesson:
A collectible set can have **tiered completion rewards**, not only one final prize.

---

## Totenreich — documented optional systems

Current guide coverage: 7 major side Easter eggs.

### Tyr coordinate repeatable

1. Read Tyr's flashing letter/number coordinate.
2. Translate the coordinate onto the Tactical Map grid.
3. Travel to that zone.
4. The accompanying number specifies the exact zombie-kill count.
5. Get exactly that many kills.
6. Return for a free power-up.
7. Repeat in later rounds.
8. Ten successful completions contribute to the Cointoss Helm.

Reusable lesson:
A side activity can become a **repeatable every-round micro-contract**, with a long-form mastery reward after repeated perfect execution.

### Fishing

- Build/find the rod.
- Use multiple fishing spots around the map.
- Catches can yield ordinary rewards and progress.
- A special catch can spawn the Olaf zombie.
- Killing him awards Golden Tide Helmet.
- The helmet improves/faster fishing.

Reusable lesson:
A side system can contain its **own equipment upgrade**, forming a miniature progression economy independent from combat.

### Viking helmet system

Several wearable helmets have separate requirements and narrow bonuses.

Reusable lesson:
Map-specific wearables provide long-form side mastery without bloating the perk system.

### Richtofen character quest

Gate:
- play as Richtofen;
- round/ability prerequisites.

Flow:
1. Trigger the hidden interaction.
2. Enter the castle/throne progression.
3. Recover/read documents/radio codes.
4. Complete the balance/throne interaction.
5. Obtain the Ritterkreuz artifact / challenge payoff.

Reusable lesson:
Character-specific quests can deepen lore while remaining optional and cosmetic/prestige focused.

---

## Kowakujō — documented optional systems

Current guide coverage: 7 major side Easter eggs.

### Takeo / Path of Sorrows character quest

1. Play as Takeo.
2. Reach the required map/Main Quest state.
3. Craft/use the Psych Grenade at the World Seed route.
4. Reveal the Takeo illusion/katana.
5. Enter the character-specific combat gauntlet.
6. Fight themed enemy waves and the Oni encounter.
7. Keep/unlock Path of Sorrows and the associated mastery reward.

Reusable lesson:
An optional character quest can end in a **unique persistent weapon identity** rather than a generic loot chest.

### Lava parkour → free Ray Gun

1. Open Pack-a-Punch/required route.
2. Start the lava-platform challenge.
3. Traverse timed platforms, wall jumps and moving hazards.
4. Checkpoints add time.
5. Complete the course.
6. Every player who completes it can receive their own reward rather than one team-only pickup.

Reusable lesson:
Movement mastery should be individually rewarded in co-op.

### Toy mice

- Five active collectibles are selected from a larger possible-location pool each round/match.
- Find the active subset.
- Complete the set for the reward.

Reusable lesson:
Randomized **subset spawning** keeps collectible routes from becoming pure memorization.

### Hidden power-up completion chain

Initial hidden targets unlock additional premium power-ups after the base set is completed.

---

# Rex Infernus — high-density optional-content model

Current guide coverage: **21 documented side Easter eggs**, making Rex a valuable reference for how much optional content a very large map can hold without putting everything in the Main Quest.

Not every launch-window micro-trigger is equally well verified; uncertain character-specific/alternate spawns are kept separate below.

## Wearable mask/helmet system

### Goat Mask

- Hidden Her House interaction.
- Reward quality depends partly on how long the player survives the starting-house setup.
- Passive: remaining completely still eventually creates a damaging purple-fire zone around the player.
- Internal cooldown prevents constant activation.

Reusable lesson:
A wearable can reward a behavior style—here, deliberate stillness—without becoming a full perk.

### Twins Mask

Unlocked by completing the deeper/harder Forest toy-box minigame progression.

Passive:
- invokes a Twins-themed damage event/lightning behavior.

Reusable lesson:
A side-quest chain can culminate in a wearable that **references the minigame used to earn it**.

### Space Helmet

1. Collect six Mr Peeks components in grapple-required positions.
2. Complete the follow-up grapple-ring course.
3. Faster completion improves rewards.
4. Top timing tier can add a Ray Gun.
5. Helmet increases grapple duration and removes fall damage.

Reusable lesson:
A movement challenge can reward **movement utility**, creating a coherent mastery loop.

### Warden's Hat

- High-round requirement.
- Use the grapple/Web Mother interaction.
- Kill enemies while riding/attached to the creature.
- Kill count persists.
- Reward grants resistance/immunity to the associated web-slow behavior.

Reusable lesson:
Enemy-specific mastery should reward a **counter to that same enemy behavior**.

## Corrupted Legacy Weapons

1. Choose the legacy wall-buy that determines the eventual reward.
2. Pack-a-Punch three other weapons.
3. Force/wait for rain.
4. The chosen wall-buy enters the glowing state.
5. Use the Nexus purple-flame interaction.
6. Kill the HVT Web Mother.
7. Buy the Ultra-rarity legacy weapon.
8. On pickup:
   - it damages the player over time;
   - weapon switching is locked;
   - reaching Pack-a-Punch and upgrading it ends the emergency condition.
9. Going down loses the weapon and the player must retry on a later rain state.

Reusable lesson:
A high-tier reward can arrive as a **dangerous cursed object transport**, turning the reward pickup itself into gameplay.

## Her House micro-secrets

The sealed starting house contains multiple tiny interactions:
- piano melody/intel/Essence;
- bed-bounce intel;
- movable painting / hidden statue / Max Ammo;
- gramophone callbacks;
- basketball interaction tied into grapple progression.

Reusable lesson:
A starting room can be rich in secrets even before the full map opens.

## Dance-off

1. Grapple the correct outer-island bone piles.
2. Find the cassette.
3. Carry it to the cassette player on Aranea Insula.
4. Start the dance event.
5. Co-op uses a vote.
6. Performance controls reward quality.
7. Completion awards a mastery calling card/challenge.

Reusable lesson:
A score-based rhythm/performance game is a strong tonal break because the reward ladder motivates replay without forcing success.

## Forest toy-box / Mask progression

1. Find the music box/toy-box trigger in the Forest.
2. A new toy/minigame becomes available over successive rounds.
3. Minigame families include:
   - hide-and-seek;
   - jump rope;
   - stuffed-animal/toy challenge.
4. Base clears pay rewards.
5. Harder repeat versions progress the Twins Mask.

Reusable lesson:
One side quest can behave like a **mini campaign of different minigames** instead of one repeated mechanic.

## Rain Pool

The four-cube/wall-state progression can make rain a controllable world state.

Rain is then consumed by:
- Corrupted Legacy Weapon setup;
- other weather-dependent side systems.

Reusable lesson:
Once a map supports weather as state, optional content should treat weather as a **quest resource**, not decoration.

## Crew character cutscene secrets — verification caution

Rex contains crew/character-specific secret scenes, but current community documentation does **not** provide equally verified trigger chains for every character.

Research rule:
- store them as known-present;
- mark exact trigger state as incomplete/disputed until multiple independent routes agree;
- never invent missing steps.

This is exactly how Xziel's internal research database should distinguish:
- discovered content;
- suspected route;
- verified route;
- patched route.

## Widow's Wine — system/bug research

Rex brings Widow's Wine into the map's modern perk ecosystem.

Research policy:
- keep intended mechanics separate from reported live bugs;
- never build our own reference around bugged behavior;
- patch/version-tag mechanic observations.

---

# BO7 Survival maps

Survival maps intentionally remove the giant Main Quest and isolate a smaller combat space.

Documented slices include:
- Vandorn Farm;
- Ashwood;
- Exit 115;
- Zarya Cosmodrome;
- Nuked;
- Mars;
- Eidskallen Lighthouse.

Design value:
- reuse the same art/POI with different progression constraints;
- eliminate quest overhead;
- produce fast-start challenge spaces;
- support leaderboard/high-round audiences;
- let a large map generate several smaller game modes.

Xziel application:
A large original map should be authored so 2–4 POIs can later run as standalone Survival arenas without duplicating geometry.

---

# Dead Ops Arcade 4

Dead Ops Arcade remains a separate arcade interpretation of Zombies rather than a traditional Main Quest map.

Design value:
- alternate camera/control language;
- score/challenge emphasis;
- exaggerated pickup economy;
- short-run arcade feedback;
- reuse of Zombies themes without the normal FPS rules.

Xziel application:
Keep the quest engine decoupled enough that optional arcade modes do not depend on first-person map scripting.

---

# BO7 Rogue Run — roguelite progression laboratory

Rogue Run is a permanent run-based mode, not a conventional Easter Egg.

## Core loop

1. Spawn with a random Common pistol.
2. No normal loadout weapon.
3. Clear the current combat round.
4. Enter the reward area.
5. Three pedestals offer different reward pools.
6. Pick exactly one before the timer expires.
7. Miss the timer and a reward is assigned automatically/randomly.
8. Return to combat.
9. Stack upgrades into a coherent build.
10. HVT bosses gate progression.
11. A wipe ends the run.
12. Permanent account unlocks crossed during the run remain earned.

## Pedestal categories

Examples include:
- weapon;
- perk;
- ammo mod;
- Field Upgrade;
- utility;
- stat/economy buffs.

Best design principle:
**synergy beats hoarding**. A good roguelite reward pool should invite a build identity rather than simply stack additive damage.

## Playlist structure

The mode has expanded across multiple map/playlists and difficulty variants.

Permanent progression carries across them.

Design lesson:
A new playlist can be content expansion without resetting the player's meta progression.

## Relic interaction

Relics unlocked elsewhere can be used by the run's Curse/Relic systems.

This connects:
- round-based map mastery;
- optional Cursed unlocks;
- roguelite runs.

Xziel lesson:
Separate modes become much more valuable when they share a **global challenge/modifier library**.

## HVT/milestone progression

- HVT bosses gate major run milestones.
- Round survival can provide separate milestone rewards.
- Permanent rewards can remain banked even if the player later wipes.

Xziel lesson:
A roguelite run should distinguish:
- run inventory, lost on wipe;
- milestone unlocks, retained permanently.

---

# What modern optional content adds to the Xziel engine vocabulary

The BO6/BO7 side-content pass confirms the engine should support all of these without custom one-off hacks:

- hidden collectible sets;
- randomized active-subset collectibles;
- bankable hidden power-ups;
- score-based minigames;
- one-attempt-per-match challenges;
- performance reward tiers;
- temporary player transformation;
- alternate combat form;
- persistent in-match companions;
- companion evolution;
- repeatable per-round interactions;
- final-jackpot/cash-out choice;
- character-specific quests;
- movement/parkour courses;
- individual co-op completion;
- vehicle races;
- cooking/recipe systems;
- fishing;
- treasure maps;
- cursed risk/reward items;
- wearable masks/helmets;
- temporary world-state/weather controls;
- friendly converted-enemy puzzle actors;
- scorestreak-only / melee-only / weapon-class trials;
- high-round optional bosses;
- survival-map extraction from larger maps;
- roguelite pedestal choices and build synergies;
- permanent meta rewards surviving a wiped run;
- versioned known/suspected/verified secret status.

---

# Recommended Xziel side-content architecture

```
SideQuestDefinition
{
    id
    sourceMap
    discoveryState
    prerequisites[]
    trigger
    stages[]
    failurePolicy
    retryPolicy
    reward
    persistence
    multiplayerScope
}

MinigameDefinition
{
    ruleset
    scoreModel
    timeLimit
    attemptPolicy
    consolationReward
    rewardTiers[]
}

CollectibleSetDefinition
{
    possibleSpawns[]
    activeCount
    randomSubsetSeed
    proximityFeedback
    perPlayerOrShared
    completionReward
}

RunModifierReward
{
    effect
    duration
    downside
    stackRules
}

ResearchVerification
{
    status: Known | Suspected | Datamined | Verified | Patched | Removed
    firstSeenVersion
    lastVerifiedVersion
    independentSources
}
```

Critical rule:
**optional content should be cheap to fail and expensive to master.**

The player should enjoy discovering it on attempt one, understand it better on attempt two, and have a skill/reward reason to perfect it on attempt ten.
