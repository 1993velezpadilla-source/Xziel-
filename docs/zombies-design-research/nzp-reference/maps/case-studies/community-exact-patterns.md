# NZ:P Community Exact Quest Patterns

Updated: 2026-09-20

This file captures community-map quest patterns whose behavior is specific enough in release notes/comments to normalize into reusable Xziel mechanics, even when editable source has not yet been extracted.

## Facility V2 — order-sensitive side quest

Source: https://github.com/nzp-team/nzportable/discussions/1444

Verified:
- five teddy bears total
- all five -> Easter-egg song
- if all five are completed **before power is turned on**, the map provides a hint toward a free Ray Gun Easter egg
- key-card and other interact triggers were explicitly fixed in release updates
- editable `.map` exists in the release package

Normalized graph:

```
Teddy1..Teddy5 -> Counter(5)
CounterComplete
  -> PlaySong
  -> If(Power == OFF)
       -> RevealFreeRayGunHint
```

Pattern class:
- `ConditionalAtCompletion`
- `OrderSensitiveSideQuest`
- `GlobalWorldStatePredicate`

## Isolation — three distinct secret archetypes in one map

Source: https://github.com/nzp-team/nzportable/discussions/882

### Secret A — 3 teddies -> hidden room -> reward wallbuy

Three teddies:
1. outside spawn-room windows on brick wall
2. path between garage and factory/power/teleporter
3. behind Deadshot, on a tree branch

After all three are shot:
- hidden factory room opens
- room contains PaP'd Wunderwaffe wallbuy for 4000

Normalized:

`3 ShootableSecrets -> Counter(3) -> RevealHiddenRoom -> EnableRewardWallbuy`

### Secret B — timed hidden rooms from switches

Two hidden red switches can be shot/interacted with.

Switch 1:
- near first purchased door from spawn
- reveals a timed hidden room
- reward: PaP'd Double Barrel Shotgun wallbuy for 2000

Switch 2:
- at PPSH wallbuy
- reveals a timed hidden room near Mule Kick building
- reward: PaP'd Ray Gun wallbuy for 3000

Normalized:

`SecretSwitch -> RevealRoom(duration=T) -> TemporaryRewardAccess`

This proves temporary world geometry/access is a first-class quest mechanic.

### Secret C — reveal collectible -> shoot collectible -> song

- interact with button on second-story factory balcony
- hidden garage barrier/covering changes
- teddy becomes visible
- shoot teddy
- song plays

Normalized:

`InteractButton -> RevealSecretObject -> ShootSecretObject -> Song`

### Finale

Buyable ending is the Jeep in garage.

## No Man's Land — round-driven world expansion

Source: https://github.com/nzp-team/nzportable/discussions/1450

Verified progression:
- power switch starts/alerts the horde
- every 5 rounds activates additional zombie spawns, capped at round 25
- teleporter accesses the shop
- every 7 rounds expands/unlocks more shop content
- five hidden teddies -> reward + song
- round 35 -> buyable ending
- later versions add zones preventing zombie spawning while players are inside shop
- v1.2 added an exit teleporter pad specifically to prevent softlock
- v1.4 added shop-expansion audio feedback

Normalized:

```
PowerOn -> StartHorde

For round in {5,10,15,20,25}
  -> EnableAdditionalSpawnTier

For round in {7,14,21,28,...}
  -> ExpandShopTier
  -> PlayExpansionFeedback

Round35
  -> EnableEnding

Teleporter
  -> EnterShop
  -> ZoneState(SuppressOutsideSpawns)
  -> ExplicitExitPortal
```

Pattern class:
- `PeriodicRoundGate`
- `CappedProgressionTier`
- `AntiSoftlockExit`
- `ZoneAwareSpawnPolicy`

## Nacht 2.0 — compact PAP unlock

Source: https://github.com/nzp-team/nzportable/discussions/688

Verified:
- three hidden teddies
- all three unlock Pack-a-Punch

Normalized:

`3 ShootableSecrets -> Counter(3) -> EnablePackAPunch`

This is one of the cleanest minimal examples of a quest reward directly enabling a core map system.

## Nacht der Untoten Plus — five-secret PAP quest

Source: https://github.com/nzp-team/nzportable/discussions/1432

Verified:
- Pack-a-Punch Easter egg
- five hidden teddies
- author hints locations by region:
  - one outside
  - one roof
  - one second floor
  - two in the room behind the Help door
- some teddy placements visually interact with nearby barrels/cover and can be difficult to read
- later update moved several teddies and changed interaction text/feedback

Pattern lesson:
- secret placement must be readable enough to solve without noclip
- collision/cover around shootable secrets can accidentally make a puzzle feel bugged even when logic is correct

## Croft Manor — parallel collectible families and ending clue

Source: https://github.com/nzp-team/nzportable/discussions/963

Verified:
- 5 teddy chain -> secret weapon + song
- 3 dragon-trophy chain -> another secret weapon + song
- dragons are **interacted with**, not shot
- multiple minor Easter eggs including a third song
- full Easter egg with map ending
- weapons board inside PaP room is a key clue toward the ending
- 1.1.0 fixed buyable ending

Pattern class:
- `ParallelCollectionFamilies`
- `MixedActivationModes`
- `ClueObject -> MainQuestProgression`

## House — source-inspection correction

Source: https://github.com/nzp-team/nzportable/discussions/903

Verified correction:
- 3 teddies only trigger the music
- Pack-a-Punch is actually available via an illusionary wall on third floor
- secret room also contains random buff-drink dispenser
- this was confirmed by a community member opening the map in a map editor

Normalized lesson:
- player walkthroughs can conflate unrelated secrets
- source/map-editor evidence outranks folklore
- `VisualSecretEntrance` and `CollectibleQuest` must remain separate graph branches until source proves they converge

## BO2 Town — broken quest as failure-analysis reference

Source: https://github.com/nzp-team/nzportable/discussions/470

Verified:
- release advertises a vault EE
- community solved five teddy locations
- intended vault contains multiple weapon rewards
- author later confirms Easter egg is still not working

Use as a negative test case:
- a complete-looking collectible sequence can fail if final transition/reveal is disconnected
- Xziel quest tooling should have graph validation for:
  - unreachable reward nodes
  - no outgoing edge from completed counter
  - missing targetname
  - target resolves to zero entities
  - target resolves only to disabled/dead nodes
  - final world blocker never removed

## Engine requirements derived from these community patterns

Xziel's QuestGraph should support:
- exact N-of-M counters
- shoot/interact/touch/damage activation modes
- global-state predicates at completion time
- temporary room/reveal timers
- round modulo/periodic triggers
- capped tier progression
- zone-dependent spawn policies
- hidden clue objects
- parallel collectible families
- explicit anti-softlock exits
- graph validation before shipping

