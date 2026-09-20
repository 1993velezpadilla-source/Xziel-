# Xziel Engine research — mobile FPS modernization

Date: 2026-09-20

## What Call of Duty: Mobile actually uses

Call of Duty: Mobile is not an Android build of the console IW engine. Public
Activision material states that the title was developed by Tencent/TiMi using
the Unity real-time 3D development platform. Unity also recognized the title in
the 2019 Unity Awards. Samsung published a technical collaboration with TiMi J3
showing Call of Duty: Mobile using Unity Adaptive Performance for stable frame
rate and thermal/power management.

Primary references:

- Activision announcement:
  https://investor.activisionblizzard.com/news-releases/news-release-details/call-duty-mobile-revealed
- Activision development article:
  https://blog.activision.com/uk/en/call-of-duty/2019-03/Announcing-Call-of-Duty-Mobile-coming-to-the-west-on-Android-and-iOS
- Unity Awards 2019:
  https://unity.com/awards/2019
- Samsung adaptive performance case:
  https://developer.samsung.com/galaxy-gamedev/gamedev-blog/cod.html

## Why we are not placing Unity "on top of Quake"

That would solve the wrong problem.

1. Unity is a licensed proprietary engine. Using it would not make the engine
   ours.
2. The current Vril engine is GPL-2.0. Combining proprietary engine technology
   and GPL code into one distributed work creates avoidable licensing
   complexity.
3. Unity's current terms restrict reverse engineering and certain combinations
   that would cause Unity technology to become subject to copyleft terms.
4. Copying or decompiling COD Mobile/Unity internals would defeat the goal of a
   clean engine whose provenance can be defended.

Instead, COD Mobile is treated as a behavior/quality reference: low-latency
touch input, gyro, frame pacing, weapon feel, animation responsiveness,
adaptive quality, and mobile-first UX.

## Target: Xziel Engine

A new native engine is developed beside the legacy APK. The old build is used
as a visual/gameplay regression reference until the replacement can run the
same scenarios without Vril/Quake code.

### Phase 0 — foundation (started)

- Standalone C++20 engine core.
- Fixed 120 Hz simulation step.
- Input snapshots.
- Deterministic timing smoke test.
- No Vril, Quake, Unity or COD Mobile source dependency.

### Phase 1 — Android platform layer

Use Android GameActivity rather than inheriting the long-term architecture from
SDLActivity. Keep Java/Kotlin glue tiny and gameplay native.

Targets:

- API/lifecycle correctness.
- Surface creation/destruction.
- Multi-touch pointer tracking.
- Gyroscope at the highest sustainable sensor rate.
- Controller input.
- 60/90/120 Hz display selection.
- 16 KB page-size compatibility.
- Suspend/resume without simulation explosions.

Android reference:
https://developer.android.com/games/agdk/game-activity/get-started

### Phase 2 — frame pacing and performance governor

Integrate Android Frame Pacing (Swappy) and later ADPF/performance hints.

Targets:

- Stable 60/90/120 FPS modes.
- No short-frame/long-frame cadence.
- Thermal-aware quality scaling.
- Dynamic resolution and quality tiers.
- CPU/GPU frame-time telemetry.

References:

- https://developer.android.com/games/sdk/frame-pacing
- https://developer.android.com/games/optimize/overview

### Phase 3 — renderer

Vulkan-first renderer. OpenGL ES is retained only as a compatibility route
during migration.

Android now documents Vulkan as its primary low-level graphics API and notes
that OpenGL ES is no longer under active feature development.

Reference:
https://developer.android.com/games/develop/vulkan/overview

Initial renderer capabilities:

- Forward+/clustered mobile lighting.
- GPU instancing for zombie crowds.
- Texture streaming.
- KTX2/Basis-style compressed texture path.
- Occlusion/frustum culling.
- Shadow quality tiers.
- Static light baking support.
- Screen-space effects only when the device budget allows.
- Render scale independent of HUD resolution.

A renderer abstraction must make it possible to use a permissive backend such
as bgfx during bootstrap or replace it later with a fully first-party Vulkan
backend.

### Phase 4 — legacy map bridge without legacy engine code

Do not execute Vril rendering code in the new engine.

Build an offline importer that reads legal legacy map/content formats and
converts them into an Xziel native package:

- geometry
- collision
- spawn points
- triggers
- doors
- lights
- entities
- navigation seed data

The importer is the compatibility boundary. Runtime code stays independent.

### Phase 5 — movement and camera

Recreate the already validated Android feel from behavior and tests, not copied
legacy implementation:

- walk/sprint
- crouch
- slide
- jump
- stair stepping
- slope handling
- ADS walk speed
- per-weapon sensitivity multipliers
- touch acceleration/dead zones
- gyro ADS/non-ADS scaling
- camera bob/recoil/viewmodel inertia

Golden tests compare recorded input traces and resulting transforms against the
desired feel.

### Phase 6 — animation

Use a modern skeletal animation graph:

- locomotion blend space
- additive hit reactions
- upper/lower-body layering
- zombie stagger/flinch/death transitions
- viewmodel sprint/slide/reload/fire states
- animation events for muzzle flash, shell ejection and footsteps

A permissive library such as ozz-animation can bootstrap runtime animation
while preserving the ability to replace it later.

### Phase 7 — physics, AI and navigation

Potential permissive bootstrap components:

- Jolt Physics (MIT) for rigid bodies/collision.
- Recast/Detour (zlib) for navigation meshes.
- EnTT (MIT) for ECS-style entity storage.

Zombie AI stays game-specific and first-party: perception, path requests,
attack windows, crowd separation and round-state behavior.

### Phase 8 — audio

Native low-latency audio, with first-party spatial/mixing rules. miniaudio is a
possible permissive bootstrap layer and supports AAudio on modern Android.

Targets:

- 3D emitters
- voice limits/priorities
- occlusion/reverb sends
- weapon tails by environment
- deterministic gameplay cues independent of audio frame size

### Phase 9 — networking

Design for both local and internet co-op from the start:

- server-authoritative game state
- input commands rather than raw transforms
- snapshot/interpolation path
- client prediction for player movement
- lag compensation where appropriate
- LAN discovery over Wi-Fi/hotspot
- online transport that does not require a dedicated server for friend-hosted
  sessions, while retaining a dedicated-server path later

Networking is engine-owned rather than copied from COD Mobile.

### Phase 10 — content independence

Every asset must have a provenance record.

Allowed categories for the public build:

- original Xziel-created content
- CC0/public-domain assets
- permissively licensed assets
- assets with explicit redistribution/modification permission
- NZ:P assets only while intentionally honoring their existing license

Do not ship ripped Call of Duty content merely because the game is free.

## Dependency policy for the new engine

Preferred bootstrap dependencies are permissive and replaceable:

- bgfx — BSD-2-Clause renderer abstraction
- Jolt Physics — MIT
- ozz-animation — MIT
- EnTT — MIT
- Recast/Detour — zlib
- meshoptimizer — MIT
- miniaudio — public domain or MIT-0

Each dependency remains owned by its authors. "Our engine" means Xziel owns the
original engine architecture and code, not that third-party copyright notices
disappear.

## Migration rule

Do not touch the current working APK while a release iteration is being
validated. New-engine work happens on a separate branch and separate build
target until it can pass the same gameplay smoke tests.

The first milestone is not visual parity. It is:

1. boot native Android surface;
2. receive touch + gyro;
3. run fixed simulation;
4. draw a test world at stable frame pacing;
5. move a first-person controller;
6. load a converted legacy test room;
7. fire a test weapon;
8. spawn one simple AI target.

After that, migrate Nacht der Untoten as the first complete vertical slice.
