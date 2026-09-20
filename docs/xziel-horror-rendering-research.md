# Xziel Engine — horror presentation + reflection/shadow strategy

Date: 2026-09-20

## Design target

The engine should create fear through anticipation, uncertainty, spatial audio,
contrast and readable danger rather than permanently maxing every effect.

A constant 100% intensity is not frightening for long. The new HorrorDirector
therefore has separate tension and adrenaline envelopes with different attack
and release rates. Safe spaces deliberately release pressure, while chase,
proximity, damage, low health/ammo, darkness and isolation contribute bounded
signals.

The director outputs *presentation targets only*:

- ambient drone gain
- heartbeat/breathing gain
- vignette
- exposure bias
- subtle camera breathing
- light flicker amount/rate
- fog boost
- authored-window audio stinger request

It never changes zombie damage, hit registration, player input or other
gameplay-critical state.

## Audio latency

Horror depends heavily on audiovisual timing. Android recommends Oboe/AAudio
low-latency mode, callbacks, avoiding locks/allocation/file I/O inside the audio
callback, and a roughly double-burst buffer target.

Reference:
https://developer.android.com/games/sdk/oboe/low-latency-audio

This will inform the future native mixer. HorrorDirector parameters are control
plane values and must be smoothed outside the real-time callback.

## Mobile renderer choice

Khronos currently documents Forward+ as a strong middle ground when an engine
needs many local lights while retaining forward rendering's friendly handling
of transparency and MSAA.

Reference:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Advanced_Topics/Forward_ForwardPlus_Deferred.html

Xziel target:

- depth/prepass when scene complexity warrants it
- Forward+ tiled/clustered local-light assignment
- forward transparent pass for glass/water/particles
- baked lighting/lightmaps for static environment
- limited high-value dynamic shadow lights
- PBR materials for wetness, metal, concrete, glass and water

## Reflections: quality hierarchy

Mirrors and water should not all use the same reflection technique.

### Static reflection probes

Cheapest fallback and baseline for shiny/wet materials. Good for rough
reflections, distant surfaces and thermally constrained devices.

### Screen-space reflections

Useful for wet floors, puddles, water and polished materials because they reuse
the main camera buffers rather than rerendering the entire scene. They cannot
reflect off-screen information, so they should blend into a probe fallback.

AMD FidelityFX SSSR documents hierarchical screen-space traversal plus temporal/
spatial denoising for stable glossy reflection signals and supports Vulkan.

References:
https://gpuopen.com/fidelityfx-sssr/
https://gpuopen.com/manuals/fidelityfx_sdk/techniques/stochastic-screen-space-reflections/

The Xziel planner exposes SSR as a capability; the first renderer may implement
a simpler hierarchical-Z SSR before evaluating FidelityFX integration on
Android GPUs.

### Planar reflections

Best baseline for actual mirrors and calm water because they can reflect
off-screen geometry correctly, but they require an extra reflected scene render.

Khronos's Vulkan engine tutorial demonstrates exactly this pattern: an optional
off-screen reflection pass, mirrored camera, color/depth target, then sampling
the reflection in the main/transparent path.

References:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Advanced_Topics/Planar_Reflections.html
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Advanced_Topics/Rendering_Pipeline_Overview.html

Therefore Xziel hard-budgets planar passes. Low tier can use none; higher tiers
get one or a very small number. Planar textures can update every 2–4 frames and
reuse the previous image between updates.

### Ray-traced reflections

Not a baseline Android feature. Ray Query is capability-gated future work only.
The engine must remain visually correct through probes/planar/SSR when ray
tracing extensions are unavailable.

## Shadows

Shadow maps remain the portable baseline. Khronos describes shadow mapping as
rendering depth from the light's point of view then comparing that depth during
lighting. Ray-query shadows exist but require optional hardware/extensions.

References:
https://github.khronos.org/Vulkan-Site/samples/latest/samples/performance/multithreading_render_passes/README.html
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Lighting_Materials/07_shadows.html

Xziel strategy:

- static environment: baked shadow/light data whenever possible
- moon/sun: limited cascaded shadow map
- important moving spot lights: dynamic shadow map
- point lights: dynamic cube/omnidirectional shadow only when budget allows
- unimportant/distant local lights: baked/no dynamic shadow
- static local shadow maps update less frequently
- moving lights update every frame only when actually selected by budget

This avoids "every light casts a realtime shadow," one of the easiest ways to
murder a mobile frame budget.

## Water

WaterSystem now exposes cheap time-varying parameters:

- two-direction normal scrolling
- wave phase
- wind/rain-responsive foam
- reflection/refraction strength
- Fresnel bias
- roughness

The Vulkan shader can combine two normal samples, depth-based color,
Fresnel reflection and optional planar/SSR/probe reflection. Large FFT ocean
simulation is intentionally not a dependency for a Zombies map with puddles,
flooded rooms or small exterior water surfaces.

## Mobile bandwidth/overdraw rules

Mobile GPUs are commonly tile-based and bandwidth/power constrained. Khronos
advises minimizing main-memory round trips, state changes and unnecessary
render passes; Samsung recommends early depth/stencil and front-to-back opaque
submission, then transparency.

References:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Mobile_Development/04_rendering_approaches.html
https://github.khronos.org/Vulkan-Site/tutorial/latest/Advanced_Vulkan_Compute/12_Mobile_and_Embedded_Compute/03_mobile_optimization.html
https://developer.samsung.com/galaxy-gamedev/resources/articles/usage.html

Xziel renderer rules:

- transient tile-local depth/intermediate attachments where appropriate
- merge/fuse passes when that actually reduces bandwidth
- reuse descriptors/pipelines and render targets
- front-to-back opaque submission
- batch transparent VFX by material
- dynamic resolution for the 3D scene; native-resolution HUD
- reflection and shadow passes use lower resolution when quality tier drops
- mirror/water captures skip frames and reuse previous results
- fog and SSR may run at reduced resolution then composite
- no per-frame resource creation in the render loop
- no Vulkan feature is enabled merely because one vendor exposes it; every
  optional path has a portable fallback and capability check

Samsung documents reduced-resolution scene rendering followed by native-size UI
as an effective way to lower fragment shading cost, and notes that a fullscreen
quad upscale can be preferable to vkCmdBlitImage on mobile GPUs.

Reference:
https://developer.samsung.com/galaxy-gamedev/resources/articles/usage.html

Android also documents FP16/reduced precision as a bandwidth/cache/throughput
optimization when the precision is sufficient.

Reference:
https://developer.android.com/games/optimize/vulkan-reduced-precision

## Stability rule

Visual ambition never gets to destabilize gameplay.

Every expensive feature must satisfy all of these:

1. capability check
2. explicit quality budget
3. deterministic fallback
4. bounded memory/resource count
5. no unbounded frame catch-up
6. automated tests for planners/state machines
7. real-device profiling before raising default quality

That means a broken mirror falls back to a reflection probe; an overloaded GPU
reduces SSR/planar/shadow cost; thermal pressure reduces presentation quality;
none of those cases may break movement, shooting, zombie simulation or map
logic.
