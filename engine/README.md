# Xziel Engine

This directory is the start of a new first-party engine track for the Android
project.

## Important boundary

This code is intentionally **not copied from Call of Duty: Mobile, Unity, Vril,
Quake, QuakeC, or decompiled binaries**. It is a clean-room implementation
based on documented platform APIs, public behavior, and Xziel's own gameplay
requirements.

The existing NZ:P/Vril APK remains the reference implementation while the new
engine becomes capable enough to replace it subsystem by subsystem.

Nothing in this directory is linked into the shipping Vril-based APK yet.

## Phase 0 implemented

- C++20 standalone static library.
- Deterministic fixed-step simulation clock.
- Bounded catch-up after stalls/resume.
- Renderer-independent input snapshot including touch-style move/look and gyro.
- Host smoke test proving 60 rendered frames at 60 Hz produce 120 simulation
  ticks at a 120 Hz fixed simulation rate.

## Planned service split

- Platform: Android GameActivity, lifecycle, storage, display/refresh handling.
- Input: multi-touch HUD, gyro, controller, remapping, sensitivity curves.
- Renderer: Vulkan-first, with a compatibility fallback path.
- Frame pacing: Android Frame Pacing / Swappy.
- Audio: low-latency native Android audio.
- Physics: deterministic character movement, collision, crouch/slide/step logic.
- Animation: skeletal player/zombie/viewmodel animation and blending.
- Gameplay: weapon state machines, rounds, perks, interactions and AI.
- Networking: LAN/online co-op with server-authoritative simulation.
- Content: a legal asset pipeline with explicit provenance and licenses.

## Ownership goal

Original Xziel Engine code can be kept under a license chosen by the project
owner. Any third-party libraries introduced later must remain under their own
licenses and must be tracked in a third-party manifest.

The current GPL/CC-BY-SA NZ:P code and assets remain a separate legacy track
until they are replaced or intentionally distributed under their existing
license obligations.
