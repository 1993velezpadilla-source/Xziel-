# NZ:P Community Quest / Interaction Catalog

Updated: 2026-09-20

This file records **verified** quest/Easter-egg/interactable behavior from NZ:P community releases. A feature advertised in a release post is not treated as working when later comments explicitly report it broken.

## Kino der Toten (For realsies) — Discussion #708

Source: https://github.com/nzp-team/nzportable/discussions/708  
Status: **SOURCE_AVAILABLE / MECHANICS_VERIFIED**. The author explicitly says sources are included; a later update also links source files.

Verified interaction vocabulary:

- map power/progression and door/zone flow
- Kino-style teleporter flow into projector/Pack-a-Punch room
- teleporter return flow
- Easter-egg song activated by interacting with **three meteor chunks**
- co-op teleporter behavior is relevant, but current NZ:P has a multi-player teleporter bug: community reports say 2+ users can glitch; one maintainer/user reports two as the practical safe limit, not four
- source/map package has been updated with zones/waypoint fixes

Important: this is **not evidence of a four-player-required quest**.

## BO2 Town — Discussion #470

Source: https://github.com/nzp-team/nzportable/discussions/470  
Status: **MECHANICS_VERIFIED, EASTER EGG BROKEN**.

Advertised/verified systems:

- Pack-a-Punch
- 13 wall-buy weapons
- dog rounds
- traps
- seven perks
- four-player co-op support
- teddy-based bank-vault Easter-egg concept
- five teddy locations were community-solved:
  - Bar roof / first floor
  - bank window slab
  - protruding corner in Jug house window
  - protruding corner near Stamin-Up
  - protruding corner near PhD
- intended vault rewards documented by players:
  - PaP .357 Magnum wallbuy
  - Ray Gun wallbuy
  - FG42 wallbuy
  - MG42 wallbuy
  - Bowie Knife wallbuy

Do **not** model this as a proven working chain: author/community comments through 2026 explicitly state the Easter egg/vault still does not work.

## Croft Manor — Discussion #963

Source: https://github.com/nzp-team/nzportable/discussions/963  
Status: **MECHANICS_VERIFIED / FULL RELEASE 1.1.0**.

Verified systems:

- Kino-style teleporter room + Pack-a-Punch
- randomized perk locations
- randomized mystery-box locations
- five-teddy collection chain
  - completion enables a buyable secret Easter-egg weapon
  - completion triggers/unlocks a song
- three-dragon-trophy collection chain
  - completion enables another buyable secret Easter-egg weapon
  - completion triggers/unlocks another song
- multiple minor Easter eggs, including a third song
- full Easter egg with map ending
- buyable ending fixed in 1.1.0
- zoning and spawn activation tied to map traversal
- perk randomization had an explicit edge case when Juggernog had no valid placement
- musical Easter eggs have platform-specific risk on 3DS; issue #1504 reports MP3-buffer crash behavior

No source-backed evidence found that the quest requires all four players.

## Facility V2 — Discussion #1444

Source: https://github.com/nzp-team/nzportable/discussions/1444  
Status: **SOURCE_AVAILABLE / MECHANICS_VERIFIED**. The release package is confirmed by discussion comments to contain the editable `.map`.

Verified systems:

- Key Card interaction
- other explicit interact-trigger objects
- Ray Gun Easter egg
- secret/updated Pack Room
- zone system
- interaction bugs were specifically fixed in later updates
- source-level implementation is a prime candidate for extracting reusable key/item -> interact -> unlock chains

The source package should be treated as authoritative over prose when normalizing the exact target graph.

## No Man's Land — Discussion #1450

Source: https://github.com/nzp-team/nzportable/discussions/1450  
Status: **MECHANICS_VERIFIED**.

Verified chain:

1. player activates the power switch to alert/start the horde
2. every 5 rounds additional zombie spawns are activated, capped at round 25
3. teleporter enters a shop
4. every 7 rounds additional shop content unlocks
5. five hidden teddies form a reward chain
6. teddy interaction/song Easter egg
7. round 35 enables a buyable ending
8. zones prevent inappropriate spawns while players occupy the shop

This is valuable precedent for **round-gated state-machine progression** rather than only one-time switches.

## Nacht der Untoten Plus — Discussion #1432

Source: https://github.com/nzp-team/nzportable/discussions/1432  
Status: **MECHANICS_VERIFIED**.

Verified systems:

- Nacht revamp with more perks
- Pack-a-Punch Easter egg
- five hidden teddies
- some teddies can be activated indirectly with grenades/explosive reach
- update moved teddies and changed interaction feedback
- Ray Gun Mk II and Wunderwaffe added to box

This is useful precedent for a collectible counter driving a PAP unlock.

## Das Alte Haus — Discussion #1440

Source: https://github.com/nzp-team/nzportable/discussions/1440  
Status: **MECHANICS_VERIFIED**.

Verified systems:

- teddy-bear song chain
- Kino-style Pack-a-Punch flow
- four core perks
- dog rounds
- spawn zones
- a purchasable bookcase/door exposes the power switch
- another purchased moving obstruction gates the Double Tap room
- the author explicitly identified `killtarget`-on-door behavior as involved in an older 3DS bug

This release is especially useful for testing `killtarget` and moving-door state transitions across platforms.

## Isolation — Discussion #882

Source: https://github.com/nzp-team/nzportable/discussions/882  
Status: **MECHANICS_VERIFIED**.

Verified systems:

- teleporter
- Zapper trap
- Pack-a-Punch room
- buyable ending via Jeep in garage
- three-teddy chain:
  - teddy 1 outside spawn-room windows
  - teddy 2 on path between garage and factory/power/teleporter
  - teddy 3 behind Deadshot on tree branch
  - completing all three reveals a hidden factory room
  - hidden room contains a purchasable PaP Wunderwaffe
- two hidden switch interactions reveal hidden rooms
- those hidden rooms are timer-controlled
- another button/teddy interaction is used for a song Easter egg
- secrets were explicitly repaired in changelog

This map is strong reference material for **counter -> hidden-room reveal -> timed state -> reward**.

## The Thingy — Discussion #894

Source: https://github.com/nzp-team/nzportable/discussions/894  
Status: **MECHANICS_VERIFIED / WIP HISTORY**.

Verified release/changelog systems include:

- teddy requirement/counter
- light-trail feedback after progress
- power/mystery-box/teleporter-related content in the release history
- Pack-a-Punch
- song/secret unlockables
- buyable ending added in a later update

Because the map has a WIP history and platform limitations, use the actual source/package revision rather than assuming all historical features coexist in one build.

## Perish — Discussion #1133

Source: https://github.com/nzp-team/nzportable/discussions/1133  
Status: **SOURCE_AVAILABLE / SURVIVAL-FOCUSED**.

The author directly publishes J.A.C.K project files. Verified gameplay is mainly survival progression (doors, power routing, wall-buys, mystery-box placement and spawn/pathing). No substantial multi-step Easter-egg quest is established in the release evidence reviewed here.

The project files remain valuable for normal survival-map interaction patterns and should not be mislabeled as a full quest.

## Four-player requirement audit

The engine and release board contain many maps that support **up to four-player co-op**, but that is different from a quest step that requires four simultaneous/assigned players.

Current verified result for the entries above:

- **BO2 Town:** 4-player co-op advertised; no verified four-player-only quest step.
- **Kino:** multiplayer teleporter is actually constrained by a current bug; no four-player-only quest.
- **Croft Manor / Facility V2 / No Man's Land / Nacht Plus / Das Alte Haus / Isolation / The Thingy / Perish:** no source-backed four-player-only quest requirement found in the reviewed evidence.

Rule for future extraction: only set `min_players=4` when map source or authoritative release instructions prove it. Otherwise preserve `coop_supported` separately from `quest_player_requirement`.

## Reusable quest patterns extracted from these maps

- collectible N-of-M -> secret room/reward/song
- multiple collectible families in one map
- interact key/card -> unlock target chain
- switch -> moving obstruction -> newly reachable power/room
- one-time trigger -> target relay -> door/reveal
- round modulo gate -> enable spawn/shop content
- round threshold -> buyable ending
- teleporter link/use/return state
- timed hidden room
- random perk/box placement
- trap activation
- counter completion -> weapon reward
- secret completion -> audiovisual feedback
- zone activation/deactivation tied to traversal
- platform-specific fail behavior that must be tested independently


## Research expansion — 2026-09-20 (community release sweep)

## Shipment Survival v1.1 — Discussion #1513

Source: https://github.com/nzp-team/nzportable/discussions/1513  
Status: **SURVIVAL_ONLY_OR_NO_QUEST_FOUND**.

Verified:
- classic Shipment survival layout
- four original World at War perks
- mystery box
- no Pack-a-Punch
- no substantial quest/Easter-egg chain described in the release
- v1.1 fixed two glitch spots and added Ray Gun Mk II to the box pool

Keep as a clean survival-map baseline rather than inventing a quest classification.

## Yukon Yard v1.0 — Discussion #1526

Source: https://github.com/nzp-team/nzportable/discussions/1526  
Status: **MECHANICS_VERIFIED / EXACT BUNKER STEPS NOT YET SOURCE-EXTRACTED**.

Verified:
- four classic perks plus Stamin-Up and Mule Kick
- mystery box
- Pack-a-Punch
- a hidden bunker whose opening is deliberately part of discovery
- buyable ending connected to the hidden progression
- a player later confirmed reaching the buyable ending
- Ray Gun Mk II can be allowed into the mystery-box pool via map box settings

Reusable pattern:
`discover hidden condition -> unlock bunker -> access PAP/finale path`.

Do not invent the bunker solution until source/archive logic proves it.

## Alley v1.2 — Discussion #1393

Source: https://github.com/nzp-team/nzportable/discussions/1393  
Status: **MECHANICS_VERIFIED / MINOR_EASTER_EGG**.

Verified:
- Pack-a-Punch within normal map progression
- spawn zones
- a "spare change" Easter egg explicitly re-balanced in v1.1

Useful as an example of a lightweight side secret embedded in ordinary survival flow rather than a full main quest.

## RWBY_B.A. — Discussion #1502

Source: https://github.com/nzp-team/nzportable/discussions/1502  
Status: **MAIN_EE_ADVERTISED / STEPS_UNVERIFIED**.

Verified from the release author:
- Pack-a-Punch
- Juggernog, Stamin-Up, Quick Revive, Speed Cola and PhD
- mystery box
- Bowie Knife wallbuy
- a mysterious Easter-egg wallbuy
- author explicitly states the map contains a **main Easter egg**

No exact step chain has been established from public release text yet. Keep the map in the source-extraction queue rather than fabricating the quest path.

## Poop of the Dead — Discussion #1352

Source: https://github.com/nzp-team/nzportable/discussions/1352  
Status: **SOURCE_AVAILABLE / QUEST_UNVERIFIED**.

Verified:
- release explicitly publishes J.A.C.K project files
- source archive therefore exists for direct entity/target-graph extraction
- thread itself does not establish a complete EE chain

High-priority source candidate because it can move from prose-level claims to source-level evidence once the project archive is accessible.

## Haus Uberleben — Discussion #1376

Source: https://github.com/nzp-team/nzportable/discussions/1376  
Status: **MECHANICS_VERIFIED**.

Verified:
- four core perks
- randomized perk-machine spawning
- Free Perk Easter egg
- unlockable Pack-a-Punch
- buyable ending
- community feedback explicitly references finding the hidden perk power-up

Reusable patterns:
- randomized interactable placement
- hidden reward pickup
- side EE reward independent from main survival economy
- unlock PAP -> buyable finale progression

Exact trigger chain remains a source/archive extraction task.

## TOILETTEN — Discussion #739

Source: https://github.com/nzp-team/nzportable/discussions/739  
Status: **MECHANICS_VERIFIED / TWO-PART_EASTER_EGG**.

Verified:
- author explicitly describes a **short two-part Easter egg**
- buyable ending
- community comments show players progressing from first step to second
- Pack-a-Punch is part of the hidden progression discussion
- co-op was tested with 1–2 players
- author says 4 players should be possible

Important multiplayer classification:
**4-player support is not a 4-player quest requirement.** No evidence establishes `min_players=4`.

Reusable pattern:
`EE step A -> EE step B -> unlock/finale state`.

## Simulacra — Discussion #858

Source: https://github.com/nzp-team/nzportable/discussions/858  
Project archive: Archive.org release linked by author.  
Status: **SOURCE_AVAILABLE / MECHANICS_PARTIAL**.

Verified:
- J.A.C.K project files are explicitly published
- an update fixed a missing model on `func_ending`
- an update made obtaining Double Tap II clearer
- source/download archive exposes a dedicated J.A.C.K files package
- Archive.org metadata identifies the map project and its reuse license separately from NZ:P engine code

This is another high-priority source extraction candidate because an editable project exists and the changelog already proves hidden progression plus a global ending primitive.

## BusDepot v1.0 — Discussion #1471

Source: https://github.com/nzp-team/nzportable/discussions/1471  
Status: **MECHANICS_VERIFIED / TEDDY EASTER EGG**.

Verified:
- initial release stated no Easter eggs
- author later edited the release to say the map **now has an Easter egg**
- buyable ending
- community interaction confirms shooting teddies is part of the EE
- discussion references an "EE room"
- PSP pathfinding/performance in the EE room was identified and worked on

Do not infer the exact teddy count or full chain until source/package evidence establishes it.

## One Window In NZP — Discussion #997

Source: https://github.com/nzp-team/nzportable/discussions/997  
Status: **SURVIVAL_ONLY_OR_NO_QUEST_FOUND**.

Verified:
- one-window challenge
- wall weapon
- eight perks
- Pack-a-Punch
- mystery box
- no substantive quest chain established in the reviewed release evidence

## Teddy Survival — Discussion #321

Source: https://github.com/nzp-team/nzportable/discussions/321  
Status: **EASTER_EGG_ADVERTISED / CURRENT BUG REPORTS**.

Verified:
- migrated release advertises all perks, Easter egg and Pack-a-Punch
- recent community feedback reports serious barricade/spawn behavior problems

Do not use it as a "known-good quest implementation" until source/runtime behavior is validated.

## Pump — Discussion #166

Source: https://github.com/nzp-team/nzportable/discussions/166  
Status: **SURVIVAL_ONLY_OR_NO_QUEST_FOUND**.

Verified:
- basic survival setup
- no Pack-a-Punch
- no mystery box
- no substantial EE chain established

## Old beta maps — Discussion #373

Source: https://github.com/nzp-team/nzportable/discussions/373  
Status: **ARCHIVE COLLECTION / PER-MAP EXTRACTION REQUIRED**.

Verified:
- archive of maps recovered from the older NZ:P forum ecosystem
- community comments identify at least one lost-to-time map, "Zombie Island"
- whole archive should be treated as a source-discovery pool, not one logical map

Each map needs its own immutable source/package fingerprint and extraction status.

## Alleyway — Discussion #173

Source: https://github.com/nzp-team/nzportable/discussions/173  
Status: **SURVIVAL_ONLY_OR_NO_QUEST_FOUND**.

Small Left 4 Dead-inspired survival release; no substantial EE chain established in the release evidence reviewed.

## Updated release-version notes

The current map-release board labels:
- **No Man's Land — update 1.6**
- **Das Alte Haus — update 1.2**

The No Man's Land discussion body currently exposes changelog detail through v1.5 in the public crawl, while the category board advertises v1.6. Keep that version difference explicit until the v1.6 delta itself is source-visible.

Das Alte Haus v1.2 adds/fixes:
- Vril fog
- broad performance improvements, especially lower-end devices
- Vril loading-screen music
- teddy visibility across devices
- backyard detail
- Vril ambience
- perk ambience incorrectly playing without power

Community follow-up also confirms an older 3DS `killtarget`/moving-door failure was fixed by a newer game version.

## Research expansion — hidden/older releases and source archives

## Yume Diner V1.0.1 — Discussion #1481

Source: https://github.com/nzp-team/nzportable/discussions/1481  
Status: **BROKEN_RELEASE / QUEST_MECHANICS_PARTIALLY_VERIFIED**.

Verified from the author/replies:

- Diner recreation includes an Easter egg and random perk behavior.
- The author later marked the map broken and disabled the primary download.
- A community mirror was posted while the original release was disabled.
- A player explicitly reports:
  - obtaining a **key**
  - killing/shooting many teddy bears
  - then being unable to open a **wooden door**
- Author clarifies the next step: after picking up the key, **interact with the wooden door**.
- Author also reports an interaction-range/position edge case: when standing too close to the door the interact may fail, so stepping slightly back can make it register.
- Community feedback identifies working TranZit-style lava in the recreation.

Source-backed normalized mechanic from public evidence:

`AcquireKey -> Enable/qualify WoodenDoorInteract -> InteractDoor -> ContinueQuest`

The teddy role and full post-door chain remain unverified. Do not infer that the teddies are the key requirement without source evidence.

Important engine lesson: interaction conditions should not depend on a fragile exact proximity shell; Xziel should test near/inside-edge cases and give deterministic focus feedback.

## Die Verlorenen — Discussion #686

Source: https://github.com/nzp-team/nzportable/discussions/686  
Status: **MECHANICS_VERIFIED / SOURCE_ARCHIVE_NOT_CONFIRMED**.

Verified features:

- unlockable Pack-a-Punch
- Easter-egg song
- four core perks
- random perk machine
- buyable ending
- creator intended a small environmental story that players piece together from map details
- player feedback confirms teddies are discoverable and the buyable ending can be found during blind play

Reusable patterns:

- hidden PAP access independent from ordinary room purchase flow
- random-perk placement/selection
- environmental-story clues plus secret progression
- discoverable global ending

Exact PAP unlock graph and ending prerequisites remain source-extraction tasks.

## Stairway to Heaven — Discussion #1364

Source: https://github.com/nzp-team/nzportable/discussions/1364  
Status: **SOURCE_AVAILABLE / SURVIVAL-CHALLENGE FOCUS**.

Verified:

- second entry in Jeyphr's four-map **MICRO MAP MADNESS** February 2026 series
- public **J.A.C.K Project Files** link
- zones were part of the map's implementation
- release is deliberately built as a very hard progression/challenge map
- collision exploits involving dolphin-dive/railings were reported and patched
- old 3DS crash reported

No substantial multi-step Easter-egg chain is established by the release post itself, so this is primarily useful as editable source precedent for vertical survival progression, zoning and collision/parkour edge cases.

## BCDeshiG Beta Map Archive Re-Pack — Discussion #158

Source: https://github.com/nzp-team/nzportable/discussions/158  
Status: **ARCHIVE_INDEX / ORIGINAL_SOURCE_PACKS_LINKED**.

Verified:

- preservation repack of the older NZ:P Beta map ecosystem after MediaFire pruning
- repack intentionally omits some additional content
- the post explicitly points to **two original Google Drive map packs** for additional material including **released mapper source files**
- therefore this is a major source-discovery pool, not merely a playable-map bundle

Extraction rule:

1. enumerate each map/source file from the original packs
2. fingerprint archive + individual file
3. identify map/runtime generation
4. parse entity graph if source is textual/editable
5. never merge unrelated maps into one inferred quest

This archive is high priority for finding older/lost interaction techniques that may no longer appear in current stock maps.

## Perish — Discussion #1133 / Internet Archive `perish_202504`

Sources:
- https://github.com/nzp-team/nzportable/discussions/1133
- https://archive.org/details/perish_202504

Status: **SOURCE_AVAILABLE / LICENSE_RECORDED / SURVIVAL-FOCUSED**.

Additional verified provenance:

- public J.A.C.K project-files link
- Archive identifier: `perish_202504`
- publication date: 2025-04-20
- Internet Archive item marks usage as **CC BY-SA 4.0**
- Archive item exposes multiple ZIPs including `DevCube.zip`, `Perish.zip`, and `Perish_v2.zip`
- creator identifies J.A.C.K among the programs used
- current release description focuses on survival rather than a multi-step main quest

This archive is eligible for source-logic extraction once the raw ZIP is accessible in the tooling environment.

## Buried [MAP RELEASE V1] — Discussion #854

Source: https://github.com/nzp-team/nzportable/discussions/854  
Status: **RECREATION/WIP / SOLO_DESIGN / QUEST_UNVERIFIED**.

Verified:

- fan map explicitly titled/referencing Buried
- author says it is designed for **solo play**
- V1 playable state
- author calls it an underground obstacle course with mental challenges
- author warns of zombie pathfinding/stuck behavior due map complexity
- community describes it as visually resembling the original map

No source-backed evidence currently establishes Treyarch Buried's original main-quest chain, Leroy systems, buildables, time bomb steps, or four-player Richtofen/Maxis progression. Do **not** classify it as a 1:1 quest recreation.

## Der Riese community recreation — Discussion #473

Source: https://github.com/nzp-team/nzportable/discussions/473  
Status: **RECREATION / TEDDY_EE_EVIDENCE / CURRENT DOWNLOAD HISTORY COMPLEX**.

Verified from discussion:

- players explicitly reference an Easter egg with teddy bears
- one player found two and asked for the remaining steps
- a later player refers to **4 teddies**
- creator tells that player they had downloaded the wrong version and points to an updated Der Riese
- reports show major platform/performance/rendering limitations on handheld builds

This is evidence that an EE path exists in at least one revision, but not enough to claim the original Der Riese fly-trap/teleporter Easter egg is reproduced 1:1.

## House — correction from map-editor inspection

Source: https://github.com/nzp-team/nzportable/discussions/903  
Status: **MECHANIC_CORRECTION / MAP_EDITOR_EVIDENCE**.

A useful community correction:

- players initially believed three teddy bears unlocked Pack-a-Punch
- another player reports the three teddies only activate the music
- a community member says they opened the map in a map editor and found PAP behind an **illusionary wall** on the third floor
- the hidden room also contains a random buff-drink dispenser

Research lesson: player folklore is not source truth. Where map-editor/source evidence contradicts a guessed walkthrough, preserve the correction.


## Facility V2 — deeper 1.2.3 audit

Source: https://github.com/nzp-team/nzportable/discussions/1444  
Archive identifier inferred from current download URL: `ftwo_20260601`  
Current release filename exposed by the download link: `ftwo (1.2.3).zip`

Additional verified details:

- update changelog explicitly says the **Ray Gun EE** was fixed and its room moved
- **Key Card** and other interact triggers were fixed
- Pack Room was updated as a spoiler-sensitive secret
- functional zone files were added
- a community reply confirms the release ZIP contains the editable `.map`
- the teddy Easter egg contains **5 teddy bears**
- all 5 teddies unlock the Easter-egg song
- **ordering branch:** if all 5 are completed **before power is turned on**, the player receives a hint toward obtaining the free Ray Gun
- community play also confirms a separate bonus Pack-a-Punch Easter egg

Normalized design pattern:

```
Teddy1..5 -> Counter(5)
CounterComplete -> Song

if CounterComplete && Power == OFF:
    -> RayGunHint
```

This is important because the completion event reads **shared world state at the moment of completion**. Xziel therefore needs quest conditions that can branch on current state, not only static prerequisites.

The source-extraction target for Facility is now:

1. identify exact teddy event class/targets
2. identify Power-state branch implementation
3. reconstruct KeyCard acquisition/use graph
4. reconstruct free-Ray-Gun reward path
5. reconstruct bonus Pack Room/PAP path
6. capture retry/failure behavior
7. verify solo/co-op semantics independently

