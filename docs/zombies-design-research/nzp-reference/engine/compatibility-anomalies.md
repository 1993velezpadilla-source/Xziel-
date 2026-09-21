# NZ:P Quest Compatibility / Source Anomalies

Updated: 2026-09-20

Pinned references:

- `nzp-team/assets@c8135a66e00bb64577912fbf792f8fef7f47658e`
- `nzp-team/quakec@dc107a103a9a5bdb53bdef78c6d8cb18a4dd6163`

Purpose: record places where the mapper FGD, public documentation, compiled-map pipeline, and current QuakeC runtime do **not** obviously describe the same thing. These are high-risk areas for a clean-room Xziel quest implementation.

## 1. `func_counter` and `func_oncount`: FGD-visible, runtime symbol not found

Both current upstream FGD files expose:

- `func_counter` — "Activation Counter"
- `func_oncount` — "Counter Target"

However, a search of the pinned server QuakeC snapshot finds no corresponding `func_counter` or `func_oncount` implementation symbol, and the 20 official source-map snapshot contains no entities using either classname.

Current evidence classification:

`FGD_DEFINED / SERVER_QC_SYMBOL_NOT_FOUND / OFFICIAL_MAP_USAGE_NOT_FOUND`

Possible explanations include legacy/stale editor definitions, engine-side handling, compatibility translation, or removed code. Do not rely on these classes in Xziel until an executable runtime path is proven.

Preferred current NZ:P counter precedent is `game_counter`, which has source implementation and tests.

## 2. `spawn_zone`: authoring marker, not ordinary runtime entity

The FGD exposes `spawn_zone`, but current `source/server/ai/zoning_core.qc` explicitly removes `spawn_zone` entities at runtime.

The NZ:P map toolchain processes authored zone data separately. Therefore a zone brush is best understood as **authoring/compiler input** rather than a normal quest node that persists as a runtime trigger.

Xziel should likewise separate:

- editor-only volumes / baking metadata
- runtime zone graph
- player current-zone state
- AI spawn eligibility

Do not copy the old classname semantics directly into runtime quest logic.

## 3. `delay` versus `round_delay`: source/documentation mismatch

Current `SUB_UseTargets` source checks:

1. `delay`
2. then `round_delay`

Both branches create a delayed-use object and return. Therefore in the pinned source, if both are non-zero, ordinary seconds delay wins before round delay can be considered.

Public mapping documentation has described round delay as taking precedence over delay.

Classification:

`DOCS_SOURCE_MISMATCH`

Xziel must define this deterministically rather than preserve ambiguity. Recommended model:

- `DelaySeconds(n)`
- `DelayRounds(n)`
- allow explicit composition if both are wanted

## 4. Multi-target fan-out goes through `target` ... `target8`

The current runtime event bus supports eight named target slots plus `killtarget`.

This is broader than a simplistic `target -> one destination` model. Many quest graphs depend on one interaction producing parallel world-state, audio, UI and progression effects.

Xziel should use an unbounded/array-based action list rather than reproducing an eight-slot limit.

## 5. `killtarget` is not deletion by pointer

`SUB_UseTargets` searches **all** entities whose `targetname` equals the requested `killtarget` and fake-removes them.

This is a selector-based world-state action. In source maps it is used for:

- secret blockers
- PAP blockers
- collectible visuals
- quest keys
- interaction blockers

Xziel should represent this as an explicit named/tagged world-state removal action and define save/restore behavior.

## 6. Spawn-target side effects are broader than quest startup

Player spawn entities can fire targets. This means a target attached to a player spawn may execute on respawn as well as initial match start, depending on the current game path.

The official `nzp_xmas2` source targets `q_gramo_start` from all four player spawn entities. That is useful initialization precedent, but Xziel should distinguish:

- `OnMatchStart`
- `OnPlayerFirstSpawn`
- `OnPlayerRespawn`
- `OnPlayerJoinLate`

rather than overloading spawn targets.

## 7. `trigger_interact` is deliberately single-use-until-rearmed

A mapper might reasonably assume an interaction volume remains continuously usable. Current runtime does not: after successful use, its touch function is disabled until another event re-arms it.

This behavior is powerful for quests but also easy to misread from map data. A source extractor must preserve **arming edges**, not merely count interactions.

## 8. `trigger_activator` is specialized despite its generic name

Current runtime behavior is oriented around activating inactive zombie-spawn targets and then rebuilding spawn IDs.

Do not infer generic "activator" semantics from the classname. This is a source-level semantic trap.

## 9. Teddy/secret behavior is target-driven, not teddy-specific

`teddy_spawn` is a damageable event source. Different maps use it to:

- increment songs
- remove/reveal other entities
- target labels such as Jug/PAP
- produce arbitrary target-graph actions

Therefore Xziel must not encode `TeddyEasterEgg` as an engine primitive. Use generic shootable/interactable quest sources plus content data.

## 10. Legacy release behavior changed across NZ:P versions

Community release changelogs and old map reports show that target routing, killtargets, moving doors, teleporter behavior and old entity compatibility have changed over NZ:P versions.

Therefore every extracted community map needs both:

- map/archive revision
- NZ:P runtime version or test date when known

A map that was broken on an old PSP/3DS build may be correct on the current runtime; likewise a historically working workaround may be unnecessary today.

## Compatibility classification used by this corpus

- `CURRENT_SOURCE_PROVEN`
- `CURRENT_TEST_PROVEN`
- `OFFICIAL_MAP_USAGE_PROVEN`
- `COMMUNITY_RUNTIME_REPORTED`
- `FGD_ONLY`
- `DOCS_ONLY`
- `LEGACY_SOURCE`
- `DOCS_SOURCE_MISMATCH`
- `BROKEN_IN_REPORTED_VERSION`
- `SOURCE_AVAILABLE_NOT_EXTRACTED`

These labels should accompany future quest primitives so provenance never gets lost.

