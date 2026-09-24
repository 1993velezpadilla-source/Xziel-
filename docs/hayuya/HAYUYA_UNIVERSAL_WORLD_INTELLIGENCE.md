# HAYUYA Map — Universal World Intelligence

**Status:** expanded World Brain design + executable planning foundations  
**Updated:** 2026-09-24

HAYUYA Map is not a Call of Duty Zombies map generator and is not limited to any fixed genre, asset list, map taxonomy, or world provider.

The Zombies atlas remains one specialist body of knowledge. The universal layer sits above it.

## Product mental model

HAYUYA Map should operate like a team of specialists sharing one durable world graph:

1. **Intent Brain** — understands what the user is trying to build.
2. **Universal Game Design Brain** — reasons about navigation, combat, stealth, survival horror, roguelike, metroidvania, puzzle, platforming, racing, open world, extraction, tactical, PvP, co-op, social sandbox, narrative and immersive-sim constraints.
3. **World Reasoning Brain** — architecture, interiors, urbanism, utilities, terrain/drainage, ecology, materials/weathering, lighting/cinematography, acoustics, signage, accessibility, environmental storytelling, AI navigation, multiplayer networking, mobile rendering and monetization.
4. **World Brain** — open-vocabulary entities, evidence, relationships, uncertainty and geospatial coordinates.
5. **Structure Brain** — topology/progression/pressure patterns; Zombies is one selectable specialist.
6. **Lighting Brain** — lighting composition, state changes, readability, atmosphere and mobile budgets.
7. **Perception Ensemble** — vision-language reasoning + open-vocabulary detection + segmentation + OCR + geometry estimation.
8. **Metric Geometry Arena** — independent camera/depth/point/mesh hypotheses.
9. **Asset Brain / HAYUYA Monster** — high-quality isolated asset reconstruction/generation.
10. **Gameplay Graph Solver** — proves routes/gates/loops/dead ends before expensive art.
11. **Monetization Brain** — pre-authors safe inventory while keeping gameplay ad-independent.
12. **World Judge** — evaluates source fidelity, physical/spatial consistency, gameplay, beauty, performance and policy.
13. **Xziel Compiler** — turns the accepted world into runtime render/gameplay/navigation/streaming data.

## Why the universal layer matters

A visually plausible AI scene can still fail as a game because:
- the player can become trapped;
- a required route is unreachable;
- stairs/doors do not work at human scale;
- rain has nowhere to drain;
- utilities appear without service logic;
- AI cannot navigate the same path the player can;
- landmarks do not support wayfinding;
- lighting hides enemies or exits;
- audio ignores rooms and portals;
- multiplayer state cannot replicate cleanly;
- the world cannot stream within a mobile thermal/memory budget;
- monetization conflicts with gameplay.

HAYUYA therefore treats these as first-class world data, not polish.

## Public AI/world-system architecture research

### MapAnything

Transferable pattern:
- treat cameras, depth and metric geometry as coupled tasks;
- accept optional geometric priors;
- use one reconstruction backbone for multiple metric scene tasks.

HAYUYA use:
- metric geometry arena candidate, never sole authority.

Public reference:
- https://github.com/facebookresearch/map-anything

### VGGT

Transferable pattern:
- infer several geometric products from multi-view evidence;
- use independent geometry hypotheses to detect reconstruction failure.

HAYUYA use:
- challenger for camera/depth/point consistency.

Public reference:
- https://github.com/facebookresearch/vggt

### HY-World 2.x

Public project describes a multimodal system for reconstructing, generating and simulating 3D worlds.

Transferable pattern:
- reconstruction, generation and simulation are separate capabilities;
- editable/persistent 3D world representation matters downstream.

HAYUYA use:
- architecture research and optional backend only after checkpoint/license review.

Public reference:
- https://github.com/Tencent-Hunyuan/HY-World-2.0

### HunyuanWorld Voyager

Public project uses camera-conditioned world-consistent RGB-D generation and can produce aligned RGB/depth sequences for 3D reconstruction.

Transferable pattern:
- explicit camera trajectory is a world-generation control;
- RGB and depth should remain aligned;
- long-range extension needs persistent world memory/cache.

HAYUYA use:
- research lane for missing-space expansion and guided exploration.

Public reference:
- https://github.com/Tencent-Hunyuan/HunyuanWorld-Voyager

### HY-WorldPlay

Transferable pattern:
- world consistency is temporal, not only spatial;
- action/state conditioning matters for interactive worlds;
- interactive latency and offline quality are separate targets.

HAYUYA use:
- simulation/reaction research; Xziel remains the deterministic shipping runtime.

Public reference:
- https://github.com/Tencent-Hunyuan/HY-WorldPlay

### World Labs Marble

Public product accepts text, image, video and coarse 3D layout and supports editing/expanding/combining worlds.

Transferable pattern:
- multimodal intake;
- coarse layout as a control signal;
- post-generation editability;
- world expansion as an explicit operation.

HAYUYA use:
- product-behavior benchmark.

Public reference:
- https://www.worldlabs.ai/blog/marble-world-model

### Google DeepMind Genie 3

Public project demonstrates real-time interactive visual world generation from text descriptions.

Transferable pattern:
- evaluate world behavior over interaction/time;
- action consequences are part of world modeling;
- visually generated worlds and editable game-engine geometry are different products.

HAYUYA use:
- interactive simulation benchmark, not geometry authority.

Public reference:
- https://deepmind.google/models/genie/

### WorldGen

Public project supports text/image scene generation, 360 exploration and mesh or Gaussian scene representations.

Transferable pattern:
- use world proxies and depth for scene bootstrap;
- splats and meshes can be parallel representation targets;
- global scale/loop closure require explicit QA.

Public reference:
- https://github.com/ZiYang-xie/WorldGen

### NVIDIA Edify 3D scene composition research

Public research shows a scene-generation application where an LLM proposes object layout/positions/scales and an asset generator creates individual assets.

Transferable pattern:
- scene layout reasoning and asset creation should be separate stages.

HAYUYA already follows this:
- Universal/Structure Brain -> layout
- Monster -> hero asset
- World Judge -> promotion

Public reference:
- https://research.nvidia.com/labs/cosmos-lab/edify-3d/

### Promethean AI

Public product describes an AI asset/world-building brain that reasons over a studio's existing images, video, models, animations and documents while leaving assets in the existing pipeline.

Transferable pattern:
- search/reuse the user's asset library before regenerating;
- metadata and creative decisions are durable knowledge;
- AI should augment an editor workflow rather than hide it.

Public reference:
- https://www.prometheanai.com/ai-world-building

### Ludo.ai

Public product connects ideation, game design documents and asset-generation tools.

Transferable pattern:
- creative intent/genre/platform/perspective should be structured inputs;
- iteration/variation is a first-class workflow;
- accepted decisions should feed later production stages.

Public reference:
- https://ludo.ai/features/game-ideator

### Unreal PCG

Epic's public PCG material emphasizes rule graphs, artist parameters, reuse and large-world procedural population.

Transferable pattern:
- procedural generation must expose rules and artist overrides;
- the same graph concept should work from local dressing through world scale;
- partition/streaming must be considered while generating.

Public reference:
- https://www.unrealengine.com/electric-dreams-environment

## Solver-before-art contract

Before high-cost geometry/texturing, generated gameplay graphs should be evaluated for:

- required-node reachability;
- locked progression edges;
- cycles/loops;
- unintended directed traps;
- dead ends;
- articulation/choke points;
- route redundancy;
- terminal-node correctness.

Initial executable implementation:

`tools/hayuya3d/gameplay_graph_solver.py`

Later solver layers should add:
- agent radius/height;
- traversal abilities;
- door/power/quest states;
- enemy traversal;
- navmesh;
- LOS;
- cover;
- checkpoint/revive;
- co-op separation/rejoin;
- accessibility;
- speedrun/sequence-break simulation.

## Cross-disciplinary plausibility

Every map can use the full knowledge bank; priority is only a compute/reasoning hint.

A church, city, jungle, spaceship, racetrack or surreal nightmare may still need questions such as:
- what physically supports it?
- how does someone circulate through it?
- where does water go?
- where do utilities/service routes go?
- why does vegetation/weathering look this way?
- how does sound move?
- how will a lost player orient themselves?
- can NPCs and co-op players traverse it?
- how does it stream on mobile?

For fictional/supernatural spaces, HAYUYA may intentionally break reality, but the break should be an authored rule rather than an accidental AI error.

## Monetization architecture

HAYUYA keeps two ad lanes separate.

### Direct Diegetic Sponsor

World-space inventory:
- posters/notices;
- screens/projectors;
- world-positioned radio/TV audio;
- believable prop branding;
- environment text;
- banners/flags;
- vehicle livery;
- arena/sports boards;
- storefront branding.

Each candidate requires:
- geometry fit;
- gameplay/nav/narrative exclusion;
- fallback lore asset;
- creative/content validation;
- bounded performance cost;
- exposure telemetry off realtime threads.

No paid campaign means the fallback remains, so the world never depends on advertising.

### Google AdMob UI

Google Mobile Ads formats remain in the app/UI layer:
- App Open during safe foreground/loading moments;
- Interstitial only at natural transitions such as completed match -> summary/lobby;
- Rewarded only after explicit player opt-in;
- Native UI only inside the required native ad container with attribution/AdChoices;
- banner UI is optional and is not placed over continuously interactive gameplay.

Do not texture-bake a Google native ad onto arbitrary 3D world geometry.

The World Brain emits hooks before SDK integration so map/game code does not later need invasive changes.

## Automatic diegetic slot discovery

World entities can expose semantic capabilities rather than advertising-specific object classes:

- `flat_noninteractive_surface`
- `screen_or_projector`
- `radio_or_speaker`
- `brandable_prop`
- `environment_text_surface`
- `cloth_banner_anchor`
- `vehicle_body_panel`
- `arena_perimeter_board`
- `storefront_fascia`

HAYUYA Monetization Brain can propose a candidate from these capabilities.

It must reject candidates tagged as gameplay/navigation/narrative critical, corpse/gore, boss focal, objective/quest surface, HUD, revive/downed UI, accessibility cue, or other hard exclusion.

Semantic candidate != sellable placement.

Only geometry-fit + actual player-route capture + policy validation promotes a candidate.

## Clean-room rule

"Reverse engineer" in HAYUYA means:
- inspect public documentation;
- inspect legally available open-source code;
- compare documented product capabilities;
- infer reusable architectural principles;
- implement original code and original content.

It does not mean:
- bypass access controls;
- scrape private APIs;
- extract proprietary game source;
- copy proprietary model weights/training data;
- clone maps/assets/scripts/lightmaps.

The target is to understand **why strong systems work**, then build HAYUYA's own implementation.
