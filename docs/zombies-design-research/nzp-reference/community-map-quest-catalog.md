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

