# HAYUYA MAP — Open-World World Brain Architecture

**Status:** v1 foundation  
**Branch:** `feature/hayuya-map-world-brain-v1`  
**Goal:** turn heterogeneous real-world, visual, geospatial, and authored references into an evidence-traceable world model that can later compile into Xziel map/runtime assets.

## Non-negotiable design rule: no closed object taxonomy

HAYUYA Map must not be defined by a fixed list such as "building / tree / road / vehicle".

The World Brain stores:
- arbitrary free-form labels and aliases;
- arbitrary properties;
- spatial geometry and coordinate frames;
- arbitrary typed relationships;
- capabilities discovered from geometry/semantics rather than a hard-coded asset class;
- per-observation confidence;
- source provenance;
- uncertainty;
- whether information was **observed**, **inferred**, or **generated**.

An entity may remain `unknown` indefinitely and still participate in geometry, occlusion, collision, navigation, and later reclassification. New concepts do not require a code release merely to exist in the scene graph.

The existing HAYUYA Monster asset profiles remain useful as specialized downstream processors. They are not the ontology of HAYUYA Map.

## Audit of the current Hayuya stack

### Reuse

The existing Monster branch already has production-oriented machinery that should become shared infrastructure:
- multi-reference input;
- ViewForge;
- multiple 3D reconstruction candidates;
- source-aware Judge;
- appearance Judge;
- Material Bridge;
- Mesh Doctor;
- retopology;
- GamePrep;
- mobile portability tiers;
- manifests and QA;
- remote/GitHub execution.

### Current closed-world assumptions to bypass/refactor

`tools/hayuya3d/hayuya.py` currently exposes a finite `ASSET_PROFILE_IDS` set and finite CLI `--mode` choices. Its filename/token heuristics are appropriate as hints for Monster but cannot be the World Brain.

`tools/hayuya3d/internet_asset_research.py` currently uses Wikipedia MediaWiki and a weapon-oriented pattern table. HAYUYA Map needs a provider broker, provenance policy, open-vocabulary perception, and geospatial sources rather than expanding that pattern table.

## World Brain pipeline

### 1. World Intake

Accept any useful combination of:
- concept art;
- sketches/floor plans;
- screenshots;
- photographs;
- image sequences/video;
- drone/aerial imagery when the user has rights to use it;
- satellite/map imagery through licensed APIs;
- Street View imagery through licensed APIs;
- 2D/3D map tiles;
- latitude/longitude or a bounding area;
- OSM/Overture features;
- point clouds / LiDAR / depth;
- meshes / splats;
- existing XZSM/XMAP assets;
- user annotations and text instructions.

Every input gets an immutable source record, hash where applicable, acquisition method, provider, timestamp, coordinate-frame metadata, and usage/attribution policy.

### 2. Source Broker

Providers are adapters, not architecture.

Initial provider families:
- **Google Maps Platform Map Tiles API** — roadmap, satellite, terrain, Street View, Photorealistic 3D Tiles.
- **Google Street View Tiles API** — panorama tiles + metadata where available.
- **Overture Maps** — buildings, places, transportation, divisions, addresses/base/infrastructure depending on release.
- **OpenStreetMap / Overpass** — queryable open geographic features.
- **Mapbox** — map/satellite/terrain/3D presentation and model layers where licensed.
- **Cesium ion / 3D Tiles** — geospatial 3D streaming and coordinate infrastructure.
- **Esri / ArcGIS Reality** — reality-capture/reconstruction interoperability where licensed.
- **generic web-image research** — provider-pluggable reference discovery with provenance.

Secrets never enter Git. Tokens/keys are environment/secret-store inputs.

### Google Images policy

Do **not** build HAYUYA Map around scraping Google Images pages.

Google's Custom Search JSON API historically supports image search, but Google currently documents it as closed to new customers with existing users transitioning by January 1, 2027. Therefore it may be supported as a legacy optional adapter when credentials already exist, but it is not the core dependency.

Image research must be provider-pluggable and must retain:
- source URL;
- host/provider;
- license/usage evidence when known;
- attribution requirements;
- image hash;
- whether the reference is permitted for transient analysis, redistribution, or derived-asset use.

Unknown rights => research/reference evidence only, never silently redistributed into a shipped game.

### 3. Open-World Perception

Use an ensemble instead of a closed classifier.

Recommended layers:
- vision-language model for scene description, attributes, affordances, and relation proposals;
- Grounding DINO family for open-vocabulary text-conditioned detection;
- SAM 2 / Grounded SAM family for masks and video tracking;
- OCR/document/sign reader;
- depth/normal estimation;
- MapAnything / VGGT-style camera + metric geometry reconstruction;
- geospatial foundation models (for example Clay / Prithvi class models) for Earth-observation imagery where useful.

No single detector is authoritative. Every observation enters as evidence.

### 4. Universal World Graph

The canonical intermediate representation is a graph:

`World -> Region -> Entity/Surface/Volume -> observations + relations + geometry`

Example labels are descriptive only, never a schema ceiling:
- `gothic_church`
- `wet_asphalt`
- `broken_stained_glass`
- `utility_pole`
- `storm_drain`
- `unidentified_metal_fixture`
- `tree_with_exposed_roots`

Relations are also extensible:
- inside / contains;
- on / below / above;
- connected_to;
- supports;
- adjacent_to;
- occludes;
- entrance_to;
- traversable_to;
- power_feeds;
- drains_to;
- user-defined predicates.

### 5. Geospatial Fusion

Maintain explicit transformations between:
- WGS84 latitude/longitude/height;
- ECEF;
- local ENU;
- HAYUYA local metric coordinates;
- Xziel world coordinates.

Fuse sources by confidence and purpose rather than flattening them:
- vector map data: topology/roads/building footprint priors;
- terrain/elevation: macro geometry;
- imagery: appearance/evidence;
- Street View/user photos: facade/ground-level evidence;
- reconstruction: metric local geometry;
- authored instructions: creative/gameplay intent.

Never pretend two conflicting sources agree. Preserve the conflict and select a working hypothesis with confidence.

### 6. Geometry / Reality Reconstruction

Use a layered strategy:
1. obtain camera/metric structure;
2. produce depth/point maps;
3. register views;
4. build mesh and/or Gaussian-splat reality representation;
5. segment meaningful entities/surfaces;
6. send hero objects to the existing HAYUYA Monster arena when an isolated high-quality asset is useful;
7. keep large continuous environment geometry in a world-oriented pipeline.

**MapAnything** is a strong research foundation because one transformer can consume images plus optional cameras/depth and solve multiple metric 3D tasks. **VGGT** is a useful camera/depth/point-track challenger. Neither should become an irreplaceable single dependency.

### 7. Missing-space / Interior Inference

Real sources often do not observe interiors, backsides, tunnels, roofs, basements, or occluded spaces.

HAYUYA Map must keep three separate truth layers:
- **OBSERVED** — direct source evidence;
- **INFERRED** — geometrically/semantically plausible completion;
- **GENERATED** — intentionally authored creative content.

Inferred/generated geometry must never masquerade as surveyed truth.

Interior planning can use:
- exterior footprint and floor count;
- visible doors/windows;
- stairs/elevators;
- architectural priors;
- user prompt;
- gameplay constraints.

### 8. World Synthesis

Generate independently controllable layers:
- terrain;
- structural shell;
- interiors;
- roads/paths;
- vegetation;
- props/dressing;
- decals/material variation;
- water/weather;
- lighting/atmosphere;
- collision;
- nav/traversal;
- gameplay volumes;
- spawn/encounter data;
- audio zones/portals;
- streaming cells and LOD/HLOD.

### 9. World Judge

A candidate world is not promoted because it "looks good" once.

Automatic gates should score:
- source alignment;
- camera/metric consistency;
- scale consistency;
- silhouette/depth agreement where applicable;
- topology and holes;
- disconnected/floating geometry;
- material/texture clarity;
- semantic coverage;
- relation consistency;
- building/road footprint agreement;
- walkable connectivity;
- stair/door reachability;
- collision leaks/traps;
- navigation reachability;
- spawn safety;
- line-of-sight/occlusion plausibility;
- streaming-cell health;
- triangles/materials/textures/draw budget by device tier;
- Xziel import/runtime sanity.

Failure should produce actionable evidence, not a single opaque score.

### 10. Xziel Compiler

Target outputs:
- preserved Hero World source package;
- world graph JSON;
- source/provenance manifest;
- metric coordinate transform manifest;
- XZSM render geometry;
- XMAP gameplay/collision data;
- nav graph/navmesh;
- streaming cells;
- LOD/HLOD tiers;
- material/texture packages;
- audio/portal zones;
- gameplay hooks;
- QA renders/reports.

The compiler consumes the graph; it does not need to know every noun that the perception system can discover.

## Google Maps / real-world data boundary

Google Maps Platform is an input/service provider, not a dataset we silently clone.

Implementation must honor current Google terms for:
- attribution;
- display;
- caching/storage;
- allowed mixing with other map datasets;
- session/token handling;
- photorealistic 3D and Street View use.

Where persistent editable geometry is needed, prefer data the project is actually permitted to transform/store (user-owned capture, Overture/OSM under their terms, licensed reality-capture data, or original generated geometry).

## Commercial / premium products worth benchmarking

These are capability references, not code to copy:
- Google Maps Platform / Photorealistic 3D Tiles — planet-scale real-world visual context.
- Cesium — 3D Tiles/geospatial streaming and coordinate handling.
- Mapbox — high-quality mapping/satellite/terrain/3D presentation.
- Esri ArcGIS Reality — photogrammetry/reality capture including meshes/point clouds/splats.
- World Labs Marble — multimodal image/text/video-to-3D-world product reference.
- Meshy / Tripo / Rodin — asset reconstruction/productization references already studied by HAYUYA Monster.

HAYUYA's advantage should be orchestration + evidence + editability + Xziel compilation, not pretending one generative model knows everything.

## Model/research foundations to evaluate

- Meta MapAnything
- Meta VGGT
- Grounding DINO / Grounded SAM
- SAM 2
- Clay Foundation Model
- IBM/NASA Prithvi family
- existing HAYUYA Monster reconstruction arena

Every model must pass a license/commercial-use review before becoming a shipping default.

## Runtime/provider principles

1. **No fixed ontology ceiling.**
2. **No single model authority.**
3. **No hidden source provenance.**
4. **No API key in repository.**
5. **No scraping dependency for services that provide/require official APIs.**
6. **Observed != inferred != generated.**
7. **Unknown is valid.**
8. **User corrections override model guesses and are retained as evidence.**
9. **Hero/source data is preserved before mobile derivation.**
10. **World generation and Xziel optimization are separate stages.**

## v1 implementation milestones

### M1 — World Brain foundation
- dynamic world graph;
- arbitrary labels/properties/relations;
- evidence/provenance records;
- provider registry/readiness;
- plan-only HAYUYA Map CLI;
- CI tests proving unseen labels do not require schema changes.

### M2 — Geospatial intake
- Overture/OSM adapters;
- coordinate transforms;
- bounds/area jobs;
- source cache with policy metadata;
- Google Maps readiness + licensed API client layer.

### M3 — Open perception
- Grounding DINO + SAM 2 ensemble;
- OCR;
- VLM scene/relationship planner;
- semantic graph merge and conflict tracking.

### M4 — Metric 3D
- MapAnything/VGGT arena;
- camera/depth/point-map evaluation;
- mesh/splat reconstruction;
- geo-registration.

### M5 — World synthesis
- terrain/structure/interior layers;
- object isolation -> HAYUYA Monster delegation;
- procedural completion;
- World Judge.

### M6 — Xziel shipping path
- XZSM/XMAP compiler;
- collision/nav;
- streaming cells;
- device tiers;
- Android runtime acceptance gates.

## Public references

- Meta MapAnything: https://github.com/facebookresearch/map-anything
- Meta VGGT: https://github.com/facebookresearch/vggt
- Grounding DINO: https://github.com/IDEA-Research/GroundingDINO
- Grounded SAM 2: https://github.com/IDEA-Research/Grounded-SAM-2
- SAM 2: https://github.com/facebookresearch/sam2
- Google Map Tiles API: https://developers.google.com/maps/documentation/tile/overview
- Google Street View Tiles: https://developers.google.com/maps/documentation/tile/streetview
- Overture Maps: https://docs.overturemaps.org/
- OpenStreetMap Overpass: https://wiki.openstreetmap.org/wiki/Overpass_API
- Cesium + Google Photorealistic 3D Tiles: https://cesium.com/platform/cesium-ion/content/google-photorealistic-3d-tiles/
- Mapbox Maps SDK / 3D: https://docs.mapbox.com/
- ArcGIS Reality: https://www.esri.com/en-us/arcgis/products/arcgis-reality/overview
- Clay Foundation Model: https://github.com/Clay-foundation/model
