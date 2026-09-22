# Xziel Engine — mobile VFX architecture

Date: 2026-09-20

## Design goal

Rain, fog, splashes, lightning, wind, smoke and combat particles should look
modern without turning a mobile GPU into a transparency/overdraw furnace.

The effect library is renderer-independent. The simulation emits compact render
items; the future Vulkan renderer decides whether an item is a billboard,
streak, mesh particle, decal, light pulse, fog volume or GPU-simulated effect.

## Effect vocabulary

The engine-level particle kinds now cover:

- rain
- surface splash
- fog
- mist
- smoke
- dust
- sparks
- embers
- snow
- ash
- blood mist
- debris
- steam
- fireflies / ambient motes

Lightning is split into two layers:

1. deterministic storm/light pulse in EnvironmentSystem
2. visual bolt asset/procedural bolt in the renderer

Wind is not a particle itself. It is a shared vector field/input that affects
rain, snow, ash, smoke, foliage and selected debris.

## Performance rules already implemented

### Fixed-capacity pools

ParticleEmitter allocates all SoA buffers at construction. Per-frame update,
spawn and render-item generation do not allocate.

### Structure of arrays

Position, velocity, age, lifetime, size and rotation live in separate packed
arrays. This favors sequential mobile CPU access and later maps naturally to
GPU storage buffers.

### Packed active range

Expired particles are removed by swapping the last live particle into the
hole. There is no fragmented free-list traversal.

### Bounded spawn catch-up

A resumed or stalled phone cannot create thousands of delayed particles in one
frame. The spawn burst is hard-capped and old debt is discarded.

### Distance-based spawn LOD

Emitters stop spawning outside their authored distance. Spawn density fades
before the cutoff. Existing particles can retire normally.

### Caller-owned render buffer

The simulation fills caller-owned ParticleRenderItem memory. It does not create
a vector or heap allocation every rendered frame.

## Vulkan renderer rules

Transparent effects are one of the easiest ways to destroy mobile fill rate.

Samsung recommends minimizing overdraw; opaque objects should benefit from
early depth/stencil and transparent work comes afterward. Android similarly
warns about the cost of transparency/overdraw.

References:
https://developer.samsung.com/galaxy-gamedev/resources/articles/usage.html
https://developer.android.com/topic/performance/rendering/overdraw

Therefore Xziel will:

- batch particles by material/blend/depth mode
- use camera-local rain rather than filling the entire map
- cull emitters before particle expansion
- use depth-aware fading/soft particles only on tiers that can afford it
- aggressively reduce fog/smoke layers on fill-rate-limited GPUs
- render rain as stretched quads/streaks rather than expensive geometry
- reserve mesh particles for nearby debris
- use decals or material response for persistent wet/blood marks
- keep lightning mostly as a tiny bolt mesh/sprite plus scene light/exposure
  pulse rather than thousands of particles
- avoid dynamic shadows on normal particles

Android notes that Vulkan requires the application to perform its own pipeline
reuse/optimization rather than expecting the driver to do it. Pipeline and
descriptor reuse therefore belongs in the renderer cache.

Reference:
https://developer.android.com/ndk/guides/graphics/design-notes

Reduced precision is also useful on mobile. Android documents FP16 as a way to
reduce memory bandwidth/cache pressure and improve throughput when precision is
sufficient. Particle color/size/age and many VFX shader intermediates are good
candidates after visual validation.

Reference:
https://developer.android.com/games/optimize/vulkan-reduced-precision

## Adaptive performance

PerformanceGovernor now tracks the slower of CPU/GPU frame time with smoothing
and hysteresis. It changes a RenderWorkload rather than randomly toggling
individual effects.

Quality changes affect together:

- render scale
- particle density
- shadow distance
- fog quality
- dynamic-light count
- shadowed-light count
- shadow-map resolution

Thermal state can impose an immediate quality ceiling. This is intended to be
fed by Android thermal/ADPF signals when the native platform layer lands.

Android explicitly recommends adapting workload to thermal conditions to avoid
thermal throttling.

Reference:
https://developer.android.com/games/optimize/power

## Free/open VFX search and provenance

A source manifest lives at:

assets/vfx/sources.json

Current reviewed candidate catalogs/packs:

- Kenney Particle Pack — CC0, 80 VFX/particle/light-cookie sprites
- Kenney Smoke Particles — CC0, smoke/explosion/puff sprites
- Kenney Splat Pack — CC0, 30+ splat/decal sprites
- hdst lightning sprite on OpenGameArt — CC0
- Poly Haven — CC0 HDRIs, PBR textures and models

Kenney pages explicitly identify these packs as CC0. Poly Haven states its
assets are CC0 and its public API can enumerate/download the library.

The repository intentionally does not silently pull mutable internet assets
into a release. scripts/fetch_free_vfx.py downloads a reviewed candidate,
prints SHA-256 and supports a release-safe --require-locked mode. We pin the
hash only after inspecting the downloaded archive and confirming the source
page/license.

Sources:
https://kenney.nl/assets/particle-pack
https://kenney.nl/assets/smoke-particles
https://kenney.nl/assets/splat-pack
https://opengameart.org/content/lightnings
https://polyhaven.com/license
https://polyhaven.com/our-api

## Blender/procedural fallback

We do not need a desktop Blender session for every effect.

Rain streaks, snow, ash, sparks, lightning bolt ribbons, fog noise cards and
simple splash meshes can be generated procedurally by build tools. Blender is
useful later for authored mesh VFX and baking flipbooks, but the engine should
never depend on a proprietary/ripped effect just because a free sprite was not
available.

A future headless Blender build step may be added only for reproducible,
scripted generation and will output glTF/KTX2 assets with a provenance record.
