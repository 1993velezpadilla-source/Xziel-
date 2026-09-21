# Xziel AAA-Mobile Engine Synthesis

Research date: 2026-09-21

Reference titles:
- Call of Duty: Mobile
- Apex Legends Mobile
- PUBG Mobile
- Arena Breakout
- Wuthering Waves
- Call of Duty: Warzone Mobile
- Delta Force
- Earth: Revival
- LifeAfter (software-occlusion subsystem study)

## What all successful high-end mobile engines converge on

The exact engines differ, but the engineering patterns repeat:

1. **Device-specific scalability**
2. **Bandwidth-aware rendering**
3. **Aggressive visibility reduction**
4. **Precomputation wherever possible**
5. **Streaming instead of all-resident content**
6. **Shader/PSO prewarming**
7. **Stable sustained frame rate over cold peak FPS**
8. **Thermal and power telemetry**
9. **Different rendering techniques by capability tier**
10. **Presentation decoupled from authoritative simulation**

## Per-game strongest lesson

| Title | Strongest reusable lesson for Xziel |
|---|---|
| COD Mobile | adaptive thermal/device quality governor + scalable PBR |
| Apex Legends Mobile | CPU cluster culling + mobile RenderPass/LiteHDR discipline |
| PUBG Mobile | massive device matrix + CPU occlusion + RHI threading |
| Arena Breakout | hybrid Vulkan Ray Query + frame prediction/high refresh |
| Wuthering Waves | one-pass deferred + measured power engineering |
| Warzone Mobile | shared high-end content with mobile-specific renderer/cook, plus streaming/product cautions |
| Delta Force | unified source content + automatic platform recomposition + feature planning |
| Earth: Revival | render graph + multithreaded rendering + tile-based deferred + hybrid occlusion |
| LifeAfter | software occlusion benchmark: ~1.5 ms low-end / ~65% average draw-call reduction |

## Proposed Xziel renderer stack

```
                     XZIEL
                       |
               Authoritative Vril
          QuakeC / collision / rules
                       |
            presentation snapshots
                       v
          +-------------------------+
          |      Xz Runtime         |
          +-------------------------+
             |       |       |
             |       |       +--> Audio / VFX
             |       +----------> Streaming / Animation
             +------------------> Renderer
                                  |
                            Xz Render Graph
                                  |
                    +-------------+-------------+
                    |                           |
              Forward / Forward+        Future One-Pass Deferred
                    |                           |
                    +-------------+-------------+
                                  |
                                XzRHI
                         /        |        \
                   GLES3       Vulkan     Legacy
                                          GL4ES
```

## Rendering quality tiers

### Compatibility
- legacy/GLES fallback
- lightmaps
- simple directional lighting
- low particle limits
- no expensive screen-space effects

### Low
- GLES3
- simplified PBR
- reflection probes
- baked GI
- short shadow distance
- basic SSAO optional

### Medium
- full standard PBR
- short-range CSM
- probes + lightmaps
- SSR/GTAO selectively
- better VFX and decals

### High
- Vulkan preferred
- richer dynamic lighting
- higher shadow quality
- dynamic resolution
- upscale
- stronger weather/VFX
- optional one-pass deferred experiment by GPU family

### Ultra
- Vulkan
- high-refresh path
- selected Ray Query effects
- temporal reconstruction/frame prediction where validated
- highest animation/VFX budgets

## Visibility architecture

Combine the strengths of classic Quake spatial data and modern mobile rendering:

```
BSP/PVS
  -> semantic room/cell visibility
  -> object frustum cull
  -> projected-size cull
  -> CPU occlusion
  -> mesh-cluster hierarchy
  -> optional GPU/HZB refinement
  -> instance/dynamic batch
```

This should be one of Xziel's biggest advantages.

## World streaming architecture

Use room topology as natural streaming information.

```
Current room
 + visible door graph
 + player velocity
 + destination prediction
        |
        v
Priority streamer
        |
  +-----+------+-----+------+
  mesh texture audio shader
```

Each room/cell:
- low-res always-ready representation;
- optional high-res textures;
- render mesh chunks;
- lightmap/probe pages;
- audio ambience;
- local VFX;
- cached pipelines.

Gameplay-critical collision/state never depends on optional visual streaming.

## Material architecture

Shared PBR model:
- base color
- normal
- roughness
- metallic
- AO
- emissive

World surfaces should maximize:
- texture arrays
- atlases where safe
- shared shader permutations
- instance parameters
- packed textures
- ASTC on supported Android

Avoid unique materials for trivial variations.

## Lighting

Default:
- baked static GI
- lightmaps
- SH/probes for moving entities
- reflection probes
- one dominant realtime directional light when needed
- strict local-light budget

High tier:
- SSR/GTAO

Ultra:
- selective Ray Query reflections/shadows/AO

Never require RT for the intended art style.

## Shadows

Use:
- baked static shadow visibility
- short CSM near player
- cached static shadow depth
- simplified actor shadows at low tier
- selective ray-query soft shadows only on capable devices

## Mesh-cluster cooker

Offline:
- partition large mesh into spatial triangle clusters
- create hierarchy
- reorder index buffer
- store compact bounds/index ranges

Runtime:
- recursively test visible hierarchy
- merge contiguous visible sections
- submit only useful geometry

Target CPU cost:
< 0.5 ms on representative mid-tier device for a map view.

## Batching

Two runtime paths:

### Compatible path
- CPU builds compact instance data
- UBO/uniform-backed instance records
- gl_InstanceID
- cache visible instance combinations

### Advanced path
- SSBO/indirect/device-address Vulkan implementation
- only enabled where it benchmarks faster

Do not assume GPU-driven automatically wins on mobile.

## Post-processing

Low:
- tonemap in cheapest possible final/base path
- no heavy multi-pass stack

Medium:
- lightweight bloom
- basic exposure/color grade

High:
- temporally amortized bloom/exposure
- higher quality SSR/GTAO

Ultra:
- reconstructive/upscale features

Every post effect must publish:
- GPU ms
- bandwidth
- render-target memory
- temperature/power delta in A/B tests

## XzPerformanceGovernor

Inputs:
- CPU frame ms
- GPU frame ms
- thermal headroom
- memory pressure
- refresh rate
- power mode
- recent stutter
- renderer/backend
- device profile

Outputs:
- render scale
- FPS target
- LOD bias
- shadow distance/resolution
- animation update rate
- VFX budget
- light budget
- SSR/GTAO/RT state
- streaming aggressiveness

Use hysteresis and cooldown windows to prevent visible quality oscillation.

## XzFeaturePlanner

Delta Force adds a stronger idea on top of ordinary quality presets: treat scalable presentation features as an optimization problem.

Each candidate feature has:
- visual value;
- gameplay value;
- CPU cost;
- GPU cost;
- memory cost;
- dependencies/conflicts;
- distance/screen-size/importance constraints.

The planner selects the best feature set that fits the current budgets.

This lets Xziel preserve premium presentation on the most important entities instead of degrading the whole scene uniformly.

Example:
- nearest zombie: full animation rate, hit reaction, dynamic shadow, premium VFX/audio;
- mid zombie: lower animation rate, cheaper shadow, reduced VFX;
- distant zombie: authoritative gameplay unchanged, but no IK/dynamic shadow and minimal presentation cost.

XzPerformanceGovernor chooses the global budgets; XzFeaturePlanner distributes those budgets intelligently.

## Shader / PSO system

At cook time:
- enumerate valid material/backend/tier combinations
- strip impossible variants
- produce warmup manifest

At runtime:
- persistent pipeline cache
- prewarm critical content
- telemetry on misses
- background warm optional content

No first-shot shader compile.

## Animation

Long-term:
- skeletal mesh path
- GPU skinning
- compressed clips
- additive recoil
- animation graph
- update-rate optimization
- distance LOD

Classic MDL remains compatibility content.

## High-refresh strategy

60 FPS is the baseline goal for capable devices.

90/120/144 should require:
- sustained thermal headroom
- correct frame pacing
- enough CPU and GPU headroom
- verified input latency
- no major visual degradation

Later:
- frame prediction/reconstruction as an optional Ultra feature.

## Ray tracing strategy

Ray Query is a late-stage enhancement.

Required before RT:
- Vulkan backend mature
- material IDs/proxies stable
- acceleration-structure memory budget
- low-res temporal denoiser
- fallback path

Never enable on model name alone. Benchmark it.

## Power lab

A/B test engine changes using:
- same device
- same brightness
- same camera path
- same FPS target
- same scene
- same duration
- similar starting temperature

Measure:
- CPU
- GPU
- memory
- power rails when available
- thermal state
- frame-time percentiles

Performance is not "FPS only."

## Near-term Xziel implementation order

### 1. Instrumentation
- XzFrameMetrics
- XzMemoryBudget
- XzDeviceCaps
- XzPerformanceGovernor
- thermal hooks
- frame pacing

### 2. Content/runtime recomposition
- XzFeaturePlanner
- XzVirtualMaterial
- platform/quality cook profiles
- runtime-level builder
- gameplay collision contracts
- automatic asset validation and performance estimates

### 3. Modern rendering foundation
- XzRHI
- XzRenderGraph
- GLES3 backend
- GPU timers
- resource lifetime tracking
- transient render-target pool
- render-pass/subpass abstraction
- multithreaded render preparation

### 4. Visibility
- room/cell layer over BSP
- CPU/software occlusion with conservative occluder meshes
- zero-false-occlusion regression path
- static instancing
- cluster cooker/culling
- target <=1.5 ms SOC stress cost on representative low/mid hardware when enabled
- target strong indoor draw-call rejection before default-on

### 5. Materials/lighting
- linear PBR
- texture arrays
- lightmaps
- probes
- short-range shadows

### 6. Streaming
- asynchronous textures/meshes/audio
- memory-aware eviction
- preload graph

### 7. Vulkan
- backend
- PSO cache
- renderpass/subpass capabilities
- dynamic resolution/upscale

### 8. Modern presentation
- skeletal animation
- VFX engine
- decals
- unified/spatial audio

### 9. Experimental flagship features
- one-pass deferred
- RT Ray Query
- frame prediction/high-refresh reconstruction

## Release philosophy

The target is not maximum screenshot quality.

The target is:

```
AAA visual language
+ predictable memory
+ fast loading
+ stable input
+ sustained thermals
+ broad Android support
+ graceful quality degradation
```

The strongest lesson from the accumulated production case studies is that mobile AAA quality comes from **removing invisible work, cooking the right representation for the target, and spending runtime budget only where the player can perceive the value**.
