# Xziel Engine — sustained runtime hardening II

Date: 2026-09-20

## Goal

Keep the horror intense while making long sessions predictable on a wide range
of Android devices.

This pass adds four engine-level systems:

- semantic haptics
- frame-time telemetry
- game-mode/memory-pressure runtime policy
- fixed lock-free single-producer/single-consumer command queues

## Haptics

Android's current haptics guidance emphasizes clear/rich feedback and warns
against gratuitous long buzzy vibration. It also exposes feature checks for
amplitude control, composition primitives and newer envelope effects.

References:
https://developer.android.com/develop/ui/views/haptics/haptics-principles
https://developer.android.com/develop/ui/views/haptics/haptics-apis

Xziel therefore emits semantic events rather than raw motor waveforms:

- gun fire
- reload mechanics
- player hit
- zombie grab
- nearby explosion
- slide/mantle impact
- heartbeat
- horror stinger
- UI feedback

The Android backend chooses the richest supported implementation. Unsupported
rich effects fall back to a clear predefined effect rather than a long buzzy
waveform.

Rapid events have minimum-gap suppression. An automatic weapon cannot turn the
phone into a permanently vibrating block.

## Frame-time telemetry

Average FPS is insufficient for judging a horror/FPS game. A session can average
60 while repeatedly producing 30–50 ms hitches.

FrameTelemetry keeps a fixed 240-sample ring and reports:

- average frame time
- p95
- p99
- maximum
- hitch count/ratio
- likely CPU-bound or GPU-bound state

The data can feed diagnostics, auto-quality tuning and future on-device
benchmarking.

Android Vitals also evaluates slow game sessions using frame presentation timing;
Android documents SurfaceFlinger timestats as one way to inspect actual
present-to-present behavior.

Reference:
https://developer.android.com/topic/performance/vitals/slow-session

## High refresh rates

Android 15 defaults games to 60 Hz unless they explicitly request higher frame
rates using the Frame Rate API or Swappy. The platform may still override the
request because of battery or temperature.

Reference:
https://developer.android.com/games/optimize/display-refresh-rate-change

RuntimePolicyPlanner therefore treats 90/120 Hz as a request, never an
assumption.

## Game Mode

Android exposes Standard, Performance and Battery-oriented game modes on
supported devices. Google recommends adjusting fidelity/frame-rate targets
according to the selected mode.

Reference:
https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api

Xziel maps those modes into preferred FPS and maximum presentation quality.
Gameplay simulation remains independent.

## Memory pressure

Android's Memory Advice API is now deprecated, so Xziel will NOT add it as a new
dependency. Current Android guidance instead emphasizes profiling and platform
memory-pressure/lifecycle signals such as onTrimMemory alongside system tools.

References:
https://developer.android.com/games/optimize/memory-overview
https://developer.android.com/games/sdk/memory-advice/start

The engine receives a generic Normal/Elevated/Critical memory-pressure signal.
Platform glue can derive it from current recommended APIs without coupling the
core to a deprecated library.

Memory pressure scales texture/mesh/audio budgets and places a maximum visual
quality ceiling. It never changes hit detection, AI logic or movement.

## Game State API

Android also provides Game State API so a game can tell the platform whether it
is loading or in uninterrupted gameplay, allowing resource/power decisions to
be better informed.

Reference:
https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api

This will be connected in the GameActivity platform layer once real Android
runtime integration begins.

## SPSC command queues

Cross-thread renderer/audio commands now have a reusable fixed-capacity SPSC
queue template:

- no locks
- no allocations
- no blocking
- explicit overflow result
- release/acquire ordering
- cache-line separation for head/tail atomics

This is appropriate for single-owner producer/consumer paths such as a game
thread feeding a render or audio-control thread. Multi-producer work will use a
different bounded primitive rather than abusing SPSC semantics.

## Tile GPU reminder

Current Khronos mobile/TBR guidance emphasizes keeping attachment data on-chip,
using proper load/store ops, transient attachments, precise barriers and avoiding
unnecessary main-memory round trips.

References:
https://github.khronos.org/Vulkan-Site/guide/latest/tile_based_rendering_best_practices.html
https://github.khronos.org/Vulkan-Site/tutorial/latest/Building_a_Simple_Engine/Mobile_Development/04_rendering_approaches.html

The frame graph introduced in the previous pass is the control point where those
attachment lifetime and synchronization rules will be applied in the real
Vulkan backend.
