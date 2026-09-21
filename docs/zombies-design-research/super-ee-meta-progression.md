# Super Easter Egg & Persistent Meta-Progression Research

Updated: 2026-09-20

Purpose: study how Zombies turns map completions into reasons to replay the **entire mode**, then convert those lessons into an original Xziel progression system.

## 1. Black Ops III — permanent starting utility

Cross-map completion culminates in Revelations. Documented rewards include:
- a large XP grant;
- Dark Ops completion recognition;
- RK5 added permanently as an extra starting pistol with full ammunition.

Design lesson:
A Super Quest reward does not need to be overpowered. A modest permanent starting option becomes meaningful because players see it every future match.

Xziel adaptation:
- alternate starting sidearm;
- extra starting equipment choice;
- additional cosmetic loadout slot;
- second melee appearance;
- no direct damage multiplier.

## 2. Infinite Warfare — Director's Cut

This is one of the strongest persistent reward designs in Zombies.

After all five map Main Quests:
- Director's Cut becomes a toggleable mode;
- players begin with 25,000 points;
- all Candy Perks are active;
- Magic Wheel weapons are already Pack-a-Punched;
- map Wonder Weapons can appear in the wheel;
- Double Pack-a-Punch is immediately available.

Then the game creates a second mastery loop:
1. Beat all maps normally.
2. Unlock Director's Cut.
3. Replay the maps in Director's Cut.
4. Collect the higher-tier talisman progression.
5. Reach the optional Mephistopheles super-boss.
6. Earn additional completion rewards / character access.

This is crucial: the Super EE does not merely end the game. It **changes the rules of future games and creates another campaign**.

## 3. WWII — character challenge ecosystem

WWII ties long-term mastery to hidden character unlocks.

Examples of requirement families:
- complete Main Quests;
- complete Hardcore Main Quest;
- solo completions;
- high-round survival;
- no-down conditions;
- low-spend economy challenges;
- weapon-specific feats;
- Treasure Zombie collectible fragments;
- special-boss behavior challenges.

Many tasks persist across different sessions rather than demanding everything in one run.

Design lesson:
Meta-progression can be a **collection of feats**, not a single XP bar.

Xziel adaptation:
Each map can contain a hidden 5-part "Legend" challenge set.
Completing all five unlocks:
- survivor skin;
- themed mask;
- voice pack;
- safehouse trophy.

## 4. Black Ops Cold War — The Pact

Cold War adds a ritual site in Outbreak's Zoo region where Main Quest completion converts into a permanent starting-weapon rarity bonus.

The reward scales with number of completed quests and can be toggled off by returning to the ritual site.

Other rewards include:
- quest-related emblems;
- Dark Ops calling card;
- legendary watch.

Design lessons:
- partial completion can grant partial reward;
- permanent power can be **opt-in / opt-out**;
- claiming the meta reward inside the game world feels more memorable than a menu pop-up.

## 5. Black Ops 7 — Main Quest chain + Cursed Relics

By Season 06, BO7 requires completion of the six Round-Based Main Quests:
- Ashes of the Damned;
- Astra Malorum;
- Paradox Junction;
- Totenreich;
- Kowakujō;
- Rex Infernus.

Season 06 officially adds a Super Easter Egg with new rewards including The Warden as an unlockable Operator.

BO7 also demonstrates a second meta track through Cursed Mode / Relic tiers:
- voluntarily equip harder conditions;
- survive milestone rounds;
- earn escalating GobbleGums, XP, calling cards, charms and other rewards.

Design lesson:
The strongest long-term structure may use **two orthogonal tracks**:
A) narrative completion;
B) challenge-modifier mastery.

## 6. Recommended Xziel meta structure

### Track A — Map Sigils
Every Main Quest awards one permanent Map Sigil.

The player's safehouse displays them physically.

### Track B — Cursed Relics
Each map contains several optional difficulty Relics.

Relics alter:
- enemy speed;
- ammo economy;
- HUD;
- armor;
- elite population;
- darkness;
- movement;
- friendly-fire rules;
- boss modifiers.

### Track C — Legends
Hidden feats unlock character cosmetics.

Examples:
- no-down quest;
- solo quest;
- low-spend quest;
- under-time quest;
- all-side-quests run;
- boss with no armor;
- high-round survival.

### Track D — Secret Fragments
Small optional quests can award fragments toward a mode-wide mystery.

The fragment is visible in the safehouse but its final purpose is not immediately explained.

## 7. Proposed Xziel Super Quest loop

### First campaign
1. Complete each map's Main Quest.
2. Earn one Map Sigil per map.
3. Return to the safehouse after every completion.
4. Place each Sigil into a central occult machine.
5. Final slot activates only when all launch-map Sigils are present.
6. Unlock the first Super Quest.

### First Super Quest reward
Unlock **Aftermath Mode** as a toggle.

Possible effects:
- choose one starting perk from a limited pool;
- one additional sidearm option;
- mystery-box first roll has minimum rarity;
- alternate safehouse;
- new announcer;
- cosmetic aura around completed-map portal.

Keep the power meaningful but not enough to trivialize the game.

### Second campaign
When Aftermath Mode is enabled:
- each Main Quest contains one altered step;
- bosses gain one additional mechanic;
- a new hidden object appears in each map;
- completion grants an Infernal Fragment.

Collect all Infernal Fragments to open the true mode-wide super-boss.

### Super-boss
The final encounter should remix mechanics from every previous map.

Example:
- Map 1 movement mechanic;
- Map 2 companion mechanic;
- Map 3 elemental weapon logic;
- Map 4 evidence/symbol logic;
- Map 5 vehicle/trap mechanic;
- Map 6 cursed relic mechanic.

That makes the final fight a test of the entire game rather than a giant bullet sponge.

## 8. Partial-completion rewards

Do not make players wait until 100% completion to feel progress.

Example:
- 2 Sigils → cosmetic emblem + small starting-resource option.
- 4 Sigils → alternate starting melee.
- all Sigils → Aftermath Mode.
- all Infernal Fragments → super-boss.
- super-boss → operator/character skin + title + safehouse transformation.

## 9. Toggleable permanent advantages

Cold War's Pact is a good precedent for allowing permanent bonuses to be disabled.

Xziel should let players choose:
- Classic Start;
- Earned Start;
- Cursed Start.

This protects:
- challenge runs;
- speedruns;
- leaderboard fairness;
- nostalgia;
- players who want progression power.

## 10. Never sell quest power

Super Quest progression should be earned through gameplay.

Safe monetizable categories, if the project ever has monetization:
- cosmetic character skins;
- weapon cosmetics;
- soundtrack;
- supporter badge;
- non-gameplay safehouse decorations.

Do not sell:
- Main Quest completion;
- Relic completion;
- Super Quest tokens;
- starting rarity;
- boss damage;
- puzzle solutions.

## 11. Save-data model

Suggested persistent records:

PlayerZombiesMeta
- completedMainQuests
- completedSideMasteries
- mapSigils
- cursedRelics
- legendChallenges
- secretFragments
- superQuestTier
- superBossCompletions
- cosmeticsUnlocked
- gameplayBonusesUnlocked
- gameplayBonusesEnabled

Every unlock should have:
- version;
- source map;
- source challenge;
- timestamp;
- validation hash / server authority when online.

## 12. Seasonal expansion rule

New maps should extend the system without invalidating old completion.

Possible model:
- Launch Arc Sigils
- Expansion Arc Sigils
- Year-One Crown
- Ultimate Crown

Players who completed older arcs keep their rewards permanently.

Never require redoing all previous Main Quests because a patch added one new map unless the replay itself contains genuinely new content.

## 13. Core conclusion

The progression system should make a player think:

**"I beat the map — and now the entire Zombies mode is different."**

That is the strongest lesson from Director's Cut, The Pact, WWII's hidden challenge characters, BO3's permanent reward, and BO7's modern cross-map quest/relic structure.
