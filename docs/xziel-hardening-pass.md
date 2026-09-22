# Xziel Engine — hardening pass: rendering, streaming, audio and stability

Date: 2026-09-20

## Objective

Keep adding visual ambition without letting optional effects become a source of
crashes, memory pressure, shader stutter or device-specific black screens.

## Capability negotiation

The engine now plans renderer features from detected capabilities instead of
assuming a modern flagship.

The preferred path is Android 10+ and Vulkan 1.1+. If that baseline is not
available, the plan can select a future OpenGL ES 3 compatibility renderer
rather than attempting unsupported Vulkan features.

Optional features are individually gated:

- FP16 arithmetic
- timeline semaphores
- dynamic rendering
- descriptor indexing
- memory-budget telemetry
- present timing
- async compute
- ray query

Ray query remains experimental and opt-in even when hardware reports support.

Android's native-engine guidance recommends Android 10+, Vulkan 1.1+ and the
Android Baseline profile as a sensible minimum Vulkan target.

Reference:
https://developer.android.com/games/develop/vulkan/native-engine-support

## Texture compression

ASTC is preferred, ETC2 is fallback, RGBA8 is last resort. Android recommends
ASTC as the primary modern texture compression option and ETC2 as a widely
supported fallback.

Reference:
https://developer.android.com/games/optimize/textures

The runtime plan also reduces texture budgets when uncompressed fallback is
necessary.

## Pipeline and descriptor stability

Xziel will never intentionally compile a graphics/compute pipeline in the hot
draw path. Known pipelines are created/prewarmed and stored in a persistent
pipeline cache.

Khronos shows that pipeline cache can more than halve pipeline recreation time
in its mobile sample and warns that draw-time pipeline creation causes frame
stutters.

Reference:
https://github.khronos.org/Vulkan-Site/samples/latest/samples/performance/pipeline_cache/README.html

Descriptor sets are also cached/reused. Khronos notes that repeated descriptor
allocation/update can cost more CPU time than the draws themselves on mobile.

Reference:
https://github.khronos.org/Vulkan-Site/samples/latest/samples/performance/descriptor_management/README.html

## Streaming/residency

ResidencyManager is a bounded resource registry that tracks:

- textures
- meshes
- audio banks
- resident bytes
- last-used frame
- pinned resources

Eviction planning writes into caller-owned memory and selects stale unpinned
resources until a requested byte target is met.

The Vulkan layer will combine this with real heap telemetry when
VK_EXT_memory_budget is available.

No streaming failure may invalidate a live gameplay object. The visible object
must retain a low-LOD/fallback material/placeholder until replacement content
is resident.

## Decals

Bullet holes, blood, scorch marks, wet footprints, mud and slime use a bounded
DecalPool.

When the pool fills, old non-persistent marks are recycled. Authored persistent
marks are protected when possible. This keeps long zombie sessions from
accumulating an unbounded number of blood/bullet decals.

## Post processing

PostProcessPlanner keeps horror presentation subtle and quality-aware:

- exposure
- bloom
- vignette
- film grain
- tiny chromatic aberration
- color grading
- sharpening
- ambient occlusion
- volumetric fog

Temporal history is invalidated after camera cuts/teleports instead of blending
stale history and producing giant smears/ghosts.

Global motion blur is intentionally not part of the baseline. Fast first-person
movement plus mobile touch input makes excessive blur both unpleasant and
expensive.

## Spatial horror audio

AudioScenePlanner prioritizes a bounded number of voices. Player weapon/UI/
horror stingers and nearby zombie threats outrank distant ambience.

Occlusion reduces gain and applies a low-pass target; reverb-zone send is
separate. Looping sources can be virtualized instead of destroyed, allowing
them to resume without losing timeline state.

The future mixer will use Oboe/AAudio low latency. Android explicitly recommends
callbacks and avoiding blocking work/allocations inside the real-time audio
callback.

Reference:
https://developer.android.com/games/sdk/oboe/low-latency-audio

## Sustained mobile performance

The goal is not a screenshot that runs at 14 FPS. It is a horror scene that can
remain stable for a full Zombies session.

Android recommends Swappy/frame pacing and ADPF to handle heterogeneous display,
CPU/GPU and thermal behavior.

References:
https://developer.android.com/games/sdk/frame-pacing
https://developer.android.com/games/optimize/adpf

The engine's degradation order remains presentation-first:

1. lower reflection/SSR/fog/post resolution
2. reduce particle density and shadow distance
3. reduce dynamic/shadowed light budgets
4. reduce scene render scale
5. preserve movement, shooting, AI tick and hit registration

## Vulkan synchronization rule

The renderer will not rely on incidental blocking behavior from
vkAcquireNextImageKHR/vkQueuePresentKHR. Android's native-engine guidance warns
that behavior differs across devices/drivers and recommends explicit semaphores,
fences and barriers.

Reference:
https://developer.android.com/games/develop/vulkan/native-engine-support

## Memory allocation rule

Khronos recommends pooling/suballocation rather than many small GPU allocations
on mobile. Xziel therefore targets large Vulkan memory blocks with suballocation
and transient attachment reuse rather than allocating/freeing images/buffers in
the frame loop.

Reference:
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Mobile_Development/03_performance_optimizations.html

## Definition of "ready"

A subsystem is not considered ready merely because it compiles.

For each engine feature we require:

- host unit/smoke tests
- no unbounded allocations or work in hot paths
- safe fallback path
- device capability gate where needed
- explicit memory/frame budget
- Android real-device test before becoming a default
- long-session test before release

This is intentionally stricter than the current legacy reference APK. The new
engine is being built to survive the part after the first impressive screenshot.
