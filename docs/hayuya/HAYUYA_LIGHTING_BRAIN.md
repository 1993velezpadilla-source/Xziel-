# HAYUYA LIGHTING — Semantic Lighting Brain v1

**Status:** v1 foundation  
**Parent:** HAYUYA MAP World Brain  
**Purpose:** turn world semantics, gameplay routes, material evidence, atmosphere goals, and device constraints into an authored lighting plan.

## Why this is separate from geometry reconstruction

A reconstructed world can be metrically accurate and still look dead.

HAYUYA Lighting therefore operates as its own reasoning pass after the World Brain has enough geometry and semantics to understand:

- traversable floors;
- walls/ceilings/openings;
- major landmarks;
- player-critical routes;
- combat spaces;
- interaction anchors;
- likely practical light fixtures;
- outdoor/indoor transitions;
- material response;
- weather and time-of-day intent.

It does not blindly brighten the reconstruction. It composes the scene.

## Inputs

HAYUYA Lighting may consume:

- World Graph entities and relations;
- map-design intelligence;
- observed lights in references;
- user art direction;
- material/albedo/roughness/emissive evidence;
- portal/room graph;
- nav graph;
- spawn pressure vectors;
- quest/progression state graph;
- weather/time-of-day state;
- device tier.

## Output layers

1. **Base visibility** — critical navigation and combat floor remain readable.
2. **Motivated practicals** — bulbs, candles, lamps, fire, machinery, moon/window spill, electrical effects, or authored supernatural sources.
3. **Landmark guidance** — contrast guides the player toward important silhouettes and destinations.
4. **Anxiety shadow** — preserve negative space and partial information outside critical readability.
5. **Event lighting** — authored state changes such as lightning, power startup, ritual pulses, fixture failure, or boss escalation.
6. **Mobile derivation** — bake, cluster, cull or simplify lights without destroying composition.

## Power-state contract

Power is a scene transition, not a boolean UI unlock.

### Power off

- readable floor;
- localized practicals;
- strong exterior spill where appropriate;
- unresolved noncritical depth;
- landmark silhouette preserved.

### Power on

- lights energize in authored sequence;
- machinery/emissive materials wake up;
- new routes become easier to read;
- the map must retain shadow and threat;
- newly active machinery may create new moving shadow or danger cues.

## Horror composition rules

- Darkness is not pure black.
- Combat information wins over mood when the two conflict.
- Strong lights need a believable source or explicit supernatural cause.
- Repetition must be intentional; random flicker everywhere is rejected.
- Projected shadow, silhouette and occlusion are preferred over flat brightness.
- Rare event lighting is more powerful than constant effects.
- Exterior weather can be part of lighting composition.
- A major landmark should retain a readable lighting identity across states.

## Beauty Judge

A map does not pass merely because every polygon is visible.

The judge checks:

- critical-path luminance separation;
- enemy silhouette separation;
- depth layering;
- landmark contrast;
- coherent color-temperature relationships;
- material response;
- exposure consistency;
- darkness reserve;
- practical-source justification;
- event-state readability;
- dynamic-light cost by device tier.

## Mobile policy

The Hero World preserves authored intent first.

Portable derivation may then:

- cull invisible lights by room/portal/cell;
- prioritize shadow casters near the player;
- bake stable distant contribution;
- replace distant dynamic fixtures with emissive/material cues;
- use sparse camera-relevant volumetric effects;
- keep event lights deterministic and bounded;
- retain the same progression/landmark composition across fidelity tiers.

The mobile pass is not allowed to flatten the scene into uniform lighting simply to reduce cost.

## Zombies knowledge integration

For Xziel Zombies work, the lighting brain can consume:

- `docs/WAW_ZOMBIES_HORROR_DNA.md`;
- `docs/waw-zombies-horror-checklist.json`;
- `docs/zombies-map-dna-atlas.v1.json`;
- `docs/sanctum-zombies-dna-profile.v1.json`.

These sources provide abstract design evidence only. HAYUYA must author original light placement, geometry, textures, assets and event sequences.

## Runtime handoff

HAYUYA Lighting emits an authored plan suitable for later compilation into:

- static/baked contribution;
- dynamic light entities;
- shadow policy;
- emissive states;
- light groups/circuits;
- event curves;
- zone exposure/fog data;
- XMAP logic links;
- Xziel runtime quality tiers.

The renderer remains responsible for implementing the result efficiently. HAYUYA Lighting owns composition intent.
