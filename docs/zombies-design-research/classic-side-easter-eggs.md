# Classic Side Easter Eggs & Optional Systems — WaW through Black Ops 4

Updated: 2026-09-20

Purpose: preserve the **optional systems, side quests, secret weapons, alternate player states, persistent economies, challenge boards, wearable rewards and minigames** that made the classic Zombies era replayable outside the Main Quest.

These are normalized design notes. Exact pins and version-specific quirks remain in sources.md.

---

# WORLD AT WAR / BLACK OPS FOUNDATIONS

## Nacht der Untoten

Optional-content lesson:
The original map proves that **survival itself can be the content**. A future game should not assume every map needs a giant Main Quest.

Reusable design:
- Mystery Box as the main run randomizer.
- weapon-wall economy.
- escalating route pressure.
- almost zero quest overhead.

## Verrückt

Reusable systems:
- split co-op spawn.
- power reconnects teams.
- electro-shock defenses and route traps.
- oppressive environmental storytelling.

Design lesson:
A map can produce a strong co-op story simply through **where players begin** and how the map reconnects.

## Shi No Numa

Reusable systems:
- randomized perk-machine hut assignment.
- trap route choices.
- swamp movement pressure.
- early hidden-song collectible grammar.

## Der Riese

Reusable systems:
- teleporter-link network.
- Pack-a-Punch as a map-wide setup reward.
- Fly Trap hidden-object chain.
- small narrative/audio reward rather than combat power.

Design lesson:
Some secrets should exist because discovery is fun, even if the reward is not statistically valuable.

---

# BLACK OPS

## Ascension

Side-system lessons:
- Lunar Landers begin as traversal and later become puzzle verbs.
- Space Monkeys directly attack the player's purchased perk infrastructure.
- rocket launch changes the world and opens Pack-a-Punch.

Xziel abstraction:
**enemy attacks owned infrastructure** rather than only health.

## Call of the Dead

Side-system lessons:
- George Romero is a persistent roaming boss who follows players around the normal map.
- defeat/reward loop exists without requiring a dedicated arena.
- freezing water creates an environmental status system.
- lighthouse geometry doubles as navigation and quest device.

Xziel abstraction:
A roaming boss can create a map-wide secondary objective that the team can engage with or avoid.

## Shangri-La

Side-system lessons:
- Eclipse Mode temporarily reconfigures the map into a quest-state version.
- minecart, slide, geysers and moving terrain become traversal toys.
- Focusing Stone reward can affect continued survival rather than merely ending the quest.

Xziel abstraction:
**alternate world state + post-quest survival bonus**.

## Moon

Side-system lessons:
- P.E.S. vs Hacker is an equipment-slot tradeoff.
- Hacker turns doors, boxes, wall weapons and machines into manipulable economy objects.
- Excavators are timed environmental threats that can permanently change routes.
- Area 51 is a special pressure zone with different progression behavior.
- gravity itself is variable world state.

Xziel abstraction:
A utility tool can change **economy and infrastructure**, not only combat.

---

# BLACK OPS II

## TranZit

Reusable side systems:
- bus route and wait/run decisions.
- buildables distributed across POIs.
- persistent BO2 bank and weapon locker ecosystem.
- teleport lamps / Denizen traversal shortcut.
- carried tools such as Turbine let players temporarily power otherwise-dead equipment.

Design lesson:
Portable utility can make the player create their own temporary power network.

## Die Rise

Reusable side systems:
- elevators move perks/Pack-a-Punch through the map.
- vertical traversal is a constant survival challenge.
- Trample Steam doubles as mobility tool and quest object.
- bank/locker persistence links the map to the wider Victis economy.

Design lesson:
Moving utilities create run-to-run timing decisions that static machines cannot.

## Mob of the Dead

Current research coverage: 8 documented side Easter eggs.

### Afterlife — alternate player state

Afterlife changes the player's verbs:
- pass through/enter spirit-only spaces;
- shock electrical panels;
- reveal hidden information;
- self-revive by returning to body.

Xziel lesson:
An alternate form should expose a **second interaction layer** rather than simply buff combat.

### Hell's Retriever → Hell's Redeemer

1. Feed the three Cerberus heads.
2. Claim the Retriever.
3. On the required round/bridge condition, use it as the only kill source for a full-round challenge.
4. Perform the sacrificial/return interaction.
5. Retrieve the upgraded Redeemer in the alternate state.

Reusable lesson:
Equipment mastery can unlock a stronger version through **behavioral proof**, not a crafting recipe.

### Five blue skulls → free Blundergat

- skulls are hidden/invisible until the correct perception/knowledge state.
- Hell's Retriever physically collects them.
- full set pays a powerful weapon.

Reusable lesson:
A weapon/tool acquired from one side quest can become the **collector tool** for another, creating interlocking side content.

### Golden Spork

Normalized structure:
1. expose hidden route/poster;
2. use Afterlife to activate inaccessible interaction;
3. recover spoon;
4. transform/use it through the blood-bathtub chain;
5. score a substantial Acid Gat kill requirement;
6. claim Golden Spork.

Reward:
extremely strong melee performance well into later rounds.

Reusable lesson:
A long side quest feels justified when the reward creates a distinct new playstyle rather than a minor stat bump.

### Brutus infrastructure sabotage

The Warden can disable:
- perk machines;
- Mystery Box;
- workbenches;
- other player infrastructure.

Reopening costs resources.

Reusable lesson:
A special enemy can create **economic damage** and strategic repair priorities.

### Opening-lullaby anti-secret

A deliberately strange match-start interaction can cause a unique narrative outcome even though it is useless for a normal run.

Reusable lesson:
Not every Easter Egg should optimize survival.

---

## Buried

Current research coverage: 8 documented side Easter eggs.

### Leroy / Arthur favors

Candy and Booze change what the giant NPC will do.

World-manipulation functions include:
- smash barricades;
- assist with chalk/build interactions;
- manipulate crowds;
- help with buildables/objects.

Reusable lesson:
A companion is much more interesting when players **command it indirectly through treats/items** instead of a normal radial command menu.

### Chalk wall-buy placement

Players can carry weapon chalk and decide where to place wall buys.

Reusable lesson:
Letting the player alter the **map's future economy layout** is a powerful reward.

### Persistent bank

- deposit points;
- withdraw on later games;
- move points between players through drop interactions.

### Persistent weapon locker

- store one eligible weapon;
- retrieve it in another match/map in the connected Victis system.

Reusable lesson:
Persistent progression existed in Zombies long before modern loadouts; a map object can embody account/session continuity diegetically.

### Ghost mansion free-perk loop

- entering changes normal enemy behavior;
- Ghost Ladies steal points on contact;
- killing enough can pay a free perk;
- leaving the mansion ends the special enemy state.

Reusable lesson:
A traversal corridor can become a temporary **economy-risk combat biome**.

---

## Origins

Current research coverage: 7 documented side Easter eggs.

### Rituals of the Ancients challenge board

Visible challenge goals feed staged reward chests.

Reward types include:
- perk/utility rewards;
- upgraded weapon reward;
- ammo;
- powerful melee progression.

Reusable lesson:
A challenge board can make normal play feed optional progression without becoming a Main Quest.

### Golden Shovel

Repeated digging progresses the shovel state.

Benefits:
- stronger dig-site reward table;
- access to deeper mastery systems.

### Golden Helmet

Further digging/mastery can unlock immunity/protection related to the giant robots.

Reusable lesson:
One side system can have **hidden internal progression tiers**.

### Empty Perk Bottles / perk-slot expansion

A Golden Shovel + perception/world-state route can reveal hidden dig sites that award Empty Perk Bottles.

Reward:
raises the perk capacity beyond the normal limit.

Reusable lesson:
A side quest can upgrade the **rules of the run** rather than give a gun.

### Elemental staff ecosystem

Even though the staffs are Main Quest tools, each build/upgrade behaves like a separate side quest and gives teams four parallel specialization roles.

Reusable lesson:
A shared base template can support four thematically different upgrade puzzles.

---

# BLACK OPS III

## Shadows of Evil

Current guide coverage: 14 documented side Easter eggs.

### Beast Mode as a map-wide secondary verbs layer

Beast Mode supports:
- grappling;
- shocking power boxes;
- breaking hidden doors;
- reaching ritual objects;
- exposing shortcuts.

Reusable lesson:
Temporary transformations are strongest when their verbs are useful throughout the map, not only during one scripted scene.

### Civil Protector

A summoned friendly NPC provides combat assistance in districts.

Reusable lesson:
Map currency/power can be exchanged for a temporary helper rather than another turret.

### Apothicon Servant

Parts acquired from special enemies/events create a map-specific Wonder Weapon.

Reusable lesson:
A Wonder Weapon can feel like the map's ecosystem condensed into an object.

### Sword progression

Egg → soul charging → sword → separate upgrade rituals.

Reusable lesson:
A Main Quest-adjacent weapon can have its **own contained quest graph**.

---

## Der Eisendrache

Current guide coverage: 15 documented side Easter eggs.

### Panzer Helmet

1. Use three ceiling-claw traps/objects.
2. Each must kill a Panzersoldat.
3. Claim the helmet.
4. Permanent-in-match Panzer damage resistance.

Reusable lesson:
**enemy-specific mastery → matching defensive reward**.

### Plunger

1. manipulate the clock/time-travel system;
2. recover the Plunger;
3. kill a Panzer to charge it;
4. gain a temporary powerful melee state.

Reusable lesson:
Comedy items can still become meaningful mastery rewards.

### Free Mega GobbleGum plant

- move a small plant between present/past states;
- let it grow;
- reclaim a consumable reward in the present.

Reusable lesson:
Time-state puzzles can create **growth over time** rather than only code solving.

### Skeleton Mode

- equip the correct GobbleGum/state;
- trigger hidden skull interactions;
- replace ordinary zombies with skeletons.

Reusable lesson:
A side secret can modify the **enemy presentation/roster for the whole match**.

### Micro-rewards

The map also includes:
- free Death Machine;
- hidden BRM wall-buy;
- alternate cable-car/gondola interactions;
- songs and environmental callbacks.

Design lesson:
Large quests benefit from tiny secrets between major systems.

---

## Zetsubou No Shima

Current guide coverage: 11 documented side Easter eggs.

### Imprint Plant

A carefully grown plant can store the player's current:
- weapons/equipment;
- perks/state;
- other run loadout information.

After death, it can restore the stored state.

Reusable lesson:
A side quest can create a **player-authored checkpoint** inside a survival run.

### Golden Bucket

Upgrades the water-carry system into a stronger/permanent utility state.

Reusable lesson:
If a map has a bespoke resource system, optional mastery should improve that exact resource loop.

### Spider Bait / temporary creature play

The player can temporarily become/control a spider-like form.

Reusable lesson:
Side content can grant an alternate creature perspective without needing a whole separate mode.

### Friendly Thrasher

Plant mutation/growth can produce an allied monster.

Reusable lesson:
Randomized crafting becomes interesting when one rare outcome **changes faction allegiance**.

### Plant genetics/water-color system

Different water types and cultivation conditions change plant outcomes.

Reusable lesson:
Procedural/random crafting is fairer when players have **inputs that bias the outcome**.

---

## Gorod Krovi

Current guide coverage: 12 documented side Easter eggs.

### Time-trial melee ladder

Known milestones:
- Round 5 before 5:00 → Wrench.
- Round 10 before 13:00 → Malice.
- Round 15 before 24:00 → Slash N Burn.
- Round 20 before 32:00 → Fury's Song.

Reusable lesson:
Speedrunning can be embedded inside ordinary survival without a separate queue.

### Dragon Wings

- build/obtain the Gauntlet prerequisite;
- ride from all three dragon stations;
- claim wings from mannequin.

Reward:
- fire/explosive resistance;
- free dragon travel.

Reusable lesson:
Traversal mastery can permanently make future traversal **cheaper and safer**.

### Mangler and Valkyrie Helmets

Enemy-specific kill/weak-point requirements award matching resistance helmets.

Reusable lesson:
Wearables are an elegant side-progression layer between perks and pure cosmetics.

### Upgraded Dragon Strike

- earn substantial Dragon Strike kills;
- complete flag interactions;
- repeat a Hatchery lockdown using the Strike.

Reusable lesson:
A map ability can receive an optional **mastery upgrade** after the player proves they understand it.

### Upgraded Monkey Bombs

The classic throwable gets a map-specific upgrade route.

Reusable lesson:
Even universal equipment can receive map identity through optional upgrades.

### Samantha doll hide-and-seek

A Monkey Bomb/fire setup spawns a doll-hunt sequence with timed listening/search.

Reusable lesson:
Audio localization can be the primary puzzle channel.

---

## Revelations

Current guide coverage: 12 documented side Easter eggs.

### Masks and hats

Kill/interact with matching enemy types in the Kino mask room to unlock themed wearables such as:
- Wolf;
- Margwa;
- Panzer;
- Fury;
- Keeper;
- Viking;
- God mask.

Effects include narrow defensive/movement bonuses.

Reusable lesson:
A finale map can convert enemy mastery from previous maps into **wearable progression**.

### Wall-run free perk

Complete the anti-gravity wall-run route through hidden blue runes.

Reusable lesson:
Traversal skill can directly award core survival economy.

### M1927 chalk table

Collect weapon chalk outlines and place them to alter/unlock a wall-buy arrangement.

Reusable lesson:
Weapon-wall placement can itself be a collectible puzzle.

### Time trials

Round/time milestones award melee rewards.

### Super Easter Egg RK5

With the required prior-map profile state, Revelations completion adds RK5 starting utility and further secret behavior.

Reusable lesson:
A map can inspect cross-map completion state and alter all future starts.

---

# BLACK OPS 4

## IX

Current guide coverage: 5 documented side Easter eggs.

### Challenge podium

The spawn-area podium offers explicit combat challenges and staged rewards.

Reusable lesson:
Optional challenges can be **front-and-center** without ruining the hidden Main Quest.

### Crowd affinity

Arena crowd approval changes with player performance.

Reusable lesson:
The environment/audience can act as a living performance meter.

### Viking funeral

1. unlock Pack-a-Punch prerequisite;
2. recover Mug, Sword and Helmet;
3. place them with the Viking skeleton;
4. complete burial;
5. earn free perk.

Reusable lesson:
A reward quest feels memorable when every item belongs to one small environmental story.

### Brazen Bull

A buildable shield-gun is useful in survival and later puzzle logic.

### Acid Trap construction

Challenge reward + mechanical parts create a map trap used again by another weapon quest.

Reusable lesson:
Side systems should intersect instead of existing as isolated checklists.

---

## Voyage of Despair

Reusable systems:
- Stoker Key + repeated soul chest can award a free Kraken.
- Kraken has elemental variants.
- clocks/dials and ship machinery are used as puzzle UI.
- architecture and ship systems provide natural clue carriers.

Reusable lesson:
Do not place puzzle terminals everywhere when the setting already contains clocks, gauges, valves and navigation instruments.

---

## Blood of the Dead

Reusable systems:
- Spectral Shield acts as defense, perception tool and spirit-attack device.
- Spoon/Golden Spork lineage continues melee progression.
- Hell's Retriever/Redeemer-style equipment returns through new rules.
- Warden infrastructure pressure remains a map identity.
- spectral bird tracking uses audio/visual hunting over several rounds.

Reusable lesson:
A shield can be a full **quest interface** rather than a passive health item.

---

## Dead of the Night

Current guide coverage: 4 documented major side Easter eggs plus its large weapon ecosystem.

### Silver Bullets

Provides renewable premium ammunition for eligible weapons.

Reusable lesson:
A high-powered special weapon ecosystem can be supported by a **renewable but costly ammo economy**.

### Alistair's Folly upgrade ladder

Folly → Chaos Theory → Annihilator.

Each tier adds new behavior rather than only bigger numbers.

Reusable lesson:
Three-stage weapon progression can keep one signature weapon relevant for an entire run.

### Stake Knife / Savage Impaler ecosystem

The map supports additional powerful side weapons tied to its vampire/werewolf fiction.

Reusable lesson:
Optional weapons should counter or resonate with the map's specific enemy ecology.

---

## Ancient Evil

Current guide coverage: 3 major side systems, with extensive weapon specialization.

### God Hands → Exalted mastery

The four God Hands can be upgraded beyond the level strictly required for the Main Quest.

Reusable lesson:
A Main Quest-required upgrade can expose an optional **post-upgrade mastery tier**.

### Tribute system

Oracle tributes create a structured challenge/reward layer.

### Apollo's Will / Pegasus traversal

Shield and Pegasus mechanics remain useful outside one scripted interaction.

Reusable lesson:
Signature traversal and defense tools should stay relevant to normal survival.

---

## Alpha Omega

Reusable systems:
- Rushmore as talking map controller.
- multiple Ray Gun Mark II variants.
- house/TV/code puzzles.
- mannequin and Nuketown callbacks.
- free Pack-a-Punched reward paths.

Reusable lesson:
A controller/NPC system can act as both story character and **diegetic quest UI**.

---

## Tag der Toten

Reusable systems:
- Challenge Totems.
- Hermit barter/exchange.
- Golden Pack-a-Punch.
- zipline upgrade.
- free/alternate Wonder Weapon routes.
- final-map post-quest state.

Reusable lesson:
A finale map benefits from **multiple mastery economies**—challenge, barter, traversal upgrade, weapon upgrade—rather than one giant linear quest.

---

# Classic-era mechanic families now captured

The classic research supplies proven examples for:

- alternate spirit/player form;
- environmental sabotage enemy;
- cross-match bank/weapon storage;
- NPC favor system;
- player-placed wall buys;
- challenge board;
- hidden progression tiers;
- perk-cap expansion;
- time-trial reward ladder;
- enemy mastery wearables;
- movement mastery rewards;
- player-authored death checkpoint;
- farming/gardening genetics;
- creature transformation;
- friendly monster creation;
- secondary weapon mastery quest;
- temporary full-map enemy reskin/mode;
- crowd/audience reputation;
- reusable premium-ammo economy;
- post-upgrade weapon mastery;
- barter NPC;
- map-controller NPC;
- cross-map profile reward.

---

# Xziel rule extracted from the classics

The classic maps are strongest when a side quest **changes how the player plays the map afterward**.

Examples of the design principle:
- a helmet changes enemy matchup;
- wings change travel cost;
- a plant changes death consequences;
- a bank changes next run;
- an upgraded tomahawk changes ammo economy;
- a perk bottle changes the perk cap;
- a companion changes world interaction;
- a time trial changes the starting/midgame weapon path.

For Xziel, prefer run-changing rewards over one-time piles of points.
