# Xziel Mobile Renderer Clean-Room Roadmap

This document records the public mobile-engine architecture being adapted into
Xziel. It is a clean-room implementation guide: no proprietary Call of Duty
Mobile / TiMi code or assets are used.

## Public reference model

- Samsung / TiMi Call of Duty Mobile Adaptive Performance case study:
  CPU/GPU bottleneck detection, thermal stages, shadow-distance scaling,
  foliage LOD, animation update LOD and target-FPS control.
  https://developer.samsung.com/galaxy-gamedev/gamedev-blog/cod.html
- Android ADPF, Thermal Headroom, Performance Hint, Game Mode and Game State:
  https://developer.android.com/games/optimize/adpf
- Android Frame Pacing / Swappy:
  https://developer.android.com/games/sdk/frame-pacing
- Android texture guidance (ASTC primary, ETC2 fallback):
  https://developer.android.com/games/optimize/textures
- Filament PBR reference for efficient mobile material/lighting design:
  https://google.github.io/filament/main/filament.html
- Godot Forward Mobile architecture:
  https://docs.godotengine.org/en/stable/engine_details/architecture/internal_rendering_architecture.html

## Phase A — measurement and sustainable performance

Status: active.

- Real Vulkan GPU timestamp timing.
- Real CPU render submission timing.
- Thermal status plus predicted thermal headroom.
- Android 16 CPU/GPU headroom when available.
- Android Game Mode (Standard / Performance / Battery).
- GPU capability profile: ASTC, MSAA, anisotropy, texture dimension, memory.
- Transient/lazy depth on tile-based GPUs.
- Stable swapchain policy: OUT_OF_DATE recreates; persistent SUBOPTIMAL does
  not rebuild unchanged pipelines continuously.
- Delayed Swappy activation after healthy first frames; software Vulkan skips.
- Game State publication for loading/gameplay.

Acceptance: no swapchain recreation loop, stable frame pacing, telemetry
identifies CPU/GPU/thermal pressure instead of guessing.

## Phase B — real adaptive workload controls

- Classify CPU-bound, GPU-bound, frame-rate-bound and thermal-bound states.
- Independent hysteresis so quality does not oscillate.
- GPU pressure controls scene resolution, expensive post/volumetrics,
  reflection quality and GPU-heavy LOD.
- CPU pressure controls draw/visibility work, animation update rate, shadow
  submission distance and streaming work.
- Thermal pressure first removes optional work, then caps FPS only when needed.
- All RenderWorkload fields must have a real backend consumer. No policy-only
  knobs are allowed.

## Phase C — scene render graph, dynamic resolution and AA

- Split world scene from native-resolution HUD.
- Render world into a scalable offscreen scene target.
- Composite/upscale to the native swapchain; HUD remains sharp.
- Use transient MSAA color/depth where supported and resolve on-chip.
- Select 1x/2x/4x by device tier and measured GPU headroom.
- Quantize dynamic resolution to stable steps and avoid per-frame allocation.
- Migrate depth to reverse-Z when the scene pass architecture is stable.

## Phase D — mobile PBR material system

XZSM material generation must support:
- base color (sRGB)
- normal (linear)
- packed AO / roughness / metallic (linear)
- emissive
- alpha mode / double-sided flag
- baked-photogrammetry legacy/unlit mode

Lighting target:
- linear/HDR scene lighting
- Cook-Torrance style metallic/roughness PBR
- image-based lighting / reflection probes
- tone mapping + exposure
- cheap specular anti-aliasing
- mobile-forward light limits rather than desktop clustered assumptions

The current Sanctum baked photogrammetry can remain legacy/unlit while authored
materials progressively move to PBR.

## Phase E — texture memory and streaming

- ASTC primary GPU format, ETC2/RGBA compatibility fallback.
- KTX2 or equivalent precompressed container; no PNG->RGBA expansion for
  shipping high-resolution world textures.
- Preserve mip chains and anisotropic filtering.
- Residency budget tied to RuntimePolicy.textureBudgetScale.
- Async IO/decode/upload with bounded staging rings.
- Distance/projected-size mip residency and eviction.
- No synchronous queue-idle uploads during normal gameplay.

## Phase F — geometry visibility and draw efficiency

- Validate/fix mesh winding before enabling back-face culling on imported scans.
- Static LOD/HLOD generated offline.
- Per-batch projected-size LOD.
- Instance repeated props and enemies.
- Occlusion/HZB after frustum + LOD are proven.
- Mesh residency budget tied to RuntimePolicy.meshBudgetScale.
- Track visible batches, submitted triangles and draw calls each frame.

## Phase G — lighting, shadows and reflections

- Forward-mobile single-pass lighting budget.
- Prefer baked/IBL for static church lighting.
- Strict small budget for shadow-casting dynamic lights.
- Shadow distance/resolution/update rate react independently to CPU/GPU state.
- Reflection probes are default; planar reflections only for authored,
  high-importance surfaces.
- Never run prototype reflection passes in production maps.

## Phase H — characters, zombies and animation

- True skinned/rigged character path.
- Animation LOD: full-rate nearby combat, reduced matrix update rate at distance.
- GPU/CPU skinning choice by device tier and measured bottleneck.
- Instanced materials/meshes for hordes.
- Visibility, ragdoll and audio updates use importance/distance budgets.

## Phase I — loading, memory, audio and platform integration

- Game State loading/gameplay signals.
- Performance Hint session for periodic render/game work.
- Async package/asset loading.
- Memory-pressure-driven residency reduction.
- Spatial audio voices budgeted by distance/importance.
- Long-session thermal soak tests, not only first-frame tests.

## Phase J — real-device acceptance

CI software Vulkan proves correctness only. Shipping performance gates require
representative Adreno and Mali hardware with Android GPU Inspector / Perfetto.

Record for every device tier:
- p50/p95 CPU render ms
- p50/p95 GPU frame ms
- FPS/frame pacing
- thermal headroom trend
- resolution scale
- visible batches/triangles/draw calls
- texture/mesh residency
- peak device-local memory
- 15/30 minute sustained temperature and throttling behavior

Visual acceptance is compared at the same camera, resolution, lighting and
quality tier so “faster” never hides a fidelity regression.
